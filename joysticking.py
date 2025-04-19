#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program joysticking.py
# Created by john
# Created Thu Feb 13 05:23:46 PM PST 2025
#*********************************/

#/* Import block */
import os
import re
import sys
import time
import pygame

import Animatronics
# Import commlib for my board
try:
    import commlib
    ser = commlib.openPort()
    if ser is not None:
        COMMLIB_ENABLED = True
        ser.close()
    else:
        COMMLIB_ENABLED = False
except:
    COMMLIB_ENABLED = False

# Import local version of PyQt, either 5 or 6
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

import Widgets

#/* Define block */
verbosity = False

def clearLayout(theLayout):
    for i in reversed(range(theLayout.count())):
        item = theLayout.takeAt(i)
        widgie = item.widget()
        if widgie is not None:
            widgie.deleteLater()
        else:
            layout = item.layout()
            clearLayout(layout)
        theLayout.removeItem(item)

#####################################################################
# The Table class represents the mapping from joystick, axis, and
# button to each channel.
#####################################################################
class Table:
    def __init__(self, filename=None):
        self.filename = filename
        self.clearTable()
        if filename is not None:
            self.read(filename=filename)

    def clearTable(self):
        self.joysticks = {}
        self.axes = {}
        self.buttons = {}
        self.recordbutton = -1
        self.recordjoystick = -1

    def addJoystick(self, index, channelname):
        self.joysticks[channelname] = index

    def addAxis(self, index, channelname):
        # A channel may only be attached to an axis or a button but not both
        self.removeButton(channelname)
        self.removeAxis(channelname)
        if index >= 0:
            self.axes[channelname] = index

    def removeAxis(self, channelname):
        if channelname in self.axes:
            del self.axes[channelname]

    def addButton(self, index, channelname):
        # A channel may only be attached to an axis or a button but not both
        self.removeAxis(channelname)
        self.removeButton(channelname)
        if index >= 0:
            self.buttons[channelname] = index

    def removeButton(self, channelname):
        if channelname in self.buttons:
            del self.buttons[channelname]

    def setRecordButton(self, index):
        self.recordbutton = index

    def setRecordJoystick(self, index):
        self.recordjoystick = index

    def getRecordButton(self):
        return self.recordbutton

    def getRecordJoystick(self):
        return self.recordjoystick

    def getAxisForChannel(self, channame):
        if channame in self.axes and channame in self.joysticks:
            return (self.joysticks[channame], self.axes[channame])
        else:
            return None

    def getAxisIndices(self):
        return self.axes.keys()

    def getButtonForChannel(self, channame):
        if channame in self.buttons and channame in self.joysticks:
            return (self.joysticks[channame], self.buttons[channame])
        else:
            return None

    def getButtonIndices(self):
        return self.buttons.keys()

    def getChannelForAxis(self, joystickID, axisID):
        for channame in self.joysticks:
            jsid = self.joysticks[channame]
            if jsid == joystickID:
                if channame in self.axes and self.axes[channame] == axisID:
                    return channame
        return None

    def getChannelForButton(self, joystickID, buttonID):
        for channame in self.joysticks:
            jsid = self.joysticks[channame]
            if jsid == joystickID:
                if channame in self.buttons and self.buttons[channame] == buttonID:
                    return channame
        return None

    def read(self, filename=None):
        '''
        Reads a table mapping file of the form:
        Axis/Button,ChannelName,JoystickID,AxisorButtonID
        where ChannelName can be Record for the record button
        '''
        try:
            if filename is not None:
                file = open(filename, 'r')
            elif self.filename is not None:
                file = open(self.filename, 'r')
            else:
                sys.stderr.write("Whoops - Unspecified table file!\n")
                return

            # Clear out the old table
            self.clearTable()

            # Skip header line in file
            skipline = file.readline()
            if skipline != 'Type,ChannelName,Joystick,ID\n':
                sys.stderr.write("Whoops - Not a valid table file!\n")
                raise FileError('Not a valid table file!')

            for line in file:
                row = line.strip().split(',')
                if len(row) == 4:
                    if row[1] == 'Record':
                        self.recordjoystick = int(row[2])
                        self.recordbutton = int(row[3])
                    elif row[0] == 'Button':
                        self.addJoystick(int(row[2]), row[1])
                        self.addButton(int(row[3]), row[1])
                    elif row[0] == 'Axis':
                        self.addJoystick(int(row[2]), row[1])
                        self.addAxis(int(row[3]), row[1])

            file.close()
            self.filename = filename

        except:
            sys.stderr.write("Whoops - Error reading table file!\n")

    def write(self, filename=None):
        '''
        Writes a table mapping file of the form:
        Axis/Button,ChannelName,JoystickID,AxisorButtonID
        where ChannelName can be Record for the record button
        print('Joysticks')
        for cname in self.joysticks:
            print('    ', cname,':', self.joysticks[cname])
        print('Axes')
        for cname in self.axes:
            print('    ', cname,':', self.axes[cname])
        print('buttons')
        for cname in self.buttons:
            print('    ', cname,':', self.buttons[cname])
        '''
        if True: #try:
            if filename is not None:
                file = open(filename, 'w')
            elif self.filename is not None:
                file = open(self.filename, 'w')
            else:
                sys.stderr.write("Whoops - Unspecified table file!\n")
                return

            file.write('Type,ChannelName,Joystick,ID\n')

            if self.recordjoystick >= 0 and self.recordbutton >= 0:
                file.write('Button,Record,%d,%d\n' % (self.recordjoystick,self.recordbutton))

            for channame in self.axes:
                if channame in self.joysticks:
                    file.write('Axis,%s,%d,%d\n' % (channame, self.joysticks[channame], self.axes[channame]))

            for channame in self.buttons:
                if channame in self.joysticks:
                    file.write('Button,%s,%d,%d\n' % (channame, self.joysticks[channame], self.buttons[channame]))

            file.close()
        else: #except:
            sys.stderr.write("Whoops - Error writing table file!\n")

