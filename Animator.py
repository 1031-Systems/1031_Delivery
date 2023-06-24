#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program Animator.py
# Created by john
# Created Tue Jun 13 17:35:31 PDT 2023
#*********************************/

#/* Import block */
import os
import shutil
import re
import math
import wave
import struct
import sys
from io import StringIO

# Utilize XML to read/write animatronics files
import xml.etree.ElementTree as ET

try:
    # Qt import block for all widgets
    from PyQt5.QtCore import (QByteArray, QDate, QDateTime, QDir, QEvent, QPoint,
        QRect, QRegularExpression, QSettings, QSize, QTime, QTimer, Qt, pyqtSlot, QUrl)
    from PyQt5.QtGui import (QBrush, QColor, QIcon, QIntValidator, QPen,
        QDoubleValidator, QRegularExpressionValidator, QValidator, 
        QStandardItem, QStandardItemModel, QFont)
    from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication,
        QCheckBox, QComboBox, QFileDialog, QDialog, QDialogButtonBox, QGridLayout,
        QGroupBox, QHeaderView, QInputDialog, QItemDelegate, QLabel, QLineEdit, QListView,
        QMainWindow, QMessageBox, QScrollArea, QStyle, QSpinBox, QStyleOptionViewItem,
        QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
        QHBoxLayout, QWidget, QPushButton, QTextEdit, QFormLayout, QTextBrowser,
        QErrorMessage, QMenu)
    from PyQt5 import QtMultimedia as qm
except:
    try:
        # Qt import block for all widgets
        from PyQt6.QtCore import (QByteArray, QDate, QDateTime, QDir, QEvent, QPoint,
            QRect, QRegularExpression, QSettings, QSize, QTime, QTimer, Qt, pyqtSlot, QUrl)
        from PyQt6.QtGui import (QBrush, QColor, QIcon, QIntValidator, QPen,
            QDoubleValidator, QRegularExpressionValidator, QValidator, 
            QStandardItem, QStandardItemModel, QAction)
        from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
            QCheckBox, QComboBox, QFileDialog, QDialog, QDialogButtonBox, QGridLayout,
            QGroupBox, QHeaderView, QInputDialog, QItemDelegate, QLabel, QLineEdit, QListView,
            QMainWindow, QMessageBox, QScrollArea, QStyle, QSpinBox, QStyleOptionViewItem,
            QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
            QHBoxLayout, QWidget, QPushButton, QTextEdit, QFormLayout, QTextBrowser,
            QErrorMessage, QMenu)
        from PyQt6 import QtMultimedia as qm
    except:
        print('Whoops - Unable to find PyQt5 or PyQt6 - Quitting')
        exit(10)
import qwt


#/* Define block */
verbosity = False

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose]\n" % name);
    sys.stderr.write("Enter purpose here.\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("\n\n");

#####################################################################
class TextDisplayDialog(QDialog):

    def __init__(self,
        name,
        text,
        parent=None,
        ):
        super(TextDisplayDialog, self).__init__(parent)

        self.name = name
        self.textView = QTextBrowser(self)
        self.textView.setPlainText(text)
        self.textView.setReadOnly(True)

        layout = QFormLayout()
        self.setLayout(layout)
        layout.addRow(self.textView)
        
#####################################################################
class ChecklistDialog(QDialog):

    def __init__(self,
        name,
        stringlist=None,
        checked=False,
        icon=None,
        parent=None,
        ):
        super(ChecklistDialog, self).__init__(parent)

        self.name = name
        self.icon = icon
        self.model = QStandardItemModel()
        self.listView = QListView()

        for string in stringlist:
            item = QStandardItem(string)
            item.setCheckable(True)
            check = \
                (Qt.Checked if checked else Qt.Unchecked)
            item.setCheckState(check)
            self.model.appendRow(item)

        self.listView.setModel(self.model)

        self.okButton = QPushButton('OK')
        self.cancelButton = QPushButton('Cancel')
        self.selectButton = QPushButton('Select All')
        self.unselectButton = QPushButton('Unselect All')

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)
        hbox.addWidget(self.selectButton)
        hbox.addWidget(self.unselectButton)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.listView)
        vbox.addStretch(1)
        vbox.addLayout(hbox)

        self.setWindowTitle(self.name)
        if self.icon:
            self.setWindowIcon(self.icon)

        self.okButton.clicked.connect(self.onAccepted)
        self.cancelButton.clicked.connect(self.reject)
        self.selectButton.clicked.connect(self.select)
        self.unselectButton.clicked.connect(self.unselect)

    def setStates(self, checklist):
        for i in range(min(len(checklist), self.model.rowCount())):
            self.model.item(i).setCheckState(checklist[i])

    def onAccepted(self):
        self.choices = [self.model.item(i).text() for i in
                        range(self.model.rowCount())
                        if self.model.item(i).checkState()
                        == Qt.Checked]
        self.accept()

    def select(self):
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            item.setCheckState(Qt.Checked)

    def unselect(self):
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            item.setCheckState(Qt.Unchecked)


