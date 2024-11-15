#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program phonemes.py
# Created by john
# Created Sat Apr 6 02:13:36 PM PDT 2024
#*********************************/

#/* Import block */
import os
import sys
import string

# Allow test code to find Animatronics module
if __name__ == "__main__": sys.path.append('..')
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

#/* Define block */
# Local Globals
lastAudioFile = None
verbosity = False
lastTagFlag = None


class UserPrompt(QDialog):
    def __init__(self, typelist, audiofile):
        super().__init__()

        self.title = 'Phoneme Channel Generator'
        widget = QWidget()
        layout = QFormLayout()
        self._nameedit = QLineEdit()
        self._nameedit.setText(audiofile)
        #layout.addRow(QLabel('Audio File:'), self._nameedit)
        #layout.addRow(QLabel(''), openbutton)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('Audio File:'))
        hlayout.addWidget(self._nameedit)
        openbutton = QPushButton()
        # Add nice icon to button
        pixmapi = getattr(QStyle, 'SP_DirOpenIcon')
        icon = self.style().standardIcon(pixmapi)
        openbutton.setIcon(icon)
        openbutton.clicked.connect(self._audioopen)
        openbutton.setToolTip('Select alternative audio file')
        hlayout.addWidget(openbutton)
        layout.addRow(hlayout)

        if typelist is not None and len(typelist) > 0:
            self.typeselect = QComboBox()
            self.typeselect.addItems(typelist)
            layout.addRow(QLabel('Move Type:'), self.typeselect)

        self.tagselect = QComboBox()
        self.tagselect.addItems(['None', 'Words', 'Phonemes'])
        layout.addRow(QLabel('Update Tags'), self.tagselect)
        if lastTagFlag is not None:
            self.tagselect.setCurrentText(lastTagFlag)

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

    def getTagFlag(self):
        global lastTagFlag
        lastTagFlag = self.tagselect.currentText()
        return lastTagFlag

    def _audioopen(self):
        fileName, _ = QFileDialog.getOpenFileName(self,"Select Audio File", "",
                            "Wave Audio Files (*.wav);;All Files (*)",
                            options=QFileDialog.DontUseNativeDialog)
        if fileName:
            self._nameedit.setText(fileName)

def runSphinxWords(audiofile, dict=None):
    # Create a decoder with certain model
    config = Config()
    if dict is not None:
        config.set_string('-dict', dict)

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

    # Output list of words with start and end times
    words = []
    for s in decoder.seg():
        if verbosity: print(s.start_frame, s.end_frame, s.word)
        theword = s.word
        # Remove silences that are contained in <> pairs
        if '<' not in theword and '>' not in theword:
            # Also remove trailing stresses in parens
            indx = theword.find('(')
            if indx > 0:
                theword = theword[0:indx]
            words.append((theword, float(s.start_frame) / 100.0, float(s.end_frame) / 100.0))

    return words

def runSphinx(audiofile, dict=None):
    # Create a decoder with certain model
    config = Config()
    config.set_string('-hmm', get_model_path('en-us/en-us'))
    config.set_string('-lm', None)  # Must remove language model from default config
    config.set_string('-allphone', get_model_path('en-us/en-us-phone.lm.bin'))
    config.set_float('-lw', 2.0)
    config.set_float('-beam', 1e-20)
    config.set_float('-pbeam', 1e-20)
    if dict is not None:
        config.set_string('-dict', dict)

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
        if verbosity: print(s.start_frame, s.end_frame, s.word)
        phones.append((s.word, float(s.start_frame + s.end_frame) / 200.0))

    # If we don't have a dictionary, this is as good as we can do
    if dict is None: return phones

    # Because the above seems to be not so good, we try something else
    # First get the words and timing
    words = runSphinxWords(audiofile, dict)
    # Now distribute phonemes in word evenly over the duration of the word
    phones = []
    dict = readLocalDictionary(dict)
    for word in words:
        if word[0] in dict:
            phonelist = dict[word[0]].split()[1:]
            if verbosity: print('Word:', word[0], 'Phonemes:', phonelist)
            # If the word is a single phoneme, it is a vowel and will be held for the word duration
            if len(phonelist) == 1: phonelist.append(phonelist[0])
            step = (word[2] - word[1]) / (len(phonelist) - 1)
            time = word[1]
            for phone in phonelist:
                phones.append((phone, time))
                time += step

    return phones

def readLocalDictionary(infile):
    thedict = {}
    with open(infile, 'r') as dict:
        wordline = dict.readline()
        while len(wordline) > 0:
            vals = wordline.split()
            thedict[vals[0]] = wordline
            wordline = dict.readline()
    return thedict