class Audio:

    def __init__(self, file=None):
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.5)
        self.length = 0.0
        if file is not None:
            self.load(file)

    def load(self, wavefile):
        sound = pygame.mixer.Sound(wavefile)
        self.length = sound.get_length()
        pygame.mixer.music.load(wavefile)
        pygame.mixer.music.play()
        pygame.mixer.music.pause()

    def play(self, startTime=None):
        if self.length <= 0.0: return   # Check to make sure a sound file has been loaded
        # Check to see if start time is reasonable
        if startTime is not None and (startTime < 0.0 or startTime > self.length): return

        # If player not busy it must have reached end so rewind
        if not pygame.mixer.music.get_busy():
            self.rewind()
        # Rewind leaves it busy so we can set the optional start time
        if startTime is not None:
            pygame.mixer.music.set_pos(startTime)
        # Play from current position
        pygame.mixer.music.unpause()

    def stop(self):
        if self.length <= 0.0: return   # Check to make sure a sound file has been loaded
        pygame.mixer.music.pause()

    def rewind(self):
        if self.length <= 0.0: return   # Check to make sure a sound file has been loaded
        pygame.mixer.music.rewind()
        pygame.mixer.music.play()
        pygame.mixer.music.pause()

    def get_pos(self):
        if self.length <= 0.0: return 0.0  # Check to make sure a sound file has been loaded
        return pygame.mixer.music.get_pos()/1000.0

    def playing(self):
        if self.length <= 0.0: return False   # Check to make sure a sound file has been loaded
        return pygame.mixer.music.get_busy()

class JSWrapper:

    deadband = 0.0

    def __init__(self, index=None):
        if index is not None:
            self.js = pygame.joystick.Joystick(index)
            self.js.init()
            self.buttonCount = self.js.get_numbuttons()
            self.axisCount = self.js.get_numaxes()
            # Check for any initially pressed buttons
            buttons = self.getPushedButtons()
            time.sleep(0.1)
            buttons = self.getPushedButtons()
            if len(buttons) > 0:
                sys.stderr.write("\nWhoops - Button states indicate some button(s) are already pressed.\n")
                sys.stderr.write("This could be due to leftover state from previous code.\n")
                sys.stderr.write("Release any buttons currently pressed, then press and release other buttons\n")
                sys.stderr.write("until problem is cleared.\n\n")
                while len(buttons) > 0:
                    sys.stderr.write("Current buttons pressed:")
                    for index in buttons:
                        sys.stderr.write(" %d" % index)
                    sys.stderr.write("                                    \r")
                    buttons = self.getPushedButtons()

                sys.stderr.write("All clear -- proceeding.                                                    \n\n")


    def eatEvents(self):
        for event in pygame.event.get():
            if verbosity: print('Got event:', event)
            pass

    def getPushedButtons(self):
        self.eatEvents()
        pushed_ones = []
        for index in range(self.buttonCount):
            if self.js.get_button(index):
                pushed_ones.append(index)
        return pushed_ones

    def pushed(self, index):
        if index >= 0 and index < self.buttonCount:
            return self.js.get_button(index)
        else:
            return None

    def getMaxAxis(self):
        self.eatEvents()
        maxaxisindex = -1
        maxaxisvalue = 0.0
        for index in range(self.axisCount):
            if abs(self.js.get_axis(index)) > maxaxisvalue:
                maxaxisvalue = abs(self.js.get_axis(index))
                maxaxisindex = index
        return maxaxisindex, maxaxisvalue

    def getAxisValue(self, index):
        if index >= 0 and index < self.axisCount:
            if self.js.get_axis(index) > self.deadband:
                value = (self.js.get_axis(index) - self.deadband) / (1.0 - self.deadband)
            elif self.js.get_axis(index) < -self.deadband:
                value = (self.js.get_axis(index) + self.deadband) / (1.0 - self.deadband)
            else:
                value = 0.0
            return value
        else:
            return None

    def getAxisValues(self):
        self.eatEvents()
        values = []
        for index in range(self.axisCount):
            values.append(self.getAxisValue(index))
        return values

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-V/-version] [-v/-verbose] [-a/-animfile animfilename] [-t tablefilename] [-s/-start starttime] [-e/-end endtime] [-r/-rate samplerate]\n" % name)
    sys.stderr.write("\n");
    sys.stderr.write("    This tool supports the use of a joystick for populating channels in an\n");
    sys.stderr.write("animatronics file.  Channels to be populated must already be defined in the\n");
    sys.stderr.write("anim file.  The specified table file maps joystick actions to channels.\n");
    if verbosity:
        sys.stderr.write("This tool begins recording when the specified button is pressed on the\n");
        sys.stderr.write("joystick and continues until either the button is released or the end time\n");
        sys.stderr.write("is reached.  Users may specify start and end times as desired.\n");
        sys.stderr.write("Recording is done at the rate specified, 10Hz by default.\n");
        sys.stderr.write("Any existing data between start and end time is deleted.\n");
        sys.stderr.write("Upon completion, the animatronics file may be overwritten with the new channel\n");
        sys.stderr.write("data or a new animation file may be written instead.\n");  
    sys.stderr.write("\n");
    sys.stderr.write("-/-h/-help                    :show this information\n");
    sys.stderr.write("-V/-version                   :print version information and exit\n")
    sys.stderr.write("-v/-verbose                   :run more verbosely, including help\n");
    sys.stderr.write("-a/-animfile animfilename     :animatronics file\n")
    sys.stderr.write("-t/-tablefile tablefilename   :channel association table file\n")
    sys.stderr.write("-s/-start starttime           :start time (float seconds default: 0.0)\n")
    sys.stderr.write("-e/-end endtime               :end time (float seconds default: none)\n")
    sys.stderr.write("-r/-rate samplerate           :sample rate in Hz (default: 10Hz)\n")
    sys.stderr.write("\n\n");

def print_module_version(module_name):
    try:
        import importlib
        import importlib.metadata
        version = importlib.metadata.version(module_name)
        print(module_name + ':', version)
        exitcode = 0
    except:
        print('Version information not available')
        exitcode = 1
    return exitcode

