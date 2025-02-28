#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program MainWindow.py
# Created by John R. Wright
# Created Tue Jun 13 17:35:31 PDT 2023
#*********************************/
'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

#/* Import block */
import os
import shutil
import re
import random
import sys
import importlib
import pkgutil

from Animatronics import *

# System Preferences Block
SystemPreferences = {
'MaxDigitalChannels':48,        # Maximum number of digital channels controller can handle
'MaxServoChannels':32,          # Maximum number of servo/numeric channels controller cah handle
'ServoDefaultMinimum':0,        # Default minimum servo setting
'ServoDefaultMaximum':65535,    # Default maximum servo setting
'AutoSave':True,                # Perfrom saving automatically flag
'ShowTips':True,                # Show tool tips flag
'ServoDataFile':'servotypes',   # Name of file containing predefined servos
'UploadPath':'/sd/anims/',      # Name of upload directory on controller
'TTYPortRoot':'/dev/ttyACM',    # Root of tty port for usb comm
}
SystemPreferenceTypes = {
'MaxDigitalChannels':'int',
'MaxServoChannels':'int',
'ServoDefaultMinimum':'int',
'ServoDefaultMaximum':'int',
'AutoSave':'bool',
'ShowTips':'bool',
'ServoDataFile':'str',
'UploadPath':'str',
'TTYPortRoot':'str',
}


# Utilize XML to read/write animatronics files
import xml.etree.ElementTree as ET

# Import commlib for my board
try:
    import commlib
    COMMLIB_ENABLED = True
except:
    COMMLIB_ENABLED = False

usedPyQt = None

try:
    # PyQt5 import block for all widgets
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5 import QtMultimedia as qm
    usedPyQt = 5
except:
    try:
        # PyQt6 import block for all widgets
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        from PyQt6.QtWidgets import *
        from PyQt6 import QtMultimedia as qm
        usedPyQt = 6
    except:
        sys.stderr.write('Whoops - Unable to find PyQt5 or PyQt6 - Quitting\n')
        exit(10)
import qwt
from qwt import plot_layout

#/* Define block */
verbosity = False

main_win = None     # Global reference to the main window for global methods

# Dictionary of known servo types to aid user
ServoData = {}

#/* Usage method */
def print_usage(name):
    """
    The method print_usage prints the standard usage message.
    Parameters
    ----------
    name : str
        The name of the application from argv[0]
    """
    sys.stderr.write("\nUsage: %s [-/-h/-help]\n")
    sys.stderr.write("Run regression tests.\n");
    sys.stderr.write("-/-h/-help             :show this information\n");
    #sys.stderr.write("-f/-file infilename    :Input anim file\n")
    sys.stderr.write("\n\n");

def pushState():
    """
    The method pushState pipes a request to save state for undo to the
    main window.
    """
    if main_win is not None: main_win.pushState()

def popState():
    """
    The method popState pipes a request to pop state for undo to the
    main window.
    """
    if main_win is not None: main_win.popState()

def getExecPath():
    # Get path to executable (this file)
    try:
        sFile = os.path.abspath(sys.modules['__main__'].__file__)
    except:
        sFile = sys.executable
    return os.path.dirname(sFile)

def toHMS(seconds):
    flag = seconds < 0
    if flag:
        seconds = -seconds
    hours = int(seconds/3600.0)
    seconds -= hours*3600
    minutes = int(seconds/60.0)
    seconds -= minutes*60
    time = '%02d:%02d:%05.2f' % (hours, minutes, seconds)
    if flag: time = '-' + time
    return time

def fromHMS(string):
    seconds = 0.0
    m = re.match('^(-?)(\d+):(\d+):(\d+\.?\d*)', string)
    if m:
        seconds = int(m.group(2)) * 3600.0
        seconds += int(m.group(3)) * 60
        seconds += float(m.group(4))
        if m.group(0) == '-': seconds = -seconds
    return seconds

#####################################################################
class AmpingWidget(QDialog):

    def __init__(self, parent=None, startTime=0.0, endTime=0.0, cutoff=0.0, popRate=10.0):
        super().__init__(parent)

        self.startTime = startTime
        self.endTime = endTime
        self.cutoff = cutoff
        self.popRate = popRate

        self.setWindowTitle('Amplitudize Control')
        widget = QWidget()
        layout = QFormLayout()

        self._startedit = QLineEdit()
        self._startedit.setText('%.3f' % startTime)
        layout.addRow(QLabel('Start Time:'), self._startedit)

        self._endedit = QLineEdit()
        self._endedit.setText('%.3f' % endTime)
        layout.addRow(QLabel('End Time:'), self._endedit)

        self._cutoffedit = QLineEdit()
        self._cutoffedit.setText('%.3f' % cutoff)
        layout.addRow(QLabel('Cutoff:'), self._cutoffedit)

        self._rateedit = QLineEdit()
        self._rateedit.setText('%.3f' % popRate)
        layout.addRow(QLabel('Sample Rate:'), self._rateedit)

        widget.setLayout(layout)

        self.okButton = QPushButton('Do It')
        self.okButton.setDefault(True)
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
        tstring = self._startedit.text()
        if len(tstring) > 0:
            self.startTime = float(tstring)
        else:
            self.startTime = -1.0e34

        tstring = self._endedit.text()
        if len(tstring) > 0:
            self.endTime = float(tstring)
        else:
            self.endTime = 1.0e34

        tstring = self._cutoffedit.text()
        if len(tstring) > 0:
            self.cutoff = float(tstring)

        tstring = self._rateedit.text()
        if len(tstring) > 0:
            self.popRate = float(tstring)

        self.accept()



#####################################################################
class SetDigitalWidget(QDialog):

    def __init__(self, parent=None, port=-1):
        super().__init__(parent)

        self.port = port

        vbox = QVBoxLayout(self)

        group = QButtonGroup(self)
        self.onButton = QRadioButton('On', self)
        group.addButton(self.onButton)
        vbox.addWidget(self.onButton)
        self.onButton.toggled.connect(self.update)
        self.offButton = QRadioButton('Off', self)
        group.addButton(self.offButton)
        vbox.addWidget(self.offButton)
        self.offButton.toggled.connect(self.update)

    def update(self):
        if self.port < 0 or not COMMLIB_ENABLED: return
        if self.onButton.isChecked():
            commlib.setDigitalChannel(self.port, 1)
        else:
            commlib.setDigitalChannel(self.port, 0)

#####################################################################
class LimitWidget(QDialog):

    setMinSignal = pyqtSignal(str)
    setMaxSignal = pyqtSignal(str)

    def __init__(self, parent=None, port=-1, minimum=0.0, maximum=180.0):
        super().__init__(parent)

        self.port = port

        vbox = QVBoxLayout(self)

        # Create the slider
        hbox = QHBoxLayout()    # Put slider in horizontal layout for good centering
        self.slider = QSlider(self)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setMinimum(int(minimum))
        self.slider.setMaximum(int(maximum))
        self.slider.setTickInterval(int((maximum-minimum)/16))
        self.slider.valueChanged.connect(self.valueIs)
        self.slider.setSingleStep(max(int((maximum-minimum)/256),1))
        self.slider.setPageStep(int((maximum-minimum)/16))
        self.slider.setFixedHeight(300)
        hbox.addStretch()
        hbox.addWidget(self.slider)
        hbox.addStretch()
        vbox.addLayout(hbox)

        # Create the value display
        self.display = QLineEdit()
        self.display.setFixedWidth(50)
        self.display.setReadOnly(True)
        self.display.setMaxLength(6)
        self.display.selectionChanged.connect(self.fixFocus)
        vbox.addWidget(self.display)

        # Create the checkbox for live control of servo
        self.liveCheck = QCheckBox('Live')
        self.liveCheck.setChecked(False)
        self.liveCheck.setEnabled(COMMLIB_ENABLED and self.port >= 0)
        self.liveCheck.stateChanged.connect(self.fixFocus)
        vbox.addWidget(self.liveCheck)

        # Create the buttons to set max and min limits
        maxButton = QPushButton('Max')
        maxButton.clicked.connect(self.sendMax)
        vbox.addWidget(maxButton)
        minButton = QPushButton('Min')
        minButton.clicked.connect(self.sendMin)
        vbox.addWidget(minButton)
        vbox.addStretch()

        # Initialize to midway between min and max
        initValue = int((maximum+minimum)/2)
        # per Bill, initialize unspecified servos to 1.5msec pulse width in 20 msec cycle
        if initValue > 4915 and minimum < 4915 and maximum > 4915: initValue = 4915
        self.slider.setValue(initValue)
        self.display.setText('%d' % initValue)

        # Set the width to match what's needed
        self.setFixedWidth(70)

    def valueIs(self, value):
        self.display.setText('%d' % value)
        if self.liveCheck.isChecked() and self.port >= 0 and COMMLIB_ENABLED:
            # Send the value, appropriately formatted, to hardware controller
            #print('Sending to controller port %d value %d' % (self.port, value))
            code = commlib.setServo(self.port, value)
            pass

    def sendMin(self):
        self.setMinSignal.emit(self.display.text())
        self.slider.setFocus()

    def sendMax(self):
        self.setMaxSignal.emit(self.display.text())
        self.slider.setFocus()

    def fixFocus(self):
        self.slider.setFocus()