def createLocalDictionary(transcript=None):
    dictfile = None

    if transcript is not None:
        # Get list of all words in transcript without punctuation
        with open(transcript, 'r') as f:
            text = f.read()
            text = text.translate(str.maketrans('\n', ' ', string.punctuation))
            text = text.lower()
            tlist = text.split()
            # Remove duplicates
            tlist = list(set(tlist))
            # Read in the main dictionary
            maindict = {}
            with open(get_model_path('en-us/cmudict-en-us.dict'), 'r') as dict:
                wordline = dict.readline()
                while len(wordline) > 0:
                    vals = wordline.split()
                    maindict[vals[0]] = wordline
                    wordline = dict.readline()
            # Get those entries from main dictionary and copy to local dictionary
            flocal = open('temp.dict', 'w')
            for word in tlist:
                if word in maindict:
                    flocal.write(maindict[word])
            flocal.close()
            dictfile = 'temp.dict'

    return dictfile

def create_phoneme_channel(channellist, theanim, starttime=0.0, endtime=0.0):
    global lastAudioFile

    if channellist is None or len(channellist) <= 0: return False
    # Get path to executable
    try:
        sFile = os.path.abspath(sys.modules['__main__'].__file__)
    except:
        sFile = sys.executable
    sFile = os.path.dirname(sFile)

    # Read CSV file
    with open(os.path.join(sFile, 'plugins/phonemes.csv'), 'r') as csvfile:
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
    if verbosity: print(channelpositions)

    # Get name of audio file and channel type
    if lastAudioFile is None and theanim.newAudio is not None:
        lastAudioFile = theanim.newAudio.audiofile
    widget = UserPrompt(channeltypes, lastAudioFile)
    code = widget.exec_()
    if verbosity: print('Code:', code, 'Type:', widget.getType(), 'Audio File:', widget.getAudioFile())
    if code != QDialog.Accepted: return False

    audiofile = widget.getAudioFile()
    if not os.path.exists(audiofile): return False
    # Check for matching transcript for audio file
    dictfile = None
    transcript = audiofile[:-3] + 'txt'
    if os.path.exists(transcript):
        dictfile = createLocalDictionary(transcript)

    # Run through sphinx
    phones = runSphinx(widget.getAudioFile(), dict=dictfile)

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
                if verbosity: print('Adding knot value:', value, 'at time:', phone[1], 'to channel:', channel.name, 'for phone:', phone[0])

    if widget.getTagFlag() == 'Words':
        # Rerun sphinx just looking for word timing
        phones = runSphinxWords(widget.getAudioFile(), dict=dictfile)

    if widget.getTagFlag() != 'None':
        theanim.clearTags()
        for phone in phones:
            theanim.addTag(phone[0], phone[1])

    return True

external_callables = [create_phoneme_channel]

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose] -f/-file audio [-t/-text textfile]\n" % name);
    sys.stderr.write("Run tests with the phoneme plugin.\n");
    sys.stderr.write("    This package contains a couple of methods for processing audio files and\n");
    sys.stderr.write("producing channels to move body parts in sync with the phonemes of the speech.\n");
    sys.stderr.write("It is normally imported by Animator for this purpose.  This module also contains\n");
    sys.stderr.write("this main which can be used to test audio files and report on how the phonemes\n");
    sys.stderr.write("are generated.  It also validates the audio file to verify that it is of the\n");
    sys.stderr.write("correct format.\n");
    sys.stderr.write("\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("-f/-file audio    :name of audio file to test and process\n");
    sys.stderr.write("-t/-text textfile :name of transcription file to test and process\n");
    sys.stderr.write("\n\n");

#/* Main */
if __name__ == "__main__":

    audiofile = None
    transcript = None

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        elif sys.argv[i] == '-f' or sys.argv[i] == '-file':
            i += 1
            if i < len(sys.argv):
                audiofile = sys.argv[i]
        elif sys.argv[i] == '-t' or sys.argv[i] == '-text':
            i += 1
            if i < len(sys.argv):
                transcript = sys.argv[i]
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    dictfile = createLocalDictionary(transcript)

    if audiofile is not None:
        import wave
        okay = False
        # Attempt to process the audio file and print the text derived from it
        with wave.open(audiofile, "rb") as audio:
            if audio.getframerate() < 13600:
                sys.stderr.write("Specified audio file must be sampled at a minimum of 13600 Hz for pocketsphinx.\n")
            else:
                okay = True
                decoder = Decoder(samprate=audio.getframerate())
                decoder.start_utt()
                decoder.process_raw(audio.getfp().read(), full_utt=True)
                decoder.end_utt()
                print('Sphinx raw speech recognition results:')
                print(decoder.hyp().hypstr)
                print()

            if audio.getframerate() != 16000:
                sys.stderr.write("Error: Specified audio file not sampled at 16000 Hz as required for phonemes\n")
                okay = False
            if audio.getsampwidth() != 2:
                sys.stderr.write("Error: Specified audio file not sampled at 16 bits (2 bytes) as required for phonemes\n")
                okay = False
            if audio.getnchannels() != 1:
                sys.stderr.write("Error: Specified audio file not mono as required for phonemes\n")
                okay = False

        if okay:
            phones = runSphinx(audiofile, dict=dictfile)
            if verbosity:
                print(phones)
            words = runSphinxWords(audiofile, dict=dictfile)
            print('Sphinx adjusted speech recognition results:')
            for word in words:
                sys.stdout.write(word[0] + ' ')
            sys.stdout.write('\n')

    else:
        pass