#####################################################################
# The ChannelPane class represents the display widget for a
# single channel.
#####################################################################
class ChannelPane(qwt.QwtPlot):
    Y_LEFT_AXIS_ID = 0
    Y_RIGHT_AXIS_ID = 1
    X_BOTTOM_AXIS_ID = 2
    X_TOP_AXIS_ID = 3
    BoxSize = 10

    class ChannelMenu(QMenu):
        """The popup widget for an individual channel pane"""
        def __init__(self, parent, channel):
            super().__init__(parent)
            self.parent = parent
            self.channel = channel
            self.name = channel.name

            # Make the font daintier for this popup menu
            smallfont = QFont()
            smallfont.setPointSize(6)
            self.setFont(smallfont)

            # metadata menu item
            self._metadata_action = QAction("metadata", self,
                triggered=self.metadata_action)
            self.addAction(self._metadata_action)

            # invert menu item
            self._invert_action = QAction("invert", self,
                triggered=self.invert_action)
            self.addAction(self._invert_action)

            # smooth menu item only for Linear channels
            if self.channel.type == self.channel.Linear:
                self._smooth_action = QAction("smooth", self,
                    triggered=self.smooth_action)
                self.addAction(self._smooth_action)

            # wrap menu item
            self._wrap_action = QAction("wrap", self,
                triggered=self.wrap_action)
            self.addAction(self._wrap_action)

            # copy menu item
            self._copy_action = QAction("copy", self,
                shortcut="Ctrl+C",
                triggered=self.copy_action)
            self.addAction(self._copy_action)

            # paste menu item
            self._paste_action = QAction("paste", self,
                shortcut="Ctrl+V",
                triggered=self.paste_action)
            self.addAction(self._paste_action)

            # Rescale menu item
            self._Rescale_action = QAction("Rescale", self,
                triggered=self.Rescale_action)
            self.addAction(self._Rescale_action)

            # Hide menu item
            self._Hide_action = QAction("Hide", self,
                triggered=self.Hide_action)
            self.addAction(self._Hide_action)

            # Delete menu item
            self.addSeparator()
            self._Delete_action = QAction("Delete", self,
                triggered=self.Delete_action)
            self.addAction(self._Delete_action)

            self.hide()

        def metadata_action(self):
            """ Perform metadata action"""
            pass

        def invert_action(self):
            """ Perform invert action"""
            pass

        def smooth_action(self):
            """ Perform smooth action"""
            pass

        def wrap_action(self):
            """ Perform wrap action"""
            pass

        def copy_action(self):
            """ Perform copy action"""
            pass

        def paste_action(self):
            """ Perform paste action"""
            pass

        def Rescale_action(self):
            """ Perform Rescale action"""
            self.parent.resetDataRange()
            pass

        def Hide_action(self):
            """ Perform Hide action"""
            self.parent.hidePane()
            pass

        def Delete_action(self):
            """ Perform Delete action"""
            if self.parent.holder is not None:
                self.parent.holder.deleteChannels([self.name])
            pass

    def __init__(self, parent=None, inchannel=None, mainwindow=None):
        super().__init__(parent)

        self.parent = parent
        self.channel = inchannel
        self.holder = mainwindow
        self.curve = None

        # Set initial values to avoid dta race
        self.minTime = 0.0
        self.maxTime = 1.0
        self.minVal = -1.0
        self.maxVal = 1.0
        self.xoffset = 0
        self.yoffset = 0
        self.selectedKey= None
        self.settimerange(0.0, 100.0)
        self.setDataRange(-1.0, 1.0)
        self.setAxisTitle(self.Y_LEFT_AXIS_ID, self.channel.name)

        self.create()
    
    def settimerange(self, mintime, maxtime):
        self.minTime = mintime
        self.maxTime = maxtime
        self.setAxisScale(self.X_BOTTOM_AXIS_ID, self.minTime, self.maxTime)
        self.replot()

    def setDataRange(self, minval, maxval):
        self.minVal = minval
        self.maxVal = maxval
        self.setAxisScale(self.Y_LEFT_AXIS_ID, self.minVal, self.maxVal)
        self.replot()

    def resetDataRange(self):
        self.minVal = 1.0e34
        self.maxVal = -1.0e34
        for keyval in self.channel.knots:
            if self.channel.knots[keyval] < self.minVal: self.minVal = self.channel.knots[keyval]
            if self.channel.knots[keyval] > self.maxVal: self.maxVal = self.channel.knots[keyval]
        if self.minVal == self.maxVal:
            margin = 0.5
        else:
            margin = 0.05 * (self.maxVal - self.minVal)
        self.setDataRange(self.minVal - margin, self.maxVal + margin)

    def getTimeRange(self):
        minVal = 1.0e34
        maxVal = -1.0e34
        for keyval in self.channel.knots:
            if keyval < minVal: minVal = keyval
            if keyval > maxVal: maxVal = keyval
        return minVal, maxVal

    def setOffsets(self):
        # Compute axis offset from size of anything displayed at top
        rect = self.plotLayout().scaleRect(self.X_TOP_AXIS_ID)
        self.yoffset = rect.height()
        # Compute axis offset
        rect = self.plotLayout().scaleRect(self.Y_LEFT_AXIS_ID)
        self.xoffset = rect.width()

    def hidePane(self):
        self.hide()

    def create(self):
        """Create all the widget stuff for the channel plot"""
        grid = qwt.QwtPlotGrid()
        grid.enableXMin(True)
        grid.attach(self)
        grid.setPen(QPen(Qt.black, 0, Qt.DotLine))

        # Create the data plot
        xdata = sorted(self.channel.knots)
        ydata = [self.channel.knots[key] for key in xdata]
        self.curve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=ydata, plot=self,
            symbol=qwt.symbol.QwtSymbol(qwt.symbol.QwtSymbol.Rect,
                QBrush(), QPen(Qt.green), QSize(self.BoxSize, self.BoxSize))
        )
        if len(ydata) <= 0:
            self.setDataRange(0.0, 1.0)
        else:
            self.resetDataRange()

        # Create red bar for audio sync
        self.timeSlider = qwt.QwtPlotCurve()
        self.timeSlider.setStyle(qwt.QwtPlotCurve.Sticks)
        self.timeSlider.setData([0.0], [30000.0])
        self.timeSlider.setPen(Qt.red, 3.0, Qt.SolidLine)
        self.timeSlider.setBaseline(-30000.0)
        self.timeSlider.attach(self)

        # Create the popup menu
        self.popup = self.ChannelMenu(self, self.channel)

        pass

    def findClosestPointWithinBox(self, i,j):
        """Finds the nearest plot point within BoxSize of mouse click"""
        for keyval in self.channel.knots:
            pnti = self.transform(self.X_BOTTOM_AXIS_ID, keyval) + self.xoffset
            pntj = self.transform(self.Y_LEFT_AXIS_ID, self.channel.knots[keyval]) + self.yoffset
            if abs(i-pnti) <= self.BoxSize/2 and abs(j-pntj) <= self.BoxSize/2:
                return keyval
        return None

    def getPlotValues(self, pixelX, pixelY):
        # Get the rectangle containing the stuff to left of plot
        rect = self.audioPlot.plotLayout().scaleRect(self.Y_LEFT_AXIS_ID)
        # Get the width of that rectangle to use as offset in X
        xoffset = rect.width()
        valueX = self.audioPlot.invTransform(self.X_BOTTOM_AXIS_ID, pixelX - xoffset)

        # Get the rectangle containing the stuff above top of plot
        rect = self.audioPlot.plotLayout().scaleRect(self.X_TOP_AXIS_ID)
        # Get the height of that rectangle to use as offset in Y
        yoffset = rect.height()
        valueY = self.audioPlot.invTransform(self.Y_LEFT_AXIS_ID, pixelY - yoffset)

        return valueX,valueY

    def mousePressEvent(self, event):
        self.setOffsets()
        if event.buttons() == Qt.LeftButton :
            xplotval = self.invTransform(self.X_BOTTOM_AXIS_ID, event.pos().x() - self.xoffset)
            yplotval = self.invTransform(self.Y_LEFT_AXIS_ID, event.pos().y() - self.yoffset)
            # If shift key is down then
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ShiftModifier:
                # Find nearest point
                nearkey = self.findClosestPointWithinBox(event.pos().x(), event.pos().y())
                if nearkey is not None:
                    # If close enough, select it and drag it around
                    self.selectedKey = nearkey
                else:
                    # else Insert a new point and drag it around
                    nearkey = xplotval
                    self.channel.knots[nearkey] = yplotval
                    self.selectedKey = nearkey
                    self.redrawme()
            # else, drag to adjust vertical zoom and pan of this pane
        elif event.buttons()== Qt.MiddleButton :
            # Vertical pan of pane with wheel/mouse?
            pass
        elif event.buttons()== Qt.RightButton :
            # Pop up menu for controls (Delete, Hide, etc. at the mouse click position on screen
            whereat = QPoint(event.pos().x(), event.pos().y())
            whereat = self.mapToGlobal(whereat)
            self.popup.popup(whereat)
            pass
        pass
    
    def mouseReleaseEvent(self, event):
        print('Something released')
        if self.selectedKey is not None:
            print('Left release')
            self.selectedKey = None
            self.replot()
        pass

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton :
            if self.selectedKey is not None:
                xplotval = self.invTransform(self.X_BOTTOM_AXIS_ID, event.pos().x() - self.xoffset)
                yplotval = self.invTransform(self.Y_LEFT_AXIS_ID, event.pos().y() - self.yoffset)
                del self.channel.knots[self.selectedKey]
                # Avoid overwriting existing point as we drag past
                if xplotval in self.channel.knots:
                    xplotval += 0.00000001
                self.channel.knots[xplotval] = yplotval
                self.selectedKey = xplotval
                self.redrawme()
        pass

    def setSlider(self, timeVal):
        if self.timeSlider is not None:
            self.timeSlider.setData([timeVal], [30000.0])
            self.replot()
        
    def redrawme(self):
        # Create the data plot
        xdata = sorted(self.channel.knots)
        ydata = [self.channel.knots[key] for key in xdata]
        if self.curve is not None:
            self.curve.setData(xdata, ydata)
        self.replot()

