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
from functools import reduce
import operator

# Utilize XML to read/write animatronics files
import xml.etree.ElementTree as ET

try:
    # Qt import block for all widgets
    from PyQt5.QtCore import (QByteArray, QDate, QDateTime, QDir, QEvent, QPoint,
        QRect, QRegularExpression, QSettings, QSize, QTime, QTimer, Qt, pyqtSlot, QUrl)
    from PyQt5.QtGui import (QBrush, QColor, QIcon, QIntValidator, QPen,
        QDoubleValidator, QRegularExpressionValidator, QValidator, 
        QStandardItem, QStandardItemModel, QFont, QKeySequence)
    from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication,
        QCheckBox, QComboBox, QFileDialog, QDialog, QDialogButtonBox, QGridLayout,
        QGroupBox, QHeaderView, QInputDialog, QItemDelegate, QLabel, QLineEdit, QListView,
        QMainWindow, QMessageBox, QScrollArea, QStyle, QSpinBox, QStyleOptionViewItem,
        QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
        QHBoxLayout, QWidget, QPushButton, QTextEdit, QFormLayout, QTextBrowser,
        QErrorMessage, QMenu, QShortcut)
    from PyQt5 import QtMultimedia as qm
except:
    try:
        # Qt import block for all widgets
        from PyQt6.QtCore import (QByteArray, QDate, QDateTime, QDir, QEvent, QPoint,
            QRect, QRegularExpression, QSettings, QSize, QTime, QTimer, Qt, pyqtSlot, QUrl)
        from PyQt6.QtGui import (QBrush, QColor, QIcon, QIntValidator, QPen,
            QDoubleValidator, QRegularExpressionValidator, QValidator, 
            QStandardItem, QStandardItemModel, QAction, QFont, QKeySequence, QShortcut)
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
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-f/-file infilename]\n")
    sys.stderr.write("Create and edit animatronics control channels.\n");
    sys.stderr.write("-/-h/-help             :show this information\n");
    sys.stderr.write("-f/-file infilename    :Input anim file\n")
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
            smallfont.setPointSize(8)
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
            tname = self.channel.name
            td = ChannelMetadataWidget(channel=self.channel, parent=self, editable=False)
            code = td.exec_()

            if code == QDialog.Accepted:
                # Need to trigger redraw
                self.parent.holder.setAnimatronics(self.parent.holder.animatronics)
                pass
                
            pass

        def invert_action(self):
            """ Perform invert action"""
            if ((self.channel.maxLimit > 1.0e33 and self.channel.minLimit > -1.0e33) or
                (self.channel.maxLimit < 1.0e33 and self.channel.minLimit < -1.0e33)):
                msgBox = QMessageBox()
                msgBox.setText('A channel cannot be inverted with only one limit set!')
                msgBox.setInformativeText("Set or clear both limits.")
                msgBox.setStandardButtons(QMessageBox.Cancel)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
                return
            else:
                for key in self.channel.knots:
                    self.channel.knots[key] = (self.channel.maxLimit + self.channel.minLimit) - self.channel.knots[key]
                self.parent.redrawme()
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
        self.curve2 = None

        # Set initial values to avoid data race
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
        self.redrawme()

    def setDataRange(self, minval, maxval):
        self.minVal = minval
        self.maxVal = maxval
        self.setAxisScale(self.Y_LEFT_AXIS_ID, self.minVal, self.maxVal)
        self.redrawme()

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

        # Create the data plot for the curve and another just for the knots
        xdata = sorted(self.channel.knots)
        ydata = [self.channel.knots[key] for key in xdata]
        self.curve2 = qwt.QwtPlotCurve.make(xdata=xdata, ydata=ydata, plot=self,
            symbol=qwt.symbol.QwtSymbol(qwt.symbol.QwtSymbol.Rect,
                QBrush(), QPen(Qt.green), QSize(self.BoxSize, self.BoxSize))
        )
        self.curve2.setStyle(qwt.QwtPlotCurve.NoCurve)
        self.curve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=ydata, plot=self)
        
        if len(ydata) <= 0:
            self.setDataRange(0.0, 1.0)
        else:
            self.resetDataRange()

        # Create green bar for audio sync
        self.timeSlider = qwt.QwtPlotCurve()
        self.timeSlider.setStyle(qwt.QwtPlotCurve.Sticks)
        self.timeSlider.setData([0.0], [30000.0])
        self.timeSlider.setPen(Qt.green, 3.0, Qt.SolidLine)
        self.timeSlider.setBaseline(-30000.0)
        self.timeSlider.attach(self)

        # Optionally create red line for upper and lower limits
        mintime,maxtime = self.getTimeRange()
        self.lowerLimitBar = qwt.QwtPlotCurve()
        self.lowerLimitBar.setStyle(qwt.QwtPlotCurve.Sticks)
        self.lowerLimitBar.setOrientation(Qt.Vertical)
        self.lowerLimitBar.setPen(Qt.red, 2.0, Qt.SolidLine)
        self.lowerLimitBar.attach(self)
        if self.channel.minLimit > -1.0e33:
            self.lowerLimitBar.setData([maxtime], [self.channel.minLimit])
            self.lowerLimitBar.setBaseline(mintime)
        self.upperLimitBar = qwt.QwtPlotCurve()
        self.upperLimitBar.setStyle(qwt.QwtPlotCurve.Sticks)
        self.upperLimitBar.setOrientation(Qt.Vertical)
        self.upperLimitBar.setPen(Qt.red, 2.0, Qt.SolidLine)
        self.upperLimitBar.attach(self)
        if self.channel.maxLimit < 1.0e33:
            self.upperLimitBar.setData([maxtime], [self.channel.maxLimit])
            self.upperLimitBar.setBaseline(mintime)

        # Create the popup menu
        self.popup = self.ChannelMenu(self, self.channel)

        pass

    def redrawLimits(self):
        if self.channel.minLimit > -1.0e33 or self.channel.maxLimit < 1.0e33:
            mintime,maxtime = self.getTimeRange()
            if self.channel.minLimit > -1.0e33:
                self.lowerLimitBar.setData([maxtime], [self.channel.minLimit])
                self.lowerLimitBar.setBaseline(mintime)
            if self.channel.maxLimit < 1.0e33:
                self.upperLimitBar.setData([maxtime], [self.channel.maxLimit])
                self.upperLimitBar.setBaseline(mintime)

    def findClosestPointWithinBox(self, i,j):
        """Finds the nearest plot point within BoxSize of mouse click"""
        for keyval in self.channel.knots:
            pnti = self.transform(self.X_BOTTOM_AXIS_ID, keyval) + self.xoffset
            pntj = self.transform(self.Y_LEFT_AXIS_ID, self.channel.knots[keyval]) + self.yoffset
            if abs(i-pnti) <= self.BoxSize/2 and abs(j-pntj) <= self.BoxSize/2:
                return keyval
        return None

    def wheelEvent(self, event):
        numDegrees = event.angleDelta() / 8
        vertDegrees = numDegrees.y()

        # Get the data value where the cursor is located
        yplotval = self.invTransform(self.Y_LEFT_AXIS_ID, event.pos().y() - self.yoffset)
        minval = yplotval - (yplotval - self.minVal) * (1.0 - vertDegrees/100.0)
        maxval = yplotval - (yplotval - self.maxVal) * (1.0 - vertDegrees/100.0)
        self.setDataRange(minval, maxval)

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
            self.redrawLimits()
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
                # Apply limits
                if self.channel.minLimit > -1.0e33 or self.channel.maxLimit < 1.0e33:
                    if yplotval > self.channel.maxLimit: yplotval = self.channel.maxLimit
                    if yplotval < self.channel.minLimit: yplotval = self.channel.minLimit
                self.channel.knots[xplotval] = yplotval
                self.selectedKey = xplotval
                if yplotval < self.minVal: self.minVal = yplotval
                if yplotval > self.maxVal: self.maxVal = yplotval
                self.redrawme()
        pass

    def setSlider(self, timeVal):
        if self.timeSlider is not None:
            self.timeSlider.setData([timeVal], [30000.0])
            self.replot()
        
    def redrawme(self):
        # Recreate the data plot
        xdata,ydata = self.channel.getPlotData(self.minTime, self.maxTime, 100)
        if self.curve is not None and xdata is not None and ydata is not None:
            self.curve.setData(xdata, ydata)
        # Recreate the knot plot
        xdata,ydata = self.channel.getKnotData(self.minTime, self.maxTime, 100)
        if self.curve2 is not None and xdata is not None and ydata is not None:
            self.curve2.setData(xdata, ydata)
            if len(xdata) > 1:
                margin = (self.maxVal - self.minVal) * 0.05
                self.setAxisScale(self.Y_LEFT_AXIS_ID, self.minVal-margin, self.maxVal+margin)
        
        self.replot()

