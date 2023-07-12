#!/usr/bin/env python
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

usedPyQt = None

try:
    # Qt import block for all widgets
    from PyQt5.QtCore import (QByteArray, QDate, QDateTime, QDir, QEvent, QPoint,
        QFile, QIODevice, QBuffer,
        QRect, QRegularExpression, QSettings, QSize, QTime, QTimer, Qt, pyqtSlot, QUrl)
    from PyQt5.QtGui import (QBrush, QColor, QIcon, QIntValidator, QPen,
        QClipboard, QGuiApplication,
        QDoubleValidator, QRegularExpressionValidator, QValidator, QCursor,
        QStandardItem, QStandardItemModel, QFont, QKeySequence, QPalette)
    from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication,
        QCheckBox, QComboBox, QFileDialog, QDialog, QDialogButtonBox, QGridLayout,
        QGroupBox, QHeaderView, QInputDialog, QItemDelegate, QLabel, QLineEdit, QListView,
        QMainWindow, QMessageBox, QScrollArea, QStyle, QSpinBox, QStyleOptionViewItem,
        QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
        QHBoxLayout, QWidget, QPushButton, QTextEdit, QFormLayout, QTextBrowser,
        QErrorMessage, QMenu, QShortcut)
    from PyQt5 import QtMultimedia as qm
    usedPyQt = 5
except:
    try:
        # Qt import block for all widgets
        from PyQt6.QtCore import (QByteArray, QDate, QDateTime, QDir, QEvent, QPoint,
            QFile, QIODevice, QBuffer,
            QRect, QRegularExpression, QSettings, QSize, QTime, QTimer, Qt, pyqtSlot, QUrl)
        from PyQt6.QtGui import (QBrush, QColor, QIcon, QIntValidator, QPen, QPalette,
            QClipboard, QGuiApplication,
            QDoubleValidator, QRegularExpressionValidator, QValidator, QCursor,
            QStandardItem, QStandardItemModel, QAction, QFont, QKeySequence, QShortcut)
        from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
            QCheckBox, QComboBox, QFileDialog, QDialog, QDialogButtonBox, QGridLayout,
            QGroupBox, QHeaderView, QInputDialog, QItemDelegate, QLabel, QLineEdit, QListView,
            QMainWindow, QMessageBox, QScrollArea, QStyle, QSpinBox, QStyleOptionViewItem,
            QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
            QHBoxLayout, QWidget, QPushButton, QTextEdit, QFormLayout, QTextBrowser,
            QErrorMessage, QMenu)
        from PyQt6 import QtMultimedia as qm
        usedPyQt = 6
    except:
        sys.stderr.write('Whoops - Unable to find PyQt5 or PyQt6 - Quitting\n')
        exit(10)
import qwt

#/* Define block */
verbosity = False

# System Preferences Block
SystemPreferences = {
'MaxDigitalChannels':48,
'MaxServoChannels':32,
'ServoDefaultMinimum':0.0,
'ServoDefaultMaximum':180.0,
'Ordering':'Numeric',
}
SystemPreferenceTypes = {
'MaxDigitalChannels':'int',
'MaxServoChannels':'int',
'ServoDefaultMinimum':'float',
'ServoDefaultMaximum':'float',
'Ordering':['Alphabetic','Numeric','Creation'],
}

#/* Usage method */
def print_usage(name):
    """
    The method print_usage prints the standard usage message.
    Parameters
    ----------
    name : str
        The name of the application from argv[0]
    """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-f/-file infilename]\n")
    sys.stderr.write("Create and edit animatronics control channels.\n");
    sys.stderr.write("-/-h/-help             :show this information\n");
    sys.stderr.write("-f/-file infilename    :Input anim file\n")
    sys.stderr.write("\n\n");

def pushState():
    """
    The method pushState pipes a request to save state for undo to the
    main window.
    """
    global main_win
    main_win.pushState()

def popState():
    """
    The method popState pipes a request to pop state for undo to the
    main window.
    """
    global main_win
    main_win.popState()

#####################################################################
class TagPane(qwt.QwtPlot):
    def __init__(self, parent=None, intags = None, mainwindow=None):
        super().__init__(parent)

        self.parent = parent
        self._tags = intags
        self.mainwindow = mainwindow

        self.selectedtag = None
        self.minTime = 0.0
        self.maxTime = 1.0

        self.allMarkers = {}

        if intags is None or len(intags) == 0:
            self.hide()

        self.setAxisScale(qwt.QwtPlot.yLeft, -1.0, 1.0, 2.0)
        self.setAxisTitle(qwt.QwtPlot.yLeft, 'Tags')
        self.setAxisMaxMinor(qwt.QwtPlot.yLeft, 1)

        self.tagSlider = qwt.QwtPlotCurve()
        self.tagSlider.setStyle(qwt.QwtPlotCurve.Sticks)
        self.tagSlider.setData([0.0], [3.0])
        self.tagSlider.setPen(Qt.green, 3.0, Qt.SolidLine)
        self.tagSlider.setBaseline(-3.0)
        self.tagSlider.attach(self)

        self.redrawme()

    def redrawTags(self, tMin, tMax):
        self.minTime = tMin
        self.maxTime = tMax
        self.setAxisScale(qwt.QwtPlot.xBottom, tMin, tMax)
        self.replot()

    def redrawme(self):
        for marker in self.allMarkers:
            self.allMarkers[marker].detach()
        self.allMarkers = {}
        for tag in self._tags:
            marker = qwt.QwtPlotMarker(self._tags[tag])
            marker.setValue(tag, 0.0)
            marker.setLabel(self._tags[tag])
            marker.attach(self)
            marker.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
            marker.setLineStyle(qwt.QwtPlotMarker.VLine)
            self.allMarkers[tag] = marker
        self.replot()

    def addTag(self, time, text):
        while time in self._tags:
            time += 0.000001
        self._tags[time] = text
        marker = qwt.QwtPlotMarker(text)
        marker.setValue(time, 0.0)
        marker.setLabel(text)
        marker.attach(self)
        marker.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        marker.setLineStyle(qwt.QwtPlotMarker.VLine)
        self.allMarkers[time] = marker
        self.replot()
        # Return time just in case we tweaked it
        return time

    def deleteTag(self, time):
        if time in self._tags:
            del self._tags[time]
        if time in self.allMarkers:
            self.allMarkers[time].detach()
            del self.allMarkers[time]
            self.replot()

    def setSlider(self, time):
        self.tagSlider.setData([time], [30000.0])
        self.replot()

    def findClickedTag(self, i):
        for tagX in self._tags:
            pnti = self.transform(qwt.QwtPlot.xBottom, tagX) + self.xoffset
            if abs(i-pnti) <= 5:
                return tagX
        return None

    def mousePressEvent(self, event):
        # Get left offset
        rect = self.plotLayout().scaleRect(qwt.QwtPlot.yLeft)
        self.xoffset = rect.width()

        if event.buttons() == Qt.LeftButton :
            # Get time at point of click
            xplotval = self.invTransform(qwt.QwtPlot.xBottom, event.pos().x() - self.xoffset)

            # Check to see if we are clicking on an existing tag
            neartag = self.findClickedTag(event.pos().x())

            # Check for Shift Key
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ShiftModifier:
                # If shift key is down then we want to insert or delete a tag
                # Push current state for undo
                pushState()

                if neartag is not None:
                    # Delete currently selected tag
                    self.deleteTag(neartag)
                    self.selectedtag = None
                    pass
                else:
                    # Insert a new tag
                    neartag = xplotval
                    neartag = self.addTag(neartag, 'Temp')
                    self.selectedtag = neartag

                event.ignore()
            else:
                # Not shift so select near one to drag or pass to main window
                if neartag is not None:
                    self.selectedtag = neartag
                    event.accept()
                else:
                    # Nobody is selected so pass to main window
                    self.selectedtag = None

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton :
            # If dragging something
            if self.selectedtag is not None:
                # Get time at point of click
                xplotval = self.invTransform(qwt.QwtPlot.xBottom, event.pos().x() - self.xoffset)
                # Move marker from old time to new time
                tlabel = self._tags[self.selectedtag]
                self.deleteTag(self.selectedtag)
                self.selectedtag = self.addTag(xplotval, tlabel)
                self.redrawme()
            else:
                # Send the event up to the main window
                event.ignore()

    def mouseReleaseEvent(self, event):
        if self.selectedtag is not None:
            # We are dragging a tag around - see if it needs a new label
            if self._tags[self.selectedtag] == 'Temp':
                # Bring up window to get actual label from user
                text, ok = QInputDialog().getText(self, "Tag Entry", "Enter Tag:",
                    QLineEdit.Normal, self._tags[self.selectedtag])
                self.deleteTag(self.selectedtag)
                if ok and text:
                    self.addTag(self.selectedtag, text)
#####################################################################
class TextDisplayDialog(QDialog):
    """
    Class: TextDisplayDialog
        Derives from: (QDialog)

    The TextDisplayDialog class is a popup window that displays text
    from a string or a file.
    ...
    Attributes
    ----------
    name : str
        Title of window
    textView : QTextBrowser

    Methods
    -------
    setText(self, text)
    setSource(self, instr)
    """

    def __init__(self,
        name,
        text='',
        parent=None,
        ):
        super(TextDisplayDialog, self).__init__(parent)

        self.name = name
        self.textView = QTextBrowser(self)
        self.textView.setPlainText(text)
        self.textView.setReadOnly(True)
        self.resize(500, 600)

        layout = QFormLayout()
        self.setLayout(layout)
        layout.addRow(self.textView)

    def setText(self, text):
        """
        The method setText sets the displayed text to the incoming text
            member of class: TextDisplayDialog
        Parameters
        ----------
        self : TextDisplayDialog
        text : str
            The text to be displayed
        """
        self.textView.setPlainText(text)

    def setSource(self, instr):
        """
        The method setSource sets the displayed text from the
        specified local file.
            member of class: TextDisplayDialog
        Parameters
        ----------
        self : TextDisplayDialog
        instr : Path to local file
        """
        self.textView.setSource(QUrl.fromLocalFile(instr))
        
#####################################################################
class ChecklistDialog(QDialog):
    """
    Class: ChecklistDialog
        Derives from: (QDialog)

    The ChecklistDialog class provides a popup checklist of the
    channels for selecting those to be hidden or deleted or other
    actions.
    ...
    Attributes
    ----------
    name : str
        Window Title
    icon : QIcon
        Hmmm, not sure what this does??
    model : QStandardItemModel
    listView : QListView
    okButton : QPushButton
    cancelButton : QPushButton
    selectButton : QPushButton
    unselectButton : QPushButton
    choices : str array
        Array of strings containing names of checked channels

    Methods
    -------
    setStates(self, checklist)
    onAccepted(self)
    select(self)
    unselect(self)
    """

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
        """
        The method setStates sets the initial checked state of all the
        checkboxes
            member of class: ChecklistDialog
        Parameters
        ----------
        self : ChecklistDialog
        checklist : boolean array
            Array of booleans of checked status for each channel
        """
        for i in range(min(len(checklist), self.model.rowCount())):
            self.model.item(i).setCheckState(checklist[i])

    def onAccepted(self):
        """
        The method onAccepted copies the set of checked item names
        into the choices for later retrieval and signals approval.
            member of class: ChecklistDialog
        Parameters
        ----------
        self : ChecklistDialog
        """
        self.choices = [self.model.item(i).text() for i in
                        range(self.model.rowCount())
                        if self.model.item(i).checkState()
                        == Qt.Checked]
        self.accept()

    def select(self):
        """
        The method select checks all items
            member of class: ChecklistDialog
        Parameters
        ----------
        self : ChecklistDialog
        """
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            item.setCheckState(Qt.Checked)

    def unselect(self):
        """
        The method unselect unchecks all items
            member of class: ChecklistDialog
        Parameters
        ----------
        self : ChecklistDialog
        """
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            item.setCheckState(Qt.Unchecked)