#####################################################################3
# The MetadataWidget is used to view and edit the metadata
# for the overall Animatronics file
#####################################################################3
class MetadataWidget(QDialog):
    def __init__(self, inanim, parent=None):
        super().__init__(parent)

        self.title = 'MetaData Editor'
        widget = QWidget()
        layout = QFormLayout()
        
        self._startedit = QLineEdit('0.0')
        self._startedit.setReadOnly(True)
        layout.addRow(QLabel('Start Time:'), self._startedit)
        self._endedit = QLineEdit()
        layout.addRow(QLabel('End Time:'), self._endedit)
        self._rateedit = QLineEdit('50')
        layout.addRow(QLabel('Sample Rate (Hz):'), self._rateedit)
        self._audioedit = QLineEdit('0.0')
        layout.addRow(QLabel('Audio Start Time:'), self._audioedit)
        layout.addRow(QLabel('Audio File:'))
        self._audiofile = QLineEdit('')
        if inanim.audiofile is not None:
            self._audiofile.setText(inanim.audiofile)
        self._audiofile.setReadOnly(True)
        layout.addRow(self._audiofile)
        widget.setLayout(layout)

        self.okButton = QPushButton('Save')
        self.cancelButton = QPushButton('Cancel')

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)

        vbox = QVBoxLayout(self)
        vbox.addWidget(widget)
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        self.okButton.clicked.connect(self.onAccepted)
        self.cancelButton.clicked.connect(self.reject)

    def onAccepted(self):
        self.accept()