#####################################################################
# The ChannelMetadataWidget is used to view and edit the metadata
# for an individual channel
#####################################################################
class ChannelMetadataWidget(QDialog):
    def __init__(self, channel=None, parent=None, editable=True):
        super().__init__(parent)

        # Save animatronics object for update if Save is selected
        self._channel = channel

        self.title = 'Channel MetaData Editor'
        widget = QWidget()
        layout = QFormLayout()
        
        self._nameedit = QLineEdit()
        self._nameedit.setReadOnly(not editable)
        layout.addRow(QLabel('Name:'), self._nameedit)
        self._typeedit = QComboBox()
        self._typeedit.addItems(('Linear', 'Spline', 'Step'))
        layout.addRow(QLabel('Type:'), self._typeedit)
        self._portedit = QLineEdit()
        layout.addRow(QLabel('Port:'), self._portedit)
        self._minedit = QLineEdit()
        layout.addRow(QLabel('Min:'), self._minedit)
        self._maxedit = QLineEdit()
        layout.addRow(QLabel('Max:'), self._maxedit)

        if self._channel is not None:
            self._nameedit.setText(self._channel.name)
            self._typeedit.setCurrentIndex(self._channel.type-1)
            if self._channel.port >= 0:
                self._portedit.setText(str(self._channel.port))
            if self._channel.minLimit > -1.0e33 or self._channel.maxLimit < 1.0e33:
                self._minedit.setText(str(self._channel.minLimit))
                self._maxedit.setText(str(self._channel.maxLimit))

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
        # Need to validate limits prior to changing things
        validate = False
        tstring = self._minedit.text()
        if len(tstring) > 0:
            minLimit = float(tstring)
            if minLimit > self._channel.minLimit: validate = True
        else:
            minLimit = self._channel.minLimit
        tstring = self._maxedit.text()
        if len(tstring) > 0:
            maxLimit = float(tstring)
            if maxLimit < self._channel.maxLimit: validate = True
        else:
            maxLimit = self._channel.maxLimit
        if validate and minLimit < maxLimit:
            minVal = 1.0e34
            maxVal = -1.0e34
            for keyval in self._channel.knots:
                if self._channel.knots[keyval] < minVal: minVal = self._channel.knots[keyval]
                if self._channel.knots[keyval] > maxVal: maxVal = self._channel.knots[keyval]
            if minVal < minLimit or maxVal > maxLimit:
                msgBox = QMessageBox()
                msgBox.setText('Knots in the channel fall outside these limits.')
                msgBox.setInformativeText("Proceed and modify them to fit?")
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
                if ret == QMessageBox.Yes:
                    for keyval in self._channel.knots:
                        if self._channel.knots[keyval] < minLimit: 
                            self._channel.knots[keyval] = minLimit
                        if self._channel.knots[keyval] > maxLimit:
                            self._channel.knots[keyval] = maxLimit
                else:
                    # Cancel selected so don't do any updating below
                    self.close()
                    return


        tstring = self._nameedit.text()
        if len(tstring) > 0:
            self._channel.name = tstring
        self._channel.type = self._typeedit.currentIndex() + 1
        tstring = self._portedit.text()
        if len(tstring) > 0:
            self._channel.port = int(tstring)
        tstring = self._minedit.text()
        if len(tstring) > 0:
            self._channel.minLimit = float(tstring)
        else:
            self._channel.minLimit = -1.0e34
        tstring = self._maxedit.text()
        if len(tstring) > 0:
            self._channel.maxLimit = float(tstring)
        else:
            self._channel.maxLimit = 1.0e34

        self.accept()

