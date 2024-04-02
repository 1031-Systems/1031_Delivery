import Animatronics
from pocketsphinx import get_model_path, Decoder, Config

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

# Local Global
lastAudioFile = None

class UserPrompt(QDialog):
    def __init__(self, typelist, audiofile):
        super().__init__()

        self.title = 'Phoneme Channel Generator'
        widget = QWidget()
        layout = QFormLayout()
        self._nameedit = QLineEdit()
        self._nameedit.setText(audiofile)
        layout.addRow(QLabel('Audio File:'), self._nameedit)

        if typelist is not None and len(typelist) > 0:
            self.typeselect = QComboBox()
            self.typeselect.addItems(typelist)
            layout.addRow(self.typeselect)

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

    def getAudioFile(self):
        return self._nameedit.text()

    def getType(self):
        return self.typeselect.currentText()

def runSphinx(audiofile):
    # Create a decoder with certain model
    config = Config()
    config.set_string('-hmm', get_model_path('en-us/en-us'))
    config.set_string('-lm', None)  # Must remove language model from default config
    config.set_string('-allphone', get_model_path('en-us/en-us-phone.lm.bin'))
    config.set_float('-lw', 2.0)
    config.set_float('-beam', 1e-20)
    config.set_float('-pbeam', 1e-20)

    # Decode streaming data.
    decoder = Decoder(config)

    decoder.start_utt()
    stream = open(audiofile, 'rb')
    while True:
      buf = stream.read(1024)
      if buf:
        decoder.process_raw(buf, False, False)
      else:
        break
    decoder.end_utt()

    # Output list of phonemes with start and end times
    phones = []
    for s in decoder.seg():
        print(s.start_frame, s.end_frame, s.word)
        phones.append((s.word, float(s.start_frame + s.end_frame) / 200.0))

    return phones

def create_phoneme_channel(channellist, theanim):
    global lastAudioFile

    if channellist is None or len(channellist) <= 0: return False
    # Read CSV file
    with open('plugins/phonemes.csv', 'r') as csvfile:
        # Get channel types from header
        firstline = csvfile.readline().strip()
        columns = firstline.split(',')
        if len(columns) <= 3: return False
        channeltypes = columns[3:]
        # Read positions of all phonemes for all channeltypes
        channelpositions = {}
        for channeltype in channeltypes:
            channelpositions[channeltype] = {}
        # Read rest of file
        line = csvfile.readline().strip()
        while len(line) > 0:
            columns = line.split(',')
            phone = columns[0]
            for indx in range(len(channeltypes)):
                channelpositions[channeltypes[indx]][phone] = int(columns[3+indx])
            line = csvfile.readline().strip()
    print(channelpositions)

    # Get name of audio file and channel type
    if lastAudioFile is None and theanim.newAudio is not None:
        lastAudioFile = theanim.newAudio.audiofile
    widget = UserPrompt(channeltypes, lastAudioFile)
    code = widget.exec_()
    print('Code:', code, 'Type:', widget.getType(), 'Audio File:', widget.getAudioFile())
    if code != QDialog.Accepted: return False

    # Run through sphinx
    phones = runSphinx(widget.getAudioFile())

    # Convert phonemes to positions and insert in channel(s)
    type = widget.getType()
    for channel in channellist:
        minval = channel.minLimit
        maxval = channel.maxLimit
        for phone in phones:
            if phone[0] in channelpositions[type]:
                phonevalue = float(channelpositions[type][phone[0]]) / 100.0
                value = (maxval - minval) * phonevalue + minval
                channel.add_knot(phone[1], value)
                print('Adding knot value:', value, 'at time:', phone[1], 'to channel:', channel.name, 'for phone:', phone[0])

    return True

channel_modifiers = [create_phoneme_channel]
channel_creators = []
channel_analyzers = []

if __name__ == "__main__":
    # Run some self tests
    if not create_phoneme_channel([5], 5):
        print('WHOOPS - create_phoneme_channel self_test failed')