#####################################################################
# The ChannelMenu class represents the editing menu for a
# single channel.
#####################################################################
class ChannelMenu(QMenu):
    """
    Class: ChannelMenu
        Derives from: (QMenu)

        Implements a popup menu within a channel pane for working with
    the particular channel or pane.  It offers several functions such
    as Metadata editing, rescaling, hide, and delete.
    ...
    Attributes
    ----------
    parent : type
    channel : type
    name : type
    _metadata_action : QAction
    _invert_action : QAction
    _smooth_action : QAction
    _wrap_action : QAction
    _Rescale_action : QAction
    _Hide_action : QAction
    _Delete_action : QAction

    Methods
    -------
    __init__(self, parent, channel)
    metadata_action(self)
    invert_action(self)
    smooth_action(self)
    wrap_action(self)
    Rescale_action(self)
    Hide_action(self)
    Delete_action(self)
    """

    """The popup widget for an individual channel pane"""
    def __init__(self, parent, channel):
        """
        The method __init__
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        parent : QWidget
            The ChannelPane upon which to display this menu
        channel : Channel
            The channel of data being manipulated
        """
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
        if self.channel.type == self.channel.LINEAR:
            self._smooth_action = QAction("smooth", self,
                triggered=self.smooth_action)
            self._smooth_action.setEnabled(False)
            self.addAction(self._smooth_action)

        # wrap menu item
        self._wrap_action = QAction("wrap", self,
            triggered=self.wrap_action)
        self._wrap_action.setEnabled(False)
        self.addAction(self._wrap_action)

        # Rescale menu item
        self._Rescale_action = QAction("Rescale", self,
            shortcut="Ctrl+R",
            triggered=self.Rescale_action)
        self._Rescale_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.addAction(self._Rescale_action)
        # self.parent.addAction(self._Rescale_action)
        # sc = QShortcut(parent=self.parent, key="Ctrl+F", shortcutContext=Qt.WidgetWithChildrenShortcut)
        # sc = QShortcut(QKeySequence("Ctrl+F"), self.parent)
        # sc.setContext(Qt.WidgetWithChildrenShortcut)
        # sc.activated.connect(self.Rescale_action)

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
        """
        The method metadata_action brings up the metadata editor widget
        for viewing or modifying the channel's information.
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """
        tname = self.channel.name
        td = ChannelMetadataWidget(channel=self.channel, parent=self, editable=False)
        code = td.exec_()

        if code == QDialog.Accepted:
            # Need to trigger redraw
            self.parent.holder.redraw()
            pass
            
        pass

    def invert_action(self):
        """
        The method invert_action flips the channel data vertically between
        the upper and lower limits.  Both or neither must be set.  If
        neither then inverts simply negates all the values.
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """

        if ((self.channel.maxLimit > 1.0e33 and self.channel.minLimit > -1.0e33) or
            (self.channel.maxLimit < 1.0e33 and self.channel.minLimit < -1.0e33)):
            msgBox = QMessageBox(parent=self)
            msgBox.setText('A channel cannot be inverted with only one limit set!')
            msgBox.setInformativeText("Set or clear both limits.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()
            return
        else:
            # Push current state for undo
            pushState()

            for key in self.channel.knots:
                self.channel.knots[key] = (self.channel.maxLimit + self.channel.minLimit) - self.channel.knots[key]
            self.parent.redrawme()
            main_win.updateXMLPane()
        pass

    def smooth_action(self):
        """
        The method smooth_action seems to be superseded by the spline
        type.
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """

        pass

    def wrap_action(self):
        """
        The method wrap_action adjusts the final point(s) in the channel
        so that it ends at the same state as the channel begins for
        smooth loops.
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """

        pass

    def Rescale_action(self):
        """
        The method Rescale_action requests the ChannelPane to adjust its
        vertical range to fit the data and limits with a bit of margin.
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """
        self.parent.resetDataRange()
        pass

    def Hide_action(self):
        """
        The method Hide_action hides the ChannelPane
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """
        self.parent.hidePane()
        pass

    def Delete_action(self):
        """
        The method Delete_action requests that this Channel be removed
        from the animation.
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """
        # self.parent.holder should be the MainWindow
        if self.parent.holder is not None:
            self.parent.holder.deleteChannels([self.name])
        pass


#####################################################################
# The ChannelPane class represents the display widget for a
# single channel.
#####################################################################
class ChannelPane(qwt.QwtPlot):
    """
    Class: ChannelPane
        Derives from: (qwt.QwtPlot)

        Implements a QWTPlot widget for displaying and working with a
    single channel of data.  Provides methods for creating and editing
    a channel.
    ...
    Shared Attributes
    ----------
    # The size of the square around each knot in the channel
    BoxSize = 10

    Attributes
    ----------
    parent : type
    channel : type
    holder : type
    curve : QwtPlotCurve
        The line representing the interpolated data points
    curve2 : QwtPlotCurve
        The symbols to be drawn at the actual data points
    minTime : type
    maxTime : type
    minVal : type
    maxVal : type
    xoffset : type
    yoffset : type
    selectedKey : type
    selected : type
    timeSlider : qwt.QwtPlotCurve
    lowerLimitBar : qwt.QwtPlotCurve
    upperLimitBar : qwt.QwtPlotCurve
    popup : ChannelMenu
    _unselectedPalette : self.palette
    _selectedPalette : QPalette

    Methods
    -------
    __init__(self, parent=None, inchannel=None, mainwindow=None)
    settimerange(self, mintime, maxtime)
    setDataRange(self, minval, maxval)
    resetDataRange(self)
    getTimeRange(self)
    setOffsets(self)
    hidePane(self)
    create(self)
    redrawLimits(self)
    findClosestPointWithinBox(self, i,j)
    select(self)
    deselect(self)
    invertselect(self)
    wheelEvent(self, event)
    mousePressEvent(self, event)
    mouseReleaseEvent(self, event)
    mouseMoveEvent(self, event)
    setSlider(self, timeVal)
    redrawme(self)
    """
    BoxSize = 10

    def __init__(self, parent=None, inchannel=None, mainwindow=None):
        """
        The method __init__
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        parent=None : QWidget
            The widget that contains this pane
        inchannel=None : 
            The data channel to be displayed and manipulated
        mainwindow=None : MainWindow
            The MainWindow of the application
        """
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
        self.selected = False
        self.settimerange(0.0, 100.0)
        self.setDataRange(-1.0, 1.0)
        channelname = self.channel.name
        # If port number is set, append it to the displayed channel name
        if self.channel.port >= 0:
            channelname += '(%d)' % self.channel.port
        self.setAxisTitle(qwt.QwtPlot.yLeft, channelname)

        self.create()

    def settimerange(self, mintime, maxtime):
        """
        The method settimerange sets the time range (X axis) to be
        displayed.  This is generally called by the main window when the
        user rescales the audio pane to make all panes show the same
        time range.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        mintime : float
        maxtime : float
        """
        self.minTime = mintime
        self.maxTime = maxtime
        self.setAxisScale(qwt.QwtPlot.xBottom, self.minTime, self.maxTime)
        self.redrawme()

    def setDataRange(self, minval, maxval, axisstep=0):
        """
        The method setDataRange sets the data range (Y axis) to be
        displayed.  This method is called internally as the user scrolls
        the mouse wheel or requests rescale.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        minval : float
        maxval : float
        """
        self.minVal = minval
        self.maxVal = maxval
        self.setAxisScale(qwt.QwtPlot.yLeft, self.minVal, self.maxVal, axisstep)
        self.redrawme()

    def resetDataRange(self):
        """
        The method resetDataRange rescales the Y axis to fit the range of
        data, including the limits, with a 5% margin top and bottom.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        self.minVal = 1.0e34
        self.maxVal = -1.0e34
        for keyval in self.channel.knots:
            if self.channel.knots[keyval] < self.minVal: 
                self.minVal = self.channel.knots[keyval]
            if self.channel.knots[keyval] > self.maxVal: 
                self.maxVal = self.channel.knots[keyval]
        if self.channel.minLimit < self.minVal and self.channel.minLimit > -1.0e33: 
                self.minVal = self.channel.minLimit
        if self.channel.maxLimit > self.maxVal and self.channel.maxLimit <  1.0e33: 
                self.maxVal = self.channel.maxLimit
        if self.minVal == self.maxVal:
            margin = 0.5
        else:
            margin = 0.05 * (self.maxVal - self.minVal)

        # Set y axis style for various types of plots
        if self.channel.type == Channel.DIGITAL:
            print('Setting axisstep to 1.0')
            self.setAxisMaxMinor(qwt.QwtPlot.yLeft, 2)
            self.setDataRange(self.minVal - margin, self.maxVal + margin, axisstep=1.0)
        else:
            if int(self.channel.maxLimit - self.channel.minLimit +0.1) % 30 == 0:
                # Likely to be in units of degrees so set scale to multiple of 30
                self.setAxisMaxMinor(qwt.QwtPlot.yLeft, 2)
                self.setDataRange(self.minVal - margin, self.maxVal + margin, axisstep=30.0)
            else:
                self.setDataRange(self.minVal - margin, self.maxVal + margin)

    def getTimeRange(self):
        """
        The method getTimeRange returns the minimum and maximum time (X)
        values of all the knots in the channel.  It is called from the
        MainWindow when scaling the application to display all the data.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        minVal = 1.0e34
        maxVal = -1.0e34
        for keyval in self.channel.knots:
            if keyval < minVal: minVal = keyval
            if keyval > maxVal: maxVal = keyval
        return minVal, maxVal

    def setOffsets(self):
        """
        The method setOffsets computes the offset of the upper left
        corner of the data display part of the widget from the upper
        left corner of the overall widget.  Essentially, this computes
        the width of the region on the left containing the title and
        the scale values and the height of the rectangle at the top
        that contains only a margin.  These values are stored and used
        to convert cursor location into data values within the range
        of the channel.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        # Compute axis offset from size of anything displayed at top
        rect = self.plotLayout().scaleRect(qwt.QwtPlot.xTop)
        self.yoffset = rect.height()
        # Compute axis offset
        rect = self.plotLayout().scaleRect(qwt.QwtPlot.yLeft)
        self.xoffset = rect.width()

    def hidePane(self):
        """
        The method hidePane hides the Pane (duh).
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        self.hide()

    def create(self):
        """
        The method create creates all the widget stuff for the channel pane
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        grid = qwt.QwtPlotGrid()
        grid.enableXMin(True)
        grid.attach(self)
        grid.setPen(QPen(Qt.black, 0, Qt.DotLine))

        # Create the data plot for the curve and another just for the knots
        xdata = sorted(self.channel.knots)
        ydata = [self.channel.knots[key] for key in xdata]
        self.curve2 = qwt.QwtPlotCurve.make(xdata=xdata, ydata=ydata, plot=self,
            symbol=qwt.symbol.QwtSymbol(qwt.symbol.QwtSymbol.Rect,
                QBrush(), QPen(Qt.black), QSize(self.BoxSize, self.BoxSize))
        )
        self.curve2.setStyle(qwt.QwtPlotCurve.NoCurve)
        self.curve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=ydata, plot=self, linewidth=2)

        # Add filler for the On times for the digital channels
        if self.channel.type == Channel.DIGITAL:
            fillbrush = QBrush(Qt.gray)
            self.curve.setBrush(fillbrush)
        
        self.resetDataRange()

        # Create green bar for audio sync
        self.timeSlider = qwt.QwtPlotCurve()
        self.timeSlider.setStyle(qwt.QwtPlotCurve.Sticks)
        self.timeSlider.setData([0.0], [30000.0])
        self.timeSlider.setPen(Qt.green, 3.0, Qt.SolidLine)
        self.timeSlider.setBaseline(-30000.0)
        self.timeSlider.attach(self)

        # Optionally create red line for upper and lower limits
        if self.channel.type != Channel.DIGITAL:
            mintime,maxtime = self.getTimeRange()
            self.lowerLimitBar = qwt.QwtPlotCurve()
            self.lowerLimitBar.setStyle(qwt.QwtPlotCurve.Sticks)
            self.lowerLimitBar.setOrientation(Qt.Vertical)
            self.lowerLimitBar.setPen(Qt.red, 2.0, Qt.SolidLine)
            self.lowerLimitBar.attach(self)
            if self.channel.minLimit > -1.0e33:
                self.lowerLimitBar.setData([maxtime+1000.0], [self.channel.minLimit])
                self.lowerLimitBar.setBaseline(mintime-1000.0)
            self.upperLimitBar = qwt.QwtPlotCurve()
            self.upperLimitBar.setStyle(qwt.QwtPlotCurve.Sticks)
            self.upperLimitBar.setOrientation(Qt.Vertical)
            self.upperLimitBar.setPen(Qt.red, 2.0, Qt.SolidLine)
            self.upperLimitBar.attach(self)
            if self.channel.maxLimit < 1.0e33:
                self.upperLimitBar.setData([maxtime+1000.0], [self.channel.maxLimit])
                self.upperLimitBar.setBaseline(mintime-1000.0)

        # Create the popup menu
        self.popup = ChannelMenu(self, self.channel)

        # Set up palettes for selected and not selected
        self._unselectedPalette = self.palette()
        backcolor = QColor()
        backcolor.setRgb(100, 200, 100)
        self._selectedPalette = QPalette()
        self._selectedPalette.setColor(self.canvas().backgroundRole(), backcolor)

        pass
    
    def redrawLimits(self):
        """
        The method redrawLimits computes the positions of the upper and
        lower limit bars drawn on the display.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        try: # Because this can crap out if done too early
            if self.channel.type != Channel.DIGITAL:
                if self.channel.minLimit > -1.0e33 or self.channel.maxLimit < 1.0e33:
                    mintime,maxtime = self.getTimeRange()
                    if mintime > maxtime:   # Happens when there are no data points so kluge
                        mintime = 0.0
                        maxtime = 1.0
                    if self.channel.minLimit > -1.0e33:
                        self.lowerLimitBar.setData([maxtime+1000.0], [self.channel.minLimit])
                        self.lowerLimitBar.setBaseline(mintime-1000.0)
                    if self.channel.maxLimit < 1.0e33:
                        self.upperLimitBar.setData([maxtime+1000.0], [self.channel.maxLimit])
                        self.upperLimitBar.setBaseline(mintime-1000.0)
        except:
            # Just ignore it if it craps out
            pass

    def findClosestPointWithinBox(self, i,j):
        """
        The method findClosestPointWithinBox finds the nearest plot point
        within BoxSize of mouse click.  Returns None if too far from any
        point.  In fact, the algorithm returns the first point it finds
        that is within BoxSize of the requested point.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        i : int
            X coordinate of pixel to check
        j : int
            Y coordinate of pixel to check
        """
        for keyval in self.channel.knots:
            # First convert each data point to pixel coordinates
            pnti = self.transform(qwt.QwtPlot.xBottom, keyval) + self.xoffset
            pntj = self.transform(qwt.QwtPlot.yLeft, self.channel.knots[keyval]) + self.yoffset
            # Check to see if converted point is close enough
            if abs(i-pnti) <= self.BoxSize/2 and abs(j-pntj) <= self.BoxSize/2:
                return keyval
        return None

    def select(self):
        """
        The method select marks the Channel and Pane as selected.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        # Set the internal selected flag
        self.selected = True
        # Go to selected background
        self.canvas().setPalette(self._selectedPalette)

    def deselect(self):
        """
        The method deselect unmarks the Channel and Pane as selected.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        # Set the internal selected flag
        self.selected = False
        # Back to blue background
        self.canvas().setPalette(self._unselectedPalette)

    def invertselect(self):
        """
        The method invertselect inverts the selected status.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        if self.selected:
            self.deselect()
        else:
            self.select()

    def wheelEvent(self, event):
        """
        The method wheelEvent uses the mouse wheel to adjust the vertical
        scale of the pane.  Each click of the wheel expands or contracts
        the range while trying to keep the value where the cursor is 
        located stationary.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        event : type
        """
        numDegrees = event.angleDelta() / 8
        vertDegrees = numDegrees.y()

        # Get the data value where the cursor is located
        yplotval = self.invTransform(qwt.QwtPlot.yLeft, event.pos().y() - self.yoffset)
        minval = yplotval - (yplotval - self.minVal) * (1.0 - vertDegrees/100.0)
        maxval = yplotval - (yplotval - self.maxVal) * (1.0 - vertDegrees/100.0)
        self.setDataRange(minval, maxval)

    def mousePressEvent(self, event):
        """
        The method mousePressEvent handles the mouse press events.  They
        are:
            Left: If on knot (see FindClosestWithinBox) grab it
                else do nothing
            Shift-Left: If on knot (see FindClosestWithinBox) grab it
                else Add a new knot at clicked location and grab it
            Control-Left: If on knot (see FindClosestWithinBox) grab it
                else Select Channel
            Middle: Does nothing as wheel and clicks are tricky
            Right: Bring up pane menu

            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        event : Event
        """
        self.setOffsets()
        if event.buttons() == Qt.LeftButton :
            xplotval = self.invTransform(qwt.QwtPlot.xBottom, event.pos().x() - self.xoffset)
            yplotval = self.invTransform(qwt.QwtPlot.yLeft, event.pos().y() - self.yoffset)
            if self.channel.type == Channel.DIGITAL:
                if yplotval >= 0.5: yplotval = 1.0
                elif yplotval < 0.5: yplotval = 0.0
            # Find nearest point
            modifiers = QApplication.keyboardModifiers()
            nearkey = self.findClosestPointWithinBox(event.pos().x(), event.pos().y())
            if modifiers == Qt.ShiftModifier:
                # If shift key is down then we want to insert or delete a point
                # Push current state for undo
                pushState()

                if nearkey is not None:
                    # Delete currently selected point
                    del self.channel.knots[nearkey]
                    self.selectedKey = None
                    pass
                else:
                    # Insert a new point
                    if self.channel.minLimit > -1.0e33 or self.channel.maxLimit < 1.0e33:
                        # Apply limits
                        if yplotval > self.channel.maxLimit: yplotval = self.channel.maxLimit
                        if yplotval < self.channel.minLimit: yplotval = self.channel.minLimit
                    # Insert a new point and drag it around
                    nearkey = xplotval
                    self.channel.knots[nearkey] = yplotval
                    self.selectedKey = nearkey
                self.redrawme()
            elif modifiers == Qt.ControlModifier:
                # Select/deselect this channel
                self.invertselect()
            else:
                # Select a point
                if nearkey is not None:
                    # If close enough, select it and drag it around
                    self.selectedKey = nearkey
                    # Push current state for undo
                    pushState()
                pass
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
        """
        The method mouseReleaseEvent handles the mouse button release
        event.  This basically entails redrawing the pane and updating
        the XML display.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        event : type
        """
        if self.selectedKey is not None:
            self.selectedKey = None
            self.replot()
            main_win.updateXMLPane()
        pass

    def mouseMoveEvent(self, event):
        """
        The method mouseMoveEvent handles drag events in the pane.  Only
        the Left mouse button is supported when dragging a point around.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        event : type
        """
        if event.buttons() == Qt.LeftButton :
            if self.selectedKey is not None:
                xplotval = self.invTransform(qwt.QwtPlot.xBottom, event.pos().x() - self.xoffset)
                yplotval = self.invTransform(qwt.QwtPlot.yLeft, event.pos().y() - self.yoffset)
                if self.channel.type == Channel.DIGITAL:
                    if yplotval >= 0.5: yplotval = 1.0
                    elif yplotval < 0.5: yplotval = 0.0
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
        """
        The method setSlider redraws the current time bar to the
        specified time.  It is called during playback to match the
        time in all the other panes.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        timeVal : float
            The time at which the time bar should be set
        """
        if self.timeSlider is not None:
            self.timeSlider.setData([timeVal], [30000.0])
            self.replot()
        
    def redrawme(self):
        """
        The method redrawme does an extensive redraw of the pane, more
        extensive than just replot().  It regenerates the interpolated
        data line, rescales to the data limits, and redraws the limit
        bars.
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        # Recreate the data plot
        xdata,ydata = self.channel.getPlotData(self.minTime, self.maxTime, 100)
        if self.curve is not None:
            self.curve.setData(xdata, ydata)
        # Recreate the knot plot
        xdata,ydata = self.channel.getKnotData(self.minTime, self.maxTime, 100)
        if self.curve2 is not None:
            self.curve2.setData(xdata, ydata)

        if xdata is not None:
            # Erase tip on how to add points
            self.setToolTip('')
        self.redrawLimits()
        self.replot()

#####################################################################
# The ChannelMetadataWidget is used to view and edit the metadata
# for an individual channel
#####################################################################
class ChannelMetadataWidget(QDialog):
    """
    Class: ChannelMetadataWidget
        Derives from: (QDialog)

    Implements a widget for editing the metadata for a channel.  It
    customizes its appearance for the type of channel being edited.
    The edits are either text entries or pulldown lists.

    This widget is used both during creation of a channel and for
    editing a channel.  When editing, it is not alowed to change the
    channel name.  When creating, it is.  Should this be changed?
    ...
    Attributes
    ----------
    _channel : Channel
        The channel whose metadata is being edited
    title : str
        The name of the popup widget
    _nameedit : QLineEdit
    _typeedit : QComboBox
    _portedit : QComboBox
    _minedit : QLineEdit
    _maxedit : QLineEdit
    okButton : QPushButton
    cancelButton : QPushButton

    Methods
    -------
    __init__(self, channel=None, parent=None, editable=True)
    onAccepted(self)
    """
    def __init__(self, channel=None, parent=None, editable=True):
        """
        The method __init__
            member of class: ChannelMetadataWidget
        Parameters
        ----------
        self : ChannelMetadataWidget
        channel=None : Channel
            The channel whose metadata is being edited
        parent=None : QWidget
            Parent widget
        editable=True : boolean
            Whether the Name of the channel can be changed as well
        """
        super().__init__(parent)

        # Save animatronics channel for update if Save is selected
        self._channel = channel

        self.title = 'Channel MetaData Editor'
        widget = QWidget()
        layout = QFormLayout()
        
        self._nameedit = QLineEdit()
        self._nameedit.setReadOnly(not editable)
        self._nameedit.setText(self._channel.name)
        layout.addRow(QLabel('Name:'), self._nameedit)

        if self._channel is not None and self._channel.type != Channel.DIGITAL:
            self._typeedit = QComboBox()
            self._typeedit.addItems(('Linear', 'Spline', 'Step'))
            self._typeedit.setCurrentIndex(self._channel.type-1)
            layout.addRow(QLabel('Type:'), self._typeedit)

        self._portedit = QComboBox()
        if self._channel.type != Channel.DIGITAL:
            chancount = SystemPreferences['MaxServoChannels']
        else:
            chancount = SystemPreferences['MaxDigitalChannels']
        self._portedit.addItem('Unassigned')
        for i in range(chancount):
            self._portedit.addItem(str(i))
        if self._channel is not None:
            if self._channel.port >= 0:
                self._portedit.setCurrentText(str(self._channel.port))
        layout.addRow(QLabel('Channel:'), self._portedit)

        if self._channel is not None and self._channel.type != Channel.DIGITAL:
            self._minedit = QLineEdit()
            layout.addRow(QLabel('Min:'), self._minedit)
            self._maxedit = QLineEdit()
            layout.addRow(QLabel('Max:'), self._maxedit)
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
        """
        The method onAccepted handles the user acceptance of the changes.
        The values are validated and, if valid, the channel data is
        updated and redrawn.
            member of class: ChannelMetadataWidget
        Parameters
        ----------
        self : ChannelMetadataWidget
        """
        if self._channel.type != Channel.DIGITAL:
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
                    if self._channel.knots[keyval] < minVal:
                        minVal = self._channel.knots[keyval]
                    if self._channel.knots[keyval] > maxVal:
                        maxVal = self._channel.knots[keyval]
                if minVal < minLimit or maxVal > maxLimit:
                    # Get user concurrence to truncate values to new limits
                    msgBox = QMessageBox(parent=self)
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

        # Push current state for undo
        pushState()

        tstring = self._nameedit.text()
        if len(tstring) > 0:
            self._channel.name = tstring

        if self._channel.type != Channel.DIGITAL:
            self._channel.type = self._typeedit.currentIndex() + 1

        tstring = self._portedit.currentText()
        if len(tstring) > 0:
            if tstring == 'Unassigned':
                self._channel.port = -1
            else:
                self._channel.port = int(tstring)

        if self._channel.type != Channel.DIGITAL:
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
        main_win.updateXMLPane()

#####################################################################
# The MetadataWidget is used to view and edit the metadata
# for the overall Animatronics file
#####################################################################
class MetadataWidget(QDialog):
    """
    Class: MetadataWidget
        Derives from: (QDialog)

    Implements a popup widget for editing the metadata in the
    Animatronics file.
    ...
    Attributes
    ----------
    _animatronics : Animatronics
        The Animatronics object being edited
    title : str
        Title of the popup widget
    _startedit : QLineEdit
    _endedit : QLineEdit
    _rateedit : QLineEdit
    _audioedit : QLineEdit
    _audiofile : QLineEdit
    okButton : QPushButton
    cancelButton : QPushButton

    Methods
    -------
    __init__(self, inanim, parent=None)
    onAccepted(self)
    """
    def __init__(self, inanim, parent=None):
        """
        The method __init__
            member of class: MetadataWidget
        Parameters
        ----------
        self : MetadataWidget
        inanim : Animatronics
        parent=None : QWidget
        """
        super().__init__(parent)

        self._parent = parent

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
        if self._animatronics.newAudio is not None:
            self._audioedit = QLineEdit(str(self._animatronics.newAudio.audiostart))
            layout.addRow(QLabel('Audio Start Time:'), self._audioedit)
            layout.addRow(QLabel('Audio File:'))
            self._audiofile = QLineEdit('')
            self._audiofile.setText(self._animatronics.newAudio.audiofile)
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
        """
        The method onAccepted handles user acceptance of the new values
        and updates the Animatronics object.
            member of class: MetadataWidget
        Parameters
        ----------
        self : MetadataWidget
        """
        # Push current state for undo
        pushState()

        tstring = self._endedit.text()
        if len(tstring) > 0:
            self._animatronics.end = float(tstring)
        tstring = self._rateedit.text()
        if len(tstring) > 0:
            self._animatronics.sample_rate = float(tstring)
        tstring = self._audioedit.text()
        if len(tstring) > 0:
            self._animatronics.newAudio.audiostart = float(tstring)
        self.accept()
        if self._parent is not None:
            self._parent.redraw()
            self._parent.updateXMLPane()

#####################################################################
# The PreferencesWidget is used to view and edit the Preferences
# for the overall application
#####################################################################
class PreferencesWidget(QDialog):
    """
    Class: PreferencesWidget
        Derives from: (QDialog)

    Implements a popup widget for editing the metadata in the
    Animatronics file.
    ...
    Attributes
    ----------
    _animatronics : Animatronics
        The Animatronics object being edited
    title : str
        Title of the popup widget
    _widgets: dictionary
        Dictionary of the editing widgets that can be autoexpanded by just adding
        new variables to the SystemPreferences dictionary
    okButton : QPushButton
    cancelButton : QPushButton

    Methods
    -------
    __init__(self, parent=None)
    onAccepted(self)
    readPreferences()
    """
    def __init__(self, parent=None):
        """
        The method __init__
            member of class: PreferencesWidget
        Parameters
        ----------
        self : PreferencesWidget
        parent=None : QWidget
        """
        super().__init__(parent)

        self.parent = parent

        self.title = 'Preferences Editor'
        widget = QWidget()
        self._layout = QFormLayout()
        
        self._widgets = {}

        for pref in SystemPreferences:
            if type(SystemPreferenceTypes[pref]) is list:
                newedit = QComboBox()
                newedit.addItems(SystemPreferenceTypes[pref])
                newedit.setCurrentText(SystemPreferences[pref])
                self._layout.addRow(QLabel(pref), newedit)
                self._widgets[pref] = newedit
                pass
            else:
                newedit = QLineEdit(str(SystemPreferences[pref]))
                self._layout.addRow(QLabel(pref), newedit)
                self._widgets[pref] = newedit
        widget.setLayout(self._layout)

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
        """
        The method onAccepted handles user acceptance of the new values
        and updates the Animatronics object.
            member of class: PreferencesWidget
        Parameters
        ----------
        self : PreferencesWidget
        """
        for pref in self._widgets:
            if type(SystemPreferenceTypes[pref]) is list:
                SystemPreferences[pref] = self._widgets[pref].currentText()
            elif type(SystemPreferenceTypes[pref]) == 'int':
                SystemPreferences[pref] = int(self._widgets[pref].text())
            elif type(SystemPreferenceTypes[pref]) == 'float':
                SystemPreferences[pref] = float(self._widgets[pref].text())
            elif type(SystemPreferenceTypes[pref]) == 'bool':
                SystemPreferences[pref] = bool(self._widgets[pref].text())
            else:
                SystemPreferences[pref] = self._widgets[pref].text()
            pass
        self.accept()
        # Write out changes to preferences file wherever we put it
        try:
            preffile = os.path.join(os.path.expanduser("~"), '.animrc')
            with open(preffile, 'w') as prefs:
                for pref in SystemPreferences:
                    if type(SystemPreferenceTypes[pref]) is list:
                        prefs.write('%s:%s\n' % ( pref, SystemPreferences[pref]))
                    elif type(SystemPreferenceTypes[pref]) == 'float':
                        prefs.write('%s:%f\n' % ( pref, float(SystemPreferences[pref])))
                    elif type(SystemPreferenceTypes[pref]) == 'int':
                        prefs.write('%s:%d\n' % ( pref, int(SystemPreferences[pref])))
                    elif type(SystemPreferenceTypes[pref]) == 'bool':
                        prefs.write('%s:%d\n' % ( pref, int(SystemPreferences[pref])))
                    else:
                        prefs.write('%s:%s\n' % ( pref, SystemPreferences[pref]))

                # If MainWindow is set as parent do a redraw
                if self.parent is not None:
                    self.parent.redraw()
                    pass
        except:
            # Unable to write preferences file
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Unable to write preferences file:')
            msgBox.setInformativeText(preffile)
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()
            pass

    @staticmethod
    def readPreferences():
        """ Static method to read the preferences file if it exists """
        #try:
        if True:
            preffile = os.path.join(os.path.expanduser("~"), '.animrc')
            with open(preffile, 'r') as prefs:
                line = prefs.readline()
                while line:
                    # Strip off trailing whitespace and split on :
                    vals = line.rstrip().split(':')
                    if len(vals) == 2:
                        if SystemPreferenceTypes[vals[0]] == 'int':
                            SystemPreferences[vals[0]] = int(vals[1])
                        elif SystemPreferenceTypes[vals[0]] == 'float':
                            SystemPreferences[vals[0]] = float(vals[1])
                        elif SystemPreferenceTypes[vals[0]] == 'bool':
                            SystemPreferences[vals[0]] = bool(vals[1])
                        else:
                            SystemPreferences[vals[0]] = vals[1]
                    line = prefs.readline()
        #except:
            # Unable to read preferences file but that's okay
            pass

#####################################################################
# The Player class is a widget with playback controls
#####################################################################
class Player(QWidget):
    """
    Class: Player
        Derives from: (QWidget)

    Implements some features needed for playback of the animation.  It
    uses a QTimer to establish the playback rate, implements playback
    controls, and starts and stops audio playback when needed.  All
    time units within this class are in milliseconds and are thus
    actually positions within the playback for compatibility with the
    QMediaPlayer position functions.

    Generally, the Player plays the data within the time range of the
    audio (and other) panes within the application.  During playback, it
    continually looks to see if the audio should be playing and starts
    and stops the audio playback at the appropriate time.  Note that
    this is merely a request for the QMediaPlayer to play and is not
    synced as the QMediaPlayer may need time to start streaming the
    data.
    ...
    Attributes
    ----------
    _startPosition : int
        milliseconds at which to start playback
    _endPosition : int
        milliseconds at which to end playback
    _offset : int
        start time of audio in milliseconds
    _audio : Audio
    timer : QTimer
    interval : int
        step size of timer in milliseconds
    currPosition : int
        current playback position in milliseconds
    playing : boolean
        flag indicating play status
    _rewindbutton : QPushButton
    _playbutton : QPushButton
    _setleftbutton : QPushButton
    _setrightbutton : QPushButton
    timeChangedCallbacks : function array
        Array of functions to be called at each time interval

    Methods
    -------
    __init__(self, parent=None, audio=None, interval=20)
    setRange(self, minTime, maxTime)
    setOffset(self, audioStartTime)
    addTimeChangedCallback(self, callback)
    stepFunction(self)
    rewind(self)
    startplaying(self)
    stopplaying(self)
    play(self)
    is_media_playing(self)
    setLeftConnect(self, leftConnection)
    setRightConnect(self, rightConnection)
    """
    def __init__(self, parent=None, audio=None, interval=20):
        """
        The method __init__
            member of class: Player
        Parameters
        ----------
        self : Player
        parent=None : QWidget
        audio=None : Audio
        interval=20 : int
            timer interval in milliseconds
        """
        super().__init__(parent)

        self._startPosition = 0
        self._endPosition = 10000   # 10 seconds
        self._offset = 0

        self._audio = None
        self.mediaPlayer = None

        if audio is not None:
            self._offset = int(audio.audiostart*1000)
            self._audio = audio
            # Create/open QtMediaPlayer
            self.mediaPlayer = qm.QMediaPlayer()
            if usedPyQt == 5:
                # PyQt5 way
                self.mediaPlayer.setMedia(qm.QMediaContent(QUrl.fromLocalFile(self._audio.audiofile)))
            elif usedPyQt == 6:
                # PyQt6 way
                self.mediaPlayer.setSource(QUrl.fromLocalFile(self._audio.audiofile))
                self._audioOut = qm.QAudioOutput()
                self.mediaPlayer.setAudioOutput(self._audioOut)

        # Create timer to provide time steps in place of media
        self.timer = QTimer(self)
        self.interval = interval
        self.timer.setInterval(self.interval)
        self.timer.timeout.connect(self.stepFunction)
        self.currPosition = 0
        self.playing = False

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

        self.timeChangedCallbacks = []

    def setRange(self, minTime, maxTime):
        """
        The method setRange sets the playback time range.  This is
        generally called by the MainWindow when rescaling the audio
        pane.  The input floats are converted to milliseconds.
            member of class: Player
        Parameters
        ----------
        self : Player
        minTime : float
            Start time of playback range in seconds
        maxTime : float
            End time of playback range in seconds
        """
        self._startPosition = int(minTime * 1000)
        self._endPosition = int(maxTime * 1000)

    def addTimeChangedCallback(self, callback):
        """
        The method addTimeChangedCallback adds the specified callback
        function to the list of callbacks to be called at each time
        step.
            member of class: Player
        Parameters
        ----------
        self : Player
        callback : function
        """
        self.timeChangedCallbacks.append(callback)

    # Slots
    def stepFunction(self):
        """
        The method stepFunction is called by the timer at each time step.
        It checks to see if the media player should be playing and starts
        or stops it as needed.  It also calls all the registered callbacks
        and lets them know what time it is.
            member of class: Player
        Parameters
        ----------
        self : Player
        """
        if self.currPosition >= self._endPosition:
            self.stopplaying()
        else:
            # If player not already playing
            if self.mediaPlayer is not None:
                if not self.is_media_playing():
                    # Check to see if it should be
                    desiredPosn = self.currPosition - self._offset
                    if desiredPosn >= 0 and desiredPosn < self.mediaPlayer.duration():
                        self.mediaPlayer.setPosition(desiredPosn)
                        self.mediaPlayer.play()
        for cb in self.timeChangedCallbacks:
            cb(float(self.currPosition) / 1000.0)
        self.currPosition += self.interval

    def rewind(self):
        """
        The method rewind sets the current time back to the start time
        and notifies all the callbacks.
            member of class: Player
        Parameters
        ----------
        self : Player
        """
        # Go to left side of playable area
        self.currPosition = self._startPosition
        self.stopplaying()
        for cb in self.timeChangedCallbacks:
            cb(float(self.currPosition) / 1000.0)
        pass

    def startplaying(self):
        """
        The method startplaying starts the callback timer and does some UI
        stuff to begin playing.  It also makes sure the time is within the
        current time range.
            member of class: Player
        Parameters
        ----------
        self : Player
        """
        if self.currPosition < self._startPosition or self.currPosition >= self._endPosition:
            self.currPosition = self._startPosition
        self._playbutton.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.playing = True
        self.timer.start()
        self.stepFunction()   # Call the timer function for time=0

    def stopplaying(self):
        """
        The method stopplaying stops the timer and terminates any playing
        conditions.
            member of class: Player
        Parameters
        ----------
        self : Player
        """
        self.playing = False
        self._playbutton.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        if self.mediaPlayer is not None: self.mediaPlayer.pause()
        self.timer.stop()

    def play(self):
        """
        The method play toggles the play state.
            member of class: Player
        Parameters
        ----------
        self : Player
        """
        if self.playing:
            self.stopplaying()
        else:
            self.startplaying()

    def is_media_playing(self):
        """
        The method is_media_playing checks to see if the QMediaPlayer is
        currently playing.
            member of class: Player
        Parameters
        ----------
        self : Player
        """
        if self.mediaPlayer is not None:
            if usedPyQt == 5:    # PyQt5
                state = self.mediaPlayer.state()
                if state == qm.QMediaPlayer.PlayingState:
                    return True
                else:
                    return False
            elif usedPyQt == 6: # PyQt6
                if self.mediaPlayer.isPlaying():
                    return True
                else:
                    return False
        else:
            return False

    def setLeftConnect(self, leftConnection):
        """
        The method setLeftConnect specifies a callback to be called when
        the user clicks the Set Left button in the playback UI.
            member of class: Player
        Parameters
        ----------
        self : Player
        leftConnection : type
        """
        # Set start of play range to current time and set left edge time to it
        self._setleftbutton.clicked.connect(leftConnection)
        pass

    def setRightConnect(self, rightConnection):
        """
        The method setRightConnect specifies a callback to be called when
        the user clicks the Set Right button in the playback UI.
            member of class: Player
        Parameters
        ----------
        self : Player
        rightConnection : type
        """
        # Set start of play range to current time and set right edge time to it
        self._setrightbutton.clicked.connect(rightConnection)
        pass

#####################################################################
# The MainWindow class represents the Qt main window.
#####################################################################
class MainWindow(QMainWindow):
    """
    Class: MainWindow
        Derives from: (QMainWindow)

    Implements the main window for the Animatronics editing application.
    ...
    Shared Attributes
    ----------

    Attributes
    ----------
    filedialog : QFileDialog
    XMLPane : TextDisplayDialog
    ClipboardPane : TextDisplayDialog
    helpPane : TextDisplayDialog
    audioPlot : QwtPlot
        The plot Pane for the mono or left stereo channel
    audioCurve : QwtPlotCurve
        The plot data for the mono or left stereo channel subsampled from
        the full audio data
    audioPlotRight : QwtPlot
        The plot Pane for the right stereo channel
    audioCurveRight : QwtPlotCurve
        The plot data for the right stereo channel subsampled from
        the full audio data
    plots : dictionary
        Set of ChannePane obbjects for displaying the individual channels
        indexed by the channel name.
    previousStates : array
        Stack of XML and more of prechange states for Undo
    pendingStates : type
        Stack of XML and more of postchange states for Redo
    saveStateOkay : boolean
        Flag indicating that requested state saves be allowed
        Used when processing many changes that should fall under one Undo
    unsavedChanges : boolean
        Flag indicating if changes have been made and not saved
    lastXmin : float
        Value of minimum displayed time prior to zooming and scrolling
        Used for helping keep the zoom and scroll under control
    lastXmax : float
        Value of maximum displayed time prior to zooming and scrolling
        Used for helping keep the zoom and scroll under control
    audioMin : float
        The current minimum displayed time
    audioMax : float
        The current maximum displayed time
    totalMin : float
        The minimum time of all data in the system
    totalMax : float
        The maximum time of all data in the system
    _slideTime : float
        The current time used for displaying the green slider bar
    clipboard : QClipboard
        Clipboard for Copy and Paste
        This clipboard supports Copy/Paste between applications
    player : qm.QMediaPlayer
    animatronics : Animatronics
        The main object being manipulated consisting of audio, data channels
        and tags.
    timeSlider : QwtPlotCurve
        Implements the green bar showing current time in mono/left audio pane
    timeSliderRight : QwtPlotCurve
        Implements the green bar showing current time in right audio pane
    _mainarea : QScrollArea
        The central widget in the main window (everything but menubar) used
        because it attaches to the sides of the main window and stretches
        with changes in size.
    _playwidget : Player
        The Player object that controls playback and notifies channels of 
        the current play time.
    _plotarea : QWidget
        The region of the main window containing all the data panes
    selectedplots : dictionary
        List of names of selected panes/plots from the user selecting and
        deselecting channels
    _audioOut : qm.QAudioOutput
        Persistent audio object needed in PyQt6 to make it work
    lastX : int
    lastY : int
        Pixel x and y coords of initial mouse click in audio panes used to keep
        pan and zoom tidy.
    centerX : float
    centerY : float
        Data x and y values at initial mouse click in audio panes used to keep
        pan and zoom tidy.

    # All the menus and action items for the menubar
    file_menu : QMenu
    _new_file_action : QAction
    _open_file_action : QAction
    _selectaudio_action : QAction
    _merge_file_action : QAction
    _save_file_action : QAction
    _save_as_file_action : QAction
    _export_file_menu : QMenu
    _export_csv_file_action : QAction
    _export_vsa_file_action : QAction
    _exit_action : QAction
    edit_menu : QMenu
    _undo_action : QAction
    _redo_action : QAction
    _newchannel_action : QAction
    _newdigital_action : QAction
    _deletechannel_action : QAction
    _editmetadata_action : QAction
    _editpreferences_action : QAction
    view_menu : QMenu
    _resetscales_action : QAction
    _scaletoaudio_action : QAction
    _showall_action : QAction
    _showselector_action : QAction
    _show_audio_menu : QMenu
    _showmono_audio_action : QAction
    _showleft_audio_action : QAction
    _showright_audio_action : QAction
    _audio_amplitude_action : QAction
    _playbackcontrols_action : QAction
    channel_menu : QMenu
    _selectAll_action : QAction
    _deselectAll_action : QAction
    _selectorPane_action : QAction
    _Copy_action : QAction
    _Paste_action : QAction
    _Shift_action : QAction
    _Delete_action : QAction
    help_menu : QMenu
    _about_action : QAction
    _help_action : QAction
    _showXML_action : QAction

    Methods
    -------
    __init__(self, parent=None)
    setAnimatronics(self, inanim)
    openAnimFile(self)
    newAnimFile(self)
    mergeAnimFile(self)
    saveAnimFile(self)
    saveAsFile(self)
    exportCSVFile(self)
    exportVSAFile(self)
    handle_unsaved_changes(self)
    exit_action(self)
    undo_action(self)
    pushState(self)
    popState(self)
    redo_action(self)
    newdigital_action(self)
    newchannel_action(self)
    deleteChannels(self, chanList)
    deletechannel_action(self)
    selectaudio_action(self)
    editmetadata_action(self)
    editpreferences_action(self)
    timeChanged(self, currTime)
    setSlider(self, timeVal)
    playbackcontrols_action(self)
    resetscales_action(self)
    redrawAudio(self, minTime, maxTime)
    scaletoaudio_action(self)
    showall_action(self)
    showselector_action(self)
    showXML_action(self)
    updateXMLPane(self)
    updateClipboardPane(self)
    getPlotValues(self, pixelX, pixelY)
    mousePressEvent(self, event)
    mouseMoveEvent(self, event)
    mouseReleaseEvent(self, event)
    setTimeRange(self, minval, maxval)
    cutLeftSide(self)
    cutRightSide(self)
    about_action(self)
    help_action(self)
    showleft_audio_action(self, checked)
    showright_audio_action(self, checked)
    showaudio_amplitude_action(self, checked)
    selectAll_action(self)
    deselectAll_action(self)
    Copy_action(self)
    Paste_action(self)
    Shift_action(self)
    Delete_action(self)
    selectorPane_action(self)
    create_menus(self)
    """

    def __init__(self, parent=None):
        """
        The method __init__
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        parent=None : QWidget
            Parent of main window, generally None but might be embedded in
            a bigger application someday
        """
        super().__init__(parent)

        # Create file dialog used only for saving files
        self.filedialog = QFileDialog(parent=self, caption="Get Save Filename")
        self.filedialog.setOption(QFileDialog.DontUseNativeDialog)
        self.filedialog.setAcceptMode(QFileDialog.AcceptSave)
        self.filedialog.setFileMode(QFileDialog.AnyFile)

        # Create the XML display dialog for constant refresh
        self.XMLPane = TextDisplayDialog('XML', parent=self)
        self.ClipboardPane = TextDisplayDialog('Clipboard', parent=self)

        # Create the Help Popup
        self.helpPane = TextDisplayDialog('Animator Help', parent=self)

        # Initialize to no audio plot and add later if read
        self.audioPlot = None
        self.audioCurve = None
        self.audioPlotRight = None
        self.audioCurveRight = None

        # Initialize empty list of channel plots
        self.plots = {}

        # Initialize stacks of XML for Undo and Redo
        self.previousStates = []
        self.pendingStates = []
        self.saveStateOkay = True
        self.unsavedChanges = False

        # Create all the dropdown menus
        self.create_menus()

        # Initialize some stuff
        self.setWindowTitle("Animation Editor")
        self.resize(500, 600)
        self.lastX = 0.0
        self.lastY = 1.0
        self.centerX = 0.0
        self.centerY = 1.0
        self.lastXmin = 0.0
        self.lastXmax = 1.0
        self.audioMin = 0.0
        self.audioMax = 1.0
        self.totalMin = 0.0
        self.totalMax = 1.0
        self._slideTime = 0.0
        self.clipboard = QGuiApplication.clipboard()

        # Initialize with an empty animatronics object
        self.setAnimatronics(Animatronics())

    def setAnimatronics(self, inanim):
        """
        The method setAnimatronics
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        inanim : Animatronics
            The Animatronics object to be manipulated and displayed
        """

        """Set the active animatronics to the input"""
        self.animatronics = inanim
        self.updateXMLPane()

        # Clear and recreate UI here
        self.audioPlot = None
        self.audioCurve = None
        self.audioPlotRight = None
        self.audioCurveRight = None
        self.tagPlot = None
        self.timeSlider = None
        self.timeSliderRight = None
        self.tagSlider = None
        self._show_audio_menu.clear()
        self._show_audio_menu.setEnabled(False)

        # Add filename to window title
        if self.animatronics.filename is not None:
            self.setWindowTitle("Animation Editor - " +
                self.animatronics.filename)
        else:
            self.setWindowTitle("Animation Editor")

        # Create the bottom level widget and make it the main widget
        self._mainarea = QScrollArea(self)
        self._mainarea.setWidgetResizable(True)
        self._mainarea.setMaximumSize(3800,1000)
        self.setCentralWidget(self._mainarea)

        # Set up the playback widget
        self._playwidget = Player(audio=self.animatronics.newAudio)
        shortcut = QShortcut(QKeySequence("Ctrl+P"), self._mainarea)
        shortcut.activated.connect(self._playwidget.play)
        self._playwidget.setLeftConnect(self.cutLeftSide)
        self._playwidget.setRightConnect(self.cutRightSide)
        self._playwidget.addTimeChangedCallback(self.timeChanged)
        self._playwidget.hide()
        tlayout = QVBoxLayout(self._mainarea)
        tlayout.addWidget(self._playwidget)

        self._plotarea = QWidget()
        tlayout.addWidget(self._plotarea)

        # Add some tooltips to get user started
        if self.animatronics.newAudio is None and len(self.animatronics.channels) == 0:
            # Just beginning so help a lot
            self._plotarea.setToolTip('Hit File->Open Audio File to add audio or\nCtrl-N or Ctrl-D to add a new control channel')
        elif len(self.animatronics.channels) == 0:
            self._plotarea.setToolTip('Ctrl-N to add a new servo channel or\nCtrl-D to add a new digital channel')

        # Set the background color
        p = self._plotarea.palette()
        backcolor = QColor()
        backcolor.setRgb(150, 200, 250)
        p.setColor(self.backgroundRole(), backcolor)
        self._plotarea.setPalette(p)

        # Create layout to hold all the channels
        layout = QVBoxLayout(self._plotarea)
        layout.setContentsMargins(0, 0, 0, 0)

        # Remove all existing plot channels
        self.plots = {}
        self.selectedplots = []

        # Add the audio channel pane(s)
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
                self.audioPlot.setMaximumHeight(200)
                self.audioPlot.setToolTip('Click and drag Left mouse button\nup/down to zoom and left/right to scroll')
                # Add visibility checkbox to menu as visible initially
                self._show_audio_menu.addAction(self._showmono_audio_action)
                self._showmono_audio_action.setChecked(True)
            else:
                newplot = qwt.QwtPlot('Audio Left')
                self.audioCurve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=leftdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlot = newplot
                self.audioPlot.setMaximumHeight(200)
                self.audioPlot.setToolTip('Click and drag Left mouse button\nup/down to zoom and left/right to scroll')
                # Add visibility checkbox to menu as visible initially
                self._show_audio_menu.addAction(self._showleft_audio_action)
                self._showleft_audio_action.setChecked(True)
                newplot = qwt.QwtPlot('Audio Right')
                self.audioCurveRight = qwt.QwtPlotCurve.make(xdata=xdata, ydata=rightdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlotRight = newplot
                self.audioPlotRight.setMaximumHeight(200)
                self.audioPlotRight.setToolTip('Click and drag Left mouse button\nup/down to zoom and left/right to scroll')
                # Add visibility checkbox to menu as visible initially
                self._show_audio_menu.addAction(self._showright_audio_action)
                self._showright_audio_action.setChecked(True)

            # Set range to match length of audio
            if self.audioMax > self.totalMax: self.totalMax = self.audioMax
            self.lastXmin = self.audioMin
            self.lastXmax = self.audioMax

            self._show_audio_menu.setEnabled(True)
            self._audio_amplitude_action.setChecked(False)

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

        else:
            # Mute the player because it does not seem to clear out old audio quite rightly
            # Not sure what I want to do here
            pass

        # Optionally add the tags pane here
        tags = self.animatronics.tags
        self.tagPlot = TagPane(self, tags, self)
        """
        if len(tags) > 0:
            self.tagPlot = qwt.QwtPlot('Tags')
            for tag in tags:
                marker = qwt.QwtPlotMarker(tags[tag])
                marker.setValue(tag, 0.0)
                marker.setLabel(tags[tag])
                marker.attach(self.tagPlot)
                marker.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
                marker.setLineStyle(qwt.QwtPlotMarker.VLine)
            self.tagPlot.setAxisScale(qwt.QwtPlot.yLeft, -1.0, 1.0, 2.0)
            self.tagPlot.setAxisTitle(qwt.QwtPlot.yLeft, 'Tags')
            self.tagPlot.setAxisMaxMinor(qwt.QwtPlot.yLeft, 1)
            layout.addWidget(self.tagPlot)

            self.tagSlider = qwt.QwtPlotCurve()
            self.tagSlider.setStyle(qwt.QwtPlotCurve.Sticks)
            self.tagSlider.setData([self.audioMin], [30000.0])
            self.tagSlider.setPen(Qt.green, 3.0, Qt.SolidLine)
            self.tagSlider.setBaseline(-30000.0)
            self.tagSlider.attach(self.tagPlot)

        """
        self.tagPlot.redrawTags(self.lastXmin, self.lastXmax)
        layout.addWidget(self.tagPlot)

        # Improve layout by sticking audio to the top
        if len(self.animatronics.channels) == 0:
            layout.addStretch()

        # Add panes for all the channels
        if SystemPreferences['Ordering'] == 'Alphabetic':
            channelList = sorted(self.animatronics.channels.keys())
        elif SystemPreferences['Ordering'] == 'Numeric':
            index = {}
            minIndex = -1000
            for channel in self.animatronics.channels:
                if self.animatronics.channels[channel].type == Channel.DIGITAL:
                    offset = 2000
                else:
                    offset = 0
                if self.animatronics.channels[channel].port >= 0:
                    index[self.animatronics.channels[channel].port + offset] = channel
                else:
                    index[minIndex + offset] = channel
                    minIndex += 1
            channelList = []
            for i in sorted(index.keys()):
                channelList.append(index[i])
        else:
            channelList = self.animatronics.channels

        for channel in channelList:
            chan = self.animatronics.channels[channel]
            newplot = ChannelPane(self._plotarea, chan, mainwindow=self)
            newplot.settimerange(self.lastXmin, self.lastXmax)
            if len(chan.knots) == 0:
                newplot.setToolTip('Use Shift-LeftMouseButton to add control points')
            layout.addWidget(newplot)
            self.plots[chan.name] = newplot

        self._playwidget.setRange(self.lastXmin, self.lastXmax)
            

    def openAnimFile(self):
        """
        The method openAnimFile opens a file dialog for the user to select
        an anim file to load.  It replaces all of the previous 
        Animatronics object except Undo history.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        if self.handle_unsaved_changes():
            """Get filename and open as active animatronics"""
            fileName, _ = QFileDialog.getOpenFileName(self,"Get Open Filename", "",
                                "Anim Files (*.anim);;All Files (*)",
                                options=QFileDialog.DontUseNativeDialog)

            if fileName:
                # Push current state for undo
                pushState()

                newAnim = Animatronics()
                try:
                    newAnim.parseXML(fileName)
                    self.setAnimatronics(newAnim)
                    # Clear out Redo history
                    self.pendingStates = []
                    self.unsavedChanges = False
        
                except Exception as e:
                    popState()
                    sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                    sys.stderr.write("Message: %s\n" % e)
                    return

    def redraw(self):
        self.setAnimatronics(self.animatronics)
        

    def newAnimFile(self):
        """
        The method newAnimFile clears out all of the previous
        Animatronics object except Undo history and starts from scratch.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        if self.handle_unsaved_changes():
            # Push current state for undo
            pushState()

            """Clear animatronics and start from scratch"""
            newAnim = Animatronics()
            self.setAnimatronics(newAnim)
            # Clear out edit history
            self.pendingStates = []
            self.unsavedChanges = False
    
    def mergeAnimFile(self):
        """
        The method mergeAnimFile opens a file dialog for the user to select
        an Animatronics file to load and then merges that file into the
        current Animatronics. (Not implemented yet).

        The merge process is intended to be used for combining multiple
        people's work on different sections of the animation.  It adds
        new channels to the current set and combines knots for channels
        with the same name.  It does not replace the current audio file.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """Merge an animatronics file into the current one"""
        fileName, _ = QFileDialog.getOpenFileName(self,"Get Merge Filename", "",
                            "Anim Files (*.anim);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                # Push current state for undo
                pushState()
                self.animatronics.parseXML(fileName)
                self.setAnimatronics(self.animatronics)
    
            except Exception as e:
                popState()
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return

        pass

    def saveAnimFile(self):
        """
        The method saveAnimFile saves the current animation file,
        overwriting any previous content.  If the user built the
        current animation from scratch and no filename has been set,
        a file dialog will be opened to query the user for a filename.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """Save the current animatronics file"""
        if self.animatronics.filename is None:
            # If the filename is not set, use the forcing dialog to get it
            self.saveAsFile()
        else:
            # Write to the previously read/written file
            try:
                with open(self.animatronics.filename, 'w') as outfile:
                    outfile.write(self.animatronics.toXML())
                self.unsavedChanges = False
    
            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % self.animatronics.filename)
                sys.stderr.write("Message: %s\n" % e)
                return
        pass

    def saveAsFile(self):
        """
        The method saveAsFile opens a file dialog to query the user for
        a filename to which to save the animation.  If the file exists, the
        user is prompted to confirm overwrite.  If the current animation
        does not have a filename associated with it, the new filename is
        associated with it.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """Save the current animatronics file"""
        self.filedialog.setDefaultSuffix('anim')
        self.filedialog.setNameFilter("Anim Files (*.anim);;All Files (*)")
        if self.filedialog.exec_():
            try:
                fileName = self.filedialog.selectedFiles()[0]
                with open(fileName, 'w') as outfile:
                    outfile.write(self.animatronics.toXML())
                self.unsavedChanges = False
                if self.animatronics.filename is None:
                    self.animatronics.filename = fileName
                    self.setWindowTitle("Animation Editor - " + 
                        self.animatronics.filename)
    
            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return

        pass

    def exportCSVFile(self):
        """
        The method exportCSVFile opens a file dialog to query the user for
        a filename and then saves a comma-separated values (CSV) file.
        The rows in the CSV file will be at exact time intervals as
        specified in the rate of the Animatronics (e.g. 50Hz or 20msec).

        The content of the CSV file will be a column for time followed by
        a column for each channel that contains at least one data point.
        The time range in the file will cover the entire duration of the
        current animation.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

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

        # Get the data points for each column
        for plot in self.plots:
            values = self.plots[plot].channel.getValuesAtTimeSteps(starttime, endtime, samplestep)
            if values is not None:
                columns[plot] = values

        # Get the filename to write to
        self.filedialog.setDefaultSuffix('csv')
        self.filedialog.setNameFilter("CSV Files (*.csv);;All Files (*)")
        if self.filedialog.exec_():
            try:
                fileName = self.filedialog.selectedFiles()[0]
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
        """
        The method exportVSAFile exports the current animatronics file
        into a Brookshire VSA format.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """Export the current animatronics file into a Brookshire VSA format"""
        pass

    def handle_unsaved_changes(self):
        """
        The method handle_unsaved_changes detects unsaved changes and
        queries the user to confirm Save or Don't Save.  It is called
        when opening or creating a new animation or exiting.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        if self.unsavedChanges:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('The current animation has unsaved changes')
            msgBox.setInformativeText("Save them?")
            msgBox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            msgBox.setDefaultButton(QMessageBox.Save)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()
            if ret == QMessageBox.Save:
                self.saveAnimFile()
            elif ret == QMessageBox.Cancel:
                return False
        return True

    def closeEvent(self, event):
        """ Catch main close event and pass it to our handler """
        if self.handle_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    def exit_action(self):
        """
        The method exit_action terminates the application.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        # Just closing here puts the onus on eventClose to handle cleanup
        self.close()

    def undo_action(self):
        """
        The method undo_action undoes the last action performed by the user.
        This is done by maintaining two stacks of state.  Each time an
        action is performed by the user that changes the animation, the
        entire XML is pushed onto the previous state stack.  This method
        pushed the current state onto the Redo stack and then restores the
        current state from the top of the previous state stack.

        In addition to the XML of the animation, certain display state is
        also pushed on the stack so the display may be restored to the
        previous state as well. (Not implemented yet)

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.saveStateOkay = False
        if len(self.previousStates) > 0:
            if self.animatronics is not None:
                # Push current state onto pending states
                currState = self.animatronics.toXML()
                self.pendingStates.append((currState, self.unsavedChanges))
                # Pop last previous state
                currState = self.previousStates.pop()
                self.animatronics.fromXML(currState[0])
                self.setAnimatronics(self.animatronics)
                self.unsavedChanges = currState[1]
                print('Number of undos left:', len(self.previousStates))
        else:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('At earliest state')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
        self.saveStateOkay = True
        # Keep XML display pane up to date with latest
        self.XMLPane.setText(self.animatronics.toXML())
            
        pass

    def pushState(self):
        """
        The method pushState pushes the current animation state onto the
        previous state stack.  It is called from a global function that is
        called by any code that modifies the animation.  It also clears
        out any pending states that Redo might have restored and notes
        thatt changes have been that must be saved.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        if self.saveStateOkay:
            # Push current state onto previous states
            currState = self.animatronics.toXML()
            self.previousStates.append((currState, self.unsavedChanges))
            # Taking a new path so clear out pending states
            self.pendingStates = []
            self.unsavedChanges = True

    def popState(self):
        """
        The method popState simply discards the last saved state and is
        called when some update failed to change the current state as
        expected.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """Discard last state saved as some update failed"""
        self.previousStates.pop()

    def redo_action(self):
        """
        The method redo_action pushes the current state onto the Undo stack
        and pulls the top state off the Redo stack to replace it.  The Undo
        action pushes states onto the Redo stack and Redo does the opposite.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.saveStateOkay = False
        if len(self.pendingStates) > 0:
            if self.animatronics is not None:
                # Push current state onto pending states
                currState = self.animatronics.toXML()
                self.previousStates.append((currState, self.unsavedChanges))
                # Pop next pending state
                currState = self.pendingStates.pop()
                self.animatronics.fromXML(currState[0])
                self.setAnimatronics(self.animatronics)
                self.unsavedChanges = currState[1]
                print('Number of redos left:', len(self.pendingStates))
        else:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('At latest state')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
        self.saveStateOkay = True
        # Keep XML display pane up to date with latest
        self.XMLPane.setText(self.animatronics.toXML())
            
        pass

    def newdigital_action(self):
        """
        The method newdigital_action creates a new Digital channel.  It
        brings up the metadata widget to initialize the channel metadata
        and adds the empty channel to the set of channels.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform newdigital action"""
        main_win.saveStateOkay = False
        tempChannel = Channel(intype=Channel.DIGITAL)
        td = ChannelMetadataWidget(channel=tempChannel, parent=self)
        code = td.exec_()
        main_win.saveStateOkay = True

        # If user signals accept
        if code == QDialog.Accepted:
            # Check to see if channel already exists
            ret = None
            text = tempChannel.name
            if len(text) <= 0:
                # If channel name is empty it is an error
                msgBox = QMessageBox(parent=self)
                msgBox.setText('A channel MUST have a name of at least one character and must be unique')
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
            elif text in self.animatronics.channels:
                # If the channel name is already in use so prompt user
                msgBox = QMessageBox(parent=self)
                msgBox.setText('The channel "%s" already exists.' % text)
                msgBox.setInformativeText("Replace it?")
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
            if ret is None or ret == QMessageBox.Yes:
                # Push current state for undo
                pushState()

                self.animatronics.channels[text] = tempChannel
                self.setAnimatronics(self.animatronics)
        pass

    def newchannel_action(self):
        """
        The method newchannel_action creates a new Servo channel.  It
        brings up the metadata widget to initialize the channel metadata
        and adds the empty channel to the set of channels.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform newchannel action"""
        main_win.saveStateOkay = False
        tempChannel = Channel()
        td = ChannelMetadataWidget(channel=tempChannel, parent=self)
        code = td.exec_()
        main_win.saveStateOkay = True

        if code == QDialog.Accepted:
            # Check to see if channel already exists
            ret = None
            text = tempChannel.name
            if len(text) <= 0:
                # If channel name is empty it is an error
                msgBox = QMessageBox(parent=self)
                msgBox.setText('A channel MUST have a name of at least one character and must be unique')
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
            elif text in self.animatronics.channels:
                # If the channel name is already in use so prompt user
                msgBox = QMessageBox(parent=self)
                msgBox.setText('The channel "%s" already exists.' % text)
                msgBox.setInformativeText("Replace it?")
                msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
            if ret is None or ret == QMessageBox.Yes:
                # Push current state for undo
                pushState()

                self.animatronics.channels[text] = tempChannel
                self.setAnimatronics(self.animatronics)
        pass

    def deleteChannels(self, chanList):
        """
        The method deleteChannels accepts a list of channels to be deleted
        and does so, after prompting the user to confirm.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        chanList : str array
            List of names of channels to be deleted
        """
        # Confirm deletion with user
        inform_text = ''
        for name in chanList:
            if len(inform_text) > 0: inform_text += ', '
            inform_text += name
        msgBox = QMessageBox(parent=self)
        msgBox.setText('Are you really sure you want to delete these channels?')
        msgBox.setInformativeText(inform_text)
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msgBox.setIcon(QMessageBox.Warning)
        ret = msgBox.exec_()
        if ret == QMessageBox.Yes:
            # Push current state for undo
            pushState()

            for name in chanList:
                del self.animatronics.channels[name]
            self.setAnimatronics(self.animatronics)

    def deletechannel_action(self):
        """
        The method deletechannel_action brings up a checklist of channels
        for the user to select one or more to be deleted.  Once the user
        signals accept, the list is sent for deletion.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

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
        """
        The method selectaudio_action opens a file dialog for the user to   
        select an audio file for use with the animation.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform selectaudio action"""
        fileName, _ = QFileDialog.getOpenFileName(self,"Get Open Filename", "",
                            "Wave Audio Files (*.wav);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            # Push current state for undo
            pushState()

            try:
                self.animatronics.set_audio(fileName)
                self.setAnimatronics(self.animatronics)
    
            except Exception as e:
                popState()
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return

        pass

    def editmetadata_action(self):
        """
        The method editmetadata_action brings up the metadata widget for
        the animation to allow the user to view or edit the metadata.
        Some metadata is not editable and can only be viewed.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        qd = MetadataWidget(self.animatronics, parent=self)
        qd.exec_()
        pass

    def editpreferences_action(self):
        """
        The method editpreferences_action brings up a preferences widget for
        the animation to allow the user to view or edit the preferences.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        qd = PreferencesWidget(parent=self)
        qd.exec_()
        pass

    def timeChanged(self, currTime):
        """
        The method timeChanged passes the new time value on to set all
        the sliders.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        currTime : float
            Time in seconds to set as the current time
        """
        self.setSlider(currTime + self.animatronics.start)

    def setSlider(self, timeVal):
        """
        The method setSlider sets the green slider bars showing current
        time in all the panes.  The 30000.0 is a constant that shows how
        high the bar goes in the plot window.  It is approximately the
        maximum value that a wave audio file can hold so it should cover
        the entire vertical range of the audio panes.  SHOULD be set to
        match the size of the audio samples.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        timeVal : float
            Time in seconds to set as the current time
        """
        if self.timeSlider is not None:
            self.timeSlider.setData([timeVal], [30000.0])
            self.audioPlot.replot()
        if self.timeSliderRight is not None:
            self.timeSliderRight.setData([timeVal], [30000.0])
            self.audioPlotRight.replot()
        if self.tagPlot is not None:
            self.tagPlot.setSlider(timeVal)
        for plot in self.plots:
            self.plots[plot].setSlider(timeVal)
        self._slideTime = timeVal

    def playbackcontrols_action(self):
        """
        The method playbackcontrols_action toggles the visibility of the
        playback widget with Rewind, Play, and Set Left and Right controls.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        if self._playwidget.isHidden():
            self._playwidget.show()
        else:
            self._playwidget.hide()
        pass

    def resetscales_action(self):
        """
        The method resetscales_action resets the time range to match the
        minimum and maximum times of all the channels.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        # Reset all horizontal and vertical scales to max X range but not local Y range
        minTime = 0.0
        maxTime = 0.0
        if self.audioPlot is not None:
            # Check time range of audio
            minTime = self.audioMin
            maxTime = self.audioMax
        for i in self.plots:
            # Check time range of every plot
            lmin,lmax = self.plots[i].getTimeRange()
            if lmin < minTime: minTime = lmin
            if lmax > maxTime: maxTime = lmax

        # Actually set all the ranges to the max
        self.setTimeRange(minTime, maxTime)
        pass

    def redrawAudio(self, minTime, maxTime):
        """
        The method redrawAudio resamples the audio channels and redraws them
        between the specified min and max times.  It plots either value or
        amplitude depending on the check state.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        minTime : type
        maxTime : type
        """
        if self.audioPlot is not None and self.audioCurve is not None:
            if self.animatronics.newAudio is not None:
                if self._audio_amplitude_action.isChecked():
                    xdata, ydata, rightdata = self.animatronics.newAudio.getAmplitudeData(minTime, maxTime, 4000)
                else:
                    xdata, ydata, rightdata = self.animatronics.newAudio.getPlotData(minTime, maxTime, 4000)
                self.audioCurve.setData(xdata, ydata)
                if self.audioCurveRight is not None and rightdata is not None:
                    self.audioCurveRight.setData(xdata, rightdata)
            self.audioPlot.setAxisScale(qwt.QwtPlot.xBottom, minTime, maxTime)
            self.audioPlot.replot()
            if self.audioPlotRight is not None:
                self.audioPlotRight.setAxisScale(qwt.QwtPlot.xBottom, minTime, maxTime)
                self.audioPlotRight.replot()
                
    def redrawTags(self, minTime, maxTime):
        if self.tagPlot is not None:
            self.tagPlot.redrawTags(minTime, maxTime)
                

    def scaletoaudio_action(self):
        """
        The method scaletoaudio_action resets the visible time range to 
        match the length of the audio data, even of come channels contain
        data points outside that range.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform scaletoaudio action"""
        # Reset all horizontal scales to audio range but not vertical scales to local Y ranges
        self.setTimeRange(self.audioMin, self.audioMax)
        pass

    def showall_action(self):
        """
        The method showall_action causes all audio and data channels to be
        displayed.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform showall action"""
        # Unhide audio channels
        if self.audioPlot is not None: self.audioPlot.show()
        self._showmono_audio_action.setChecked(True)
        self._showleft_audio_action.setChecked(True)
        if self.audioPlotRight is not None: self.audioPlotRight.show()
        self._showright_audio_action.setChecked(True)

        # Unhide all channels
        for i in self.plots:
            self.plots[i].show()
        pass

    def showselector_action(self):
        """
        The method showselector_action brings up a checklist of channels for
        the user to show or hide whatever channels they wish.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

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
            # Actually set the show/hide state
            for name in self.animatronics.channels:
                if name in form.choices:
                    self.plots[name].show()
                else:
                    self.plots[name].hide()
        pass

    def showClipboard_action(self):
        """
        The method showClipboard_action brings up a text window that displays
        the current clipboard content.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        # Pop up text window containing XML to view (uneditable)
        self.ClipboardPane.setText(self.clipboard.text())
        self.ClipboardPane.setWindowTitle('Clipboard')
        self.ClipboardPane.show()
        pass

    def showXML_action(self):
        """
        The method showXML_action brings up a text window that displays
        the current XML of the animation.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        # Pop up text window containing XML to view (uneditable)
        self.XMLPane.setText(self.animatronics.toXML())
        self.XMLPane.setWindowTitle('XML')
        self.XMLPane.show()
        pass

    def updateXMLPane(self):
        """
        The method updateXMLPane updates the text in the XML display window
        to the current state.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.XMLPane.setText(self.animatronics.toXML())

    def getPlotValues(self, pixelX, pixelY):
        """
        The method getPlotValues converts cursor coordinates in the audio
        pane of the display into time and magnitude values.  These are
        used to control the zoom and pan within the time range.

        The pixel coordinates are relative to the upper left corner of the
        rectangle containing the plot and scales and margins.  The size of
        the scale and margin and title and such not at the top and left
        must be determined and subtracted to get the coordinates within
        the plot area.  Then the transforms work to convert to data values.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        pixelX : type
        pixelY : type
        """
        if self.audioPlot is None:
            return None, None

        # Get the rectangle containing the stuff to left of plot
        rect = self.audioPlot.plotLayout().scaleRect(qwt.QwtPlot.yLeft)
        # Get the width of that rectangle to use as offset in X
        xoffset = rect.width()
        valueX = self.audioPlot.invTransform(qwt.QwtPlot.xBottom, pixelX - xoffset)

        # Get the rectangle containing the stuff above top of plot
        rect = self.audioPlot.plotLayout().scaleRect(qwt.QwtPlot.xTop)
        # Get the height of that rectangle to use as offset in Y
        yoffset = rect.height()
        valueY = self.audioPlot.invTransform(qwt.QwtPlot.yLeft, pixelY - yoffset)

        return valueX,valueY

    def mousePressEvent(self, event):
        """
        The method mousePressEvent marks the initial press of the left mouse
        button within an audio window and saves the data values at that
        point.  These are used to control the zoom and scroll when the mouse
        is dragged.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        event : type
        """
        if self.audioPlot is None: return
        if event.buttons() == Qt.LeftButton:
            self.lastX = event.pos().x()
            self.lastY = event.pos().y()
            self.centerX,self.centerY = self.getPlotValues(event.pos().x(), event.pos().y())

    def mouseMoveEvent(self, event):
        """
        The method mouseMoveEvent performs zoom and drag within the audio
        panes.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        event : type
        """
        if self.audioPlot is None: return
        if event.buttons() == Qt.LeftButton:
            # Compute how far the cursor has moved vertically and horizontally
            deltaX = self.lastX - event.pos().x()
            deltaY = self.lastY - event.pos().y()
            self.lastY = event.pos().y()
            # Use horizontal motion to drag
            newCenterX,_ = self.getPlotValues(event.pos().x(), event.pos().y())
            # Use vertical motion to zoom
            yScaler = pow(2.0, float(deltaY)/50.0)
            self.setTimeRange(self.centerX + (self.lastXmin - self.centerX) / yScaler + (self.centerX - newCenterX),
                self.centerX + (self.lastXmax - self.centerX) / yScaler + (self.centerX - newCenterX))
            
                
    def mouseReleaseEvent(self, event):
        """
        The method mouseReleaseEvent does nothing at this time
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        event : type
        """
        if self.audioPlot is None: return
        pass

    def setTimeRange(self, minval, maxval):
        """
        The method setTimeRange sets the displayed time range for all panes.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        minval : type
        maxval : type
        """
        if minval < maxval:
            self.lastXmax = maxval
            self.lastXmin = minval
            self._playwidget.setRange(self.lastXmin, self.lastXmax)
            self.redrawAudio(self.lastXmin, self.lastXmax)
            self.redrawTags(self.lastXmin, self.lastXmax)
            for i in self.plots:
                self.plots[i].settimerange(self.lastXmin, self.lastXmax)

    def cutLeftSide(self):
        """
        The method cutLeftSide sets the left edge time value to be the
        current slider position to support using it to set the playback
        range.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.setTimeRange(self._slideTime, self.lastXmax)
    
    def cutRightSide(self):
        """
        The method cutRightSide sets the right edge time value to be the
        current slider position to support using it to set the playback
        range.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.setTimeRange(self.lastXmin, self._slideTime)

    def about_action(self):
        """
        The method about_action brings up the About text in a popup.  About
        and Help use the same popup so only one can be displayed at a time.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.helpPane.setSource('docs/About.md')
        self.helpPane.resize(500, 180)
        self.helpPane.setWindowTitle('About Animator')
        self.helpPane.show()

    def help_action(self):
        """
        The method help_action brings up the Help text in a popup.  About
        and Help use the same popup so only one can be displayed at a time.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.helpPane.setSource('docs/Help.md')
        self.helpPane.resize(600, 700)
        self.helpPane.setWindowTitle('Animator Help')
        self.helpPane.show()

    def hotkeys_action(self):
        """
        The method help_action brings up the Hot Kyes text in a popup.  About
        and Help use the same popup so only one can be displayed at a time.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.helpPane.setSource('docs/HotKeys.md')
        self.helpPane.resize(600, 700)
        self.helpPane.setWindowTitle('Hot Key Cheat Sheet')
        self.helpPane.show()

    def showleft_audio_action(self, checked):
        """
        The method showleft_audio_action displays or hides the left/mono
        audio channel per the menu checkbox.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        checked : boolean
            Indicates visibility of the audio channel
        """
        if self.audioPlot is not None:
            if checked: self.audioPlot.show()
            else: self.audioPlot.hide()

    def showright_audio_action(self, checked):
        """
        The method showright_audio_action displays or hides the right
        audio channel per the menu checkbox.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        checked : boolean
            Indicates visibility of the audio channel
        """
        if self.audioPlotRight is not None:
            if checked: self.audioPlotRight.show()
            else: self.audioPlotRight.hide()

    def showaudio_amplitude_action(self, checked):
        """
        The method showaudio_amplitude_action optionally displays the audio
        channels in a value or amplitude mode.  Value mode shows the plus
        and minus values of the signal.  Amplitude mode picks maximum values
        within a window and displays those.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        checked : type
        """
        self.redrawAudio(self.lastXmin, self.lastXmax)
        return

    def selectAll_action(self):
        """
        The method selectAll_action selects all channels via the ctrl-A hot
        key or the corresponding menu item.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        for name in self.plots:
            self.plots[name].select()
        pass

    def deselectAll_action(self):
        """
        The method deselectAll_action deselects all channels via the 
        ctrl-shift-A hot key or the corresponding menu item.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        for name in self.plots:
            self.plots[name].deselect()
        pass

    def Copy_action(self):
        """
        The method Copy_action copies the content of a single channel to
        the clipboard to be pasted elsewhere.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform Copy action"""
        # Make sure there is only one channel selected
        selection = []
        for name in self.plots:
            if self.plots[name].selected:
                selection.append(name)

        if len(selection) == 0:
            # If none are selected, see if the cursor is in a ChannelPane
            cursorpos = QCursor.pos()
            channame = None
            for name in self.plots:
                if self.plots[name].isHidden(): continue
                widgetpos = self.plots[name].mapFromGlobal(cursorpos)
                width = self.plots[name].size().width()
                height = self.plots[name].size().height()
                if widgetpos.x() > 0 and widgetpos.x() < width and widgetpos.y() > 0 and widgetpos.y() < height:
                    channame = name
                    break
            if channame is not None:
                self.clipboard.setText(self.animatronics.channels[name].toXML())
                self.ClipboardPane.setText(self.clipboard.text())
        elif len(selection) > 1:
            # Warn that they need to select only one channel to copy
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Whoops - Must select one and only one channel to copy')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()
            return
            pass
        else:
            # Copy to clipboard
            name = selection[0]
            self.clipboard.setText(self.animatronics.channels[name].toXML())
            self.ClipboardPane.setText(self.clipboard.text())
            # Deselect the copied channel to avoid pasting right back over it
            self.plots[name].deselect()
        pass

    def Paste_action(self):
        """
        The method Paste_action pastes the content of the clipboard, if
        not empty, to all selected channels or the channel under the cursor.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform Paste action"""
        if len(self.clipboard.text()) == 0:
            # Warn that they need to have copied something
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Whoops - Empty clipboard')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()
            return

        # Get a list of all the currently selected channels
        selection = []
        for name in self.plots:
            if self.plots[name].selected:
                selection.append(name)

        if len(selection) == 0:
            # If none are selected, see if the cursor is in a ChannelPane
            cursorpos = QCursor.pos()
            channame = None
            for name in self.plots:
                # Check if cursor is in any visible channel pane
                if self.plots[name].isHidden(): continue
                widgetpos = self.plots[name].mapFromGlobal(cursorpos)
                width = self.plots[name].size().width()
                height = self.plots[name].size().height()
                if widgetpos.x() > 0 and widgetpos.x() < width and widgetpos.y() > 0 and widgetpos.y() < height:
                    channame = name
                    break
            if channame is not None:
                # Push current state for undo
                pushState()

                # Paste from clipboard
                try:
                    root = ET.fromstring(self.clipboard.text())
                    self.animatronics.channels[channame].parseXML(root)
                    self.plots[channame].redrawme()
                    main_win.updateXMLPane()
                except:
                    popState()
                    pass
        else:
            # Push current state for undo
            pushState()

            # Paste the clipboard into all selected channels
            try:
                root = ET.fromstring(self.clipboard.text())
                for name in selection:
                    self.animatronics.channels[name].parseXML(root)
                    self.plots[name].redrawme()
                main_win.updateXMLPane()
            except:
                popState()
                pass
        pass

    def Shift_action(self):
        """
        The method Shift_action pops up a widget allowing the user to
        shift the data points in selected channels left or right in time.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        pass

    def Delete_action(self):
        """
        The method Delete_action optionally deletes all the selected channels.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform Delete action"""
        dellist = []
        for name in self.plots:
            if self.plots[name].selected:
                dellist.append(name)
        if len(dellist) > 0:
            self.deleteChannels(dellist)
        pass

    def selectorPane_action(self):
        """
        The method selectorPane_action brings up a checklist for the user
        to select specific channels. (Not implemented yet)

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        print('Hit selectorPane action')

        """
        # Testing of preloading wave file into QByteArray to play - fails
        player = qm.QMediaPlayer(self);

        file = QFile("drama.wav");
        file.open(QIODevice.ReadOnly);
        arr = QByteArray();
        arr.append(file.readAll());
        file.close();
        buffer = QBuffer(arr);
        buffer.open(QIODevice.ReadWrite);

        player.setMedia(qm.QMediaContent(QUrl.fromLocalFile("drama.wav")), buffer);
        player.play();
        """
        pass

    def togglePane_action(self):
        if self.tagPlot is None: return
        if self.tagPlot.isHidden():
            self.tagPlot.show()
        else:
            self.tagPlot.hide()
        pass

    def importScript_action(self):
        print('Perform importScript action')
        pass

    def tagSelector_action(self):
        print('Perform tagSelector action')
        pass

    def create_menus(self):
        """
        The method create_menus creates all the dropdown menus for the 
        toolbar and associated actions.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        # Create the File dropdown menu #################################
        self.file_menu = self.menuBar().addMenu("&File")
        # New action
        self._new_file_action = QAction("&New Animation",
                self, triggered=self.newAnimFile)
        self.file_menu.addAction(self._new_file_action)

        # Open action
        self._open_file_action = QAction("&Open Anim File",
                self, shortcut="Ctrl+O", triggered=self.openAnimFile)
        self.file_menu.addAction(self._open_file_action)

        self._selectaudio_action = QAction("Open &Audio File", self,
            triggered=self.selectaudio_action)
        self.file_menu.addAction(self._selectaudio_action)

        # Merge action
        self._merge_file_action = QAction("&Merge Anim File",
                self, triggered=self.mergeAnimFile)
        self._merge_file_action.setEnabled(False)
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
        self._export_vsa_file_action.setEnabled(False)
        self._export_file_menu.addAction(self._export_vsa_file_action)

        # exit action
        self.file_menu.addSeparator()
        self._exit_action = QAction("&Quit", self, shortcut="Ctrl+Q",
                triggered=self.exit_action)
        self.file_menu.addAction(self._exit_action)

        # Create the Edit dropdown menu #################################
        self.edit_menu = self.menuBar().addMenu("&Edit")
        self._undo_action = QAction("Undo", self, shortcut="Ctrl+Z",
            triggered=self.undo_action)
        self.edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("Redo", self, shortcut="Ctrl+Shift+Z",
            triggered=self.redo_action)
        self.edit_menu.addAction(self._redo_action)

        self.edit_menu.addSeparator()

        self._newchannel_action = QAction("New Numeric Channel", self, shortcut="Ctrl+N",
            triggered=self.newchannel_action)
        self.edit_menu.addAction(self._newchannel_action)

        self._newdigital_action = QAction("New Digital Channel", self, shortcut="Ctrl+D",
            triggered=self.newdigital_action)
        self.edit_menu.addAction(self._newdigital_action)

        self._deletechannel_action = QAction("Delete Channels", self,
            triggered=self.deletechannel_action)
        self.edit_menu.addAction(self._deletechannel_action)

        self.edit_menu.addSeparator()

        # editmetadata menu item
        self._editmetadata_action = QAction("Edit Metadata", self,
            triggered=self.editmetadata_action)
        self.edit_menu.addAction(self._editmetadata_action)

        # editpreferences menu item
        self._editpreferences_action = QAction("Edit Preferences", self,
            triggered=self.editpreferences_action)
        self.edit_menu.addAction(self._editpreferences_action)

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

        self.view_menu.addSeparator()

        # showall menu item
        self._showall_action = QAction("Show All Channels", self,
            triggered=self.showall_action)
        self.view_menu.addAction(self._showall_action)

        # showselector menu item
        self._showselector_action = QAction("Select Viewed Channels", self,
            triggered=self.showselector_action)
        self.view_menu.addAction(self._showselector_action)

        self._show_audio_menu = self.view_menu.addMenu("Show Audio")
        # Make actions to be associated with menu later
        self._showmono_audio_action = QAction("Audio Mono", self,
            checkable=True,
            triggered=self.showleft_audio_action)
        self._showleft_audio_action = QAction("Audio Left", self,
            checkable=True,
            triggered=self.showleft_audio_action)
        self._showright_audio_action = QAction("Audio Right", self,
            checkable=True,
            triggered=self.showright_audio_action)

        self.view_menu.addSeparator()

        self._audio_amplitude_action = QAction("Audio Amplitude", self,
            checkable=True,
            triggered=self.showaudio_amplitude_action)
        self.view_menu.addAction(self._audio_amplitude_action)

        self.view_menu.addSeparator()

        # playbackcontrols menu item
        self._playbackcontrols_action = QAction("Toggle Playback Controls", self,
            triggered=self.playbackcontrols_action)
        self.view_menu.addAction(self._playbackcontrols_action)


        # Create the Tools dropdown menu #################################
        self.channel_menu = self.menuBar().addMenu("&Channels")

        # selectAll menu item
        self._selectAll_action = QAction("Select All", self,
            shortcut="Ctrl+A",
            triggered=self.selectAll_action)
        self.channel_menu.addAction(self._selectAll_action)

        # deselectAll menu item
        self._deselectAll_action = QAction("Deselect All", self,
            shortcut="Ctrl+Shift+A",
            triggered=self.deselectAll_action)
        self.channel_menu.addAction(self._deselectAll_action)

        # selectorPane menu item
        self._selectorPane_action = QAction("selectorPane", self,
            shortcut="P",
            triggered=self.selectorPane_action)
        self.channel_menu.addAction(self._selectorPane_action)

        self.channel_menu.addSeparator()

        # Copy menu item
        self._Copy_action = QAction("Copy", self,
            shortcut="Ctrl+C",
            triggered=self.Copy_action)
        self.channel_menu.addAction(self._Copy_action)

        # Paste menu item
        self._Paste_action = QAction("Paste", self,
            shortcut="Ctrl+V",
            triggered=self.Paste_action)
        self.channel_menu.addAction(self._Paste_action)

        # Shift menu item
        self._Shift_action = QAction("Shift", self,
            triggered=self.Shift_action)
        self._Shift_action.setEnabled(False)
        self.channel_menu.addAction(self._Shift_action)

        self.channel_menu.addSeparator()

        # Delete menu item
        self._Delete_action = QAction("Delete", self,
            triggered=self.Delete_action)
        self.channel_menu.addAction(self._Delete_action)


        # Create the Help dropdown menu #################################
        self.tag_menu = self.menuBar().addMenu("&Tags")

        # togglePane menu item
        self._togglePane_action = QAction("togglePane", self,
            shortcut="T",
            triggered=self.togglePane_action)
        self.tag_menu.addAction(self._togglePane_action)

        # tagSelector menu item
        self._tagSelector_action = QAction("tagSelector", self,
            triggered=self.tagSelector_action)
        self.tag_menu.addAction(self._tagSelector_action)

        # importScript menu item
        self._importScript_action = QAction("importScript", self,
            triggered=self.importScript_action)
        self.tag_menu.addAction(self._importScript_action)

        # Create the Help dropdown menu #################################
        self.help_menu = self.menuBar().addMenu("&Help")
        self._about_action = QAction("About", self,
            triggered=self.about_action)
        self.help_menu.addAction(self._about_action)

        self._help_action = QAction("Help", self,
            triggered=self.help_action)
        self.help_menu.addAction(self._help_action)

        self._hotkeys_action = QAction("Hot Keys", self,
            triggered=self.hotkeys_action)
        self.help_menu.addAction(self._hotkeys_action)

        self.help_menu.addSeparator()

        # showClipboard menu item
        self._showClipboard_action = QAction("Show Clipboard", self,
            triggered=self.showClipboard_action)
        self.help_menu.addAction(self._showClipboard_action)

        # showXML menu item
        self._showXML_action = QAction("Show XML", self,
            triggered=self.showXML_action)
        self.help_menu.addAction(self._showXML_action)


#####################################################################
# The AudioChannel class represents the audio channel needed for doing
# animatronics.
#####################################################################
class AudioChannel:
    """
    Class: AudioChannel

    Implements an audio channel for the Animatronics application.  It
    reads a .wav file and provides information on the audio.  It also
    subsamples the audio to speed up plotting of the data.
    ...
    Attributes
    ----------
    audiofile : str
        Name of the audio file
    audio_data : byte array
        Raw binary data from the file
    samplerate : int
        Samples per second
    numchannels : int
        Number of channels (1 for mono, 2 for stereo)
    samplesize : int
        Sample size in bytes
    audiostart : float
        Time at which audio should start playing in overall animation
    audioend : float
        Time at which audio should stop playing in overall animation

    Methods
    -------
    __init__(self, filename=None)
    audioTimeRange(self)
    getPlotData(self, minTime, maxTime, maxCount)
    getAmplitudeData(self, minTime, maxTime, maxCount)
    setAudioFile(self, infilename)
    toXML(self)
    parseXML(self, inXML)
    """

    def __init__(self, filename=None):
        """
        The method __init__
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        filename=None : str
            Name of .wav file to play
        """

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
        """
        The method audioTimeRange returns the audio start and end times,
        in seconds.  End time is just start time plus length of the
        audio.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        """

        """Return the start and end times for the audio"""
        print('Audio file:', self.audiofile)
        print('Audio samplerate:', self.samplerate)
        print('Audio numchannels:', self.numchannels)
        print('Audio samplesize:', self.samplesize)
        print('Audio datasize:', len(self.audio_data))
        self.audioend = self.audiostart + float(len(self.audio_data))/self.numchannels/self.samplerate/self.samplesize
        return self.audiostart,self.audioend

    def getPlotData(self, minTime, maxTime, maxCount):
        """
        The method getPlotData returns the requested number of samples
        by subsampling the audio data within the requested range.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        minTime : float
            Start of desired time range in seconds
        maxTime : float
            End of desired time range in seconds
        maxCount : int
            Number of samples desired
        """
        if self.numchannels == 1:
            # Process mono data
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
            # Process stereo data
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

    def getAmplitudeData(self, minTime, maxTime, maxCount):
        """
        The method getAmplitudeData returns subsampled audio data that
        has been converted to an amplitude by taking the maximum of a 
        local window.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        minTime : float
            Start of desired time range in seconds
        maxTime : float
            End of desired time range in seconds
        maxCount : int
            Number of samples desired
        """

        intSize = 30
        """ Get intSize times as much data as needed, then pick max amplitude in each intSize sample window"""
        xdata, leftdata, rightdata = self.getPlotData(minTime, maxTime, maxCount*intSize)
        outx = []
        outleft = []
        outright = None
        i = 0
        while i < len(leftdata):
            outx.append(xdata[i])
            sumleft = 0.0
            for j in range(intSize):
                if i < len(leftdata):
                    sumleft = max(sumleft, abs(leftdata[i]))
                    i += 1
            outleft.append(sumleft)

        if rightdata is not None:
            outright = []
            i = 0
            while i < len(rightdata):
                outx.append(xdata[i])
                sumright = 0.0
                for j in range(intSize):
                    if i < len(rightdata):
                        sumright = max(sumright, abs(rightdata[i]))
                        i += 1
                outright.append(sumright)

        return outx, outleft, outright

        # Below here is some alternative code that might be better and might not
        """ Get as much data as needed, then pick max amplitude in each intSize sample window"""
        if rightdata is not None:
            outright = []
            minptr = 0
            maxptr = int(intSize/2)
            while minptr < len(leftdata) - int(intSize/2):
                sumleft = 0.0
                for i in range(minptr, maxptr):
                    sumleft = max(sumleft, abs(leftdata[i]))
                outright.append(sumleft)
                if maxptr < len(leftdata): 
                    maxptr += 1
                    if minptr < maxptr - intSize:
                        minptr += 1
                else:
                    minptr += 1

        return xdata, outleft, outright
        

    def setAudioFile(self, infilename):
        """
        The method setAudioFile attempts to open the specified file and,
        if successful, sets all the internal data to that read from
        the file.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        infilename : str
        """
        # Now read the audio data
        if os.path.exists(infilename):
            try:
                audio = wave.open(infilename)
                self.audiofile = infilename
                self.samplerate = audio.getframerate()
                self.numchannels = audio.getnchannels()
                self.samplesize = audio.getsampwidth()
                self.audio_data = audio.readframes(audio.getnframes())
            except:
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Whoops - Unable to read audio file:')
                msgBox.setInformativeText(infilename)
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
                return

    def toXML(self):
        """
        The method toXML writes a block of text containing the XML
        representation of the AudioChannel object for writing to a
        file.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        """
        output = StringIO()
        if self.audiofile is not None:
            output.write('<Audio file="%s">\n' % self.audiofile)
            output.write('    <Start time="%f"/>\n' % self.audiostart)
            output.write('</Audio>\n')
        return output.getvalue()

    def parseXML(self, inXML):
        """
        The method parseXML processes an etree object containing parsed
        XML and populates the AudioChannel object.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        inXML : etree Element
        """
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
    """
    Class: Channel

    Implements a single editable channel of data of any type.  The
    Channel class stores a set of discrete points or knots representing
    a function such that no two points have the same X (time) value.  It
    provides for interpolating the data points via various methods and
    for reading from and writing to XML.
    ...
    Shared Attributes
    ----------
    DIGITAL = 0     # Digital (on/off) channel limited to 0 and 1
    LINEAR = 1      # Servo/CAN channel with linear interpolation
    SPLINE = 2      # Servo/CAN channel with Lagrange interpolation
    STEP = 3        # Servo/CAN channel with step changes

    Attributes
    ----------
    name : str
        The name of the channel
    knots : dictionary
        Dictionary of floats (Y values) with float keys (X values)
    knottitles : dictionary
        Dictionary of str (Y labels) with float keys (X values)
    type : int
        Enum of DIGITAL, LINEAR, SPLINE, or STEP
    minLimit : float
        Lowest legal Y value
    maxLimit : float
        Highest legal Y value
    port : int
        Index of port on controller for this channel (-1 means unassigned)
    rateLimit : float
        Maximum rate of change allowed for this channel in units per second

    Methods
    -------
    __init__(self, inname = '', intype = LINEAR)
    add_knot(self, key, value)
    delete_knot(self, key)
    set_name(self, inname)
    num_knots(self)
    getValueAtTime(self, inTime)
    getKnotData(self, minTime, maxTime, maxCount)
    getPlotData(self, minTime, maxTime, maxCount)
    getValuesAtTimeSteps(self, startTime, endTime, timeStep)
    toXML(self)
    parseXML(self, inXML)
    """
    DIGITAL = 0     # Digital (on/off) channel limited to 0 and 1
    LINEAR = 1      # Servo/CAN channel with linear interpolation
    SPLINE = 2      # Servo/CAN channel with Lagrange interpolation
    STEP = 3        # Servo/CAN channel with step changes

    def __init__(self, inname = '', intype = LINEAR):
        """
        The method __init__
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inname='' : str
            name of channel
        intype=LINEAR : int
            enum type of channel
        """
        self.name = inname
        self.knots = {}
        self.knottitles = {}
        self.type = intype
        if intype == self.DIGITAL:
            self.minLimit = 0.0
            self.maxLimit = 1.0
        elif intype == self.LINEAR or intype == self.SPLINE:
            self.minLimit = SystemPreferences['ServoDefaultMinimum']
            self.maxLimit = SystemPreferences['ServoDefaultMaximum']
        else:
            self.maxLimit = 1.0e34
            self.minLimit = -1.0e34
        self.port = -1
        self.rateLimit = -1.0

    def add_knot(self, key, value):
        """
        The method add_knot adds or replaces the Y value associated with
        time (X) key.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        key : float
            Time (X) value for the knot
        value : float
            Data (Y) value for the knot
        """
        self.knots[key] = value

    def delete_knot(self, key):
        """
        The method delete_knot removes the knot at time key.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        key : float
            Time (X) value for the knot to be removed
        """
        self.knots.pop(key)

    def set_name(self, inname):
        """
        The method set_name sets the name of the channel to the input value.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inname : str
            New name
        """
        self.name = inname

    def num_knots(self):
        """
        The method num_knots returns the number of knots in the channel.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        """
        return len(self.knots)

    def getValueAtTime(self, inTime):
        """
        The method getValueAtTime may eventually provide single point
        interpolation of the channel but may not.  Not currently used.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inTime : type
        """
        pass

    def getKnotData(self, minTime, maxTime, maxCount):
        """
        The method getKnotData returns arrays containing time (X) and data (Y)
        values for all the knots in the array within the specified time range.
        If there are more knots in the range than maxCount, they are
        subsampled somehow (not implemented yet).

        Currently, ALL knots are returned ALL the time.  Mostly good enough

            member of class: Channel
        Parameters
        ----------
        self : Channel
        minTime : float
            Minimum time, in seconds, of desired time range
        maxTime : float
            Maximum time, in seconds, of desired time range
        maxCount : int
            Maximum number of knots to return (not currently used)
        """

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
        """
        The method getPlotData returns arrays of interpolated points along
        the channel data curve.  Interpolation is determined by the channel
        type with Step, Linear, and Spline currently supported.  Returns
        a pair of Nones of the channel is empty.

        The QwtPlot class plots curves with lines connecting the points so
        it is not necessary to interpolate in the Linear case.  In the Step
        case, an additional point is inserted just before each knot with
        the previous knots value causing a step function appearance.  For
        Spline, Lagrange interpolation is used to compute up to maxCount
        values along the curve from minTime to maxTime.  The Spline case is
        currently the only one that pays attention to maxCount other than
        the special case of a single knot.  In the latter case, maxCount
        values are returned with the full range of time values but the same
        data value.

            member of class: Channel
        Parameters
        ----------
        self : Channel
        minTime : float
            
        maxTime : type
        maxCount : type
        """

        """Returns up to maxCount points along the visible part of the curve"""
        keys = sorted(self.knots.keys())
        if len(keys) < 1:
            # Return Nones if channel is empty
            return None,None
        if len(keys) < 2:
            # Return a constant value between minTime and maxTime
            xdata = [minTime, maxTime]
            ydata = [self.knots[keys[0]], self.knots[keys[0]]]
        elif self.type == self.LINEAR:
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
        elif self.type == self.STEP or self.type == self.DIGITAL:
            # To simulate a step function, output a value at the beginning and end
            # of each interval
            # Add value from left side of window to first point (?)
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
            # Add value from last point to right side of window (?)
            xdata.append(max(maxTime, keys[-1]))
            ydata.append(self.knots[keys[-1]])
        elif self.type == self.SPLINE:
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
                    """
                    The method _basis
                    Parameters
                    ----------
                    j : int
                        index of basis to be calculated
                    """
                    k = len(interpKeys)
                    p = [(currTime - interpKeys[m])/(interpKeys[j] - interpKeys[m]) for m in range(k) if m != j]
                    return reduce(operator.mul, p)
                weights = []
                for i in range(len(interpKeys)):
                    weights.append(_basis(i))
                xdata.append(currTime)
                ydata.append(sum(weights[j] * self.knots[interpKeys[j]] for j in range(len(interpKeys))))

                currTime += timeStep

        else:
            # Better never get here
            sys.error.write('Whoops - Type is Invalid')
            exit(10)

        # Limit the range of plot data to min and max values
        # Linear and Step curves should be self-limiting so this really
        # applies only to Spline curves
        for i in range(len(ydata)):
            if ydata[i] > self.maxLimit:
                ydata[i] = self.maxLimit
            elif ydata[i] < self.minLimit:
                ydata[i] = self.minLimit

        return xdata,ydata


    def getValuesAtTimeSteps(self, startTime, endTime, timeStep):
        """
        The method getValuesAtTimeSteps interpolates the curve at equal
        sized steps from startTime to endTime.  This is primarily used for
        creating CSV data at regular intervals.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        startTime : float
            Start time in seconds
        endTime : float
            End time in seconds
        timeStep : float
            Time step in seconds
        """

        if len(self.knots) == 0:
            return None

        # Short cut for spline and smooth curves
        if self.type == self.SPLINE:
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
                if self.type == self.LINEAR or self.type == self.STEP or self.type == self.DIGITAL:
                    values.append(self.knots[keys[0]])
            elif currTime > keys[-1]:
                if self.type == self.LINEAR or self.type == self.STEP or self.type == self.DIGITAL:
                    values.append(self.knots[keys[-1]])
            else:
                # Somewhere in range so find interval
                while nextkeyindex < len(keys) and keys[nextkeyindex] <= currTime:
                    nextkeyindex += 1
                if self.type == self.LINEAR:
                    # interpolate
                    tval = ((self.knots[keys[nextkeyindex]] * (currTime - keys[nextkeyindex-1]) +
                        self.knots[keys[nextkeyindex-1]] * (keys[nextkeyindex] - currTime)) /
                        (keys[nextkeyindex] - keys[nextkeyindex-1]))
                    values.append(tval)
                    pass
                elif self.type == self.STEP or self.type == self.DIGITAL:
                    values.append(self.knots[keys[nextkeyindex-1]])

            currTime += timeStep

        return values

    def toXML(self):
        """
        The method toXML builds a block of XML from the data within the
        Channel and returns a string.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        """
        output = StringIO()
        output.write('<Channel name="%s"' % self.name)
        if self.minLimit >= -1.0e33:
            output.write(' minLimit="%f"' % self.minLimit)
        if self.maxLimit <= 1.0e33:
            output.write(' maxLimit="%f"' % self.maxLimit)
        if self.port >= 0:
            output.write(' channel="%d"' % self.port)
        if self.rateLimit > 0.0:
            output.write(' rateLimit="%f"' % self.rateLimit)
        if self.type == self.LINEAR:
            output.write(' type="Linear">\n')
        elif self.type == self.SPLINE:
            output.write(' type="Spline">\n')
        elif self.type == self.STEP:
            output.write(' type="Step">\n')
        elif self.type == self.DIGITAL:
            output.write(' type="Digital">\n')
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
        """
        The method parseXML parses an etree ElementTree and populates the
        channel fields from the XML.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inXML : etree ElementTree
            The preparsed XML object
        """
        if inXML.tag == 'Channel':
            # Populate metadata from attributes
            if 'name' in inXML.attrib and len(self.name) == 0:
                self.name = inXML.attrib['name']
            if 'minLimit' in inXML.attrib:
                self.minLimit = float(inXML.attrib['minLimit'])
            if 'maxLimit' in inXML.attrib:
                self.maxLimit = float(inXML.attrib['maxLimit'])
            if 'rateLimit' in inXML.attrib:
                self.rateLimit = float(inXML.attrib['rateLimit'])
            if 'channel' in inXML.attrib and self.port < 0:
                self.port = int(inXML.attrib['channel'])
            if 'type' in inXML.attrib:
                if inXML.attrib['type'] == 'Linear':
                    self.type = self.LINEAR
                elif inXML.attrib['type'] == 'Spline':
                    self.type = self.SPLINE
                elif inXML.attrib['type'] == 'Step':
                    self.type = self.STEP
                elif inXML.attrib['type'] == 'Digital':
                    self.type = self.DIGITAL
                else:
                    raise Exception('Invalid Channel Type:%s' % inXML.attrib['type'])
        else:
            raise Exception('XML is not a Channel')

        # Clean out all current knots
        self.knots = {}
        # Populate knots from Point blocks
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
    """
    Class: Animatronics

    Implements the entire Animatronics construct with audio, data channels,
    tags, and useful metadata.
    ...
    Attributes
    ----------
    filename : str
        Name of file parsed for this object (None if newly created)
    newAudio : AudioChannel
        An object holding the audio information
    channels : dictionary
        A dictionary of channels keyed to the channel name
    tags : dictionary
        A dictionary of strings keyed to time
    start : float
        Start time of the animation (ALWAYS 0.0)
    end : float
        End time of the animation (defaults to end of audio)
    sample_rate : float
        Sample rate in samples per second (defaults to 50Hz)
        Used for writing CSV files and for real-time control whenever done

    Methods
    -------
    __init__(self)
    parseXML(self, inXMLFilename)
    fromXML(self, testtext)
    toXML(self)
    set_audio(self, infilename)
    """
    def __init__(self):
        """
        The method __init__
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        """
        self.filename = None
        self.newAudio = None
        self.tags = {}
        self.channels = {}
        self.start = 0.0
        self.end = -1.0
        self.sample_rate = 50.0

    def parseXML(self, inXMLFilename):
        """
        The method parseXML accepts a filename of an XML file containing an
        Animatronics specification and parses it, preserving the filename
        for later saves.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        inXMLFilename : str
            Filename of XML file to read
        """
        with open(inXMLFilename, 'r') as infile:
            testtext = infile.read()
            self.fromXML(testtext)
            self.filename = inXMLFilename

    def fromXML(self, testtext):
        """
        The method fromXML parses a block of XML text and populates the
        class members, deleting all existing data.  It is used both for
        parsing files and for parsing Undo and Redo state information.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        testtext : type
        """
        # Clean up existing stuff
        self.newAudio = None
        self.channels = {}
        self.sample_rate = 50.0

        # Scan the XML text
        root = ET.fromstring(testtext)
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
            elif child.tag == 'Tags':
                print('Found Tags block')
                for tag in child:
                    if tag.tag == 'Tag':
                        if 'time' in tag.attrib:
                            time = float(tag.attrib['time'])
                            self.tags[time] = tag.text.strip()

        print('Number of tags found:', len(self.tags))

    def toXML(self):
        """
        The method toXML creates and returns a block of XML text from 
        the object's members.  The text may be written to a file or saved
        as state for Undo and Redo.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        """
        output = StringIO()
        output.write('<?xml version="1.0"?>\n')
        output.write('<Animatronics starttime="%f"' % self.start)
        if self.end > self.start:
            output.write(' endtime="%f"' % self.end)
        output.write('>\n')
        output.write('<Control rate="%f"/>\n' % self.sample_rate)
        if self.newAudio is not None:
            output.write(self.newAudio.toXML())
        if len(self.tags) > 0:
            output.write('<Tags>\n')
            for tag in self.tags:
                output.write('    <Tag time="%f">\n' % tag)
                output.write(self.tags[tag] + '\n')
                output.write('    </Tag>\n')
            output.write('</Tags>\n')
        for channel in self.channels.values():
            output.write(channel.toXML())
        output.write('</Animatronics>\n')
        return output.getvalue()

    def set_audio(self, infilename):
        """
        The method set_audio accepts the specified audio filename and
        creates a new AudioChannel object for that audio file.  This
        associates the audio file with this animation.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        infilename : type
        """
        self.newAudio = AudioChannel(infilename)


#/* Main */
def doAnimatronics():
    """
    The method doAnimatronics is the main function of the application.
    It parses the command line arguments, handles them, and then opens
    the main window and proceeds.
    """
    # Make main window global to support saving state for undo/redo
    global main_win

    # Local Variables to support parsing an Animatronics file specified
    # on the command line
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

    # Create the global main window
    app = QApplication(sys.argv)
    main_win = MainWindow()
    PreferencesWidget.readPreferences()

    # If an input file was specified, parse it or die trying
    if infilename is not None:
        # Do not update state if we read here
        main_win.saveStateOkay = False
        try:
            animation.parseXML(infilename)

        except Exception as e:
            sys.stderr.write("\nWhoops - Error reading input file %s\n" % infilename)
            sys.stderr.write("Message: %s\n" % e)
            sys.exit(11)

        main_win.saveStateOkay = True

    # Open the main window and process events
    main_win.setAnimatronics(animation)
    main_win.show()
    app.exec_()


if __name__ == "__main__":
    doAnimatronics()