#======================================================================================================
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
# The MainWindow class represents the Qt main window.
#####################################################################
class MainWindow(QMainWindow):
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

        self.unsavedChanges = False
        self.time = 0.0
        self.monoStartTime = 0.0
        self.startTime = 0.0
        self.endTime = 3599.0
        self.table = None
        self.currentRecordState = False
        self.onRecordTab = False
        self.recordingEnabled = False
        self.recordRate = 10.0  # in Hz
        self.nextRecordTime = 0.0
        self.playbackEnabled = False
        self.currentButtonSelector = None     # QComboBox that cursor is currently in, None if not in one
        self.currentAxisSelector = None     # QComboBox that cursor is currently in, None if not in one
        self.currentJoystick = None     # QComboBox that cursor is currently in, None if not in one
        self.allButtonSelectors = {}    # List/dictionary of comboboxes indexed by channelname
        self.allAxisSelectors = {}
        self.allJoystickSelectors = {}  # Record joystick and button indexed by 'RecordButton###$!'

        # Initialize all the pygame stuff to handle joystick and audio
        pygame.init()
        pygame.joystick.init()
        self.audio = Audio()

        # Get the number of joysticks attached and quit if none
        self.jsCount = pygame.joystick.get_count()
        if self.jsCount <= 0:
            sys.stderr.write('\nWhoops - Must have at least one (1) joystick attached\n')
            sys.exit(10)

        # Create wrappers for each joystick
        self.joysticks = {}
        for i in range(self.jsCount):
            self.joysticks[i] = JSWrapper(i)

        self.createUI()

    def createUI(self):
        # Creates all the permanent parts of the UI contained within
        # The UI parts dependent on the animation file are created in setAnimatronics

        # Initialize some stuff
        self.setWindowTitle("Joy")
        self.resize(520, 100)

        # Create popup stuff
        # Create file dialog used only for saving files
        self.filedialog = QFileDialog(parent=self, caption="Get Save Filename")
        self.filedialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        self.filedialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.filedialog.setFileMode(QFileDialog.FileMode.AnyFile)

        # Create the Help Popup
        self.helpPane = Widgets.TextDisplayDialog('Hauntimator Help', parent=self)

        # Create the XML display dialog for constant refresh
        self.XMLPane = Widgets.TextDisplayDialog('XML', parent=self)
        self.ClipboardPane = Widgets.TextDisplayDialog('Clipboard', parent=self)

        # Create all the dropdown menus
        self.create_menus()

        # Create the bottom level widget and make it the main widget
        self._mainarea = QFrame(self)
        self._mainarea.setMaximumSize(520,1000)
        self._mainarea.setMinimumSize(520,300)
        self.setMaximumSize(520,1000)
        self.setCentralWidget(self._mainarea)
        tlayout = QVBoxLayout(self._mainarea)
        self._tabwidget = QTabWidget()
        tlayout.addWidget(self._tabwidget)

        self.mapFrame = QFrame()
        indx = self._tabwidget.addTab(self.mapFrame, 'Channel Mapping')

        # Add tabs for recording button, axes, and other buttons
        pwidget = self._tabwidget.widget(indx)
        tframe = QFrame()
        tlayout = QVBoxLayout(pwidget)
        self._mapTabWidget = QTabWidget()
        tlayout.addWidget(self._mapTabWidget)
        tindx = self._mapTabWidget.addTab(tframe, 'Record Button Mapping')
        self.recordButtonMapWidget = self._mapTabWidget.widget(tindx)

        tscroll = QScrollArea()
        tindx = self._mapTabWidget.addTab(tscroll, 'Numeric Channel Mapping')
        tframe = QFrame()
        tscroll.setWidget(tframe)
        tscroll.setWidgetResizable(True)
        self.NumericChannelMapWidget = tframe

        tscroll = QScrollArea()
        tindx = self._mapTabWidget.addTab(tscroll, 'Digital Channel Mapping')
        self.DigitalChannelMapWidget = self._mapTabWidget.widget(tindx)
        tframe = QFrame()
        tscroll.setWidget(tframe)
        tscroll.setWidgetResizable(True)
        self.DigitalChannelMapWidget = tframe

        tframe = QFrame()
        self._tabwidget.addTab(tframe, 'Recording')
        tframe.leaveEvent = self.leaveRecordTab
        tframe.enterEvent = self.enterRecordTab
        tlayout = QVBoxLayout(tframe)

        # Create the mode display
        tframe = QFrame()
        tframe.setMaximumHeight(60)
        tframe.setMinimumHeight(60)
        xlayout = QHBoxLayout(tframe)
        self.modeLabel = QLabel(tframe)
        self.modeLabel.setText('Recording Enabled')
        self.modeLabel.setFrameStyle(QFrame.Shape.Panel)
        self.modeLabel.setLineWidth(2)
        self.modeLabel.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        self.modeLabel.setScaledContents(True)
        self.modeLabel.setFont(QFont('Arial', 30))
        self.disableAll()
        xlayout.addWidget(self.modeLabel)
        tlayout.addWidget(tframe)

        # Create the main Time display
        self.lcd = QLCDNumber()
        self.lcd.setDigitCount(8)
        self.lcd.setMaximumHeight(80)
        self.lcd.setMinimumHeight(80)
        tlayout.addWidget(self.lcd)

        # Add start and end time indicators
        widget = QWidget()
        hlayout = QHBoxLayout(widget)
        tlabel = QLabel('Start:')
        tlabel.setFont(QFont('Arial', 20))
        tlabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hlayout.addWidget(tlabel)
        self.startLCD = QLCDNumber()
        self.startLCD.setDigitCount(8)
        self.startLCD.display(toHMS(self.startTime))
        self.startLCD.mouseDoubleClickEvent = self.setStartTime
        self.startLCD.setMaximumHeight(40)
        self.startLCD.setMinimumHeight(40)
        hlayout.addWidget(self.startLCD)
        tlabel = QLabel('End:')
        tlabel.setFont(QFont('Arial', 20))
        tlabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hlayout.addWidget(tlabel)
        self.endLCD = QLCDNumber()
        self.endLCD.setDigitCount(8)
        self.endLCD.setMaximumHeight(40)
        self.endLCD.setMinimumHeight(40)
        self.endLCD.display(toHMS(self.endTime))
        self.endLCD.mouseDoubleClickEvent = self.setEndTime
        hlayout.addWidget(self.endLCD)
        tlayout.addWidget(widget)

        # Add row of buttons
        widget = QWidget()
        hlayout = QHBoxLayout(widget)
        self.enableButton = QPushButton('Enable Recording')
        self.enableButton.clicked.connect(self.enableRecording)
        hlayout.addWidget(self.enableButton)
        self.rewindButton = QPushButton('Reset to Audio Length')
        self.rewindButton.clicked.connect(self.resetToAudio)
        hlayout.addWidget(self.rewindButton)
        self.reviewButton = QPushButton('Enable Replay')
        self.reviewButton.clicked.connect(self.enablePlayback)
        hlayout.addWidget(self.reviewButton)
        tlayout.addWidget(widget)
        tlayout.addStretch()
        self.resetToAudio()

        # Add a QTimer to call the event handler
        timer = QTimer(self)
        timer.timeout.connect(self.eventHandler)
        timer.start(10) # Call eventHandler every 10msec

    def leaveRecordTab(self, event):
        # Disable recording and playback
        self.onRecordTab = False
        self.disableAll()

    def enterRecordTab(self, event):
        # Enable recording and playback
        self.onRecordTab = True

    def disableAll(self):
        # Set flag
        self.recordingEnabled = False
        self.playbackEnabled = False
        # Set text for mode
        self.modeLabel.setText('Disabled')
        palette = self.modeLabel.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor('white'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('black'))
        self.modeLabel.setPalette(palette)

    def enableRecording(self):
        if not self.onRecordTab: return
        # Set flags
        self.recordingEnabled = True
        self.playbackEnabled = False
        self.rewind()

        # Set text for mode
        self.modeLabel.setText('Recording Enabled')
        palette = self.modeLabel.palette()
        palette.setColor(self.modeLabel.backgroundRole(), QColor('red'))
        palette.setColor(self.modeLabel.foregroundRole(), QColor('white'))
        self.modeLabel.setAutoFillBackground(True)
        self.modeLabel.setPalette(palette)

        # Clear all channels to be recorded from start to end time
        for channame in self.animatronics.channels:
            if channame in self.table.buttons or channame in self.table.axes:
                self.animatronics.channels[channame].delete_knot_range(self.startTime, self.endTime)

    def enablePlayback(self):
        if not self.onRecordTab: return
        # Set flag
        self.recordingEnabled = False
        self.playbackEnabled = True
        self.rewind()
        # Set text for mode
        self.modeLabel.setText('Playback Enabled')
        palette = self.modeLabel.palette()
        palette.setColor(self.modeLabel.backgroundRole(), Qt.yellow)
        palette.setColor(self.modeLabel.foregroundRole(), Qt.black)
        self.modeLabel.setAutoFillBackground(True)
        self.modeLabel.setPalette(palette)

    def setRate(self, inrate):
        self.recordRate = inrate

    def setStartTimeTo(self, intime):
        self.startTime = intime
        self.startLCD.display(toHMS(self.startTime))

    def setStartTime(self, event):
        print('Setting start')
        text, ok = self.getSomeTime('Set Start Time', toHMS(self.time))
        if ok:
            self.startLCD.display(text)
            self.startTime = fromHMS(text)

    def setEndTimeTo(self, intime):
        self.endTime = intime
        self.endLCD.display(toHMS(self.endTime))

    def setEndTime(self, event):
        print('Setting end')
        text, ok = self.getSomeTime('Set End Time', toHMS(self.time))
        if ok:
            self.endLCD.display(text)
            self.endTime = fromHMS(text)

    def getSomeTime(self, name, buttonValue):
        text, ok = QInputDialog().getText(self, name, name, QLineEdit.EchoMode.Normal, buttonValue)
        if ok and text.find(':') < 0:
            text = toHMS(float(text))
        return text, ok

    def rewind(self):
        self.time = self.startTime
        self.startLCD.display(toHMS(self.startTime))
        self.lcd.display(toHMS(self.time))

    def resetToAudio(self):
        self.time = 0.0
        self.startTime = 0.0
        self.startLCD.display(toHMS(self.startTime))
        self.lcd.display(toHMS(self.time))
        self.endTime = self.audio.length
        self.endLCD.display(toHMS(self.endTime))

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
        self.file_menu.setToolTipsVisible(True)

        # Open action
        self._open_file_action = QAction("&Open Anim File", self,
            shortcut=QKeySequence.StandardKey.Open,
            triggered=self.openAnimFile)
        self.file_menu.addAction(self._open_file_action)

        self.file_menu.addSeparator()

        # Save action
        self._save_file_action = QAction("&Save Anim File",
                self, shortcut=QKeySequence.StandardKey.Save, triggered=self.saveAnimFile)
        self.file_menu.addAction(self._save_file_action)

        # Save As action
        self._save_as_file_action = QAction("&Save As",
                self, shortcut=QKeySequence.StandardKey.SaveAs, triggered=self.saveAsFile)
        self.file_menu.addAction(self._save_as_file_action)

        self.file_menu.addSeparator()

        self._open_map_action = QAction("&Open Mapping File", self,
            triggered=self.openMapFile)
        self.file_menu.addAction(self._open_map_action)

        # Save Map As action
        self._save_map_as_file_action = QAction("&Save Map As",
                self, triggered=self.saveMapAsFile)
        self.file_menu.addAction(self._save_map_as_file_action)

        # exit action
        self.file_menu.addSeparator()
        self._exit_action = QAction("&Quit", self, shortcut=QKeySequence.StandardKey.Quit,
                triggered=self.exit_action)
        self.file_menu.addAction(self._exit_action)

        # Create the Help dropdown menu #################################
        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.setToolTipsVisible(True)

        self._about_action = QAction("About", self,
            shortcut=QKeySequence.StandardKey.WhatsThis,
            triggered=self.about_action)
        self.help_menu.addAction(self._about_action)

        self._quick_action = QAction("Quick Start", self,
            triggered=self.quick_action)
        self.help_menu.addAction(self._quick_action)

        self._help_action = QAction("Help", self,
            shortcut=QKeySequence.StandardKey.HelpContents,
            triggered=self.help_action)
        self.help_menu.addAction(self._help_action)

        self._hotkeys_action = QAction("Hot Keys", self,
            triggered=self.hotkeys_action)
        self.help_menu.addAction(self._hotkeys_action)

        self.help_menu.addSeparator()

        # showXML menu item
        self._showXML_action = QAction("Show XML", self,
            triggered=self.showXML_action)
        self.help_menu.addAction(self._showXML_action)

    def recording(self):
        jsindex = self.table.getRecordJoystick()
        if jsindex >= 0 and self.recordingEnabled:
            butts = self.joysticks[jsindex].getPushedButtons()
            return self.table.getRecordButton() in butts
        else:
            return False

    def playingBack(self):
        jsindex = self.table.getRecordJoystick()
        if jsindex >= 0 and self.playbackEnabled:
            butts = self.joysticks[jsindex].getPushedButtons()
            return self.table.getRecordButton() in butts
        else:
            return False

    def eventHandler(self):
        for i in range(self.jsCount):
            self.joysticks[i].eatEvents()
        # Temp kluge
        self.enableButton.setEnabled(self.table is not None and self.table.getRecordButton() >= 0)
        self.reviewButton.setEnabled(self.table is not None and self.table.getRecordButton() >= 0 and COMMLIB_ENABLED)
        # Recording time controls
        if self.recording() and not self.currentRecordState:
            print('Begin Recording')
            self.currentRecordState = True
            self.monoStartTime = time.monotonic()
            self.time = self.startTime
            self.nextRecordTime = self.startTime
            if self.audio is not None: self.audio.play(startTime=self.startTime)
        elif self.playingBack() and not self.currentRecordState:
            print('Begin Playback')
            self.currentRecordState = True
            self.monoStartTime = time.monotonic()
            self.time = self.startTime
            if self.audio is not None: self.audio.play(startTime=self.startTime)
        elif (not (self.recording()or self.playingBack()) or self.time >= self.endTime) and self.currentRecordState:
            if self.audio is not None: self.audio.stop()
            if not self.recording(): self.currentRecordState = False
            self.disableAll()
        if self.audio.playing() or self.currentRecordState:
            self.time = time.monotonic() - self.monoStartTime + self.startTime
            self.lcd.display(toHMS(self.time))
            # Perform recording or playback
            if self.playingBack():
                self.playBack()
            elif self.recording():
                if self.time >= self.nextRecordTime:
                    self.nextRecordTime += 1.0/self.recordRate
                    self.record(True)
                else:
                    self.record()
        elif self.recordingEnabled:
                self.record()


        # Setting selectors from joystick actions
        # self.currentButtonSelector = None     # QComboBox that cursor is currently in, None if not in one
        # self.currentAxisSelector = None     # QComboBox that cursor is currently in, None if not in one
        # self.currentJoystick = None     # QComboBox that cursor is currently in, None if not in one
        if self.currentJoystick is not None:
            for jsindx in self.joysticks:
                butts = self.joysticks[jsindx].getPushedButtons()
                if len(butts) > 0:
                    self.currentJoystick.setCurrentIndex(jsindx)
                    channame = self.currentJoystick.property('ChannelName')
                    if isinstance(channame, str):
                        self.table.addJoystick(jsindx, channame)
                    else:
                        # Must be the record joystick because we didn't set the channel name there
                        self.table.setRecordJoystick(jsindx)
                    break
        if self.currentButtonSelector is not None:
            for jsindx in self.joysticks:
                butts = self.joysticks[jsindx].getPushedButtons()
                if len(butts) > 0:
                    self.currentButtonSelector.setCurrentIndex(butts[0]+1)
                    channame = self.currentButtonSelector.property('ChannelName')
                    if isinstance(channame, str):
                        self.table.addButton(butts[0], channame)
                    else:
                        # Must be the record button because we didn't set the channel name there
                        self.table.setRecordButton(butts[0])
                    break
        if self.currentAxisSelector is not None:
            for jsindx in self.joysticks:
                axisindx, axisvalue = self.joysticks[jsindx].getMaxAxis()
                if axisvalue > 0.75:
                    self.currentAxisSelector.setCurrentIndex(axisindx+1)
                    channame = self.currentAxisSelector.property('ChannelName')
                    if isinstance(channame, str):
                        self.table.addAxis(axisindx, channame)
                    break


    def playBack(self):
        #print('In playback with time:', self.time)
        # Play back every channel that has values
        for channame in self.animatronics.channels:
            channel = self.animatronics.channels[channame]
            if channel.num_knots() > 0:
                # Get value at current time
                value = channel.getValueAtTime(self.time)
                if value is not None:
                    # And push it out to controller
                    self.setChannel(channame, value)

    def setChannel(self, channame, value):
        if channame in self.animatronics.channels and COMMLIB_ENABLED:
            channel = self.animatronics.channels[channame]
            port = channel.port
            if port >= 0:
                if channel.type == channel.DIGITAL:
                    commlib.setDigitalChannel(port, value)
                else:
                    commlib.setServo(port, value)

    def record(self, flag=False):
        #print('In recording with time:', self.time)
        # Check every channel to see if it is mapped
        for channame in self.animatronics.channels:
            # Handle button
            buttval = self.table.getButtonForChannel(channame)
            if buttval is not None:
                state = self.joysticks[buttval[0]].pushed(buttval[1])
                # Set state in channel at current time
                # Fortunately, the UI enforces that buttons can only map to digital channels
                # so we don't have to check here
                if state is not None:
                    channel = self.animatronics.channels[channame]
                    if flag: channel.add_knot(self.time, state)
                    self.setChannel(channame, state)
            # Handle axis
            buttval = self.table.getAxisForChannel(channame)
            if buttval is not None:
                value = self.joysticks[buttval[0]].getAxisValue(buttval[1])
                if value is not None:
                    channel = self.animatronics.channels[channame]
                    # Scale the axis value to the valid channel data range
                    value = (value + 1.0) / 2.0 * (channel.maxLimit - channel.minLimit) + channel.minLimit
                    # Set value in channel at current time
                    if flag: channel.add_knot(self.time, value)
                    self.setChannel(channame, value)

    def setWindowName(self, filename):
        # Add filename to window title
        if filename is not None:
            self.setWindowTitle("Joy - " + filename)
        else:
            self.setWindowTitle("Joy")

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
        # Add filename to window title
        self.setWindowName(self.animatronics.filename)

        self.updateXMLPane()

        # Set up/Update UI based on new animation
        self.enableButton.setEnabled(False)

        self.table = Table()
        if inanim.newAudio is not None:
            self.audio.load(inanim.newAudio.audiofile)
            # Set times to match the audio length
            self.resetToAudio()

        self.allButtonSelectors = {}    # List/dictionary of comboboxes indexed by channelname
        self.allAxisSelectors = {}
        self.allJoystickSelectors = {}  # Record joystick and button stored separately

        # Create the channel mapping tabs
        # Start with record button
        tlayout = self.recordButtonMapWidget.layout()
        if tlayout is not None:
            clearLayout(tlayout)
        else:
            tlayout = QHBoxLayout()
            self.recordButtonMapWidget.setLayout(tlayout)
        self.recordButtonJoystickSelecter = QComboBox()
        self.recordButtonJoystickSelecter.setToolTip('Press any button on the joystick you want here')
        self.recordButtonJoystickSelecter.enterEvent = self.enterJoystickCombo
        self.recordButtonJoystickSelecter.leaveEvent = self.leaveCombo
        for i in range(self.jsCount):
            self.joysticks[i] = JSWrapper(i)
            self.recordButtonJoystickSelecter.addItem('%d - %s' % (i, self.joysticks[i].js.get_name()))
        tlayout.addWidget(self.recordButtonJoystickSelecter)
        self.recordButtonJoystickSelecter.activated.connect(self.recordButtonJoystickSelected)
        self.recordButtonJoystickSelecter.setCurrentIndex(0)

        self.recordButtonSelecter = QComboBox()
        self.recordButtonSelecter.setToolTip('Press any joystick button you want here')
        self.recordButtonSelecter.enterEvent = self.enterButtonCombo
        self.recordButtonSelecter.leaveEvent = self.leaveCombo
        self.recordButtonSelecter.activated.connect(self.recordButtonSelected)
        tlayout.addWidget(self.recordButtonSelecter)
        self.recordButtonJoystickSelected(0)

        # Now do axes mapping
        playout = self.NumericChannelMapWidget.layout()
        if playout is not None:
            clearLayout(playout)
        else:
            playout = QVBoxLayout()
            self.NumericChannelMapWidget.setLayout(playout)
        width = 0
        for channame in self.animatronics.channels:
            if 10 * len(channame) > width and self.animatronics.channels[channame].type != self.animatronics.channels[channame].DIGITAL:
                    width = 10 * len(channame)
        for channame in self.animatronics.channels:
            if self.animatronics.channels[channame].type != self.animatronics.channels[channame].DIGITAL:
                tlayout = QHBoxLayout()
                tlabel = QLabel(self.NumericChannelMapWidget)
                tlabel.setText(channame)
                tlabel.setMaximumWidth(width)
                tlabel.setMinimumWidth(width)
                tlayout.addWidget(tlabel)

                self.axisJoystickSelecter = QComboBox()
                self.axisJoystickSelecter.setToolTip('Press any button on the joystick you want here')
                self.allJoystickSelectors[channame] = self.axisJoystickSelecter
                self.axisJoystickSelecter.enterEvent = self.enterJoystickCombo
                self.axisJoystickSelecter.leaveEvent = self.leaveCombo
                self.axisJoystickSelecter.setProperty('ChannelName', channame)
                for i in range(self.jsCount):
                    self.joysticks[i] = JSWrapper(i)
                    self.axisJoystickSelecter.addItem('%d - %s' % (i, self.joysticks[i].js.get_name()))
                tlayout.addWidget(self.axisJoystickSelecter)
                self.axisJoystickSelecter.activated.connect(self.axisJoystickSelected)
                self.axisJoystickSelecter.setCurrentIndex(0)

                self.axisSelecter = QComboBox()
                self.axisSelecter.setToolTip('Max out any joystick axis you want here')
                self.allAxisSelectors[channame] = self.axisSelecter
                self.axisSelecter.enterEvent = self.enterAxisCombo
                self.axisSelecter.leaveEvent = self.leaveCombo
                self.axisSelecter.setProperty('ChannelName', channame)
                tlayout.addWidget(self.axisSelecter)
                self.axisSelecter.activated.connect(self.axisSelected)
                self.axisJoystickSelected(0, sender=self.axisJoystickSelecter)

                playout.addLayout(tlayout)


        # Now do button mapping
        # Check to see if the tab already has a layout
        playout = self.DigitalChannelMapWidget.layout()
        if playout is not None:
            # If so just clear it out and reuse it
            clearLayout(playout)
        else:
            # If not create a new one
            playout = QVBoxLayout()
            self.DigitalChannelMapWidget.setLayout(playout)
        width = 0
        for channame in self.animatronics.channels:
            if 10 * len(channame) > width and self.animatronics.channels[channame].type == self.animatronics.channels[channame].DIGITAL:
                    width = 10 * len(channame)
        for channame in self.animatronics.channels:
            if self.animatronics.channels[channame].type == self.animatronics.channels[channame].DIGITAL:
                tlayout = QHBoxLayout()
                tlabel = QLabel(self.DigitalChannelMapWidget)
                tlabel.setText(channame)
                tlabel.setMaximumWidth(width)
                tlabel.setMinimumWidth(width)
                tlayout.addWidget(tlabel)

                self.buttonJoystickSelecter = QComboBox()
                self.buttonJoystickSelecter.setToolTip('Press any button on the joystick you want here')
                self.allJoystickSelectors[channame] = self.buttonJoystickSelecter
                self.buttonJoystickSelecter.enterEvent = self.enterJoystickCombo
                self.buttonJoystickSelecter.leaveEvent = self.leaveCombo
                self.buttonJoystickSelecter.setProperty('ChannelName', channame)
                for i in range(self.jsCount):
                    self.joysticks[i] = JSWrapper(i)
                    self.buttonJoystickSelecter.addItem('%d - %s' % (i, self.joysticks[i].js.get_name()))
                tlayout.addWidget(self.buttonJoystickSelecter)
                self.buttonJoystickSelecter.activated.connect(self.buttonJoystickSelected)
                self.buttonJoystickSelecter.setCurrentIndex(0)

                self.buttonSelecter = QComboBox()
                self.buttonSelecter.setToolTip('Press any joystick button you want here')
                self.allButtonSelectors[channame] = self.buttonSelecter
                self.buttonSelecter.enterEvent = self.enterButtonCombo
                self.buttonSelecter.leaveEvent = self.leaveCombo
                self.buttonSelecter.setProperty('ChannelName', channame)
                tlayout.addWidget(self.buttonSelecter)
                self.buttonSelecter.activated.connect(self.buttonSelected)
                self.buttonJoystickSelected(0, sender=self.buttonJoystickSelecter)

                playout.addLayout(tlayout)

    def enterJoystickCombo(self, event):
        if usedPyQt == 5:
            self.currentJoystick = self.childAt(event.windowPos().toPoint())
        elif usedPyQt == 6:
            self.currentJoystick = self.childAt(event.scenePosition().toPoint())

    def enterButtonCombo(self, event):
        if usedPyQt == 5:
            self.currentButtonSelector = self.childAt(event.windowPos().toPoint())
        elif usedPyQt == 6:
            self.currentButtonSelector = self.childAt(event.scenePosition().toPoint())

    def enterAxisCombo(self, event):
        if usedPyQt == 5:
            self.currentAxisSelector = self.childAt(event.windowPos().toPoint())
        elif usedPyQt == 6:
            self.currentAxisSelector = self.childAt(event.scenePosition().toPoint())

    def leaveCombo(self, event):
        self.currentButtonSelector = None
        self.currentAxisSelector = None
        self.currentJoystick = None

    def recordButtonJoystickSelected(self, index):
        tcombobox = self.recordButtonSelecter
        tcombobox.clear()
        tcombobox.addItem('Unmapped')
        for i in range(self.joysticks[index].buttonCount):
            tcombobox.addItem('%d' % (i+1))
        tcombobox.setCurrentText('Unmapped')
        # Also clear the table entry
        self.table.setRecordButton(-1)
        self.table.setRecordJoystick(index)

    def recordButtonSelected(self, index):
        self.table.setRecordButton(index-1)

    def axisJoystickSelected(self, index, sender=None):
        if sender is None: sender = self.sender()
        channame = sender.property('ChannelName')
        if channame in self.allAxisSelectors:
            tcombobox = self.allAxisSelectors[channame]
            tcombobox.clear()
            tcombobox.addItem('Unmapped')
            for i in range(self.joysticks[index].axisCount):
                tcombobox.addItem('%d' % (i+1))
            tcombobox.setCurrentText('Unmapped')
            self.table.removeAxis(channame)
        self.table.addJoystick(index, channame)

    def axisSelected(self, index):
        sender = self.sender()
        channame = sender.property('ChannelName')
        self.table.addAxis(index-1, channame)

    def buttonJoystickSelected(self, index, sender=None):
        if sender is None: sender = self.sender()
        channame = sender.property('ChannelName')
        if channame in self.allButtonSelectors:
            tcombobox = self.allButtonSelectors[channame]
            tcombobox.clear()
            tcombobox.addItem('Unmapped')
            for i in range(self.joysticks[index].buttonCount):
                tcombobox.addItem('%d' % (i+1))
            tcombobox.setCurrentText('Unmapped')
            self.table.removeButton(channame)
        self.table.addJoystick(index, channame)

    def buttonSelected(self, index):
        sender = self.sender()
        channame = sender.property('ChannelName')
        self.table.addButton(index-1, channame)

    def updateUIfromTable(self):
        for channelname in self.animatronics.channels:
            if channelname in self.table.joysticks and channelname in self.allJoystickSelectors:
                selector = self.allJoystickSelectors[channelname]
                selector.setCurrentIndex(self.table.joysticks[channelname])
            elif channelname in self.allJoystickSelectors:
                selector = self.allJoystickSelectors[channelname]
                selector.setCurrentIndex(0)
                self.table.addJoystick(0, channelname)
            if channelname in self.table.axes and channelname in self.allAxisSelectors:
                selector = self.allAxisSelectors[channelname]
                selector.setCurrentIndex(self.table.axes[channelname]+1)
            if channelname in self.table.buttons and channelname in self.allButtonSelectors:
                selector = self.allButtonSelectors[channelname]
                selector.setCurrentIndex(self.table.buttons[channelname]+1)

        # Specifically do the record button
        self.table.setRecordJoystick(0) # Default to first found joystick
        if self.table.getRecordJoystick() >= 0:
            self.recordButtonJoystickSelecter.setCurrentIndex(self.table.getRecordJoystick())
        if self.table.getRecordButton() >= 0:
            self.recordButtonSelecter.setCurrentIndex(self.table.getRecordButton()+1)

    def openMapFile(self):
        """
        The method openMapFile opens a file dialog for the user to select
        a Map file to load.  It replaces all of the previous
        Table object
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        """Get filename and open as active animatronics"""
        fileName, _ = QFileDialog.getOpenFileName(self,"Get Open Filename", "",
                            "Mapping Files (*.map);;All Files (*)",
                            options=QFileDialog.Option.DontUseNativeDialog)

        if fileName:
            try:
                self.table.read(fileName)
                self.updateUIfromTable()

            except Exception as e:
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                return


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
                                options=QFileDialog.Option.DontUseNativeDialog)

            if fileName:
                newAnim = Animatronics.Animatronics()
                try:
                    newAnim.parseXML(fileName)
                    self.setAnimatronics(newAnim)
                    self.unsavedChanges = False

                except Exception as e:
                    sys.stderr.write("\nWhoops - Error reading input file %s\n" % fileName)
                    sys.stderr.write("Message: %s\n" % e)
                    return

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
                msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
                msgBox.setIcon(QMessageBox.Icon.Warning)
                ret = msgBox.exec()
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
        if self.filedialog.exec():
            try:
                fileName = self.filedialog.selectedFiles()[0]
                with open(fileName, 'w') as outfile:
                    # Set upload paths prior to writing
                    self.animatronics.setFilename(fileName)
                    outfile.write(self.animatronics.toXML())
                self.updateXMLPane()    # Refreshes XML and saves to new autosave file
                self.unsavedChanges = False
                self.setWindowName(fileName)

            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Whoops - Unable to write to specified file:')
                msgBox.setInformativeText(fileName)
                msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
                msgBox.setIcon(QMessageBox.Icon.Warning)
                ret = msgBox.exec()
                return

    def saveMapAsFile(self):
        """
        The method saveMapAsFile opens a file dialog to query the user for
        a filename to which to save the map table.  If the file exists, the
        user is prompted to confirm overwrite.

            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """

        """Save the current map table file"""
        fileName = self.animatronics.filename
        if fileName is not None:
            #fileName = os.path.basename(fileName)
            fileName = os.path.splitext(fileName)[0]
            self.filedialog.selectFile(fileName)
        self.filedialog.setDefaultSuffix('map')
        self.filedialog.setNameFilter("Map Files (*.map);;All Files (*)")
        if self.filedialog.exec():
            try:
                fileName = self.filedialog.selectedFiles()[0]
                self.table.write(filename=fileName)

            except Exception as e:
                sys.stderr.write("\nWhoops - Error writing output file %s\n" % fileName)
                sys.stderr.write("Message: %s\n" % e)
                msgBox = QMessageBox(parent=self)
                msgBox.setText('Whoops - Unable to write to specified file:')
                msgBox.setInformativeText(fileName)
                msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
                msgBox.setIcon(QMessageBox.Icon.Warning)
                ret = msgBox.exec()
                return

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
            msgBox.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            msgBox.setDefaultButton(QMessageBox.StandardButton.Save)
            msgBox.setIcon(QMessageBox.Icon.Warning)
            ret = msgBox.exec()
            if ret == QMessageBox.StandardButton.Save:
                self.saveAnimFile()
            elif ret == QMessageBox.StandardButton.Cancel:
                return False
        return True

    def closeEvent(self, event):
        """ Catch main close event and pass it to our handler """
        if self.handle_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    def about_action(self):
        """
        The method about_action brings up the About text in a popup.  About
        and Help use the same popup so only one can be displayed at a time.
            member of class: MainWindow
        Parameters
        ----------
        self : MainWindow
        """
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/JoyAbout.md'))
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
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/JoyHelp.md'))
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
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/JoyQuickStart.md'))
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
        self.helpPane.setSource(os.path.join(getExecPath(), 'docs/JoyHotKeys.md'))
        self.helpPane.resize(600, 700)
        self.helpPane.setWindowTitle('Hot Key Cheat Sheet')
        self.helpPane.show()

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
        #self.autoSave()


#======================================================================================================
#/* Main */
def doJoysticking():
    """
    The method doJoysticking is the main function of the application.
    It parses the command line arguments, handles them, and then opens
    the main window and proceeds.
    """
    global verbosity

    # Local Variables to support parsing an Animatronics file specified
    # on the command line
    starttime = 0.0
    endtime = None
    rate = 10.0  # 10Hz
    tablefilename = None
    writetable = False
    skipbuttons = False
    outfilename = None
    animfilename = None


    # Parse arguments
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-V' or sys.argv[i] == '-version':
            exitcode = print_module_version('joysticking')
            sys.exit(exitcode)
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        elif sys.argv[i] == '-tw' or sys.argv[i] == '-tablewrite':
            i += 1
            if i < len(sys.argv):
                tablefilename = sys.argv[i]
                writetable = True
        elif sys.argv[i] == '-nb' or sys.argv[i] == '-nobuttons':
            skipbuttons = True
        elif sys.argv[i] == '-a' or sys.argv[i] == '-animfile':
            i += 1
            if i < len(sys.argv):
                animfilename = sys.argv[i]
        elif sys.argv[i] == '-o' or sys.argv[i] == '-outfile':
            i += 1
            if i < len(sys.argv):
                outfilename = sys.argv[i]
        elif sys.argv[i] == '-t' or sys.argv[i] == '-tablefile':
            i += 1
            if i < len(sys.argv):
                tablefilename = sys.argv[i]
        elif sys.argv[i] == '-s' or sys.argv[i] == '-start':
            i += 1
            if i < len(sys.argv):
                starttime = float(sys.argv[i])
        elif sys.argv[i] == '-e' or sys.argv[i] == '-end':
            i += 1
            if i < len(sys.argv):
                endtime = float(sys.argv[i])
        elif sys.argv[i] == '-r' or sys.argv[i] == '-rate':
            i += 1
            if i < len(sys.argv):
                rate = float(sys.argv[i])
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    # Create the global main window
    app = QApplication(sys.argv)
    main_win = MainWindow()

    # Start with empty animation by default
    animation = Animatronics.Animatronics()

    # If an input file was specified, parse it or die trying
    if animfilename is not None:
        if os.path.isfile(animfilename):
            try:
                animation.parseXML(animfilename)

            except Exception as e:
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % animfilename)
                sys.stderr.write("Message: %s\n" % e)
                sys.exit(11)

        else:
            sys.stderr.write("\nWhoops - Unable to use %s as a file\n" % animfilename)
            sys.exit(11)

    # Open the main window and process events
    main_win.setAnimatronics(animation)
    main_win.show()

    # Set the values that were input from arguments
    if rate > 20.0:
        sys.stderr.write('\nHmmm - specified record rate of %fHz may exceed polling rate of joystick.\n' % rate)
        sys.stderr.write('Polling rate utility available to check joystick rate.\n\n')
    main_win.setRate(rate)

    if starttime > 0.0:
        main_win.setStartTimeTo(starttime)
    if endtime is not None:
        main_win.setEndTimeTo(endtime)

    if tablefilename is not None:
        main_win.table.read(tablefilename)
        main_win.updateUIfromTable()

    app.exec()

if __name__ == "__main__":
    doJoysticking()