#####################################################################
# The MetadataWidget is used to view and edit the metadata
# for the overall Animatronics file
#####################################################################
class MetadataWidget(QDialog):
    def __init__(self, inanim, parent=None):
        super().__init__(parent)

        # Save animatronics object for update if Save is selected
        self._animatronics = inanim

        self.title = 'MetaData Editor'
        widget = QWidget()
        layout = QFormLayout()
        
        self._startedit = QLineEdit('0.0')
        self._startedit.setReadOnly(True)
        layout.addRow(QLabel('Start Time:'), self._startedit)
        self._endedit = QLineEdit()
        if self._animatronics.start < self._animatronics.end:
            self._endedit.setText(str(self._animatronics.end))
        layout.addRow(QLabel('End Time:'), self._endedit)
        self._rateedit = QLineEdit(str(self._animatronics.sample_rate))
        layout.addRow(QLabel('Sample Rate (Hz):'), self._rateedit)
        self._audioedit = QLineEdit(str(self._animatronics.newAudio.audiostart))
        layout.addRow(QLabel('Audio Start Time:'), self._audioedit)
        layout.addRow(QLabel('Audio File:'))
        self._audiofile = QLineEdit('')
        if inanim.newAudio.audiofile is not None:
            self._audiofile.setText(inanim.newAudio.audiofile)
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
        tstring = self._endedit.text()
        if len(tstring) > 0:
            self._animatronics.end = float(tstring)
        tstring = self._rateedit.text()
        if len(tstring) > 0:
            self._animatronics.sample_rate = float(tstring)
        tstring = self._audioedit.text()
        if len(tstring) > 0:
            self._animatronics.audiostart = float(tstring)
        self.accept()

