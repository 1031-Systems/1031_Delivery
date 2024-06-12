#/* Import block */

import Animatronics

usedPyQt = None
try:
    # PyQt5 import block for all widgets
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    usedPyQt = 5
except:
    try:
        # PyQt6 import block for all widgets
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        from PyQt6.QtWidgets import *
        usedPyQt = 6
    except:
        sys.stderr.write('Whoops - Unable to find PyQt5 or PyQt6 - Quitting\n')
        exit(10)

#/* Define block */
# Local Globals
lastrepeatend = None
lastrepeatstart = None
lastrepeatcount = None

def invert(channelList, theanim, starttime=None, endtime=None):
    retval = False  # Return False if NO channels are modified
    for channel in channelList:
        if ((channel.maxLimit > 1.0e33 and channel.minLimit > -1.0e33) or
            (channel.maxLimit < 1.0e33 and channel.minLimit < -1.0e33)): continue
        retval = True   # Return True if ANY channel is modified
        for key in channel.knots:
            if (starttime is None or key >= starttime) and (endtime is None or key <= endtime):
                channel.knots[key] = (channel.maxLimit + channel.minLimit) - channel.knots[key]

    return(retval)

class _RepeatUserPrompt(QDialog):
    def __init__(self, starttime=None, endtime=None):
        global lastrepeatstart, lastrepeatend, lastrepeatcount

        super().__init__()

        if starttime is not None: lastrepeatstart = starttime
        if endtime is not None: lastrepeatend = endtime

        self.title = 'Repeat Parameters'
        widget = QWidget()
        layout = QFormLayout()
        self._startedit = QLineEdit()
        if lastrepeatstart is not None:
            self._startedit.setText(str(lastrepeatstart))
        else:
            self._startedit.setText('0.0')
        layout.addRow(QLabel('Start Time:'), self._startedit)
        self._endedit = QLineEdit()
        if lastrepeatend is not None:
            self._endedit.setText(str(lastrepeatend))
        else:
            self._endedit.setText('1.0')
        layout.addRow(QLabel('  End Time:'), self._endedit)
        self._countedit = QLineEdit()
        if lastrepeatcount is not None:
            self._countedit.setText(str(lastrepeatcount))
        else:
            self._countedit.setText('1')
        layout.addRow(QLabel(' Rep Count:'), self._countedit)
        widget.setLayout(layout)

        self.okButton = QPushButton('Run')
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

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    def getStartTime(self):
        return float(self._startedit.text())

    def getEndTime(self):
        return float(self._endedit.text())

    def getCount(self):
        return int(self._countedit.text())


def repeat(channelList, theanim, starttime=None, endtime=None):
    global lastrepeatend
    global lastrepeatstart
    global lastrepeatcount

    retval = False  # Return False if NO channels are modified

    # Create the dialog to prompt for range, reps, etc.
    widget = _RepeatUserPrompt(starttime=starttime, endtime=endtime)
    code = widget.exec_()
    if code != QDialog.Accepted: return False

    startTime = widget.getStartTime()
    endTime = widget.getEndTime()
    count = widget.getCount()
    deltaTime = endTime - startTime

    lastrepeatstart = startTime
    lastrepeatend = endTime
    lastrepeatcount = count

    for channel in channelList:
        # Duplicate knots between start and end time, adding delta time to each
        knotTimes,knotValues = channel.getKnotData(startTime, endTime, 1000000)
        for i in range(len(knotTimes)):
            for rep in range(count):
                channel.add_knot(knotTimes[i]+deltaTime*(rep+1), knotValues[i])
                # We will return True if ANY knots were added to ANY channels
                retval = True

    return(retval)

external_callables = [invert, repeat]