#####################################################################3
# The MainWindow class represents the Qt main window.
#####################################################################3
class MainWindow(QMainWindow):
    Y_LEFT_AXIS_ID = 0
    Y_RIGHT_AXIS_ID = 1
    X_BOTTOM_AXIS_ID = 2
    X_TOP_AXIS_ID = 3

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create file dialog on the fly when needed
        self.filedialog = None
        # Initialize to no audio plot and add later if read
        self.audioPlot = None
        # Initialize empty list of channel plots
        self.plots = {}

        # Create all the dropdown menus
        self.create_menus()

        # Initialize some stuff
        self.setWindowTitle("Animation Editor")
        self.resize(500, 600)
        self.lastXmin = 0.0
        self.lastXmax = 1.0
        self.audioMin = 0.0
        self.audioMax = 1.0
        self.totalMin = 0.0
        self.totalMax = 1.0

        self.player = qm.QMediaPlayer()
        try:
            # This fails in PyQt6???
            self.player.setNotifyInterval(30)
        except:
            pass
        # self.player.setPlaybackRate(0.5)
        self.player.positionChanged.connect(self.positionChanged)

        # Initialize with an empty animatronics object
        self.setAnimatronics(Animatronics())

    def setAnimatronics(self, inanim):
        """Set the active animatronics to the input"""
        self.animatronics = inanim

        # Clear and recreate UI here
        # Create the bottom level widget and make it the main widget
        self._plotarea = QScrollArea(self)
        self._plotarea.setWidgetResizable(True)
        self._plotarea.setMaximumSize(3800,1000)
        self.setCentralWidget(self._plotarea)

        # Set the background color
        p = self._plotarea.palette()
        backcolor = QColor()
        backcolor.setRgb(150, 200, 250)
        p.setColor(self.backgroundRole(), backcolor)
        self._plotarea.setPalette(p)

        # Create layout to hold all the channels
        layout = QVBoxLayout(self._plotarea)
        layout.setContentsMargins(10, 10, 0, 0)

        # Remove all existing plot channels
        self.plots = {}

        if self.animatronics.audio_data is not None:
            xdata = [float(i) * self.animatronics.audio_rate + self.animatronics.start for i in range(len(self.animatronics.audio_data))]
            newplot = qwt.QwtPlot('Audio')
            qwt.QwtPlotCurve.make(xdata=xdata, ydata=self.animatronics.audio_data,
                title='Audio', plot=newplot,
                )
            layout.addWidget(newplot)
            self.audioPlot = newplot
            self.audioMin = xdata[0]
            self.audioMax = xdata[-1]
            if self.audioMax > self.totalMax: self.totalMax = self.audioMax
            self.lastXmin = self.audioMin
            self.lastXmax = self.audioMax

            # Create red bar for audio sync
            self.timeSlider = qwt.QwtPlotCurve()
            self.timeSlider.setStyle(qwt.QwtPlotCurve.Sticks)
            self.timeSlider.setData([self.audioMin], [30000.0])
            self.timeSlider.setPen(Qt.red, 3.0, Qt.SolidLine)
            self.timeSlider.setBaseline(-30000.0)
            self.timeSlider.attach(newplot)

        for channel in self.animatronics.channels:
            chan = self.animatronics.channels[channel]
            newplot = ChannelPane(self._plotarea, chan, mainwindow=self)
            newplot.setAxisScale(self.X_BOTTOM_AXIS_ID, self.lastXmin, self.lastXmax)
            layout.addWidget(newplot)
            self.plots[chan.name] = newplot
            
        # print(self.animatronics.toXML())

    def openAnimFile(self):
        """Get filename and open as active animatronics"""
        if self.filedialog is None:
            self.filedialog = QFileDialog(self)

        fileName, _ = self.filedialog.getOpenFileName(self,"Get Open Filename", "",
                            "Anim Files (*.anim);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            newAnim = Animatronics()
            try:
                newAnim.parseXML(fileName)
                self.setAnimatronics(newAnim)
    
            except Exception as e:
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return


    def newAnimFile(self):
        """Clear animatronics and start from scratch"""
        newAnim = Animatronics()
        self.setAnimatronics(newAnim)
    
    def mergeAnimFile(self):
        """Merge an animatronics file into the current one"""
        if self.filedialog is None:
            self.filedialog = QFileDialog(self)

        fileName, _ = self.filedialog.getOpenFileName(self,"Get Merge Filename", "",
                            "Anim Files (*.anim);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                self.animatronics.parseXML(fileName)
                self.setAnimatronics(self.animatronics)
    
            except Exception as e:
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return
        pass

    def saveAnimFile(self):
        """Save the current animatronics file"""
        if self.animatronics.filename is None:
            # If the filename is not set, use the forcing dialog to get it
            self.saveAsFile()
        else:
            # Write to the previously read/written file
            try:
                with open(self.animatronics.filename, 'w') as outfile:
                    outfile.write(self.animatronics.toXML())
    
            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % self.animatronics.filename)
                sys.stderr.write("Message: %s\n" % e)
                return
        pass

    def saveAsFile(self):
        """Save the current animatronics file"""
        if self.filedialog is None:
            self.filedialog = QFileDialog(self)

        self.filedialog.setDefaultSuffix('anim')
        fileName, _ = self.filedialog.getSaveFileName(self,"Get Save Filename", "",
                            "Anim Files (*.anim);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                with open(fileName, 'w') as outfile:
                    outfile.write(self.animatronics.toXML())
    
            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return

        if self.animatronics.filename is None:
            self.animatronics.filename = fileName
        pass

    def exportCSVFile(self):
        """Export the current animatronics file into a CSV format"""
        pass

    def exportVSAFile(self):
        """Export the current animatronics file into a special format"""
        pass

    def newchannel_action(self):
        """ Perform newchannel action"""
        text, ok = QInputDialog.getText(self, "Get New Channel Name",
                "Channel Name", QLineEdit.Normal)
        if ok and text:
            # Check to see if channel already exists
            ret = None
            if text in self.animatronics.channels:
                rsgBox = QMessageBox()
                msgBox.setText('The channel "%s" already exists.' % text)
                msgBox.setInformativeText("Delete all its data?")
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec()
            if ret == QMessageBox.Yes:
                del self.animatronics.channels[text]
                ret = None
            if ret is None:
                self.animatronics.channels[text] = Channel(inname = text)
                self.setAnimatronics(self.animatronics)
                
        pass

    def deleteChannels(self, chanList):
        # Confirm deletion with user
        inform_text = ''
        for name in chanList:
            if len(inform_text) > 0: inform_text += ', '
            inform_text += name
        msgBox = QMessageBox()
        msgBox.setText('Are you really sure you want to delete these channels?')
        msgBox.setInformativeText(inform_text)
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msgBox.setIcon(QMessageBox.Warning)
        ret = msgBox.exec()
        if ret == QMessageBox.Yes:
            for name in chanList:
                del self.animatronics.channels[name]
            self.setAnimatronics(self.animatronics)

    def deletechannel_action(self):
        """ Perform deletechannel action"""
        form = ChecklistDialog('Channels to Delete', self.animatronics.channels)
        if form.exec_() == QDialog.Accepted:
            if len(form.choices) <= 0:
                # Laugh at user
                qem = QErrorMessage(self)
                qem.showMessage('Whoops - No channels selected for deletion!!')
                pass
            else:
                # Delete channels with confirmation
                self.deleteChannels(form.choices)
        pass

    def selectaudio_action(self):
        """ Perform selectaudio action"""
        if self.filedialog is None:
            self.filedialog = QFileDialog(self)

        fileName, _ = self.filedialog.getOpenFileName(self,"Get Open Filename", "",
                            "Wave Audio Files (*.wav);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                self.animatronics.set_audio(fileName)
                self.setAnimatronics(self.animatronics)
    
            except Exception as e:
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return
        pass

    def editmetadata_action(self):
        """ Perform editmetadata action"""
        qd = MetadataWidget(self.animatronics, parent=self)
        qd.exec_()
        pass

    def playaudio_action(self):
        """ Perform playaudio action"""
        # Kluge to play entire audio from file
        if self.animatronics.audiofile is not None:
            try:
                # The PyQt5 way
                qm.QSound.play(self.animatronics.audiofile)
            except:
                try:
                    # The PyQt6 way
                    qse = qm.QSoundEffect()
                    qse.setSource(QUrl("file:%s" % self.animatronics.audiofile))
                    qse.play()
                except:
                    # Hope it does not get here
                    print('Whoops - no quick playback')
                    pass
        pass

    def positionChanged(self, position):
        self.setSlider(float(position)/1000.0 + self.animatronics.start)

    def setSlider(self, timeVal):
        if self.timeSlider is not None:
            self.timeSlider.setData([timeVal], [30000.0])
            self.audioPlot.replot()
        for plot in self.plots:
            self.plots[plot].setSlider(timeVal)

    def playbackcontrols_action(self):
        """ Perform playbackcontrols action"""
        # Create/open QtMediaPlayer
        try:
            # PyQt5 way
            self.player.setMedia(qm.QMediaContent(QUrl.fromLocalFile(self.animatronics.audiofile)))
            self.player.play()
        except:
            try:
                # PyQt6 way
                self.player.setSource(QUrl.fromLocalFile(self.animatronics.audiofile))
                self.player.setAudioOutput(qm.QAudioOutput(qm.QAudioDevice()))
                self.player.play()
            except:
                print('Whoops - No Audio player')
                pass
        pass

    def resetscales_action(self):
        """ Perform resetscales action"""
        # Reset all horizontal and vertical scales to max X range and local Y range
        minTime = 0.0
        maxTime = 0.0
        if self.audioPlot is not None:
            minTime = self.audioMin
            maxTime = self.audioMax
        for i in self.plots:
            lmin,lmax = self.plots[i].getTimeRange()
            if lmin < minTime: minTime = lmin
            if lmax > maxTime: maxTime = lmax

        # Actually set all the ranges
        if self.audioPlot is not None:
            self.audioPlot.setAxisScale(self.X_BOTTOM_AXIS_ID, minTime, maxTime)
            self.audioPlot.replot()
        for i in self.plots:
            self.plots[i].settimerange(minTime, maxTime)
            self.plots[i].resetDataRange()
        self.lastXmax = maxTime
        self.lastXmin = minTime
        
        pass

    def scaletoaudio_action(self):
        """ Perform scaletoaudio action"""
        # Reset all horizontal scales to audio range and vertical scales to local Y ranges
        if self.audioPlot is not None:
            self.audioPlot.setAxisScale(self.X_BOTTOM_AXIS_ID, self.audioMin, self.audioMax)
            self.audioPlot.replot()
        for i in self.plots:
            self.plots[i].settimerange(self.audioMin, self.audioMax)
        self.lastXmax = self.audioMax
        self.lastXmin = self.audioMin
        pass

    def showall_action(self):
        """ Perform showall action"""
        # Unhide all channels
        for i in self.plots:
            self.plots[i].show()
        pass

    def showselector_action(self):
        """ Perform showselector action"""
        # Pop up show/hide selector to choose visible channels
        form = ChecklistDialog('Channels to Hide', self.animatronics.channels)
        checklist = []
        for name in self.plots:
            if self.plots[name].isHidden():
                checklist.append(Qt.Checked)
            else:
                checklist.append(Qt.Unchecked)
        form.setStates(checklist)
        if form.exec_() == QDialog.Accepted:
            for name in self.animatronics.channels:
                if name in form.choices:
                    self.plots[name].hide()
                else:
                    self.plots[name].show()
        pass

    def showXML_action(self):
        """ Perform showXML action"""
        # Pop up text window containing XML to view (uneditable)
        tdd = TextDisplayDialog('XML', self.animatronics.toXML(), parent=self)
        tdd.show()
        pass

    def getPlotValues(self, pixelX, pixelY):
        # Get the rectangle containing the stuff to left of plot
        rect = self.audioPlot.plotLayout().scaleRect(self.Y_LEFT_AXIS_ID)
        # Get the width of that rectangle to use as offset in X
        xoffset = rect.width()
        valueX = self.audioPlot.invTransform(self.X_BOTTOM_AXIS_ID, pixelX - xoffset)

        # Get the rectangle containing the stuff above top of plot
        rect = self.audioPlot.plotLayout().scaleRect(self.X_TOP_AXIS_ID)
        # Get the height of that rectangle to use as offset in Y
        yoffset = rect.height()
        valueY = self.audioPlot.invTransform(self.Y_LEFT_AXIS_ID, pixelY - yoffset)

        return valueX,valueY

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.lastX = event.pos().x()
            self.lastY = event.pos().y()
            self.centerX,self.centerY = self.getPlotValues(event.pos().x(), event.pos().y())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            deltaX = self.lastX - event.pos().x()
            deltaY = self.lastY - event.pos().y()
            self.lastY = event.pos().y()
            newCenterX,_ = self.getPlotValues(event.pos().x(), event.pos().y())
            yScaler = pow(2.0, float(deltaY)/50.0)
            self.lastXmax = self.centerX + (self.lastXmax - self.centerX) / yScaler + (self.centerX - newCenterX)
            self.lastXmin = self.centerX + (self.lastXmin - self.centerX) / yScaler + (self.centerX - newCenterX)
            self.audioPlot.setAxisScale(self.X_BOTTOM_AXIS_ID, self.lastXmin, self.lastXmax)
            self.audioPlot.replot()
            for i in self.plots:
                self.plots[i].settimerange(self.lastXmin, self.lastXmax)
            
                
    def mouseReleaseEvent(self, event):
        pass


    def create_menus(self):
        """Creates all the dropdown menus for the toolbar and associated actions"""

        # Create the File dropdown menu #################################
        self.file_menu = self.menuBar().addMenu("&File")
        # New action
        self._new_file_action = QAction("&New Anim File",
                self, triggered=self.newAnimFile)
        self.file_menu.addAction(self._new_file_action)

        # Open action
        self._open_file_action = QAction("&Open Anim File",
                self, shortcut="Ctrl+O", triggered=self.openAnimFile)
        self.file_menu.addAction(self._open_file_action)

        # Merge action
        self._merge_file_action = QAction("&Merge Anim File",
                self, triggered=self.mergeAnimFile)
        self.file_menu.addAction(self._merge_file_action)

        # Save action
        self._save_file_action = QAction("&Save Anim File",
                self, shortcut="Ctrl+S", triggered=self.saveAnimFile)
        self.file_menu.addAction(self._save_file_action)

        # Save As action
        self._save_as_file_action = QAction("&Save As",
                self, triggered=self.saveAsFile)
        self.file_menu.addAction(self._save_as_file_action)

        # Export action
        self._export_file_menu = self.file_menu.addMenu("Export")
        self._export_csv_file_action = QAction("&Export to CSV",
                self, triggered=self.exportCSVFile)
        self._export_file_menu.addAction(self._export_csv_file_action)

        self._export_vsa_file_action = QAction("&Export to VSA",
                self, triggered=self.exportVSAFile)
        self._export_file_menu.addAction(self._export_vsa_file_action)

        #self._export_file_action = QAction("&Export",
        #        self, triggered=self.exportAnimFile)
        #self.file_menu.addAction(self._export_file_action)
        #self.file_menu.addMenu(self._export_file_menu)

        # exit action
        self.file_menu.addSeparator()
        self._exit_action = QAction("E&xit", self, shortcut="Ctrl+Q",
                triggered=self.close)
        self.file_menu.addAction(self._exit_action)

        # Create the Edit dropdown menu #################################
        self.edit_menu = self.menuBar().addMenu("&Edit")
        self._newchannel_action = QAction("News Cchannel", self, shortcut="Ctrl+N",
            triggered=self.newchannel_action)
        self.edit_menu.addAction(self._newchannel_action)

        self._deletechannel_action = QAction("Delete Channels", self,
            triggered=self.deletechannel_action)
        self.edit_menu.addAction(self._deletechannel_action)

        self._selectaudio_action = QAction("Select Audio", self, shortcut="Ctrl+A",
            triggered=self.selectaudio_action)
        self.edit_menu.addAction(self._selectaudio_action)

        # editmetadata menu item
        self._editmetadata_action = QAction("Edit Metadata", self,
            triggered=self.editmetadata_action)
        self.edit_menu.addAction(self._editmetadata_action)

        # Create the View dropdown menu #################################
        self.view_menu = self.menuBar().addMenu("&View")
        # resetscales menu item
        self._resetscales_action = QAction("Fit to All Data", self,
            triggered=self.resetscales_action)
        self.view_menu.addAction(self._resetscales_action)

        # scaletoaudio menu item
        self._scaletoaudio_action = QAction("Fit to Audio", self,
            shortcut="Ctrl+F",
            triggered=self.scaletoaudio_action)
        self.view_menu.addAction(self._scaletoaudio_action)

        # showall menu item
        self._showall_action = QAction("Show All Channels", self,
            triggered=self.showall_action)
        self.view_menu.addAction(self._showall_action)

        # showselector menu item
        self._showselector_action = QAction("Select Viewed Channels", self,
            triggered=self.showselector_action)
        self.view_menu.addAction(self._showselector_action)

        # showXML menu item
        self._showXML_action = QAction("Show XML", self,
            triggered=self.showXML_action)
        self.view_menu.addAction(self._showXML_action)


        # Create the Playback dropdown menu #################################
        self.playback_menu = self.menuBar().addMenu("&Playback")
        # playaudio menu item
        self._playaudio_action = QAction("Preview Audio", self,
            triggered=self.playaudio_action)
        self.playback_menu.addAction(self._playaudio_action)

        # playbackcontrols menu item
        self._playbackcontrols_action = QAction("playbackcontrols", self,
            triggered=self.playbackcontrols_action)
        self.playback_menu.addAction(self._playbackcontrols_action)


        # Create the Tools dropdown menu #################################
        self.tools_menu = self.menuBar().addMenu("&Tools")

        self.menuBar().addSeparator()

        # Create the Help dropdown menu #################################
        self.help_menu = self.menuBar().addMenu("&Help")
        # self.help_menu.addAction(self.about_action)
        # self.help_menu.addAction(self.about_Qt_action)


#####################################################################3
# The Channel class represents the information needed for doing
# animatronics with a single control channel.
#####################################################################3
class Channel:
    Linear = 1
    Spline = 2
    Step = 3

    def __init__(self, inname = '', intype = Linear):
        self.name = inname
        self.knots = {}
        self.knottitles = {}
        self.type = intype
        self.maxLimit = -1.0
        self.minLimit = 1.0
        self.port = -1
        self.rateLimit = -1.0

    def add_knot(self, key, value):
        self.knots[key] = value

    def delete_knot(self, key):
        self.knots.pop(key)

    def set_name(self, inname):
        self.name = inname

    def num_knots(self):
        return len(self.knots)

    def toXML(self):
        output = StringIO()
        output.write('<Channel name="%s"' % self.name)
        if self.maxLimit > self.minLimit:
            output.write(' minLimit="%f" maxLimit="%f"' % (self.minLimit, self.maxLimit))
        if self.port >= 0:
            output.write(' port="%d"' % self.port)
        if self.rateLimit > 0.0:
            output.write(' rateLimit="%f"' % self.rateLimit)
        if self.type == self.Linear:
            output.write(' type="Linear">\n')
        elif self.type == self.Spline:
            output.write(' type="Spline">\n')
        elif self.type == self.Step:
            output.write(' type="Step">\n')
        for ttime in sorted(self.knots.keys()):
            if ttime not in self.knottitles:
                output.write('    <Point time="%f">\n' % ttime)
            else:
                output.write('    <Point time="%f" name="%s">\n' % (ttime, self.knottitles[ttime]))
            output.write('        %f\n' % self.knots[ttime])
            output.write('    </Point>\n')
        output.write('</Channel>\n')
        return output.getvalue()

    def parseXML(self, inXML):
        if inXML.tag == 'Channel':
            if 'name' in inXML.attrib:
                self.name = inXML.attrib['name']
            if 'minLimit' in inXML.attrib:
                self.minLimit = inXML.attrib['minLimit']
            if 'maxLimit' in inXML.attrib:
                self.maxLimit = inXML.attrib['maxLimit']
            if 'rateLimit' in inXML.attrib:
                self.rateLimit = inXML.attrib['rateLimit']
            if 'port' in inXML.attrib:
                self.port = inXML.attrib['port']
            if 'type' in inXML.attrib:
                if inXML.attrib['type'] == 'Linear':
                    self.type = self.Linear
                elif inXML.attrib['type'] == 'Spline':
                    self.type = self.Spline
                else:
                    raise Exception('Invalid Channel Type')
        else:
            raise Exception('XML is not a Channel')

        for point in inXML:
            if point.tag == 'Point':
                if 'time' in point.attrib:
                    ttime = float(point.attrib['time'])
                else:
                    raise Exception('Invalid XML')
                tvalue = float(point.text)
                self.add_knot(ttime, tvalue)
            else:
                raise Exception('Invalid XML')

        pass


#####################################################################3
# The Animatronics class represents the information needed for doing
# animatronics synced with an audio file.
#####################################################################3
class Animatronics:
    def __init__(self):
        self.filename = None
        self.audiofile = None
        self.audio_data = None
        self.audio_rate = None
        self.channels = {}
        self.start = 0.0
        self.end = -1.0
        self.audiostart = 0.0

    def parseXML(self, inXMLFilename):
        with open(inXMLFilename, 'r') as infile:
            testtext = infile.read()
            root = ET.fromstring(testtext)
            self.filename = inXMLFilename
            for child in root:
                if child.tag == 'Audio':
                    if 'file' in child.attrib:
                        self.set_audio(child.attrib['file'])
                    for start in child:
                        if start.tag == 'Start':
                            if 'time' in start.attrib:
                                self.audiostart = float(start.attrib['time'])
                elif child.tag == 'Channel':
                    tchannel = Channel()
                    tchannel.parseXML(child)
                    self.channels[tchannel.name] = tchannel

    def toXML(self):
        output = StringIO()
        output.write('<?xml version="1.0"?>\n')
        output.write('<Animatronics>\n')
        if self.audiofile is not None:
            output.write('<Audio file="%s">\n' % self.audiofile)
            output.write('    <Start time="%f"/>\n' % self.audiostart)
            output.write('</Audio>\n')
        for channel in self.channels.values():
            output.write(channel.toXML())
        output.write('</Animatronics>\n')
        return output.getvalue()

    def set_audio(self, infilename):
        if os.path.exists(infilename):
            self.audiofile = infilename

            audio = wave.open(self.audiofile)
            self.audio_rate = 1.0 / float(audio.getframerate())
            self.audio_data = []
            for i in range(audio.getnframes()):
                bit = audio.readframes(1)
                short = struct.unpack('<h', bit)
                self.audio_data.append(float(short[0]))


#/* Main */
def main():
    # Local Variables
    infilename = None
    root = None
    animation = Animatronics()

    # Parse arguments
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-f' or sys.argv[i] == '-file':
            i += 1
            if i < len(sys.argv):
                infilename = sys.argv[i]
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    # If an input file was specified, parse it or die trying
    if infilename is not None:
        try:
            animation.parseXML(infilename)

        except Exception as e:
            sys.stderr.write("\nWhoops - Error reading input file %s\n" % infilename)
            sys.stderr.write("Message: %s\n" % e)
            sys.exit(11)

    app = QApplication(sys.argv)

    main_win = MainWindow()
    main_win.setAnimatronics(animation)
    main_win.show()
    app.exec()


if __name__ == "__main__":
    main()