#####################################################################
# The Player class is a widget with playback controls
#####################################################################
class Player(QWidget):
    def __init__(self, parent=None, player=None):
        super().__init__(parent)

        self._startPosition = 0.0
        self._endPosition = 10000.0   # 10 seconds
        # The offset is the start time of the audio in case it is not 0.0
        self._offset = 0.0

        self.mediaPlayer = player
        if player is not None:
            try:    # PyQt5
                self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
            except: # PyQt6
                self.mediaPlayer.playbackStateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionNotify)

        btnSize = QSize(16, 16)

        layout = QHBoxLayout()
        self._rewindbutton = QPushButton()
        self._rewindbutton.setFixedHeight(24)
        self._rewindbutton.setIconSize(btnSize)
        self._rewindbutton.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self._rewindbutton.clicked.connect(self.rewind)
        layout.addWidget(self._rewindbutton)

        self._playbutton = QPushButton()
        self._playbutton.setFixedHeight(24)
        self._playbutton.setIconSize(btnSize)
        self._playbutton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._playbutton.clicked.connect(self.play)
        layout.addWidget(self._playbutton)

        self._setleftbutton = QPushButton()
        self._setleftbutton.setFixedHeight(24)
        self._setleftbutton.setText('Set Left')
        layout.addWidget(self._setleftbutton)

        self._setrightbutton = QPushButton()
        self._setrightbutton.setFixedHeight(24)
        self._setrightbutton.setText('Set Right')
        layout.addWidget(self._setrightbutton)

        layout.addStretch()

        self.setLayout(layout)

    def setRange(self, minTime, maxTime):
        self._startPosition = int((minTime - self._offset) * 1000)
        self._endPosition = int((maxTime - self._offset) * 1000)

    def setOffset(self, audioStartTime):
        self._offset = audioStartTime

    # Slots
    def rewind(self):
        # Go to left side of playable area
        print('Hit Rewind')
        self.mediaPlayer.setPosition(self._startPosition)
        pass

    def play(self):
        print('Hit Play')
        if self.mediaPlayer is not None:
            try:    # PyQt5
                state = self.mediaPlayer.state()
                if state == qm.QMediaPlayer.PlayingState:
                    self.mediaPlayer.pause()
                else:
                    # Limit range of playback
                    if self.mediaPlayer.position() < self._startPosition or self.mediaPlayer.position() >= self._endPosition:
                        self.mediaPlayer.setPosition(self._startPosition)
                    self.mediaPlayer.play()
            except: # PyQt6
                if self.mediaPlayer.isPlaying():
                    self.mediaPlayer.pause()
                else:
                    # Limit range of playback
                    if self.mediaPlayer.position() < self._startPosition or self.mediaPlayer.position() >= self._endPosition:
                        self.mediaPlayer.setPosition(self._startPosition)
                    self.mediaPlayer.play()

    def positionNotify(self, currPosition):
        if currPosition >= self._endPosition:
            self.mediaPlayer.stop() # Hmmm pause goes infinite here but stop does not???

    def mediaStateChanged(self, state):
        if self.mediaPlayer is not None:
            try:    # PyQt5
                state = self.mediaPlayer.state()
                if state == qm.QMediaPlayer.PlayingState:
                    self._playbutton.setIcon(
                        self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
                else:
                    self._playbutton.setIcon(
                        self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            except: # PyQt6
                state = self.mediaPlayer.playbackState()
                if self.mediaPlayer.isPlaying():
                    self._playbutton.setIcon(
                        self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
                else:
                    self._playbutton.setIcon(
                        self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))


    def setLeftConnect(self, leftConnection):
        # Set start of play range to current time and set left edge time to it
        print('Hit Left')
        self._setleftbutton.clicked.connect(leftConnection)
        pass

    def setRightConnect(self, rightConnection):
        # Set start of play range to current time and set right edge time to it
        print('Hit Right')
        self._setrightbutton.clicked.connect(rightConnection)
        pass

#####################################################################
# The MainWindow class represents the Qt main window.
#####################################################################
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
        self.audioCurve = None
        self.audioPlotRight = None
        self.audioCurveRight = None
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
        self._slideTime = 0.0

        self.player = qm.QMediaPlayer()
        self.player.positionChanged.connect(self.positionChanged)

        # Initialize with an empty animatronics object
        self.setAnimatronics(Animatronics())

    def setAnimatronics(self, inanim):
        """Set the active animatronics to the input"""
        self.animatronics = inanim

        # Clear and recreate UI here
        self.audioPlot = None
        self.audioCurve = None
        self.audioPlotRight = None
        self.audioCurveRight = None
        self.timeSlider = None
        self.timeSliderRight = None

        # Create the bottom level widget and make it the main widget
        self._mainarea = QScrollArea(self)
        self._mainarea.setWidgetResizable(True)
        self._mainarea.setMaximumSize(3800,1000)
        self.setCentralWidget(self._mainarea)

        # Set up the playback widget
        self._playwidget = Player(player=self.player)
        shortcut = QShortcut(QKeySequence("Ctrl+P"), self._mainarea)
        shortcut.activated.connect(self._playwidget.play)
        self._playwidget.setLeftConnect(self.cutLeftSide)
        self._playwidget.setRightConnect(self.cutRightSide)
        self._playwidget.hide()
        tlayout = QVBoxLayout(self._mainarea)
        tlayout.addWidget(self._playwidget)

        self._plotarea = QWidget()
        tlayout.addWidget(self._plotarea)

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

        if self.animatronics.newAudio is not None:
            self.audioMin,self.audioMax = self.animatronics.newAudio.audioTimeRange()
            xdata, leftdata, rightdata = self.animatronics.newAudio.getPlotData(self.audioMin,self.audioMax,4000)
            if rightdata is None:
                newplot = qwt.QwtPlot('Audio Mono')
                self.audioCurve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=leftdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlot = newplot
            else:
                newplot = qwt.QwtPlot('Audio Left')
                self.audioCurve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=leftdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlot = newplot
                newplot = qwt.QwtPlot('Audio Right')
                self.audioCurveRight = qwt.QwtPlotCurve.make(xdata=xdata, ydata=rightdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlotRight = newplot
            if self.audioMax > self.totalMax: self.totalMax = self.audioMax
            self.lastXmin = self.audioMin
            self.lastXmax = self.audioMax

            # Create green bars for audio sync
            self.timeSlider = qwt.QwtPlotCurve()
            self.timeSlider.setStyle(qwt.QwtPlotCurve.Sticks)
            self.timeSlider.setData([self.audioMin], [30000.0])
            self.timeSlider.setPen(Qt.green, 3.0, Qt.SolidLine)
            self.timeSlider.setBaseline(-30000.0)
            self.timeSlider.attach(self.audioPlot)

            if self.audioPlotRight is not None:
                self.timeSliderRight = qwt.QwtPlotCurve()
                self.timeSliderRight.setStyle(qwt.QwtPlotCurve.Sticks)
                self.timeSliderRight.setData([self.audioMin], [30000.0])
                self.timeSliderRight.setPen(Qt.green, 3.0, Qt.SolidLine)
                self.timeSliderRight.setBaseline(-30000.0)
                self.timeSliderRight.attach(self.audioPlotRight)


            # Create/open QtMediaPlayer
            try:
                # PyQt5 way
                self.player.setMedia(qm.QMediaContent(QUrl.fromLocalFile(self.animatronics.newAudio.audiofile)))
                # Default notification rate is 1Hz in PyQt5 so up to 50Hz
                self.player.setNotifyInterval(self.animatronics.sample_rate) # This fails in PyQt6???
            except:
                try:
                    # PyQt6 way
                    self.player.setSource(QUrl.fromLocalFile(self.animatronics.newAudio.audiofile))
                    self.player.setAudioOutput(qm.QAudioOutput(qm.QAudioDevice()))
                except:
                    print('Whoops - No Audio player')
                    pass

        for channel in self.animatronics.channels:
            chan = self.animatronics.channels[channel]
            newplot = ChannelPane(self._plotarea, chan, mainwindow=self)
            newplot.settimerange(self.lastXmin, self.lastXmax)
            layout.addWidget(newplot)
            self.plots[chan.name] = newplot

        self._playwidget.setRange(self.lastXmin, self.lastXmax)
            

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
        columns = {}
        timecolumn = []
        starttime = self.animatronics.start
        endtime = self.animatronics.end
        samplestep = 1.0/self.animatronics.sample_rate
        if endtime < starttime:
            for plot in self.plots:
                _,tend = self.plots[plot].getTimeRange()
                if tend > endtime: endtime = tend
        currtime = starttime
        while currtime < endtime:
            timecolumn.append(currtime)
            currtime += samplestep
        columns['Time'] = timecolumn

        for plot in self.plots:
            print('Getting data from:', plot, 'from time:',starttime, 'to:', endtime, 'by:', samplestep)
            values = self.plots[plot].channel.getValuesAtTimeSteps(starttime, endtime, samplestep)
            print('Got datasize:', len(values))
            columns[plot] = values

        # Get the filename to write to
        if self.filedialog is None:
            self.filedialog = QFileDialog(self)

        self.filedialog.setDefaultSuffix('csv')
        fileName, _ = self.filedialog.getSaveFileName(self,"Get Save Filename", "",
                            "Anim Files (*.csv);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                with open(fileName, 'w') as outfile:
                    # Write out the column headers
                    for channel in columns:
                        theport = ''
                        if channel != 'Time':
                            outfile.write(',')
                            portnum = self.plots[channel].channel.port
                            if portnum >= 0:
                                theport = "(%d)" % portnum
                        outfile.write('"%s%s"' % (channel,theport))
                        print('Length of column:', channel, 'is:', len(columns[channel]))
                    outfile.write('\n')
                    # Write out all the data in columns
                    for indx in range(len(timecolumn)):
                        for channel in columns:
                            if channel != 'Time':
                                outfile.write(',')
                            outfile.write('%f' % columns[channel][indx])
                        outfile.write('\n')

            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return

        pass

    def exportVSAFile(self):
        """Export the current animatronics file into a Brookshire VSA format"""
        pass

    def newchannel_action(self):
        """ Perform newchannel action"""
        tempChannel = Channel()
        td = ChannelMetadataWidget(channel=tempChannel, parent=self)
        code = td.exec_()

        if code == QDialog.Accepted:
            # Check to see if channel already exists
            ret = None
            text = tempChannel.name
            if len(text) <= 0:
                msgBox = QMessageBox()
                msgBox.setText('A channel MUST have a name of at least one character and must be unique')
                msgBox.setStandardButtons(QMessageBox.Cancel)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
            elif text in self.animatronics.channels:
                msgBox = QMessageBox()
                msgBox.setText('The channel "%s" already exists.' % text)
                msgBox.setInformativeText("Replace it?")
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
            if ret == QMessageBox.Yes:
                del self.animatronics.channels[text]
                ret = None
            if ret is None:
                self.animatronics.channels[text] = tempChannel
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
        ret = msgBox.exec_()
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

    def positionChanged(self, position):
        self.setSlider(float(position)/1000.0 + self.animatronics.start)

    def setSlider(self, timeVal):
        if self.timeSlider is not None:
            self.timeSlider.setData([timeVal], [30000.0])
            self.audioPlot.replot()
        if self.timeSliderRight is not None:
            self.timeSliderRight.setData([timeVal], [30000.0])
            self.audioPlotRight.replot()
        for plot in self.plots:
            self.plots[plot].setSlider(timeVal)
        self._slideTime = timeVal

    def playbackcontrols_action(self):
        """ Perform playbackcontrols action"""
        if self._playwidget.isHidden():
            self._playwidget.show()
        else:
            self._playwidget.hide()
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
        self.setTimeRange(minTime, maxTime)
        pass

    def redrawAudio(self, minTime, maxTime):
        if self.audioPlot is not None and self.audioCurve is not None:
            if self.animatronics.newAudio is not None:
                xdata, ydata, rightdata = self.animatronics.newAudio.getPlotData(minTime, maxTime, 4000)
                self.audioCurve.setData(xdata, ydata)
                if self.audioCurveRight is not None and rightdata is not None:
                    self.audioCurveRight.setData(xdata, rightdata)
            self.audioPlot.setAxisScale(self.X_BOTTOM_AXIS_ID, minTime, maxTime)
            self.audioPlot.replot()
            if self.audioPlotRight is not None:
                self.audioPlotRight.setAxisScale(self.X_BOTTOM_AXIS_ID, minTime, maxTime)
                self.audioPlotRight.replot()
                
                

    def scaletoaudio_action(self):
        """ Perform scaletoaudio action"""
        # Reset all horizontal scales to audio range and vertical scales to local Y ranges
        self.setTimeRange(self.audioMin, self.audioMax)
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
        form = ChecklistDialog('Channels to Show', self.animatronics.channels)
        checklist = []
        for name in self.plots:
            if self.plots[name].isHidden():
                checklist.append(Qt.Unchecked)
            else:
                checklist.append(Qt.Checked)
        form.setStates(checklist)
        if form.exec_() == QDialog.Accepted:
            for name in self.animatronics.channels:
                if name in form.choices:
                    self.plots[name].show()
                else:
                    self.plots[name].hide()
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
            self.setTimeRange(self.centerX + (self.lastXmin - self.centerX) / yScaler + (self.centerX - newCenterX),
                self.centerX + (self.lastXmax - self.centerX) / yScaler + (self.centerX - newCenterX))
            
                
    def mouseReleaseEvent(self, event):
        pass

    def setTimeRange(self, minval, maxval):
        if minval < maxval:
            self.lastXmax = maxval
            self.lastXmin = minval
            self._playwidget.setRange(self.lastXmin, self.lastXmax)
            self.redrawAudio(self.lastXmin, self.lastXmax)
            for i in self.plots:
                self.plots[i].settimerange(self.lastXmin, self.lastXmax)

    def cutLeftSide(self):
        self.setTimeRange(self._slideTime, self.lastXmax)
    
    def cutRightSide(self):
        self.setTimeRange(self.lastXmin, self._slideTime)


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
        self._newchannel_action = QAction("New Channel", self, shortcut="Ctrl+N",
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
            shortcut="Ctrl+F",
            triggered=self.resetscales_action)
        self.view_menu.addAction(self._resetscales_action)

        # scaletoaudio menu item
        self._scaletoaudio_action = QAction("Fit to Audio", self,
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

        # playbackcontrols menu item
        self._playbackcontrols_action = QAction("Toggle Playback Controls", self,
            triggered=self.playbackcontrols_action)
        self.playback_menu.addAction(self._playbackcontrols_action)


        # Create the Tools dropdown menu #################################
        self.tools_menu = self.menuBar().addMenu("&Tools")

        self.menuBar().addSeparator()

        # Create the Help dropdown menu #################################
        self.help_menu = self.menuBar().addMenu("&Help")
        # self.help_menu.addAction(self.about_action)
        # self.help_menu.addAction(self.about_Qt_action)


#####################################################################
# The AudioChannel class represents the audio channel needed for doing
# animatronics.
#####################################################################
class AudioChannel:

    def __init__(self, filename=None):

        self.audiofile = filename
        self.audio_data = None
        self.samplerate = 44100
        self.numchannels = 1
        self.samplesize = 2
        self.audiostart = 0.0
        self.audioend = 0.0
        if filename is not None:
            self.setAudioFile(filename)

    def audioTimeRange(self):
        """Return the start and end times for the audio"""
        print('Audio file:', self.audiofile)
        print('Audio samplerate:', self.samplerate)
        print('Audio numchannels:', self.numchannels)
        print('Audio samplesize:', self.samplesize)
        print('Audio datasize:', len(self.audio_data))
        self.audioend = self.audiostart + float(len(self.audio_data))/self.numchannels/self.samplerate/self.samplesize
        return self.audiostart,self.audioend

    def getPlotData(self, minTime, maxTime, maxCount):
        if self.numchannels == 1:
            structformat = '<h'
            currTime = minTime
            xdata = []
            ydata = []
            timeStep = (maxTime - minTime) / maxCount
            while currTime <= maxTime:
                sampleindex = int((currTime-self.audiostart) * self.samplerate * self.numchannels * self.samplesize)
                if sampleindex >= 0 and sampleindex <= len(self.audio_data) - self.samplesize*self.numchannels:
                    short = struct.unpack(structformat, self.audio_data[sampleindex:(sampleindex+self.samplesize*self.numchannels)])
                    xdata.append(currTime)
                    ydata.append(float(short[0]))
                currTime += timeStep
            return xdata, ydata, None
        else:
            structformat = '<hh'
            currTime = minTime
            xdata = []
            leftdata = []
            rightdata = []
            timeStep = (maxTime - minTime) / maxCount
            while currTime <= maxTime:
                sampleindex = int((currTime-self.audiostart) * self.samplerate * self.numchannels * self.samplesize)
                if sampleindex >= 0 and sampleindex <= len(self.audio_data) - self.samplesize*self.numchannels:
                    short = struct.unpack(structformat, self.audio_data[sampleindex:sampleindex+self.samplesize*self.numchannels])
                    xdata.append(currTime)
                    leftdata.append(float(short[0]))
                    rightdata.append(float(short[1]))
                currTime += timeStep
            return xdata, leftdata , rightdata

    def setAudioFile(self, infilename):
        # Now read the audio data
        if os.path.exists(infilename):
            self.audiofile = infilename

            audio = wave.open(self.audiofile)
            self.samplerate = audio.getframerate()
            self.numchannels = audio.getnchannels()
            self.samplesize = audio.getsampwidth()
            self.audio_data = audio.readframes(audio.getnframes())

    def toXML(self):
        output = StringIO()
        if self.audiofile is not None:
            output.write('<Audio file="%s">\n' % self.audiofile)
            output.write('    <Start time="%f"/>\n' % self.audiostart)
            output.write('</Audio>\n')
        return output.getvalue()

    def parseXML(self, inXML):
        if inXML.tag == 'Audio':
            if 'file' in inXML.attrib:
                self.setAudioFile(inXML.attrib['file'])

            for start in inXML:
                if start.tag == 'Start':
                    if 'time' in start.attrib:
                        self.audiostart = float(start.attrib['time'])
        pass


#####################################################################
# The Channel class represents the information needed for doing
# animatronics with a single control channel.
#####################################################################
class Channel:
    Linear = 1
    Spline = 2
    Step = 3
    Smooth = 4

    def __init__(self, inname = '', intype = Linear):
        self.name = inname
        self.knots = {}
        self.knottitles = {}
        self.type = intype
        self.maxLimit = 1.0e34
        self.minLimit = -1.0e34
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

    def getValueAtTime(self, inTime):
        pass

    def getKnotData(self, minTime, maxTime, maxCount):
        """Returns up to maxCount of the knots along the visible part of the curve"""
        keys = sorted(self.knots.keys())
        if len(keys) < 1:
            # Return Nones if channel is empty
            return None,None
        if len(keys) < 2:
            # return single values if only one knot in channel
            return [keys[0]], [self.knots[keys[0]]]
        xdata = []
        ydata = []
        if len(keys) < maxCount:
            # Return all of them
            for key in self.knots:
                xdata.append(key)
                ydata.append(self.knots[key])
        else:
            # Weed them out somehow
            # Return all of them for now
            for key in self.knots:
                xdata.append(key)
                ydata.append(self.knots[key])
        return xdata,ydata

    def getPlotData(self, minTime, maxTime, maxCount):
        """Returns up to maxCount points along the visible part of the curve"""
        keys = sorted(self.knots.keys())
        if len(keys) < 1:
            # Return Nones if channel is empty
            return None,None
        if len(keys) < 2:
            # Return a constant value
            xdata = [minTime + i * (maxTime - minTime) for i in range(maxCount+1)]
            ydata = [self.knots[keys[0]] for i in range(maxCount+1)]

        elif self.type == self.Linear:
            # Just return the points within the time range plus some on either side
            if len(keys) < maxCount:
                # Just send them all
                xdata = keys
                ydata = [self.knots[key] for key in keys]
            else:
                # Have to weed them out somehow
                # Just send them all for now
                xdata = keys
                ydata = [self.knots[key] for key in keys]
        elif self.type == self.Step:
            # To simulate a step function, output a value at the beginning and end
            # of its interval
            xdata = [min(minTime, keys[0])]
            ydata = [self.knots[keys[0]]]
            if len(keys) < maxCount:
                xdata.append(keys[0])
                ydata.append(self.knots[keys[0]])
                for i in range(1, len(keys)):
                    xdata.append(keys[i] - 0.0000001)
                    ydata.append(self.knots[keys[i-1]])
                    xdata.append(keys[i])
                    ydata.append(self.knots[keys[i]])
            xdata.append(max(maxTime, keys[-1]))
            ydata.append(self.knots[keys[-1]])
        elif self.type == self.Smooth or self.type == self.Spline:
            # Use Lagrangian interpolation of knots
            timeStep = (maxTime - minTime) / maxCount
            currTime = minTime
            xdata = []
            ydata = []
            while currTime < maxTime + timeStep:
                # Find appropriate interval for current time
                for i in range(len(keys)):
                    if keys[i] >= currTime:
                        break
                # Wants two knots before and two after for best results
                interpKeys = keys[max(0,i-2):min(i+2,len(keys))]
                def _basis(j):
                    k = len(interpKeys)
                    p = [(currTime - interpKeys[m])/(interpKeys[j] - interpKeys[m]) for m in range(k) if m != j]
                    return reduce(operator.mul, p)
                weights = []
                for i in range(len(interpKeys)):
                    weights.append(_basis(i))
                xdata.append(currTime)
                ydata.append(sum(weights[j] * self.knots[interpKeys[j]] for j in range(len(interpKeys))))

                currTime += timeStep

        elif self.type == self.Spline:
            xdata = None
            ydata = None

        # Limit the range of plot data to min and max values
        for i in range(len(ydata)):
            if ydata[i] > self.maxLimit:
                ydata[i] = self.maxLimit
            elif ydata[i] < self.minLimit:
                ydata[i] = self.minLimit

        return xdata,ydata


    def getValuesAtTimeSteps(self, startTime, endTime, timeStep):
        """Returns an array of values along the curve at each time step from start to end"""
        if len(self.knots) == 0:
            return None

        # Short cut for spline and smooth curves
        if self.type == self.Spline or self.type == self.Smooth:
            maxCount = int((endTime - startTime) / timeStep)
            _, values = self.getPlotData(startTime, endTime, maxCount)
            return values

        # Handle Linear and Step types
        keys = sorted(self.knots.keys())
        currTime = startTime
        nextkeyindex = 1
        values = []
        while currTime <= endTime:
            if currTime < keys[0]:
                if self.type == self.Linear or self.type == self.Step:
                    values.append(self.knots[keys[0]])
            elif currTime > keys[-1]:
                if self.type == self.Linear or self.type == self.Step:
                    values.append(self.knots[keys[-1]])
            else:
                # Somewhere in range so find interval
                while nextkeyindex < len(keys) and keys[nextkeyindex] <= currTime:
                    nextkeyindex += 1
                if self.type == self.Linear:
                    # interpolate
                    tval = ((self.knots[keys[nextkeyindex]] * (currTime - keys[nextkeyindex-1]) +
                        self.knots[keys[nextkeyindex-1]] * (keys[nextkeyindex] - currTime)) /
                        (keys[nextkeyindex] - keys[nextkeyindex-1]))
                    values.append(tval)
                    pass
                elif self.type == self.Step:
                    values.append(self.knots[keys[nextkeyindex-1]])

            currTime += timeStep

        return values

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
                self.minLimit = float(inXML.attrib['minLimit'])
            if 'maxLimit' in inXML.attrib:
                self.maxLimit = float(inXML.attrib['maxLimit'])
            if 'rateLimit' in inXML.attrib:
                self.rateLimit = float(inXML.attrib['rateLimit'])
            if 'port' in inXML.attrib:
                self.port = int(inXML.attrib['port'])
            if 'type' in inXML.attrib:
                if inXML.attrib['type'] == 'Linear':
                    self.type = self.Linear
                elif inXML.attrib['type'] == 'Spline':
                    self.type = self.Spline
                elif inXML.attrib['type'] == 'Step':
                    self.type = self.Step
                else:
                    raise Exception('Invalid Channel Type:%s' % inXML.attrib['type'])
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


#####################################################################
# The Animatronics class represents the information needed for doing
# animatronics synced with an audio file.
#####################################################################
class Animatronics:
    def __init__(self):
        self.filename = None
        self.newAudio = None
        self.channels = {}
        self.start = 0.0
        self.end = -1.0
        self.sample_rate = 50.0

    def parseXML(self, inXMLFilename):
        with open(inXMLFilename, 'r') as infile:
            testtext = infile.read()
            root = ET.fromstring(testtext)
            self.filename = inXMLFilename
            # Get the attributes from the XML
            if 'endtime' in root.attrib:
                self.end = float(root.attrib['endtime'])
            for child in root:
                if child.tag == 'Audio':
                    self.newAudio = AudioChannel()
                    self.newAudio.parseXML(child)
                elif child.tag == 'Channel':
                    tchannel = Channel()
                    tchannel.parseXML(child)
                    self.channels[tchannel.name] = tchannel
                elif child.tag == 'Control':
                    if 'rate' in child.attrib:
                        self.sample_rate = float(child.attrib['rate'])

    def toXML(self):
        output = StringIO()
        output.write('<?xml version="1.0"?>\n')
        output.write('<Animatronics starttime="%f"' % self.start)
        if self.end > self.start:
            output.write(' endtime="%f"' % self.end)
        output.write('>\n')
        output.write('<Control rate="%f"/>\n' % self.sample_rate)
        if self.newAudio is not None:
            output.write(self.newAudio.toXML())
        for channel in self.channels.values():
            output.write(channel.toXML())
        output.write('</Animatronics>\n')
        return output.getvalue()

    def set_audio(self, infilename):
        self.newAudio = AudioChannel(infilename)


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
    app.exec_()


if __name__ == "__main__":
    main()