#####################################################################
class LeftAlignLayout(plot_layout.QwtPlotLayout):
    # Shared width of all left scales
    leftScaleWidth = 50.0;

    def __init__(self):
        super().__init__()

    def expandLineBreaks(self, options, rect):
        dimTitle, dimFooter, dimAxes = super().expandLineBreaks(options, rect)
        dimAxes[qwt.QwtPlot.yLeft] = self.leftScaleWidth
        return dimTitle, dimFooter, dimAxes

    @classmethod
    def setMaxScaleWidth(cls, width):
        cls.leftScaleWidth = width

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

        # Limit Tag Pane height
        self.setMaximumHeight(150)

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

    def setTags(self, tagList):
        self._tags = tagList
        self.redrawme()

    def addTags(self, tagList):
        for tag in tagList:
            self.addTag(tag, tagList[tag])

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

    def tagZoom(self, neartag):
        # First find next tag after the selected one
        slist = sorted(self._tags.keys())
        indx = slist.index(neartag)
        # qwt does not seem to like setting left edge to something greater than right edge
        # so we push the right edge out past where we will set the left edge temporarily
        if self.mainwindow.lastXmax < neartag + 1.0:
            self.mainwindow.setRightEdge(neartag + 10.0)
        self.mainwindow.setLeftEdge(neartag)
        if indx < len(slist) -1:
            # Use the next tag as zoom limit
            self.mainwindow.setRightEdge(slist[indx+1])
        else:
            self.mainwindow.setRightEdge(self.mainwindow.lastXmax)

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
                    self.mainwindow.updateXMLPane()
                    self.mainwindow.tagSelectUpdate()
                    pass
                else:
                    # Insert a new tag
                    neartag = xplotval
                    neartag = self.addTag(neartag, '')
                    self.selectedtag = neartag

                event.accept()
            elif modifiers == Qt.ControlModifier:
                # Zoom to that tag
                if neartag is not None:
                    self.tagZoom(neartag)
            else:
                # Not shift so select near one to drag or pass to main window
                if neartag is not None:
                    # Push current state for undo
                    pushState()

                    self.selectedtag = neartag
                    event.accept()
                else:
                    # Nobody is selected so pass to main window
                    self.selectedtag = None
                    event.ignore()

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
            if self.selectedtag in self._tags and self._tags[self.selectedtag] == '':
                # Bring up window to get actual label from user
                text, ok = QInputDialog().getText(self, "Tag Entry", "Enter Tag:",
                    QLineEdit.Normal, self._tags[self.selectedtag])
                self.deleteTag(self.selectedtag)
                if ok and text:
                    self.addTag(self.selectedtag, text)
                else:
                    # Forget that we were trying to put in a tag
                    self.mainwindow.undo_action()
            self.mainwindow.updateXMLPane()
            self.mainwindow.tagSelectUpdate()

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
    _random_action : QAction
    _wrap_action : QAction
    _Rescale_action : QAction
    _Hide_action : QAction
    _Clear_action : QAction
    _Delete_action : QAction

    Methods
    -------
    __init__(self, parent, channel)
    metadata_action(self)
    invert_action(self)
    random_action(self)
    wrap_action(self)
    Rescale_action(self)
    Hide_action(self)
    Clear_action(self)
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
        self._metadata_action = QAction("Metadata", self,
            triggered=self.metadata_action)
        self.addAction(self._metadata_action)

        # invert menu item
        self._invert_action = QAction("Invert", self,
            triggered=self.invert_action)
        self.addAction(self._invert_action)

        # smooth menu item only for Linear channels
        self._random_action = QAction("Randomize", self,
            triggered=self.random_action)
        self.addAction(self._random_action)

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
        self._Clear_action = QAction("Clear", self,
            triggered=self.Clear_action)
        self.addAction(self._Clear_action)
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
        td = ChannelMetadataWidget(channel=self.channel, parent=self)
        code = td.exec_()

        if code == QDialog.Accepted:
            # May have been renamed
            if tname != self.channel.name:
                self.parent.holder.animatronics.reIndexChannel(tname, self.channel.name)
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
            if main_win is not None: main_win.updateXMLPane()
        pass

    def random_action(self):
        """
        The method random_action
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """
        # Open randomize widget to get values from user
        twidget = AmpingWidget(parent=main_win, startTime=self.parent.minTime, endTime=self.parent.maxTime,
                    popRate=1.0)
        twidget.setWindowTitle('Randomizer Control')
        code = twidget.exec_()
        if code != QDialog.Accepted: return # Cancel the operation

        # Do the randomize process
        pushState()     # Push current state for undo
        maxRate = (self.channel.maxLimit - self.channel.minLimit)
        minTime = twidget.startTime
        maxTime = twidget.endTime
        popRate = twidget.popRate

        # Remove all knots within randomization range
        delknots = []
        for knot in self.channel.knots:
            if knot >= minTime and knot <= maxTime:
                delknots.append(knot)
        for knot in delknots:
            self.channel.delete_knot(knot)

        currTime = minTime
        lastValue = None
        while currTime <= maxTime:
            if self.channel.type == self.channel.DIGITAL:
                currValue = float(random.randrange(2))
                if lastValue is None or lastValue != currValue:
                    self.channel.add_knot(currTime, float(currValue))
                    lastValue = currValue
                    
            else:
                currValue = random.uniform(0.0, 1.0) * maxRate + self.channel.minLimit
                if currValue > self.channel.maxLimit: currValue = self.channel.maxLimit
                if currValue < self.channel.minLimit: currValue = self.channel.minLimit
                self.channel.add_knot(currTime, currValue)
            currTime += 1.0/popRate

        self.parent.redrawme()
        if main_win is not None: main_win.updateXMLPane()
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

    def Clear_action(self):
        """
        The method Clear_action requests that this Channel have all its knots removed
        from the animation.
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """
        # self.parent.holder should be the MainWindow
        if self.channel is not None:
            if len(self.channel.knots) > 0:
                pushState()

                self.channel.delete_knots()
                if self.parent is not None:
                    self.parent.redrawme()
                if main_win is not None: main_win.updateXMLPane()
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
    # Constants
    BoxSize = 10

    NO_MODE = 0
    CHANNEL_MODE = 1
    KNOT_MODE = 2

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
        self.curve3 = None

        # Set initial values to avoid data race
        self.minTime = 0.0
        self.maxTime = 1.0
        self.minVal = -1.0
        self.maxVal = 1.0
        self.xoffset = 0
        self.yoffset = 0
        self.selectedKey = None
        self.selectedKeyList = []
        self.dragend = -1.0
        self.dragstart = -1.0
        self.selected = False
        self.currMode = self.NO_MODE
        self.lastMode = self.NO_MODE
        self.settimerange(0.0, 100.0)
        self.setDataRange(-1.0, 1.0)
        channelname = self.channel.name
        # Append the channel type indicator to the channel name
        if self.channel.type == Channel.DIGITAL:
            channelname += '(D'
        else:
            channelname += '(S'
        # If port number is set, append it to the displayed channel name
        if self.channel.port >= 0:
            channelname += '%d' % self.channel.port
        channelname += ')'
        self.setAxisTitle(qwt.QwtPlot.yLeft, channelname)

        if self.channel.type == Channel.DIGITAL:
            self.setMaximumHeight(150)

        self.create()

    def getState(self):
        return (self.minVal, self.maxVal, self.isHidden(), self.selected, list(self.selectedKeyList))

    def setState(self, inState):
        self.setDataRange(inState[0], inState[1])
        if inState[2]:
            self.hide()
        else:
            self.show()
        self.setSelected(inState[3])
        self.selectedKeyList = []
        for key in inState[4]:
            for tkey in self.channel.knots:
                # Since we wrote to text and read back in they might change a smidge so check for nearness
                if abs(key - tkey) < 1.0e-6:
                    self.selectedKeyList.append(tkey)
                    break

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
        self.deselect()
        self.hide()

    def create(self):
        """
        The method create creates all the widget stuff for the channel pane
            member of class: ChannelPane
        Parameters
        ----------
        self : ChannelPane
        """
        # Clean up old data if recreating an existing pane
        if self.curve is not None:
            self.curve.setData([],[])
        if self.curve2 is not None:
            self.curve2.setData([],[])
        if self.curve3 is not None:
            self.curve3.setData([],[])
        self.replot()

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

        # Create a curve for selected knots
        self.curve3 = qwt.QwtPlotCurve.make(xdata=[], ydata=[], plot=self,
            symbol=qwt.symbol.QwtSymbol(qwt.symbol.QwtSymbol.Rect,
                QBrush(Qt.red), QPen(Qt.black), QSize(self.BoxSize, self.BoxSize))
        )
        self.curve3.setStyle(qwt.QwtPlotCurve.NoCurve)

        # Add filler for the On times for the digital channels
        if self.channel.type == Channel.DIGITAL:
            fillbrush = QBrush(Qt.gray)
            self.curve.setBrush(fillbrush)

        self.resetDataRange()

        # Create green bar for audio sync
        self.timeSlider = qwt.QwtPlotCurve()
        self.timeSlider.setStyle(qwt.QwtPlotCurve.Sticks)
        self.timeSlider.setData([0.0], [70000.0])
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

    def setSelected(self, flag):
        if flag: self.select()
        else: self.deselect()

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
        # Do not allow resizing on digital channels
        if self.channel.type == Channel.DIGITAL: return

        numDegrees = event.angleDelta() / 8
        vertDegrees = numDegrees.y()

        # Get the data value where the cursor is located
        yplotval = self.invTransform(qwt.QwtPlot.yLeft, event.pos().y() - self.yoffset)
        minval = yplotval - (yplotval - self.minVal) * (1.0 - vertDegrees/100.0)
        maxval = yplotval - (yplotval - self.maxVal) * (1.0 - vertDegrees/100.0)
        self.setDataRange(minval, maxval)

    def deleteSelectedKnots(self):
        pushState()
        self.doTheDelete()

    def doTheDelete(self):
        if self.selected:
            # Have mainwindow move all the selected points in all selected channels
            if self.holder is not None:
                self.holder.deleteSelectedPoints()
            pass
        else:
            self.deleteMyPoints()
            self.redrawme()

    def deleteMyPoints(self):
        for knot in self.selectedKeyList:
            del self.channel.knots[knot]
        self.selectedKeyList = []

    def keyReleaseEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        xdelta = 0.1    # 1/10th of a second
        ydelta = 128.0
        if modifiers == Qt.ShiftModifier:
            xdelta *= 10
            ydelta *= 10
        elif modifiers == Qt.ControlModifier:
            xdelta /= 10
            ydelta /= 10
        if event.key() == Qt.Key_Up:
            self.moveSelectedPoints(0.0, ydelta)
        elif event.key() == Qt.Key_Down:
            self.moveSelectedPoints(0.0, -ydelta)
        elif event.key() == Qt.Key_Left:
            self.moveSelectedPoints(-xdelta, 0.0)
        elif event.key() == Qt.Key_Right:
            self.moveSelectedPoints(xdelta, 0.0)
        elif event.key() == Qt.Key_Delete:
            self.deleteSelectedKnots()
        elif event.key() == Qt.Key_R and modifiers == Qt.ControlModifier:
            self.resetDataRange()
        self.redrawme()

    def getPlotValues(self, widgetX, widgetY):
        self.setOffsets()
        xplotval = self.invTransform(qwt.QwtPlot.xBottom, widgetX - self.xoffset)
        yplotval = self.invTransform(qwt.QwtPlot.yLeft, widgetY - self.yoffset)

        return xplotval, yplotval

    def mousePressEvent(self, event):
        """
        The method mousePressEvent handles the mouse press events.  They
        are:
            Left: If on knot (see FindClosestWithinBox) grab it
                else begin multi-knot selection
            Shift-Left: If on knot (see FindClosestWithinBox) delete it
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
            modifiers = QApplication.keyboardModifiers()
            if xplotval < self.minTime:
                # We are in CHANNEL mode
                self.currMode = self.CHANNEL_MODE
                if modifiers == Qt.ShiftModifier:
                    if self.selected and self.holder is not None:
                        self.holder.shiftDeselect(self.channel.name)
                    elif self.holder is not None:
                        self.holder.shiftSelect(self.channel.name)
                elif modifiers == Qt.ControlModifier:
                    # Select/deselect this channel
                    self.invertselect()
                    if self.holder is not None:
                        self.holder.noteLast(self.channel.name)
                else:
                    # Deselect all other channels
                    if self.holder is not None:
                        self.holder.deselectAll_action()
                    # and select this one
                    self.select()
                    if self.holder is not None:
                        self.holder.noteLast(self.channel.name)
            else:
                # We are in KNOT mode
                self.currMode = self.KNOT_MODE
                self.holder.noteLast(None)
                if self.channel.type == Channel.DIGITAL:
                    if yplotval >= 0.5: yplotval = 1.0
                    elif yplotval < 0.5: yplotval = 0.0
                # Find nearest point
                nearkey = self.findClosestPointWithinBox(event.pos().x(), event.pos().y())
                if modifiers == Qt.ShiftModifier:
                    # If shift key is down then we want to insert or delete a point
                    # Push current state for undo
                    pushState()

                    if nearkey is not None:
                        # Delete currently selected point
                        del self.channel.knots[nearkey]
                        if nearkey in self.selectedKeyList:
                            self.selectedKeyList.remove(nearkey)
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
                    pass
                    # self.invertselect()
                else:
                    # Select a point
                    if nearkey is not None:
                        # If close enough, select it and drag it around
                        self.selectedKey = nearkey
                        self.redrawme() # Redraw the knot with its fill color
                        # Push current state for undo
                        pushState()
                    else:
                        # Mark beginning of drag area to select multiple knots
                        self.selectedKeyList = []   # Clear current list of selected keys
                        self.dragstart = xplotval
                        self.redrawme()
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
            self.redrawme() # Redraw the knot with its fill color
            if main_win is not None: main_win.updateXMLPane()
        pass

    def moveSelectedPoints(self, xdelta, ydelta):
        pushState()
        self.doTheMove(xdelta, ydelta)

    def doTheMove(self, xdelta, ydelta):
        if self.selected:
            # Have mainwindow move all the selected points in all selected channels
            if self.holder is not None:
                self.holder.moveSelectedPoints(xdelta, ydelta)
            pass
        else:
            self.moveMyPoints(xdelta, ydelta)
            self.redrawme()

    def moveMyPoints(self, xdelta, ydelta):
        newList = []
        for key in self.selectedKeyList:
            newx = key + xdelta
            newy = self.channel.knots[key] + ydelta
            del self.channel.knots[key]
            if newx in self.channel.knots:
                newx += 0.00000001
            if self.channel.type == Channel.DIGITAL:
                if newy >= 0.5: newy = 1.0
                else: newy = 0.0
            # Apply limits
            if self.channel.minLimit > -1.0e33 or self.channel.maxLimit < 1.0e33:
                if newy > self.channel.maxLimit: newy = self.channel.maxLimit
                if newy < self.channel.minLimit: newy = self.channel.minLimit

            self.channel.knots[newx] = newy
            if key == self.selectedKey: self.selectedKey = newx
            newList.append(newx)
        self.selectedKeyList = newList
        # Record motion in mainwindow
        self.holder.lastDeltaX += xdelta
        self.holder.lastDeltaY += ydelta

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
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier: return
        if event.buttons() == Qt.LeftButton and self.currMode == self.KNOT_MODE:
            if self.selectedKey is not None:
                if self.selectedKey not in self.selectedKeyList:
                    self.selectedKeyList = []   # Clear current list of selected keys
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
                else:
                    # Move all the knots that are selected
                    xplotval = self.invTransform(qwt.QwtPlot.xBottom, event.pos().x() - self.xoffset)
                    yplotval = self.invTransform(qwt.QwtPlot.yLeft, event.pos().y() - self.yoffset)
                    xprev = self.selectedKey
                    yprev = self.channel.knots[xprev]
                    xdelta = xplotval - xprev
                    ydelta = yplotval - yprev
                    if self.channel.type == Channel.DIGITAL:
                        # Only allow horizontal movement when dragging with mouse
                        ydelta = 0
                    self.doTheMove(xdelta, ydelta)
            else:
                # Mark current end of drag area to select multiple knots
                self.selectedKeyList = []   # Clear current list of selected keys
                xplotval = self.invTransform(qwt.QwtPlot.xBottom, event.pos().x() - self.xoffset)
                self.dragend = xplotval
                for keyval in self.channel.knots:
                    if keyval >= min(self.dragend, self.dragstart) and keyval <= max(self.dragend, self.dragstart):
                        self.selectedKeyList.append(keyval)
                self.redrawme()

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
            self.timeSlider.setData([timeVal], [70000.0])
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
        channelname = self.channel.name
        # Append the channel type indicator to the channel name
        if self.channel.type == Channel.DIGITAL:
            channelname += '(D'
        else:
            channelname += '(S'
        # If port number is set, append it to the displayed channel name
        if self.channel.port >= 0:
            channelname += '%d' % self.channel.port
        channelname += ')'
        self.setAxisTitle(qwt.QwtPlot.yLeft, channelname)
        # Recreate the data plot
        xdata,ydata = self.channel.getPlotData(self.minTime, self.maxTime, 10000)
        if self.curve is not None:
            self.curve.setData(xdata, ydata)
        # Recreate the knot plot
        xdata,ydata = self.channel.getKnotData(self.minTime, self.maxTime, 10000)
        if self.curve2 is not None:
            self.curve2.setData(xdata, ydata)
        if self.curve3 is not None:
            # Color all selected knots
            xdata = []
            if self.selectedKey is not None:
                xdata = [self.selectedKey]
            for key in self.selectedKeyList:
                if xdata not in self.selectedKeyList: xdata.append(key)
            ydata = [self.channel.knots[key] for key in xdata]
            self.curve3.setData(xdata, ydata)

        if xdata is not None:
            self.setToolTip('Use Left Mouse Button to drag individual points or select multiple points to drag')
        self.redrawLimits()
        self.replot()

#####################################################################
# The ChannelNameValidator is used to check and validate channel
# whilst the user is inputting them into a name field.
#  Rules:
# Channel Name may not start or end with a space
# Channel Name must not already be used
# Channel Name can only contain digits, upper and lower case text, and _, -, or space
# The empty string is acceptable but only one at a time
#####################################################################
class ChannelNameValidator(QValidator):
    def __init__(self, parent, namelist = []):
        super().__init__(parent)
        self.namelist = namelist

    def validate(self, arg1, arg2):
        if len(arg1) > 0 and arg1[0] == ' ':
            return QValidator.Invalid, arg1, arg2
        elif arg1 in self.namelist or len(arg1) == 0 or (len(arg1) > 0 and arg1[-1] == ' '):
            return QValidator.Intermediate, arg1, arg2
        else:
            match = re.match('^[A-Za-z0-9_\- ]*$', arg1)
            if match is not None:
                return QValidator.Acceptable, arg1, arg2
            else:
                return QValidator.Invalid, arg1, arg2



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
    editing a channel.  When editing, it is not allowed to change the
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

    # List of Configured Port Numbers, either from tables or preferences
    DigitalPorts = None
    PWMPorts = None

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

        self.okButton = QPushButton('Save')
        self.okButton.setDefault(True)
        self.cancelButton = QPushButton('Cancel')

        self._nameedit = QLineEdit()
        self._nameedit.setReadOnly(not editable)
        self._nameedit.setText('Empty So Far')
        self._nameedit.textChanged.connect(self.theTextChanged)
        invalidChannelNames = list(main_win.plots)
        # Remove this channel's current name from list
        if self._channel.name in invalidChannelNames:
            invalidChannelNames.remove(self._channel.name)
        self._nameedit.setValidator(ChannelNameValidator(parent, invalidChannelNames))
        self._nameedit.setText(self._channel.name)
        layout.addRow(QLabel('Name:'), self._nameedit)

        if self._channel is not None and self._channel.type != Channel.DIGITAL:
            self._servoedit = QComboBox()
            self._servoedit.addItem('')
            for servo in ServoData:
                self._servoedit.addItem(servo)
            if self._channel.servoType is not None:
                self._servoedit.setCurrentText(self._channel.servoType)
            else:
                self._servoedit.setCurrentIndex(0)
                self._servoedit.setToolTip('If your servo is not in list, Cancel,\nadd it through Servo tool, and come back')
            layout.addRow(QLabel('Servo:'), self._servoedit)
            self._servoedit.currentIndexChanged.connect(self.setLimitsfromType)

            self._typeedit = QComboBox()
            self._typeedit.addItems(('Linear', 'Spline', 'Step'))
            self._typeedit.setCurrentIndex(self._channel.type-1)
            layout.addRow(QLabel('Type:'), self._typeedit)

        self._portedit = QComboBox()
        currentText = 'Unassigned'
        if self._channel.type != Channel.DIGITAL:
            usedNumericPorts = main_win.getUsedNumericPorts()
            chancount = SystemPreferences['MaxServoChannels']
            for i in self.PWMPorts:
                if i not in usedNumericPorts or i == self._channel.port:
                    text = 'S' + str(i)
                    self._portedit.addItem(text)
                    if i == self._channel.port:
                        currentText = text
        else:
            usedDigitalPorts = main_win.getUsedDigitalPorts()
            chancount = SystemPreferences['MaxDigitalChannels']
            for i in self.DigitalPorts:
                if i not in usedDigitalPorts or i == self._channel.port:
                    text = 'D' + str(i)
                    self._portedit.addItem(text)
                    if i == self._channel.port:
                        currentText = text

        self._portedit.addItem('Unassigned')
        self._portedit.setCurrentText(currentText)
        layout.addRow(QLabel('Channel:'), self._portedit)

        if self._channel is not None:
            if self._channel.type != Channel.DIGITAL:
                self._maxedit = QLineEdit()
                layout.addRow(QLabel('Max:'), self._maxedit)
                self._minedit = QLineEdit()
                layout.addRow(QLabel('Min:'), self._minedit)
                if self._channel.minLimit > -1.0e33 or self._channel.maxLimit < 1.0e33:
                    self._minedit.setText(str(self._channel.minLimit))
                    self._maxedit.setText(str(self._channel.maxLimit))
                else:
                    self._minedit.setText(str(SystemPreferences['ServoDefaultMinimum']))
                    self._maxedit.setText(str(SystemPreferences['ServoDefaultMaximum']))
            interactive = QPushButton('Interactive')
            interactive.clicked.connect(self.doInteractive)
            layout.addWidget(interactive)

        widget.setLayout(layout)

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

    @staticmethod
    def setPortLists():
        if COMMLIB_ENABLED:
            ChannelMetadataWidget.DigitalPorts = commlib.getConfiguredDigitalPorts()
            ChannelMetadataWidget.PWMPorts = commlib.getConfiguredPWMPorts()
        if ChannelMetadataWidget.DigitalPorts is None:
            ChannelMetadataWidget.DigitalPorts = [i for i in range(SystemPreferences['MaxDigitalChannels'])]
        if ChannelMetadataWidget.PWMPorts is None:
            ChannelMetadataWidget.PWMPorts = [i for i in range(SystemPreferences['MaxServoChannels'])]

    def theTextChanged(self, text):
        if self._nameedit.hasAcceptableInput():
            self.okButton.setEnabled(True)
            p = self._nameedit.palette()
            p.setColor(self._nameedit.backgroundRole(), Qt.white)
            self._nameedit.setPalette(p)
            self._nameedit.setAutoFillBackground(False)
            self._nameedit.setToolTip(None)
        else:
            self.okButton.setEnabled(False)
            p = self._nameedit.palette()
            p.setColor(self._nameedit.backgroundRole(), Qt.red)
            self._nameedit.setPalette(p)
            self._nameedit.setAutoFillBackground(True)
            self._nameedit.setToolTip('Channel name "%s" may already be in use!' % text)

    def doInteractive(self):
        port = -1
        if self._portedit.currentText() != 'Unassigned':
            port = int(self._portedit.currentText()[1:])
            if self._channel.type != Channel.DIGITAL:
                widget = LimitWidget(self, minimum=float(self._minedit.text()), maximum=float(self._maxedit.text()), port = port)
                widget.setMinSignal.connect(self.setMin)
                widget.setMaxSignal.connect(self.setMax)
            else:
                widget = SetDigitalWidget(self, port = port)
            widget.setWindowTitle(str(port))
            widget.show()
        else:
            # Unable to do interactive control without a port number
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Channel must be set to support interactive control')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()

    def setMax(self, value):
        self._maxedit.setText(value)

    def setMin(self, value):
        self._minedit.setText(value)

    def setLimitsfromType(self, index):
        servoName = self._servoedit.currentText()
        if len(servoName) > 0 and servoName in ServoData:
            # Compute and set limits from servo type
            minVal = ServoData[servoName]['MinDuty']
            maxVal = ServoData[servoName]['MaxDuty']
            minVal = minVal / ServoData[servoName]['Period']
            minVal = int(minVal * (SystemPreferences['ServoDefaultMaximum'] - SystemPreferences['ServoDefaultMinimum']) +
                    SystemPreferences['ServoDefaultMinimum'] + 1)   # Add 1 to round up
            maxVal = maxVal / ServoData[servoName]['Period']
            maxVal = int(maxVal * (SystemPreferences['ServoDefaultMaximum'] - SystemPreferences['ServoDefaultMinimum']) +
                    SystemPreferences['ServoDefaultMinimum'])
            self.setMin(str(minVal))
            self.setMax(str(maxVal))

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
                # Find min and max values in the current knots
                minVal = 1.0e34
                maxVal = -1.0e34
                for keyval in self._channel.knots:
                    if self._channel.knots[keyval] < minVal:
                        minVal = self._channel.knots[keyval]
                    if self._channel.knots[keyval] > maxVal:
                        maxVal = self._channel.knots[keyval]
                # If any exceed the new limits
                if minVal < minLimit or maxVal > maxLimit:
                    # Get user concurrence to truncate values to new limits
                    msgBox = QMessageBox(parent=self)
                    msgBox.setText('Knots in the channel fall outside these limits.')
                    msgBox.setInformativeText("Proceed and modify them to fit?")
                    msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                    msgBox.setIcon(QMessageBox.Warning)
                    ret = msgBox.exec_()
                    if ret != QMessageBox.Yes:
                        # Cancel selected so don't do any updating below
                        self.close()
                        return
        else:
            # Digital channel limits are ALWAYS 0 and 1
            minLimit = 0.0
            maxLimit = 1.0

        # Push current state for undo
        pushState()

        # Limit existing values to new limits
        # Note that this will do nothing if they already fit
        for keyval in self._channel.knots:
            if self._channel.knots[keyval] < minLimit:
                self._channel.knots[keyval] = minLimit
            if self._channel.knots[keyval] > maxLimit:
                self._channel.knots[keyval] = maxLimit

        if self._channel.type != Channel.DIGITAL:
            tstring = self._servoedit.currentText()
            if len(tstring) > 0:
                self._channel.servoType = tstring
            self._channel.type = self._typeedit.currentIndex() + 1

        tstring = self._portedit.currentText()
        if len(tstring) > 0:
            if tstring == 'Unassigned':
                self._channel.port = -1
            else:
                self._channel.port = int(tstring[1:])

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

        newname = self._nameedit.text()
        self._channel.name = newname
        self.accept()
        if main_win is not None: main_win.updateXMLPane()

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
    _csvuploadedit : QLineEdit
    _audiouploadfile : QLineEdit
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
        self._audioedit = None
        if self._animatronics.newAudio is not None:
            self._audioedit = QLineEdit(str(self._animatronics.newAudio.audiostart))
            layout.addRow(QLabel('Audio Start Time:'), self._audioedit)
            layout.addRow(QLabel('Audio File:'))
            self._audiofile = QLineEdit('')
            self._audiofile.setText(self._animatronics.newAudio.audiofile)
            self._audiofile.setReadOnly(True)
            layout.addRow(self._audiofile)
        self._csvuploadedit = QLineEdit(self._animatronics.csvUploadFile)
        layout.addRow(QLabel('CSV Upload File:'), self._csvuploadedit)
        self._audiouploadedit = QLineEdit(self._animatronics.audioUploadFile)
        layout.addRow(QLabel('Audio Upload File:'), self._audiouploadedit)

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
        if self._audioedit is not None:
            tstring = self._audioedit.text()
            if len(tstring) > 0:
                self._animatronics.newAudio.audiostart = float(tstring)
        self._animatronics.csvUploadFile = self._csvuploadedit.text()
        self._animatronics.audioUploadFile = self._audiouploadedit.text()
        self.accept()
        if self._parent is not None:
            self._parent.redraw()
            self._parent.updateXMLPane()

#####################################################################
# The ServoWidget is used to twiddle servo parameters and add new ones
#####################################################################
class ServoWidget(QDialog):

    colnames = ['Name', 'Period','MinDuty', 'MaxDuty', 'MinAngle', 'MaxAngle']
    labels = ['Name', 'Period(ms)','MinDuty(ms)', 'MaxDuty(ms)', 'MinAngle(deg)', 'MaxAngle(deg)']

    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableWidget()
        self.table.setRowCount(len(ServoData))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(ServoWidget.labels)
        self.table.currentCellChanged.connect(self.checkCell)

        # Populate from ServoData
        row = 0
        for servo in ServoData:
            col = 0
            for colname in ServoWidget.colnames:
                self.table.setItem(row, col, QTableWidgetItem(str(ServoData[servo][colname])))
                col += 1
            row += 1

        self.addButton = QPushButton('Add')
        self.delButton = QPushButton('Delete')
        self.okButton = QPushButton('Save')
        self.cancelButton = QPushButton('Cancel')

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.addButton)
        hbox.addWidget(self.delButton)
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.table)
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        self.addButton.clicked.connect(self.onAdd)
        self.delButton.clicked.connect(self.onDel)
        self.okButton.clicked.connect(self.onAccepted)
        self.cancelButton.clicked.connect(self.reject)

    def checkCell(self, currRow, currCol, prevRow, prevCol):
        item = self.table.item(prevRow, prevCol)
        if item is None:
            item = QTableWidgetItem('')
            item.setBackground(QBrush(Qt.red))
            item.setToolTip('Value must be specified')
            self.table.setItem(prevRow, prevCol, item)
        elif ServoWidget.colnames[prevCol] == 'Name':
            if len(item.text()) == '0':
                item.setBackground(QBrush(Qt.red))
                item.setToolTip('Value must be specified')
            else:
                item.setBackground(QBrush(Qt.white))
                item.setToolTip('')
        else:
            item.setBackground(QBrush(Qt.white))
            item.setToolTip('')
            if len(item.text()) == '0':
                item.setBackground(QBrush(Qt.red))
                item.setToolTip('Value must be specified')
            else:
                try:
                    itemValue = float(item.text())
                except:
                    item.setBackground(QBrush(Qt.red))
                    item.setToolTip('Value must be numeric')

    def onAccepted(self):
        global ServoData

        # Validate table data
        valid = True
        usedNames = []
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item is not None:
                    if ServoWidget.colnames[col] == 'Name':
                        if len(item.text()) == '0':
                            valid = False
                            item.setBackground(QBrush(Qt.red))
                            item.setToolTip('Name must be nonempty')
                        else:
                            if item.text() in usedNames:
                                valid = False
                                item.setBackground(QBrush(Qt.red))
                                item.setToolTip('Name must be unique')
                            else:
                                item.setBackground(QBrush(Qt.white))
                                usedNames.append(item.text())
                                item.setToolTip('')
                    else:
                        if len(item.text()) == '0':
                            valid = False
                            item.setBackground(QBrush(Qt.red))
                            item.setToolTip('Value must be specified')
                        else:
                            try:
                                itemValue = float(item.text())
                                item.setBackground(QBrush(Qt.white))
                                item.setToolTip('')
                            except:
                                valid = False
                                item.setBackground(QBrush(Qt.red))
                                item.setToolTip('Value must be numeric')
                else:
                    valid = False
                    item = QTableWidgetItem('')
                    item.setBackground(QBrush(Qt.red))
                    item.setToolTip('Value must be specified')
                    self.table.setItem(row, col, item)

        if not valid: return

        # Save a backup copy of servo file
        ServoWidget.writeServoData(SystemPreferences['ServoDataFile'] + '.bak')

        # Populate servodata from table
        ServoData = {}
        for row in range(self.table.rowCount()):
            servo = {}
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if ServoWidget.colnames[col] == 'Name':
                    servo[ServoWidget.colnames[col]] = item.text()
                else:
                    servo[ServoWidget.colnames[col]] = float(item.text())
            ServoData[servo['Name']] = servo

        # Save it to file named in preferences
        ServoWidget.writeServoData(SystemPreferences['ServoDataFile'])

        self.accept()

    def onAdd(self):
        # Add a blank line at bottom of table
        self.table.insertRow(self.table.rowCount())

    def onDel(self):
        # Remove currently selected row
        self.table.removeRow(self.table.currentRow())

    @staticmethod
    def readServoData(inFilename):
        global ServoData

        if not os.path.exists(inFilename):
            inFilename = os.path.join(getExecPath(), inFilename)

        try:
            with open(inFilename, 'r') as infile:
                # Read header line
                testtext = infile.readline()
                headers = testtext.rstrip().split(',')
                try:
                    nameindex = headers.index('Name')
                except:
                    sys.stderr.write('Whoops - Unable to read servo data file %s\n' % inFilename)
                    return

                # Read the rest and build a dictionary for each and add to ServoData dictionary
                testtext = infile.readline()
                while len(testtext) > 0:
                    columns = testtext.rstrip().split(',')
                    tdict = {}
                    for i in range(len(columns)):
                        if i != nameindex:
                            value = float(columns[i])
                        else:
                            value = columns[i]
                        tdict[headers[i]] = value
                    ServoData[columns[nameindex]] = tdict
                    testtext = infile.readline()
        except:
            sys.stderr.write('Whoops - Unable to open servo data file %s\n' % inFilename)

    @staticmethod
    def writeServoData(filename):
        if len(ServoData) == 0: return
        with open(filename, 'w') as outfile:
            # Write header line
            for servo in ServoData:
                first = True
                for field in ServoData[servo]:
                    if not first: outfile.write(',')
                    outfile.write('%s' % field)
                    first = False
                outfile.write('\n')
                break
            # Write data lines
            for servo in ServoData:
                first = True
                for field in ServoData[servo]:
                    if not first: outfile.write(',')
                    outfile.write('%s' % str(ServoData[servo][field]))
                    first = False
                outfile.write('\n')


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
            elif SystemPreferenceTypes[pref] == 'bool':
                newedit = QComboBox()
                newedit.addItems(('True','False'))
                self._layout.addRow(QLabel(pref), newedit)
                self._widgets[pref] = newedit
                if SystemPreferences[pref]:
                    newedit.setCurrentText('True')
                else:
                    newedit.setCurrentText('False')
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
            elif SystemPreferenceTypes[pref] == 'int':
                SystemPreferences[pref] = int(self._widgets[pref].text())
            elif SystemPreferenceTypes[pref] == 'float':
                SystemPreferences[pref] = float(self._widgets[pref].text())
            elif SystemPreferenceTypes[pref] == 'bool':
                SystemPreferences[pref] = self._widgets[pref].currentText() == 'True'
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
                    elif SystemPreferenceTypes[pref] == 'bool':
                        if SystemPreferences[pref]:
                            prefs.write('%s:%s\n' % ( pref, 'True'))
                        else:
                            prefs.write('%s:%s\n' % ( pref, 'False'))
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
        PreferencesWidget.updateStuff()

    @staticmethod
    def updateStuff():
        # Update local data structures based on preferences updates
        try:
            if 'TTYPortRoot' in SystemPreferences and COMMLIB_ENABLED:
                commlib.portRoot = SystemPreferences['TTYPortRoot']
            if 'ServoDataFile' in SystemPreferences:
                ServoWidget.readServoData(SystemPreferences['ServoDataFile'])
            ChannelMetadataWidget.setPortLists()
        except:
            # Unable to set preferences
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Unable to set preferences locally:')
            msgBox.setInformativeText(preffile)
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()
            pass



    @staticmethod
    def readPreferences():
        """ Static method to read the preferences file if it exists """
        try:
            preffile = os.path.join(os.path.expanduser("~"), '.animrc')
            with open(preffile, 'r') as prefs:
                line = prefs.readline()
                while line:
                    # Strip off trailing whitespace and split on :
                    vals = line.rstrip().split(':')
                    if len(vals) == 2 and vals[0] in SystemPreferenceTypes and vals[0] in SystemPreferences:
                        if SystemPreferenceTypes[vals[0]] == 'int':
                            SystemPreferences[vals[0]] = int(vals[1])
                        elif SystemPreferenceTypes[vals[0]] == 'float':
                            SystemPreferences[vals[0]] = float(vals[1])
                        elif SystemPreferenceTypes[vals[0]] == 'bool':
                            SystemPreferences[vals[0]] = vals[1] == 'True'
                        else:
                            SystemPreferences[vals[0]] = vals[1]
                    line = prefs.readline()
        except:
            # Unable to read preferences file but that's okay
            # Should already be set to defaults
            pass
        PreferencesWidget.updateStuff()

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
        self.wasPlaying = False

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
        self._setleftbutton.setToolTip('Zooms display range left edge to current time')
        layout.addWidget(self._setleftbutton)

        self._setrightbutton = QPushButton()
        self._setrightbutton.setFixedHeight(24)
        self._setrightbutton.setText('Set Right')
        self._setrightbutton.setToolTip('Zooms display range right edge to current time')
        layout.addWidget(self._setrightbutton)

        tlabel = QLabel('Speed:')
        layout.addWidget(tlabel)
        self._speedselect = QComboBox()
        self.speedchoices = ['100%', '50%', '25%', '10%']
        self.speedfactors = [1.0, 0.5, 0.25, 0.1]
        self._speedselect.addItems(self.speedchoices)
        layout.addWidget(self._speedselect)

        self.liveCheck = QCheckBox('Live')
        self.liveCheck.setChecked(False)
        self.liveCheck.setEnabled(COMMLIB_ENABLED)
        self.liveCheck.setToolTip('Enables real-time output to control animation')
        layout.addWidget(self.liveCheck)

        layout.addStretch()

        self.setLayout(layout)

        self.timeChangedCallbacks = []

    def livePlay(self):
        return self.liveCheck.isChecked()

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

    def setCurrentPosition(self, newTime):
        newTime = int(newTime * 1000)
        if self.mediaPlayer is not None:
            self.mediaPlayer.setPosition(newTime)
        self.currPosition = newTime

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
        if self.currPosition >= self._endPosition or (not self.is_media_playing() and self.wasPlaying):
            # If we reached the end of the media, make sure everything is stopped and go to the beginning
            self.stopplaying()
            self.rewind()
        else:
            # If player not already playing
            if self.mediaPlayer is not None:
                self.mediaPlayer.setPlaybackRate(self.speedfactors[self._speedselect.currentIndex()])
                if not self.is_media_playing():
                    # Check to see if it should be
                    desiredPosn = self.currPosition - self._offset
                    if desiredPosn >= 0 and desiredPosn < self.mediaPlayer.duration():
                        self.mediaPlayer.setPosition(desiredPosn)
                        self.mediaPlayer.play()
                        self.wasPlaying = True
                self.currPosition = self.mediaPlayer.position()
                for cb in self.timeChangedCallbacks:
                    cb(float(self.currPosition) / 1000.0)

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
        if self.mediaPlayer is not None: self.mediaPlayer.stop()
        self.timer.stop()
        self.wasPlaying = False

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
        Set of ChannePane objects for displaying the individual channels
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

        global main_win
        main_win = self

        # Create file dialog used only for saving files
        self.filedialog = QFileDialog(parent=self, caption="Get Save Filename")
        self.filedialog.setOption(QFileDialog.DontUseNativeDialog)
        self.filedialog.setAcceptMode(QFileDialog.AcceptSave)
        self.filedialog.setFileMode(QFileDialog.AnyFile)

        # Initially Tag Selector Dialog is None
        self.tagSelectDialog = None

        # Create the XML display dialog for constant refresh
        self.XMLPane = TextDisplayDialog('XML', parent=self)
        self.ClipboardPane = TextDisplayDialog('Clipboard', parent=self)

        # Create the Help Popup
        self.helpPane = TextDisplayDialog('Hauntimator Help', parent=self)

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

        # Create dictionaries for plugins
        self.external_callables = {}

        # Create all the dropdown menus
        self.create_menus()

        # Initialize some stuff
        self.setWindowTitle("Hauntimator")
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
        self.clipboard.dataChanged.connect(self.updateClipboard_action)
        # For saving drags after pasting
        self.lastDeltaX = 0.0
        self.lastDeltaY = 0.0
        self.repCount = 0

        self.lastNoted = None

        # Create the TimeRangeDialog
        self.timerangedialog = self.TimeRangeDialog(parent=self)


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

        # Set all the left axes to align
        LeftAlignLayout.setMaxScaleWidth(70.0)

        # Add filename to window title
        if self.animatronics.filename is not None:
            self.setWindowTitle("Hauntimator - " +
                self.animatronics.filename)
        else:
            self.setWindowTitle("Hauntimator")

        # Create the bottom level widget and make it the main widget
        self._mainarea = QFrame(self)
        self._mainarea.setMaximumSize(3800,1000)
        self.setCentralWidget(self._mainarea)

        # Set up the playback widget
        self._playwidget = Player(audio=self.animatronics.newAudio)
        shortcut = QShortcut(QKeySequence(" "), self._mainarea)
        shortcut.activated.connect(self._playwidget.play)
        self._playwidget.setLeftConnect(self.cutLeftSide)
        self._playwidget.setRightConnect(self.cutRightSide)
        self._playwidget.addTimeChangedCallback(self.timeChanged)
        self._playwidget.addTimeChangedCallback(self.livePlay)
        self._playwidget.hide()
        tlayout = QVBoxLayout(self._mainarea)
        tlayout.addWidget(self._playwidget)

        # Create shortcut to play animation on controller
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self._mainarea)
        shortcut.activated.connect(self._hardwareplay)

        self._plotarea = QWidget()
        tlayout.addWidget(self._plotarea)

        # Add some tooltips to get user started
        if self.animatronics.newAudio is None and len(self.animatronics.channels) == 0:
            # Just beginning so help a lot
            if SystemPreferences['ShowTips']: self._plotarea.setToolTip(
                'Hit File->Open Audio File to add audio or\nCtrl-N or Ctrl-D to add a new control channel')
        elif len(self.animatronics.channels) == 0:
            if SystemPreferences['ShowTips']: self._plotarea.setToolTip(
                'Ctrl-N to add a new servo channel or\nCtrl-D to add a new digital channel')

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
                newplot.setPlotLayout(LeftAlignLayout())
                newplot.mousePressEvent = self.localmousePressEvent
                newplot.mouseMoveEvent = self.localmouseMoveEvent
                self.audioCurve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=leftdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlot = newplot
                self.audioPlot.setMaximumHeight(200)
                if SystemPreferences['ShowTips']: self.audioPlot.setToolTip('Click and drag Ctrl-Left mouse button\nup/down to zoom and left/right to scroll')
                # Add visibility checkbox to menu as visible initially
                self._show_audio_menu.addAction(self._showmono_audio_action)
                self._showmono_audio_action.setChecked(True)
            else:
                newplot = qwt.QwtPlot('Audio Left')
                newplot.setPlotLayout(LeftAlignLayout())
                newplot.mousePressEvent = self.localmousePressEvent
                newplot.mouseMoveEvent = self.localmouseMoveEvent
                self.audioCurve = qwt.QwtPlotCurve.make(xdata=xdata, ydata=leftdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlot = newplot
                self.audioPlot.setMaximumHeight(150)
                if SystemPreferences['ShowTips']: self.audioPlot.setToolTip('Click and drag Ctrl-Left mouse button\nup/down to zoom and left/right to scroll')
                # Add visibility checkbox to menu as visible initially
                self._show_audio_menu.addAction(self._showleft_audio_action)
                self._showleft_audio_action.setChecked(True)
                newplot = qwt.QwtPlot('Audio Right')
                newplot.setPlotLayout(LeftAlignLayout())
                newplot.mousePressEvent = self.localmousePressEvent
                newplot.mouseMoveEvent = self.localmouseMoveEvent
                self.audioCurveRight = qwt.QwtPlotCurve.make(xdata=xdata, ydata=rightdata,
                    title='Audio', plot=newplot,
                    )
                layout.addWidget(newplot)
                self.audioPlotRight = newplot
                self.audioPlotRight.setMaximumHeight(150)
                if SystemPreferences['ShowTips']: self.audioPlotRight.setToolTip('Click and drag Ctrl-Left mouse button\nup/down to zoom and left/right to scroll')
                # Add visibility checkbox to menu as visible initially
                self._show_audio_menu.addAction(self._showright_audio_action)
                self._showright_audio_action.setChecked(True)

            # Set range to match length of audio
            if self.audioMax > self.totalMax: self.totalMax = self.audioMax
            self.lastXmin = self.audioMin
            self.lastXmax = self.audioMax

            self.redrawAudio(self.audioMin, self.audioMax)

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

        # Add the tags pane here
        self.tagPlot = TagPane(self, self.animatronics.tags, self)
        self.tagPlot.setPlotLayout(LeftAlignLayout())
        self.tagPlot.redrawTags(self.lastXmin, self.lastXmax)
        layout.addWidget(self.tagPlot)

        # Add panes for all the channels
        channelList = self.animatronics.channels

        for channel in channelList:
            chan = self.animatronics.channels[channel]
            newplot = ChannelPane(self._plotarea, chan, mainwindow=self)
            newplot.setPlotLayout(LeftAlignLayout())
            newplot.settimerange(self.lastXmin, self.lastXmax)
            if len(chan.knots) == 0:
                if SystemPreferences['ShowTips']: newplot.setToolTip('Use Shift-LeftMouseButton to add control points')
            layout.addWidget(newplot)
            self.plots[chan.name] = newplot

        # Improve layout by sticking audio to the top
        layout.addStretch()

        self._playwidget.setRange(self.lastXmin, self.lastXmax)
        self.setSlider(self.lastXmin)

    def getUsedNumericPorts(self):
        usedPorts = []
        for channel in self.animatronics.channels:
            if self.animatronics.channels[channel].type != Channel.DIGITAL:
                if self.animatronics.channels[channel].port >= 0:
                    usedPorts.append(self.animatronics.channels[channel].port)
        return usedPorts

    def getUsedDigitalPorts(self):
        usedPorts = []
        for channel in self.animatronics.channels:
            if self.animatronics.channels[channel].type == Channel.DIGITAL:
                if self.animatronics.channels[channel].port >= 0:
                    usedPorts.append(self.animatronics.channels[channel].port)
        return usedPorts

    def deleteSelectedPoints(self):
        channellist = self.getSelectedChannelNames()
        for name in channellist:
            pane = self.plots[name]
            pane.deleteMyPoints()
            pane.redrawme()

    def moveSelectedPoints(self, xdelta, ydelta):
        channellist = self.getSelectedChannelNames()
        for name in channellist:
            pane = self.plots[name]
            if pane.channel.type == Channel.DIGITAL:
                pane.moveMyPoints(xdelta, 0)
            else:
                pane.moveMyPoints(xdelta, ydelta)
            pane.redrawme()

    def noteLast(self, channelName):
        self.lastNoted = channelName

    def shiftSelect(self, channelName):
        # Select all channels from lastNoted to this one
        if self.lastNoted is None and channelName in self.plots:
            self.plots[channelName].select()
            self.plots[channelName].redrawme()
            self.lastNoted = channelName
        else:
            inMode = False
            for name in self.plots:
                if (name == channelName or name == self.lastNoted) and self.lastNoted != channelName:
                    inMode = not inMode
                if inMode or name == channelName or name == self.lastNoted:
                    self.plots[name].select()
                    self.plots[name].redrawme()
        pass

    def shiftDeselect(self, channelName):
        # Deselect all channels from lastNoted to this one
        if self.lastNoted is None and channelName in self.plots:
            self.plots[channelName].deselect()
            self.plots[channelName].redrawme()
            self.lastNoted = channelName
        else:
            inMode = False
            for name in self.plots:
                if (name == channelName or name == self.lastNoted) and self.lastNoted != channelName:
                    inMode = not inMode
                if inMode or name == channelName or name == self.lastNoted:
                    self.plots[name].deselect()
                    self.plots[name].redrawme()
            pass

    def _hardwareplay(self):
        """
        The method _hardwareplay uses commlib to signal the hardware to play
        as though the onboard button was pressed once.
        """
        if COMMLIB_ENABLED: commlib.playOnce()

    def livePlay(self, currTime):
        if self._playwidget.livePlay():
            channellist = self.getSelectedChannelNames()
            for channel in channellist:
                if self.animatronics.channels[channel].port >= 0:
                    # getValueAtTime is not implemented so we get a range of values and take the first one
                    value = self.animatronics.channels[channel].getValuesAtTimeSteps(currTime, currTime+1.0, 0.5)[0]
                    port = self.animatronics.channels[channel].port
                    if self.animatronics.channels[channel].type == Channel.DIGITAL:
                        commlib.setDigitalChannel(port, value)
                    else:   # For now must be servo type channel
                        commlib.setServo(port, value)

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
                    newAnim.parseXML(fileName, uploadpath=SystemPreferences['UploadPath'])
                    self.setAnimatronics(newAnim)
                    # Clear out Redo history
                    self.pendingStates = []
                    self.unsavedChanges = False

                except Exception as e:
                    self.undo_action()
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

    def matchup(self, newanim):
        bothlist = []
        newlist = []
        oldlist = []

        for name in self.animatronics.channels:
            if name in newanim.channels:
                bothlist.append(name)
            else:
                oldlist.append(name)
        for name in newanim.channels:
            if name not in self.animatronics.channels:
                newlist.append(name)

        return bothlist, newlist, oldlist

    def appendAnimFile(self):
        """
        The method appendAnimFile opens a file dialog for the user to select
        an Animatronics file to load and then appends that file into the
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

        """Append an animatronics file onto the current one"""
        fileName, _ = QFileDialog.getOpenFileName(self,"Get Append Filename", "",
                            "Anim Files (*.anim);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                newanimatronics = Animatronics()
                newanimatronics.parseXML(fileName)
                bothlist, newlist, oldlist = self.matchup(newanimatronics)

                if len(newlist) == 0 and len(oldlist) == 0:
                    # easy append as all channels are in both
                    pass
                else:
                    # Issue a warning
                    msgBox = QMessageBox(parent=self)
                    msgBox.setText('The two sets of animation channels do not match!')
                    msgBox.setInformativeText("Proceed?")
                    detailedtext = ''
                    if len(bothlist) > 0:
                        detailedtext += 'These channels match and will be appended:\n    '
                        for name in bothlist:
                            detailedtext += name + ', '
                        detailedtext = detailedtext[:-2]
                    if len(newlist) > 0:
                        detailedtext += '\nThese channels are only in the incoming animation and will not be appended:\n    '
                        for name in newlist:
                            detailedtext += name + ', '
                        detailedtext = detailedtext[:-2]
                    if len(oldlist) > 0:
                        detailedtext += '\nThese channels are only in the existing animation with nothing to append:\n    '
                        for name in oldlist:
                            detailedtext += name + ', '
                        detailedtext = detailedtext[:-2]
                    detailedtext += '\nTags will be appended.'
                    msgBox.setDetailedText(detailedtext)

                    msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                    msgBox.setDefaultButton(QMessageBox.Cancel)
                    msgBox.setIcon(QMessageBox.Warning)
                    ret = msgBox.exec_()
                    if ret == QMessageBox.Cancel:
                        return False

                # Push current state for undo
                pushState()

                # Do the actual appending of common channels
                for name in bothlist:
                    for knot in newanimatronics.channels[name].knots:
                        self.animatronics.channels[name].add_knot(knot, newanimatronics.channels[name].knots[knot])

                # Append the Tags channel as well
                self.animatronics.addTags(newanimatronics.tags)

                # Make sure everything gets redrawn
                self.setAnimatronics(self.animatronics)

            except Exception as e:
                self.undo_action()
                sys.stderr.write("\nWhoops - Error appending input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return

        pass

    def mergeAnimFile(self):
        """
        The method mergeAnimFile opens a file dialog for the user to select
        an Animatronics file to load and then merges that file into the
        current Animatronics.

        The merge process is intended to be used for combining multiple
        people's work on different sections of the animation.  It adds
        new channels to the current set.  It does not replace the current audio file.

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
                newanimatronics = Animatronics()
                newanimatronics.parseXML(fileName)
                bothlist, newlist, oldlist = self.matchup(newanimatronics)

                if len(bothlist) == 0:
                    # easy append as no channels are shared
                    pass
                else:
                    # Issue a warning
                    msgBox = QMessageBox(parent=self)
                    msgBox.setText('The two sets of animation channels overlap!')
                    msgBox.setInformativeText("Proceed?")
                    detailedtext = ''
                    if len(bothlist) > 0:
                        detailedtext += 'These channels match and will be ignored:\n    '
                        for name in bothlist:
                            detailedtext += name + ', '
                        detailedtext = detailedtext[:-2]
                    if len(newlist) > 0:
                        detailedtext += '\nThese channels are only in the incoming animation and will be merged:\n    '
                        for name in newlist:
                            detailedtext += name + ', '
                        detailedtext = detailedtext[:-2]
                    detailedtext += '\nTags will be merged.'
                    msgBox.setDetailedText(detailedtext)

                    msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                    msgBox.setDefaultButton(QMessageBox.Cancel)
                    msgBox.setIcon(QMessageBox.Warning)
                    ret = msgBox.exec_()
                    if ret == QMessageBox.Cancel:
                        return False

                # Push current state for undo
                pushState()

                # Do the actual adding of new channels
                for name in newlist:
                    xml = newanimatronics.channels[name].toXML()
                    self.animatronics.addChannel(xml)

                # Merge the Tags channel as well
                self.animatronics.addTags(newanimatronics.tags)

                # Make sure everything gets redrawn
                self.setAnimatronics(self.animatronics)

            except Exception as e:
                self.undo_action()
                sys.stderr.write("\nWhoops - Error merging input file %s\n" % fileName)
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
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Whoops - Unable to write to animatronics file:')
                msgBox.setInformativeText(self.animatronics.filename)
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
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
        fileName = 'Unknown'
        self.filedialog.setDefaultSuffix('anim')
        self.filedialog.setNameFilter("Anim Files (*.anim);;All Files (*)")
        if self.filedialog.exec_():
            try:
                fileName = self.filedialog.selectedFiles()[0]
                with open(fileName, 'w') as outfile:
                    # Set upload paths prior to writing
                    self.animatronics.setFilename(fileName, uploadpath=SystemPreferences['UploadPath'])
                    outfile.write(self.animatronics.toXML())
                self.updateXMLPane()    # Refreshes XML and saves to new autosave file
                self.unsavedChanges = False
                if self.animatronics.filename is None:
                    self.animatronics.filename = fileName
                    self.setWindowTitle("Hauntimator - " +
                        self.animatronics.filename)

            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Whoops - Unable to write to specified file:')
                msgBox.setInformativeText(fileName)
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
                return

        pass

    def run_plugin(self):
        #print('Running plugin', self.sender().text())
        if self.sender().data() is not None:
            # Get list of selected channels
            channellist = self.getSelectedChannels()
            if len(channellist) > 0:
                # Push current state for undo
                pushState()
                # Pass selected channels to the plugin function in the data field
                starttime = self.lastXmin
                endtime = self.lastXmax
                value = self.sender().data()(channellist, self.animatronics, starttime=starttime, endtime=endtime)
                if value:
                    # Redraw the modified channels
                    for name in self.plots:
                        if self.plots[name].selected:
                            self.plots[name].redrawme()
                    self.updateXMLPane()
                    self.tagPlot.setTags(self.animatronics.tags)
                else:
                    # Nothing was done so clean up
                    self.undo_action()

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
        # Get the filename to write to
        self.filedialog.setDefaultSuffix('csv')
        self.filedialog.setNameFilter("CSV Files (*.csv);;All Files (*)")
        if self.animatronics.filename is not None:
            basename, _ = os.path.splitext(self.animatronics.filename)
            basename = basename + '.csv'
            self.filedialog.selectFile(basename)

        if self.filedialog.exec_():
            fileName = self.filedialog.selectedFiles()[0]
            """
            try:
                self.writeCSVFile(fileName)
            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return
            """
            self.writeCSVFile(fileName)

            # Always see if commlib will write any binary files as well
            if COMMLIB_ENABLED:
                commlib.csvToBin(fileName)

    def writeCSVFile(self, fileName, integers=True):
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
        endtime += samplestep   # To make sure we get final state
        while currtime < endtime:
            if integers:
                timecolumn.append(int(currtime * 1000)) # Convert time column to integer milliseconds
            else:
                timecolumn.append(currtime)
            currtime += samplestep
        columns['Time'] = timecolumn

        # Get the data points for each column
        for plot in self.plots:
            values = self.plots[plot].channel.getValuesAtTimeSteps(starttime, endtime, samplestep)
            if values is not None:
                columns[plot] = values

        with open(fileName, 'w') as outfile:
            # Write out the column headers
            for channel in columns:
                theport = ''
                if channel != 'Time':
                    outfile.write(',')
                    portnum = self.plots[channel].channel.port
                    if self.plots[channel].channel.type == Channel.DIGITAL:
                        outfile.write('D%d' % portnum)
                    else:
                        outfile.write('S%d' % portnum)
                else:
                    outfile.write('Time')
            outfile.write('\n')
            # Write out all the data in columns
            for indx in range(len(timecolumn)):
                for channel in columns:
                    if channel != 'Time':
                        outfile.write(',')
                    if integers:
                        outfile.write('%i' % columns[channel][indx])
                    else:
                        outfile.write('%f' % columns[channel][indx])
                outfile.write('\n')


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

    def newProgressBar(self, title):
        # Create a ProgressDialog for use by verious operations
        progressdialog = QProgressDialog(title, 'Cancel', 0, 1, parent=self)
        progressdialog.setWindowModality(Qt.WindowModal)
        return progressdialog

    def uploadToHW(self):
        if self.animatronics.filename is not None:
            # Change the root filename extension to .csv and write to it
            tempfilename = os.path.splitext(self.animatronics.filename)[0] + '.csv'
        else:
            # Write CSV temp file
            tempfilename = 'tempdata%6d.csv' % random.randrange(100000,1000000)

        # Verify that destination is specified
        if self.animatronics.csvUploadFile is None:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Whoops - Upload destination not set.\n' +
                'Save animation file to implicitly set or\n' +
                'Edit metadata to explicitly set.')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
            return

        # Write the actual CSV file locally
        self.writeCSVFile(tempfilename)

        # Upload with commlib
        if COMMLIB_ENABLED:
            localprogressdialog = self.newProgressBar('Uploading Controls')
            code = commlib.xferCSVToController(tempfilename, dest=self.animatronics.csvUploadFile,
                progressbar=localprogressdialog)
            localprogressdialog.cancel()

            # Check return code
            if code < 0:
                # Cancel the progress dialog
                # Bring up message box to tell user
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Failed to upload CSV file to controller.\n' +
                    'Make sure you are not running thonny or rshell elsewhere.\n' +
                    'May need to reboot controller.')
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Information)
                ret = msgBox.exec_()
                pass
            elif self.animatronics.filename is None:
                # Delete data.csv
                os.remove(tempfilename)
            else:
                # Keep the local .csv and .bin if created
                pass

            if code == 1:
                starttime = self.animatronics.start
                endtime = self.animatronics.end
                binarytime = int((self.totalMax - self.totalMin) / 4 + len(self.plots) * 10)
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Conversion to binary format may be in progress.\n' +
                    'Wait for status LED to resume flashing before proceeding.\n' +
                    'Do not reset or power down hardware to avoid loss of data.\n' +
                    'May take up to %d seconds.' % binarytime)
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Information)
                msgBox.exec_()
        else:
            # no commlib.py in current directory
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Unable to upload data to controller without commlib\n')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()


    def uploadAudio(self):
        # Verify that destination is specified
        if self.animatronics.audioUploadFile is None:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Whoops - Upload destination not set.\n' +
                'Save animation file to implicitly set or\n' +
                'Edit metadata to explicitly set.')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
            return

        # Verify that an audio file has been specified
        if self.animatronics.newAudio is None or self.animatronics.newAudio.audiofile is None:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Whoops - No audio has been selected.\n')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
            return

        # Upload the audio file
        localprogressdialog = self.newProgressBar('Uploading Audio')
        if COMMLIB_ENABLED:
            code = commlib.xferFileToController(self.animatronics.newAudio.audiofile,
                dest=self.animatronics.audioUploadFile, progressbar=localprogressdialog)
        else:
            code = 1
        # Check return code
        if code != 0:
            # Cancel the progress dialog
            localprogressdialog.cancel()
            # Bring up message box to tell user
            msgBox = QMessageBox(parent=self)
            if not COMMLIB_ENABLED:
                msgBox.setText('Unable to upload audio to controller without commlib\n')
            else:
                msgBox.setText('Failed to upload audio file to controller.\n' +
                    'Make sure you are not running thonny or rshell elsewhere.\n' +
                    'May need to unplug and replug board USB connector and wait 30 seconds.')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
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
        self.saveStateOkay = False  # Do not save state for any changes here
        if len(self.previousStates) > 0:
            if self.animatronics is not None:
                # Get the display states of all channels
                chanStates = {}
                for plot in self.plots:
                    chanStates[plot] = self.plots[plot].getState()
                # Push current state onto pending states
                currState = self.animatronics.toXML()
                self.pendingStates.append((currState,
                    self.animatronics.filename,
                    self.lastXmin, self.lastXmax,
                    self.unsavedChanges, chanStates))
                # Pop last previous state
                currState = self.previousStates.pop()
                self.animatronics.fromXML(currState[0])
                self.setAnimatronics(self.animatronics)
                self.animatronics.filename = currState[1]
                # setTimeRange does the redraw so restore the state prior to that
                for plot in currState[5]:
                    self.plots[plot].setState(currState[5][plot])
                self.setTimeRange(currState[2], currState[3])
                self.unsavedChanges = currState[4]
                #print('Number of undos left:', len(self.previousStates))
        else:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('At earliest state')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
        self.saveStateOkay = True   # Allow saving state again
        # Keep XML display pane up to date with latest
        self.XMLPane.setText(self.animatronics.toXML())
        self.tagSelectUpdate()

    def autoSave(self):
        if SystemPreferences['AutoSave']:
            if self.animatronics.filename is not None:
                backupFilename = self.animatronics.filename + '.autosave'
            else:
                backupFilename = 'unnamedfile.anim.autosave'
            try:
                with open(backupFilename, 'w') as bakfile:
                    currState = self.animatronics.toXML()
                    bakfile.write(currState)
            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing autosave file %s\n" % backupFilename)
                sys.stderr.write("Message: %s\n" % e)
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Whoops - Unable to write to autosave file:')
                msgBox.setInformativeText(backupFilename)
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()

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
            # Get the display states of all channels
            chanStates = {}
            for plot in self.plots:
                chanStates[plot] = self.plots[plot].getState()
            # Push current state onto previous states
            currState = self.animatronics.toXML()
            self.previousStates.append((currState,
                self.animatronics.filename,
                self.lastXmin, self.lastXmax,
                self.unsavedChanges, chanStates))
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
                # Get the display states of all channels
                chanStates = {}
                for plot in self.plots:
                    chanStates[plot] = self.plots[plot].getState()
                self.previousStates.append((currState,
                    self.animatronics.filename,
                    self.lastXmin, self.lastXmax,
                    self.unsavedChanges, chanStates))
                # Pop next pending state
                currState = self.pendingStates.pop()
                self.animatronics.fromXML(currState[0])
                self.setAnimatronics(self.animatronics)
                self.animatronics.filename = currState[1]
                # setTimeRange does the redraw so restore the state prior to that
                for plot in currState[5]:
                    self.plots[plot].setState(currState[5][plot])
                self.setTimeRange(currState[2], currState[3])
                self.unsavedChanges = currState[4]
                #print('Number of redos left:', len(self.pendingStates))
        else:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('At latest state')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
        self.saveStateOkay = True
        # Keep XML display pane up to date with latest
        self.XMLPane.setText(self.animatronics.toXML())
        self.tagSelectUpdate()

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

        # Make sure we are allowed to create new Digital channels
        if SystemPreferences['MaxDigitalChannels'] <= 0:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Max count of Digital Channels has been exceeded.')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
            return

        """ Perform newdigital action"""
        if main_win is not None: main_win.saveStateOkay = False
        tempChannel = Channel(intype=Channel.DIGITAL)
        td = ChannelMetadataWidget(channel=tempChannel, parent=self)
        code = td.exec_()
        if main_win is not None: main_win.saveStateOkay = True

        # If user signals accept
        if code == QDialog.Accepted:
            # Check to see if channel already exists
            ret = None
            text = tempChannel.name
            if text in self.plots:
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

                placename = None
                # If any channels are selected, use first one as insertion point
                selection = self.getSelectedChannelNames()
                if len(selection) > 0: placename = selection[0]
                self.animatronics.insertChannel(tempChannel, placename=placename)
                self.setAnimatronics(self.animatronics)
                self.selectChannels(selection)

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
        # Make sure we are allowed to create new servo channels
        if SystemPreferences['MaxServoChannels'] <= 0:
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Max count of Servo Channels has been exceeded.')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information)
            ret = msgBox.exec_()
            return

        """ Perform newchannel action"""
        if main_win is not None: main_win.saveStateOkay = False
        tempChannel = Channel()
        td = ChannelMetadataWidget(channel=tempChannel, parent=self)
        code = td.exec_()
        if main_win is not None: main_win.saveStateOkay = True

        if code == QDialog.Accepted:
            # Check to see if channel already exists
            ret = None
            text = tempChannel.name
            if text in self.animatronics.channels:
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

                placename = None
                # If any channels are selected, use first one as insertion point
                selection = self.getSelectedChannelNames()
                if len(selection) > 0: placename = selection[0]
                self.animatronics.insertChannel(tempChannel, placename=placename)
                self.setAnimatronics(self.animatronics)
                self.selectChannels(selection)

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
        # Get list of channels in current display order
        channelList = self.animatronics.channels

        form = ChecklistDialog('Channels to Delete', channelList, parent=main_win)
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
                self.undo_action()
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return

        pass

    def editservodata_action(self):
        qd = ServoWidget(parent=self)
        qd.exec_()

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
        minTime = 0.0   # Playback always starts at 0.0 so use this as initial min
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
        for i in self.animatronics.tags:
            if i < minTime: minTime = i
            if i+1.0 > maxTime: maxTime = i + 1.0   # Give a bit of margin so it's not right at edge

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
            if len(ydata) > 0:
                minVal = min(ydata)
                maxVal = max(ydata)
                self.audioPlot.setAxisScale(qwt.QwtPlot.yLeft, minVal, maxVal)
            self.audioPlot.replot()
            if self.audioPlotRight is not None:
                self.audioPlotRight.setAxisScale(qwt.QwtPlot.xBottom, minTime, maxTime)
                if len(rightdata) > 0:
                    minVal = min(rightdata)
                    maxVal = max(rightdata)
                    self.audioPlotRight.setAxisScale(qwt.QwtPlot.yLeft, minVal, maxVal)
                self.audioPlotRight.replot()

    def redrawTags(self, minTime, maxTime):
        if self.tagPlot is not None:
            self.tagPlot.redrawTags(minTime, maxTime)

    def scaletoaudio_action(self):
        """
        The method scaletoaudio_action resets the visible time range to
        match the length of the audio data, even of some channels contain
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

    def scaletotimerange_action(self):
        """
        The method scaletotimerange_action resets the visible time range to
        match the length of the time range data, even of some channels contain
        data points outside that range.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform scaletotimerange action"""
        # Reset all horizontal scales to time range but not vertical scales to local Y ranges
        self.setTimeRange(self.animatronics.start, self.animatronics.end)
        pass

    def settimerange_action(self):
        """
        The method settimerange_action brings up a dialog box to set the visible time range to
        match that specified by the user, even of some channels contain data points outside that range.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ show the dialog and use its methods to set the time range """
        self.timerangedialog.show()
        pass

    def zoomin_action(self):
        cursorpos = QCursor.pos()
        if self.audioPlot is not None:
            widgetpos = self.audioPlot.mapFromGlobal(cursorpos)
            centerX,_ = self.getPlotValues(widgetpos.x(), widgetpos.y())
        elif len(self.plots) > 0:
            for name in self.plots:
                if self.plots[name].isHidden(): continue
                widgetpos = self.plots[name].mapFromGlobal(cursorpos)
                centerX,_ = self.plots[name].getPlotValues(widgetpos.x(), widgetpos.y())
                break
        elif self.tagPlot is not None:
            self.tagPlot.show()
            widgetpos = self.tagPlot.mapFromGlobal(cursorpos)
            centerX,_ = self.getPlotValues(widgetpos.x(), widgetpos.y())
        else:
            return

        # Zoom in to cursor and center it if off window
        currLeft = self.lastXmin
        currRight = self.lastXmax
        if centerX > currLeft and centerX < currRight:
            newLeft = centerX - (centerX - currLeft) / 2.0
            newRight = centerX + (currRight - centerX) / 2.0
        else:
            newLeft = centerX - (currRight - currLeft) / 4.0
            newRight = centerX + (currRight - currLeft) / 4.0
        self.setTimeRange(newLeft, newRight)

    def zoomout_action(self):
        cursorpos = QCursor.pos()
        if self.audioPlot is not None:
            widgetpos = self.audioPlot.mapFromGlobal(cursorpos)
            centerX,_ = self.getPlotValues(widgetpos.x(), widgetpos.y())
        elif len(self.plots) > 0:
            for name in self.plots:
                if self.plots[name].isHidden(): continue
                widgetpos = self.plots[name].mapFromGlobal(cursorpos)
                centerX,_ = self.plots[name].getPlotValues(widgetpos.x(), widgetpos.y())
                break
        elif self.tagPlot is not None:
            self.tagPlot.show()
            widgetpos = self.tagPlot.mapFromGlobal(cursorpos)
            centerX,_ = self.getPlotValues(widgetpos.x(), widgetpos.y())
        else:
            return

        # Zoom in to cursor and center it if off window
        currLeft = self.lastXmin
        currRight = self.lastXmax
        if centerX > currLeft and centerX < currRight:
            newLeft = centerX - (centerX - currLeft) * 2.0
            newRight = centerX + (currRight - centerX) * 2.0
        else:
            newLeft = centerX - (currRight - currLeft)
            newRight = centerX + (currRight - currLeft)
        self.setTimeRange(newLeft, newRight)
        

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

    def name_sort_action(self):
        # Get list of channels in current display order
        channelList = list(self.animatronics.channels)
        if len(channelList) < 2: return

        tlist = sorted(channelList)
        if tlist == channelList:
            # Already sorted forward so reverse
            tlist = sorted(channelList, reverse=True)

        pushState()
        newplots = {}
        for name in tlist:
            newplots[name] = self.animatronics.channels[name]
        self.animatronics.channels = newplots
        self.redraw()

    def port_sort_action(self):
        # Get list of channels in current display order
        channelList = list(self.animatronics.channels)
        if len(channelList) < 2: return

        # Convert to a list of port numbers with associated names in tuples
        tuples = []
        for name in channelList:
            tuples.append((self.animatronics.channels[name].port, name))
        tlist = sorted(tuples)
        if tlist == tuples:
            # Already sorted forward so reverse
            tlist = sorted(tuples, reverse=True)

        pushState()
        newplots = {}
        for tuple in tlist:
            newplots[tuple[1]] = self.animatronics.channels[tuple[1]]
        self.animatronics.channels = newplots
        self.redraw()
        pass

    def showselector_action(self):
        """
        The method showselector_action brings up a checklist of channels for
        the user to show or hide whatever channels they wish.

            member of class: MainWindow
        Parameteranimatronics.channels
        ----------
        self : MainWindow
        """

        """ Perform showselector action"""
        # Get list of channels in current display order
        channelList = self.animatronics.channels

        # Pop up show/hide selector to choose visible channels
        form = ChecklistDialog('Channels to Show', channelList, parent=main_win)
        checklist = []
        for name in channelList:
            if self.plots[name].isHidden():
                checklist.append(Qt.Unchecked)
            else:
                checklist.append(Qt.Checked)
        form.setStates(checklist)
        if form.exec_() == QDialog.Accepted:
            # Actually set the show/hide state
            for name in channelList:
                if name in form.choices:
                    self.plots[name].show()
                else:
                    self.plots[name].hidePane()
        pass

    def updateClipboard_action(self):
        """
        The method updateClipboard_action refreshes the window that displays
        the current clipboard content with new content.  It does not bring 
        it up though.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        # Pop up text window containing XML to view (uneditable)
        self.ClipboardPane.setText(self.clipboard.text())

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
        self.ClipboardPane.show()

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
        self.autoSave()

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
        if self.audioPlot is not None:
            thePlot = self.audioPlot
        elif self.tagPlot is not None:
            thePlot = self.tagPlot
        else:
            return None, None

        # Get the rectangle containing the stuff to left of plot
        rect = thePlot.plotLayout().scaleRect(qwt.QwtPlot.yLeft)
        # Get the width of that rectangle to use as offset in X
        xoffset = rect.width()
        valueX = thePlot.invTransform(qwt.QwtPlot.xBottom, pixelX - xoffset)

        # Get the rectangle containing the stuff above top of plot
        rect = thePlot.plotLayout().scaleRect(qwt.QwtPlot.xTop)
        # Get the height of that rectangle to use as offset in Y
        yoffset = rect.height()
        valueY = thePlot.invTransform(qwt.QwtPlot.yLeft, pixelY - yoffset)

        return valueX,valueY

    def localmousePressEvent(self, event):
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
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            if event.buttons() == Qt.LeftButton:
                self.lastX = event.pos().x()
                self.lastY = event.pos().y()
                self.centerX,self.centerY = self.getPlotValues(event.pos().x(), event.pos().y())
        elif modifiers == Qt.ShiftModifier:
            pass
        else:
            if event.buttons() == Qt.LeftButton:
                # Use horizontal motion to drag
                newCenterX,_ = self.getPlotValues(event.pos().x(), event.pos().y())
                self.timeChanged(newCenterX)
                if self._playwidget is not None:
                    self._playwidget.setCurrentPosition(newCenterX)

    def localmouseMoveEvent(self, event):
        """
        The method mouseMoveEvent performs zoom and drag within the audio
        panes.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        event : type
        """
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
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
        elif modifiers == Qt.ShiftModifier:
            pass
        else:
            if event.buttons() == Qt.LeftButton:
                # Use horizontal motion to drag
                newCenterX,_ = self.getPlotValues(event.pos().x(), event.pos().y())
                self.timeChanged(newCenterX)
                if self._playwidget is not None:
                    self._playwidget.setCurrentPosition(newCenterX)

    def localmouseReleaseEvent(self, event):
        """
        The method mouseReleaseEvent does nothing at this time
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        event : type
        """
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
        self.setLeftEdge(self._slideTime)

    def setLeftEdge(self, intime):
        self.setTimeRange(intime, self.lastXmax)

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
        self.setRightEdge(self._slideTime)

    def setRightEdge(self, intime):
        self.setTimeRange(self.lastXmin, intime)

    def about_action(self):
        """
        The method about_action brings up the About text in a popup.  About
        and Help use the same popup so only one can be displayed at a time.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/About.md'))
        self.helpPane.resize(500, 380)
        self.helpPane.setWindowTitle('About Hauntimator')
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
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/Help.md'))
        self.helpPane.resize(600, 700)
        self.helpPane.setWindowTitle('Hauntimator Help')
        self.helpPane.show()

    def quick_action(self):
        """
        The method quick_action brings up the QuickStart text in a popup.  About
        and QuickStart use the same popup so only one can be displayed at a time.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/QuickStart.md'))
        self.helpPane.resize(600, 700)
        self.helpPane.setWindowTitle('Quick Start')
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
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/HotKeys.md'))
        self.helpPane.resize(600, 700)
        self.helpPane.setWindowTitle('Hot Key Cheat Sheet')
        self.helpPane.show()

    def plugin_help_action(self):
        if self.sender().text() is not None:
            pluginname = self.sender().text()
            self.helpPane.setSource(os.path.join(getExecPath(), 'plugins', pluginname + '.md'))
            self.helpPane.resize(600, 700)
            self.helpPane.setWindowTitle(pluginname)
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

    def getFocusChannel(self):
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
        return channame

    def keyReleaseEvent(self, event):
        """
        Apparently, Arrow Keys and Page Up/Down keys are only passed into the
        keyReleaseEvent methods, NOT the keyPressEvent methods.  WTF?
        """
        # Pass arrow keys to focused channel
        focuschannel = self.getFocusChannel()
        if focuschannel is not None:
            self.plots[focuschannel].keyReleaseEvent(event)

    def Cut_action(self):
        """
        The method Cut_action cuts the content of a single channel to
        the clipboard to be pasted elsewhere.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform Cut action"""
        # Make sure there is only one channel selected
        selection = self.getSelectedChannelNames()

        # Reset the last slide
        self.lastDeltaX = 0.0
        self.lastDeltaY = 0.0
        self.repCount = 1

        if len(selection) == 0:
            # If none are selected, see if the cursor is in a ChannelPane
            channame = self.getFocusChannel()
            if channame is not None:
                pane = self.plots[channame]
                if len(pane.selectedKeyList) > 0:
                    # Copy the selected knots as XML string
                    theXML = StringIO()
                    theXML.write('<Channel>\n')
                    for key in pane.selectedKeyList:
                        theXML.write('  <Point time="%f">%f</Point>\n' % (key, pane.channel.knots[key]))
                    theXML.write('</Channel>\n')
                    self.clipboard.setText(theXML.getvalue())
                    pass
                else:
                    pushState()
                    # Copy all the knots
                    self.clipboard.setText(self.animatronics.channels[channame].toXML())
                    self.animatronics.deleteChannel(channame)
                    self.setAnimatronics(self.animatronics)
        elif len(selection) > 1:
            pushState()     # Save state for Undo
            # Copy all channels into an XML block
            xmlText = '<Block>'
            for name in selection:
                ttext = self.animatronics.channels[name].toXML()
                xmlText += '\n' + ttext
                # Delete the copied channel to implement Cut operation
                self.animatronics.deleteChannel(name)
            xmlText += '\n</Block>\n'
            self.clipboard.setText(xmlText)
            self.setAnimatronics(self.animatronics)
        else:
            # Copy to clipboard
            name = selection[0]
            self.clipboard.setText(self.animatronics.channels[name].toXML())
            pushState()     # Save state for Undo
            # Delete the copied channel to implement Cut operation
            self.animatronics.deleteChannel(name)
            self.setAnimatronics(self.animatronics)

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
        selection = self.getSelectedChannelNames()

        # Reset the last slide
        self.lastDeltaX = 0.0
        self.lastDeltaY = 0.0
        self.repCount = 1

        if len(selection) == 0:
            # If none are selected, see if the cursor is in a ChannelPane
            channame = self.getFocusChannel()
            if channame is not None:
                pane = self.plots[channame]
                if len(pane.selectedKeyList) > 0:
                    # Copy the selected knots as XML string
                    theXML = StringIO()
                    theXML.write('<Channel>\n')
                    for key in pane.selectedKeyList:
                        theXML.write('  <Point time="%f">%f</Point>\n' % (key, pane.channel.knots[key]))
                    theXML.write('</Channel>\n')
                    self.clipboard.setText(theXML.getvalue())
                    pass
                else:
                    # Copy all the knots
                    self.clipboard.setText(self.animatronics.channels[channame].toXML())
        elif len(selection) > 1:
            # Copy all channels into an XML block
            xmlText = '<Block>'
            for name in selection:
                ttext = self.animatronics.channels[name].toXML()
                xmlText += '\n' + ttext
            xmlText += '\n</Block>\n'
            self.clipboard.setText(xmlText)
        else:
            # Copy to clipboard
            name = selection[0]
            self.clipboard.setText(self.animatronics.channels[name].toXML())
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
        selection = self.getSelectedChannelNames()
        explicitselection = selection.copy()

        if len(selection) == 0:
            # If none are selected, see if the cursor is in a ChannelPane
            channame = self.getFocusChannel()
            if channame is not None:
                selection.append(channame)
        if len(selection) > 0:
            # Push current state for undo
            pushState()

            # Paste the clipboard into all selected channels
            try:
                root = ET.fromstring(self.clipboard.text())
                if root.tag == 'Channel':
                    if 'name' not in root.attrib:
                        # Clipboard is a set of points to be inserted into all selected channels
                        for name in selection:
                            self.plots[name].selectedKey = None
                            self.plots[name].selectedKeyList = []
                            existingknots = dict(self.plots[name].channel.knots)
                            self.animatronics.channels[name].parseXML(root)
                            # Select new knots
                            for knot in self.plots[name].channel.knots:
                                if knot not in existingknots:
                                    knottime = knot + self.lastDeltaX * self.repCount
                                    knotvalue = self.animatronics.channels[name].knots[knot] + self.lastDeltaY * self.repCount
                                    while knottime in existingknots: knottime += 0.001
                                    existingknots[knottime] = knotvalue
                                    self.plots[name].selectedKeyList.append(knottime)
                            self.animatronics.channels[name].knots = existingknots
                            self.plots[name].create()
                        self.repCount += 1
                    else:
                        # Clipboard is a full, named channel to overwrite all selected or be inserted at first selected
                        # See if any of the selected channels contain knots already that might be overwritten
                        sum = 0
                        for name in selection:
                            sum += self.plots[name].channel.num_knots()
                        if sum > 0:
                            msgBox = QMessageBox(parent=self)
                            msgBox.setText('The selected channel(s) already contain data.')
                            msgBox.setInformativeText("Overwrite data or insert a new channel?")
                            overwriteButton = msgBox.addButton('Overwrite', QMessageBox.YesRole)
                            insertButton = msgBox.addButton('Insert at', QMessageBox.NoRole)
                            msgBox.setStandardButtons(QMessageBox.Cancel)
                            msgBox.setDefaultButton(QMessageBox.Save)
                            msgBox.setIcon(QMessageBox.Warning)
                            ret = msgBox.exec_()
                            if msgBox.clickedButton() == insertButton:
                                placename = selection[0]
                                self.insertChannel(root, placename=placename)
                                self.setAnimatronics(self.animatronics)
                                self.selectChannels(explicitselection)
                                return
                            elif ret == QMessageBox.Cancel:
                                return
                        # If we get here we either have all empty selected channels or the user chose overwrite
                        # So we overwrite
                        usedNumericPorts = main_win.getUsedNumericPorts()
                        usedDigitalPorts = main_win.getUsedDigitalPorts()
                        for name in selection:
                            self.animatronics.channels[name].parseXML(root)
                            if self.animatronics.channels[name].port in usedNumericPorts or self.animatronics.channels[name].port in usedDigitalPorts:
                                self.animatronics.channels[name].port = -1
                            self.animatronics.channels[name].name = name
                            self.plots[name].create()
                        pass
                elif root.tag == 'Block':
                    # Clipboard is a set of full channels to be inserted at first selected
                    if len(root) > 0:
                        placename = selection[0]
                        for child in root:
                            if child.tag == 'Channel':
                                self.insertChannel(child, placename=placename)
                        self.setAnimatronics(self.animatronics)
                        self.selectChannels(explicitselection)
                    pass
                self.updateXMLPane()
            except:
                self.undo_action()
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Whoops - Unable to parse from clipboard')
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.setIcon(QMessageBox.Warning)
                ret = msgBox.exec_()
                return
        pass

    def Insert_action(self):
        """
        The method Insert_action inserts the content of the clipboard, if
        not empty, prior to the first selected channel or the channel under the cursor.

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
        selection = self.getSelectedChannelNames()
        explicitselection = selection.copy()

        if len(selection) == 0:
            # If none are selected, see if the cursor is in a ChannelPane
            channame = self.getFocusChannel()
            if channame is not None:
                selection.append(channame)
            else:
                selection.append(None)  # Paste at the end if no channels selected
        # Push current state for undo
        pushState()

        # Paste the clipboard into all selected channels
        try:
            root = ET.fromstring(self.clipboard.text())
            if root.tag == 'Channel':
                if 'name' not in root.attrib:
                    # Clipboard is a set of points to be inserted into all selected channels
                    for name in selection:
                        self.plots[name].selectedKey = None
                        self.plots[name].selectedKeyList = []
                        existingknots = dict(self.plots[name].channel.knots)
                        self.animatronics.channels[name].parseXML(root)
                        # Select new knots
                        for knot in self.plots[name].channel.knots:
                            if knot not in existingknots:
                                knottime = knot + self.lastDeltaX * self.repCount
                                knotvalue = self.animatronics.channels[name].knots[knot] + self.lastDeltaY * self.repCount
                                while knottime in existingknots: knottime += 0.001
                                existingknots[knottime] = knotvalue
                                self.plots[name].selectedKeyList.append(knottime)
                        self.animatronics.channels[name].knots = existingknots
                        self.plots[name].create()
                else:
                    # Clipboard is a full, named channel to be inserted at first selected
                    placename = selection[0]
                    self.insertChannel(root, placename=placename)
                    self.setAnimatronics(self.animatronics)
                    self.selectChannels(explicitselection)
            elif root.tag == 'Block':
                # Clipboard is a set of full channels to be inserted at first selected
                if len(root) > 0:
                    placename = selection[0]
                    for child in root:
                        if child.tag == 'Channel':
                            self.insertChannel(child, placename=placename)
                    self.setAnimatronics(self.animatronics)
                    self.selectChannels(explicitselection)
                pass
            self.updateXMLPane()
        except:
            self.undo_action()
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Whoops - Unable to parse from clipboard')
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()
            return
        pass

    def insertChannel(self, inXML, placename=None):
        tempChannel = Channel()
        tempChannel.parseXML(inXML)
        # Make sure name and port number fields are okay
        tname = tempChannel.name
        while tname in self.plots:
            tname += '_2'
            tempChannel.name = tname
        tport = tempChannel.port
        for name in self.plots:
            if tport == self.plots[name].channel.port:
                tempChannel.port = -1
                break
        self.animatronics.insertChannel(tempChannel, placename=placename)

    def getSelectedChannels(self):
        # Get a list of all the currently selected channels
        selection = []
        for name in self.getSelectedChannelNames():
            selection.append(self.plots[name].channel)
        return selection

    def getSelectedChannelNames(self):
        namelist = []
        for name in self.plots:
            if self.plots[name].selected:
                namelist.append(name)
        return namelist

    def selectChannels(self, selection=[]):
        for name in self.plots:
            self.plots[name].deselect()
        for name in selection:
            self.plots[name].select()

    def Amplitudize_action(self):
        """
        The method Amplitudize_action
            member of class: ChannelMenu
        Parameters
        ----------
        self : ChannelMenu
        """
        # If no audio then nothing to do La Di Da
        if self.animatronics.newAudio is None:
            return

        # Get a list of all the currently selected channels
        selection = self.getSelectedChannelNames()

        if len(selection) == 0:
            return

        # Pop up widget to get sampling parameters
        twidget = AmpingWidget(parent=main_win, startTime=self.lastXmin, endTime=self.lastXmax,
                    popRate=10.0)
        code = twidget.exec_()
        if code != QDialog.Accepted: return # Cancel the operation

        # Do the amplitudize process
        popRate = twidget.popRate   # amplitude buckets per second
        cutoff = twidget.cutoff

        # Get the audio amplitude sampled at the desired rate
        # Use mono/left unless right is only one visible
        audio = self.animatronics.newAudio

        # Check to see if we are sampling too fast (30 is a constant found in Animatronics.py)
        if popRate > audio.samplerate/30.0:
            popRate = audio.samplerate/30.0
            msgBox = QMessageBox(parent=self)
            msgBox.setText('Maximum sample rate for this audio is %f!' % popRate)
            msgBox.setInformativeText("Will sample at this rate but > 50Hz is a waste.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Warning)
            ret = msgBox.exec_()

        start = twidget.startTime
        if start < self.animatronics.newAudio.audiostart:
            start = self.animatronics.newAudio.audiostart
        end = twidget.endTime
        if end > self.animatronics.newAudio.audioend:
            end = self.animatronics.newAudio.audioend
        bincount = int((end - start) * popRate + 0.999)
        _,signal,_ = audio.getAmplitudeData(start,
                    start + bincount/popRate, bincount)

        pushState()     # Push current state for undo

        for name in selection:
            self.plots[name].channel.amplitudize(start,
                    start + bincount/popRate,
                    signal,
                    cutoff=cutoff,
                    popRate=popRate)
            self.plots[name].redrawme()

        self.updateXMLPane()
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

    def Clear_action(self):
        """
        The method Clear_action optionally clears all knots from the selected channels.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform Delete action"""
        dellist = self.getSelectedChannelNames()
        if len(dellist) > 0:
            pushState()     # Push current state for undo

            for name in dellist:
                self.plots[name].selectedKey = None
                self.plots[name].selectedKeyList = []
                self.plots[name].channel.delete_knots()
                self.plots[name].redrawme()
            if main_win is not None: main_win.updateXMLPane()

    def Delete_action(self):
        """
        The method Delete_action optionally deletes all the selected channels.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """ Perform Delete action"""
        dellist = self.getSelectedChannelNames()
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
        fileName, _ = QFileDialog.getOpenFileName(self,"Get Open Filename", "",
                            ";;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)

        if fileName:
            if self.tagPlot is not None:
                # Push current state for undo
                pushState()

                offset = 0.0
                if self.animatronics.newAudio is not None:
                    offset = self.animatronics.newAudio.audiostart
                with open(fileName, 'r') as scfile:
                    script = scfile.readlines()
                    for line in script:
                        self.tagPlot.addTag(offset, line.rstrip())
                        # Guesstimate duration of audio and add to time (0.09 seconds per character)
                        offset += len(line) * 0.09
                    self.resetscales_action()
                    self.updateXMLPane()
                    self.tagSelectUpdate()

        pass

    def tagSelector_action(self):
        # Build and pop up tag selector widget
        self.tagSelectDialog = QDialog(parent=self)
        self.tagSelectDialog.rejected.connect(self.tagSelectClose)
        self._tagListWidget = QListWidget(self.tagSelectDialog)
        layout = QFormLayout()
        self.tagSelectDialog.setLayout(layout)
        layout.addRow(self._tagListWidget)
        maxWidth = 0
        for tagTime in sorted(self.animatronics.tags):
            self._tagListWidget.addItem(toHMS(tagTime) + ' - ' + self.animatronics.tags[tagTime])
            tWidth = len(self.animatronics.tags[tagTime])
            if tWidth > maxWidth: maxWidth = tWidth
        self.tagSelectDialog.setGeometry(
            self.pos().x(),
            self.pos().y(),
            min((maxWidth + 18) * 7, 800),
            min(22*len(self.animatronics.tags), 600))

        self._tagListWidget.itemSelectionChanged.connect(self.tagSelected)
        self.tagSelectDialog.show()
        pass

    def tagSelectClose(self):
        self.tagSelectDialog = None

    def tagSelectUpdate(self):
        # If it is not visible don't bother updating
        if self.tagSelectDialog is None: return

        self._tagListWidget.clear()
        maxWidth = 0
        for tagTime in sorted(self.animatronics.tags):
            self._tagListWidget.addItem(toHMS(tagTime) + ' - ' + self.animatronics.tags[tagTime])
            tWidth = len(self.animatronics.tags[tagTime])
            if tWidth > maxWidth: maxWidth = tWidth
        geom = self.tagSelectDialog.geometry()
        self.tagSelectDialog.setGeometry(
            geom.x(),
            geom.y(),
            min((maxWidth + 18) * 7, 800),
            min(22*len(self.animatronics.tags), 600))

    def findNearestTag(self, time):
        nearest = None
        for tagTime in self.animatronics.tags:
            if nearest is None:
                nearest = tagTime
                distance = abs(tagTime - time)
            elif abs(tagTime - time) < distance:
                nearest = tagTime
                distance = abs(tagTime - time)
        return nearest

    def tagSelected(self):
        if len(self._tagListWidget.selectedItems()) == 0: return
        # Get the text string
        text = self._tagListWidget.selectedItems()[0].text()
        # Convert string back to float time
        time = fromHMS(text)
        # Find nearest tag
        tagTime = self.findNearestTag(time)
        if abs(tagTime - time) < 0.01:
            # Select and display that tag
            self.tagPlot.tagZoom(tagTime)
            pass

    def tagInsert_action(self):
        # Grab the slider time as soon as we can
        ttime = self._slideTime
        text, ok = QInputDialog().getText(self, "Tag Entry", "Enter Tag:",
            QLineEdit.Normal, '')
        if ok and text:
            # Save state for undo
            pushState()
            self.tagPlot.addTag(ttime, text)
            self.updateXMLPane()
            self.tagSelectUpdate()
        pass

    def clearAllTags_action(self):
        if len(self.animatronics.tags) > 0:
            pushState()
            # First remove all tags from the animation
            self.animatronics.clearTags()
            # Remove all tags in the tags pane
            self.tagPlot.setTags([])

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
        self.file_menu.setToolTipsVisible(SystemPreferences['ShowTips'])

        # New action
        self._new_file_action = QAction("&New Animation", self,
            shortcut=QKeySequence.New,
            triggered=self.newAnimFile)
        self.file_menu.addAction(self._new_file_action)

        # Open action
        self._open_file_action = QAction("&Open Anim File", self,
            shortcut=QKeySequence.Open,
            triggered=self.openAnimFile)
        self.file_menu.addAction(self._open_file_action)

        self.file_menu.addSeparator()

        self._selectaudio_action = QAction("Open &Audio File", self,
            triggered=self.selectaudio_action)
        self.file_menu.addAction(self._selectaudio_action)

        # Merge action
        self._merge_file_action = QAction("&Merge Anim File",
                self, triggered=self.mergeAnimFile)
        #self._merge_file_action.setEnabled(False)
        self._merge_file_action.setToolTip('Merge new channels from another animation')
        self.file_menu.addAction(self._merge_file_action)

        # Append action
        self._append_file_action = QAction("&Append Anim File",
                self, triggered=self.appendAnimFile)
        #self._append_file_action.setEnabled(False)
        self._append_file_action.setToolTip('Add to matching channels from another animation')
        self.file_menu.addAction(self._append_file_action)

        self.file_menu.addSeparator()

        # Save action
        self._save_file_action = QAction("&Save Anim File",
                self, shortcut=QKeySequence.Save, triggered=self.saveAnimFile)
        self.file_menu.addAction(self._save_file_action)

        # Save As action
        self._save_as_file_action = QAction("&Save As",
                self, shortcut=QKeySequence.SaveAs, triggered=self.saveAsFile)
        self.file_menu.addAction(self._save_as_file_action)

        # Export action
        self._export_file_menu = self.file_menu.addMenu("Export")
        self._export_file_menu.setToolTipsVisible(SystemPreferences['ShowTips'])
        self._export_csv_file_action = QAction("&Export to CSV/Binary",
                self, triggered=self.exportCSVFile)
        self._export_csv_file_action.setToolTip('Save controls to local CSV file and binary file if supported')
        self._export_file_menu.addAction(self._export_csv_file_action)

        '''
        self._export_vsa_file_action = QAction("&Export to VSA",
                self, triggered=self.exportVSAFile)
        self._export_vsa_file_action.setEnabled(False)
        self._export_file_menu.addAction(self._export_vsa_file_action)
        '''

        self._export_hw_action = QAction("&Upload to Controller",
                self, triggered=self.uploadToHW)
        self._export_file_menu.addAction(self._export_hw_action)

        self._export_audio_action = QAction("&Upload Audio",
                self, triggered=self.uploadAudio)
        self._export_file_menu.addAction(self._export_audio_action)

        # exit action
        self.file_menu.addSeparator()
        self._exit_action = QAction("&Quit", self, shortcut=QKeySequence.Quit,
                triggered=self.exit_action)
        self.file_menu.addAction(self._exit_action)

        # Create the Edit dropdown menu #################################
        self.edit_menu = self.menuBar().addMenu("&Edit")
        self.edit_menu.setToolTipsVisible(SystemPreferences['ShowTips'])

        self._undo_action = QAction("Undo", self, shortcut=QKeySequence.Undo,
            triggered=self.undo_action)
        self.edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("Redo", self, shortcut=QKeySequence.Redo,
            triggered=self.redo_action)
        self.edit_menu.addAction(self._redo_action)

        self.edit_menu.addSeparator()

        # Cut menu item
        self._Cut_action = QAction("Cut", self,
            shortcut=QKeySequence.Cut,
            triggered=self.Cut_action)
        self.edit_menu.addAction(self._Cut_action)

        # Copy menu item
        self._Copy_action = QAction("Copy", self,
            shortcut=QKeySequence.Copy,
            triggered=self.Copy_action)
        self.edit_menu.addAction(self._Copy_action)

        # Paste menu item
        self._Paste_action = QAction("Paste", self,
            shortcut=QKeySequence.Paste,
            triggered=self.Paste_action)
        self.edit_menu.addAction(self._Paste_action)

        # Insert menu item
        self._Insert_action = QAction("Insert", self,
            shortcut=QKeySequence.Italic,
            triggered=self.Insert_action)
        self.edit_menu.addAction(self._Insert_action)

        self.edit_menu.addSeparator()

        # editmetadata menu item
        self._editmetadata_action = QAction("Edit Metadata", self,
            triggered=self.editmetadata_action)
        self.edit_menu.addAction(self._editmetadata_action)

        # editservodata menu item
        self._editservodata_action = QAction("Edit Servo Data", self,
            triggered=self.editservodata_action)
        self.edit_menu.addAction(self._editservodata_action)

        # editpreferences menu item
        self._editpreferences_action = QAction("Edit Preferences", self,
            triggered=self.editpreferences_action)
        self.edit_menu.addAction(self._editpreferences_action)

        # Create the View dropdown menu #################################
        self.view_menu = self.menuBar().addMenu("&View")
        self.view_menu.setToolTipsVisible(SystemPreferences['ShowTips'])

        # resetscales menu item
        self._resetscales_action = QAction("Fit to All Data", self,
            shortcut=QKeySequence.Find,
            triggered=self.resetscales_action)
        self.view_menu.addAction(self._resetscales_action)

        # scaletoaudio menu item
        self._scaletoaudio_action = QAction("Fit to Audio", self,
            triggered=self.scaletoaudio_action)
        self.view_menu.addAction(self._scaletoaudio_action)

        # scaletotimerange menu item
        ''' I don't know what this is supposed to be doing and it doesn't do much so it is gone
        self._scaletotimerange_action = QAction("Fit to Time Range", self,
            triggered=self.scaletotimerange_action)
        self.view_menu.addAction(self._scaletotimerange_action)
        '''

        # settimerange menu item
        self._settimerange_action = QAction("Set Time Range", self,
            triggered=self.settimerange_action)
        self.view_menu.addAction(self._settimerange_action)

        # Zoom In Action
        self._zoomin_action = QAction("Zoom In", self,
            shortcut=QKeySequence.ZoomIn,
            triggered=self.zoomin_action)
        self.addAction(self._zoomin_action)

        # Zoom Out Action
        self._zoomout_action = QAction("Zoom Out", self,
            shortcut=QKeySequence.ZoomOut,
            triggered=self.zoomout_action)
        self.addAction(self._zoomout_action)

        self.view_menu.addSeparator()

        # showall menu item
        self._showall_action = QAction("Show All Channels", self,
            triggered=self.showall_action)
        self.view_menu.addAction(self._showall_action)

        # showselector menu item
        self._showselector_action = QAction("Select Viewed Channels", self,
            triggered=self.showselector_action)
        self.view_menu.addAction(self._showselector_action)

        self._sort_menu = self.view_menu.addMenu("Sort Channels")
        self._name_sort_action = QAction("By Name", self,
            triggered=self.name_sort_action)
        self._sort_menu.addAction(self._name_sort_action)
        self._port_sort_action = QAction("By Port", self,
            triggered=self.port_sort_action)
        self._sort_menu.addAction(self._port_sort_action)

        self.view_menu.addSeparator()

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

        self._audio_amplitude_action = QAction("Audio Amplitude", self,
            checkable=True,
            triggered=self.showaudio_amplitude_action)
        self.view_menu.addAction(self._audio_amplitude_action)

        self.view_menu.addSeparator()

        # playbackcontrols menu item
        self._playbackcontrols_action = QAction("Toggle Playback Controls", self,
            shortcut=QKeySequence.Print,
            triggered=self.playbackcontrols_action)
        self.view_menu.addAction(self._playbackcontrols_action)


        # Create the Tools dropdown menu #################################
        self.channel_menu = self.menuBar().addMenu("&Channels")
        self.channel_menu.setToolTipsVisible(SystemPreferences['ShowTips'])

        # selectAll menu item
        self._selectAll_action = QAction("Select All", self,
            shortcut=QKeySequence.SelectAll,
            triggered=self.selectAll_action)
        self.channel_menu.addAction(self._selectAll_action)

        # deselectAll menu item
        self._deselectAll_action = QAction("Deselect All", self,
            shortcut=QKeySequence("Ctrl+Shift+A"),
            triggered=self.deselectAll_action)
        self.channel_menu.addAction(self._deselectAll_action)

        self.channel_menu.addSeparator()

        self._newchannel_action = QAction("New Numeric Channel", self,
            shortcut="Ctrl+E",
            triggered=self.newchannel_action)
        self.channel_menu.addAction(self._newchannel_action)

        self._newdigital_action = QAction("New Digital Channel", self,
            shortcut="Ctrl+D",
            triggered=self.newdigital_action)
        self.channel_menu.addAction(self._newdigital_action)

        self._deletechannel_action = QAction("Delete Dialog", self,
            triggered=self.deletechannel_action)
        self.channel_menu.addAction(self._deletechannel_action)

        self.channel_menu.addSeparator()

        # Amplitudize menu item
        self._Amplitudize_action = QAction("Amplitudize", self,
            triggered=self.Amplitudize_action)
        self.channel_menu.addAction(self._Amplitudize_action)
        self._Amplitudize_action.setToolTip('Add points to selected channels\nbased on amplitude of audio signal')

        # Shift menu item
        self._Shift_action = QAction("Shift", self,
            triggered=self.Shift_action)
        self._Shift_action.setEnabled(False)
        self.channel_menu.addAction(self._Shift_action)

        self.channel_menu.addSeparator()

        # Clear menu item
        self._Clear_action = QAction("Clear", self,
            triggered=self.Clear_action)
        self.channel_menu.addAction(self._Clear_action)

        # Delete menu item
        self._Delete_action = QAction("Delete Selected", self,
            shortcut=QKeySequence.Delete,
            triggered=self.Delete_action)
        self.channel_menu.addAction(self._Delete_action)


        # Create the Tags dropdown menu #################################
        self.tag_menu = self.menuBar().addMenu("&Tags")
        self.tag_menu.setToolTipsVisible(SystemPreferences['ShowTips'])

        # tagInsert menu item
        self._tagInsert_action = QAction("Insert Tag", self,
            shortcut=QKeySequence.AddTab,
            triggered=self.tagInsert_action)
        self.tag_menu.addAction(self._tagInsert_action)

        # tagSelector menu item
        self._tagSelector_action = QAction("Tag Selector", self,
            triggered=self.tagSelector_action)
        self.tag_menu.addAction(self._tagSelector_action)

        # importScript menu item
        self._importScript_action = QAction("Import Script", self,
            triggered=self.importScript_action)
        self.tag_menu.addAction(self._importScript_action)

        # togglePane menu item
        self._togglePane_action = QAction("Toggle Tag Pane", self,
            shortcut="T",
            triggered=self.togglePane_action)
        self.tag_menu.addAction(self._togglePane_action)

        # clearAllTags menu item
        self._clearAllTags_action = QAction("Clear All Tags", self,
            triggered=self.clearAllTags_action)
        self.tag_menu.addAction(self._clearAllTags_action)

        # Build Plugins menu returning list of plugins that provide a help file
        helped_plugins = self.buildplugins()

        # Create the Help dropdown menu #################################
        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.setToolTipsVisible(SystemPreferences['ShowTips'])

        self._about_action = QAction("About", self,
            shortcut=QKeySequence.WhatsThis,
            triggered=self.about_action)
        self.help_menu.addAction(self._about_action)

        self._quick_action = QAction("Quick Start", self,
            triggered=self.quick_action)
        self.help_menu.addAction(self._quick_action)

        self._help_action = QAction("Help", self,
            shortcut=QKeySequence.HelpContents,
            triggered=self.help_action)
        self.help_menu.addAction(self._help_action)

        self._hotkeys_action = QAction("Hot Keys", self,
            triggered=self.hotkeys_action)
        self.help_menu.addAction(self._hotkeys_action)

        self.help_menu.addSeparator()

        # If any plugins have help files, add them to the Help menu
        if len(helped_plugins) > 0:
            tmenu = self.help_menu.addMenu('Plugins')
            for pl in helped_plugins:
                taction = QAction(pl, self, triggered=self.plugin_help_action)
                tmenu.addAction(taction)
            self.help_menu.addSeparator()

        # showClipboard menu item
        self._showClipboard_action = QAction("Show Clipboard", self,
            triggered=self.showClipboard_action)
        self.help_menu.addAction(self._showClipboard_action)

        # showXML menu item
        self._showXML_action = QAction("Show XML", self,
            triggered=self.showXML_action)
        self.help_menu.addAction(self._showXML_action)

    def buildplugins(self):
        # Initialize plugin menu to None
        self._plugin_menu = None

        # initially empty list of plugins that include help files
        helped_plugins = []

        # See what plugins are available
        discovered_plugins = {}
        for pkg in pkgutil.iter_modules(path=[os.path.join(getExecPath(),'plugins')]):
            try:
                discovered_plugins[pkg.name] = importlib.import_module('plugins.' + pkg.name)
            except:
                sys.stderr.write("\nWhoops - Problem importing plugin: %s\n" % pkg.name)

        if len(discovered_plugins) <= 0: return

        # Look for the different types of functions in each plugin
        for module in discovered_plugins:
            # initially assume it has no functions
            functions = False
            tmenu = None
            # First look for callable plugin functions
            if hasattr(discovered_plugins[module], 'external_callables'):
                for modder in discovered_plugins[module].external_callables:
                    if hasattr(discovered_plugins[module], modder.__name__):
                        plugin = modder.__name__
                        # First create plugin menu if not already in existence
                        if self._plugin_menu is None:
                            self._plugin_menu = self.menuBar().addMenu("Plugins")
                            self._plugin_menu.setToolTipsVisible(SystemPreferences['ShowTips'])
                        if tmenu is None:
                            # Found first callable in plugin so create a menu for all found
                            tmenu = self._plugin_menu.addMenu(module)
                        taction = QAction(plugin, self, triggered=self.run_plugin)
                        # Store the callable function in the menu item data field to be called later
                        taction.setData(modder)
                        tmenu.addAction(taction)

            # Check for markdown file for each module to include as help
            if os.path.exists(os.path.join(getExecPath(),'plugins', module + '.md')):
                helped_plugins.append(module)

        return helped_plugins

    class TimeRangeDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.mainwindow = parent
            startTime = parent.lastXmin
            endTime = parent.lastXmax

            self.setWindowTitle('Set Time Range')

            widget = QWidget()
            layout = QFormLayout()

            self._startedit = QLineEdit()
            self._startedit.setText('%.3f' % startTime)
            layout.addRow(QLabel('Start Time:'), self._startedit)

            self._endedit = QLineEdit()
            self._endedit.setText('%.3f' % endTime)
            layout.addRow(QLabel('End Time:'), self._endedit)

            widget.setLayout(layout)

            self.okButton = QPushButton('Okay')
            self.okButton.setDefault(True)
            self.cancelButton = QPushButton('Cancel')
            self.applyButton = QPushButton('Apply')

            hbox = QHBoxLayout()
            hbox.addStretch(1)
            hbox.addWidget(self.applyButton)
            hbox.addWidget(self.okButton)
            hbox.addWidget(self.cancelButton)

            vbox = QVBoxLayout(self)
            vbox.addWidget(widget)
            vbox.addStretch(1)
            vbox.addLayout(hbox)
            self.setLayout(vbox)

            self.applyButton.clicked.connect(self.onApply)
            self.okButton.clicked.connect(self.onAccepted)
            self.cancelButton.clicked.connect(self.reject)

        def onApply(self):
            tstring = self._startedit.text()
            if len(tstring) > 0:
                startTime = float(tstring)
            else:
                startTime = -1.0e34

            tstring = self._endedit.text()
            if len(tstring) > 0:
                endTime = float(tstring)
            else:
                endTime = 1.0e34

            # Pass the time values to MainWindow
            self.mainwindow.setTimeRange(startTime, endTime)

        def onAccepted(self):
            # Execute the Apply function
            self.onApply()

            # And close up shop but not delete the dialog
            self.accept()


#/* Main */
def doRegressionTests():
    """
    The method doAnimatronics is the main function of the application.
    It parses the command line arguments, handles them, and then opens
    the main window and proceeds.
    """

    pass

if __name__ == "__main__":
    doRegressionTests()

