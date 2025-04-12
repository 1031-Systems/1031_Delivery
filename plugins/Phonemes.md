<!-- john Wed Aug  2 17:01:44 PDT 2024  -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->

<a name="top">
&nbsp;
</a>

# Phonemes Plugin

The Phonemes plugin is a module for aiding in the creation of control
channels within Hauntimator that are synchronized with a voice audio.
It utilizes pocketsphinx, a voice recognition tool from Carnegie
Mellon University, for analyzing speech and producing a phoneme
string that resembles the vocal track.

## Usage

Using the Phonemes plugin requires some work outside of Hauntimator
prior to generating the control channels within Hauntimator.  The
underlying pocketsphinx process requires the audio file to be
analyzed to be voice-only (no music, single speaker) and be recorded
at 16kHz, 16 bits per sample, in mono.  Preparing this file must be
done outside of Hauntimator prior to running the plugin.

Once the audio file is prepared, the user selects the control channel(s)
to be populated, then runs the plugin.  This prompts the user for
the audio file, defaulting to the audio file for the animation, and
then runs the plugin.  Pocketsphinx generates a stream of phonemes with
start and end times.  The times are averaged to find the midpoint and
the phonemes are translated into channel values using a table.  Then
the channel values are entered into the channel.

## Preparing the Audio

There are two primary types of audio situations.  The first is an
existing audio file containing a single voice with no background music
or sound that needs to be converted to the appropriate format.  The
second is an audio file containing background music or sound, singing,
etc. that needs to be rerecorded without the background, preferably
directly into the appropriate format.

Linux and MacOS users may use ffmpeg to convert audio files to the
appropriate format as such:

```

ffmpeg -i infile -acodec pcm_s16le -ar 16000 -af "pan=mono|FC=FL" outfile.wav
```
This converts infile to outfile.wav.  The "-acodec pcm_s16le" option
converts to PCM (.wav) with 16 bit samples.  The "-ar 16000" option
converts to 16000 samples per second (16kHz).  The -af "pan=mono|FC=FL"
says to use the Left channel only.  Change FL to FR to use the Right
channel only.  This command will produce a file that can be processed
by pocketsphinx to produce a stream of phonemes.

The second likely case is converting a music audio with singing or
something similar to a voice-only recording.  The simplest method for
doing this is to play the audio into a headset and speak the words
into a microphone synced with the audio and record a new file.  On
linux, and maybe MacOS, the following command can do this:

```

aplay infile & ; arecord -f S16_LE -r 16 outfile.wav
```
The aplay command plays the existing audio in the background while the
arecord command records the user's voice.  The "-f S16_LE" causes the
recording to be PCM (.wav) 16-bit while the "-r 16" causes 16kHz
recording.  The output file will be suitable for pocketsphinx to 
process.  Some practice may be required to get the recorded voice to
be synced well with the original audio.

### Evaluating the Audio File

The Phonemes plugin has a mode for evaluating the audio file for
suitability and accuracy.  Run the audio file through the Phonemes.py
program to provide feedback on any problems as such:

```

plugins/Phonemes.py -f outfile.wav
```
This will evaluate the recording parameters to make sure that you have everything
set up correctly.  It will also attempt to run the audio file through
pocketsphinx and display the text it finds.
If the text is a poor match for what is in the audio, you can try
rerecording it while speaking more clearly or something.  I am not sure how
to really make sure everything works great.  Sphinx used to have a way to
provide a transcript of what was said so it only had to line things up.
This made it more accurate but I have not found that method in pocketsphinx.

## Preparing the Conversion File

The Phonemes plugin uses a conversion file to convert from the phoneme
name to a control channel numeric value.  This is a comma-separated value
file that may created and edited with a text editor or a spreadsheet
program.  A simple example file is provided with the system and is in
the plugins/phonemes.csv file.

In simple terms, the file contains motion precentages for each phoneme
for each type of channel.  For example, when saying "mama", the first
"m" phoneme will have the jaw closed at 0%.  Then the "a" will have the
jaw fairly wide open at 100%.  Then the jaw closes back to 0% at the
next "m" and back to 100% for the last "a".  The conversion file must
include the percentages for all possible phonemes that pocketsphinx
can identify.  Fortunately, this is only 40, including silence, so it is
not too hard to populate the table.

### File Format

Example file
```
Phoneme,Example,Translation,Jaw
AA,odd,"AA D",100
AE,at,"AE T",80
AH,hut,"HH AH T",50
AO,ought,"AO T",60
AW,cow,"K AW",30
AY,hide,"HH AY D",80
B,be,"B IY",0
CH,cheese,"CH IY Z",0
D,dee,"D IY",10
DH,thee,"DH IY",15
EH,Ed,"EH D",55
ER,hurt,"HH ER T",10
EY,ate,"EY T",55
F,fee,"F IY",0
G,green,"G R IY N",30
HH,he,"HH IY",20
IH,it,"IH T",25
IY,eat,"IY T",20
JH,gee,"JH IY",0
K,key,"K IY",15
L,lee,"L IY",15
M,me,"M IY",0
N,knee,"N IY",25
NG,ping,"P IH NG",0
OW,oat,"OW T",10
OY,toy,"T OY",20
P,pee,"P IY",0
R,read,"R IY D",10
S,sea,"S IY",10
SH,she,"SH IY",10
T,tea,"T IY",15
TH,theta,"TH EY T AH",45
UH,hood,"HH UH D",30
UW,two,"T UW",20
V,vee,"V IY",0
W,we,"W IY",10
Y,yield,"Y IY L D",20
Z,zee,"Z IY",0
ZH,seizure,"S IY ZH ER",0
SIL,silence,"",40
```

The conversion file format is fairly straightforward.  It contains three
mandatory columns and one mandatory row.  The first row contains the
column names with the first three being Phoneme, Example,and Translation.
The remaining column names identify the type of control channels to be
generated, Jaw in the example file.

The first column contains the text string that pocketsphinx uses to
identify each of the 40 different phonemes.  To help the user know what
each phoneme really sounds like, the second column contains a word that
contains the phoneme and the third column lists all the phonemes in the
word.

The remaining columns identify different types of channels that might be
linked to phonemes.  A simple usage might be for a talking skull.  In
such a case, only the jaw moves with the voice.  However, more sophisticated
animatronics might have lips and cheeks that also move and these may be
added to the conversion file and used to control the facial features.

The entries under each of the remaining channels is an integer percentage
that indicates what fraction of the entire range of motion the feature
should be moved to.  Looking at the example file, the "AA" sound in odd
indicates that the jaw should be at its maximum open value while the "B"
sound in be should have the jaw all the way closed.  Note that this is
all subject to personal preference and experimentation and may vary for
different sets of facial features.

If you think about it, when speaking rapidly, the jaw moves less than
usual and while speaking slowly it tends to move more than usual.  Do not
change the conversion file for this variation.  The appropriate way to
actually control this is discussed in the next section.

## Preparing the Control Channel

The control channel to be populated from the phonemes should start out
empty but with the appropriate type of servo selected and its minimum
and maximum values set.  Then the user should change the minimum and maximum
values for the channel to match the minimum (e.g. mouth closed for "B") and
maximum (e.g. mouth open for "AA") such that the jaw moves over the
appropriate range for the audio.  Typically, the jaw fully open and fully
closed positions will not correspond to the limits of the servo.  Thus, the
user should reset the limits to what the mouth will actually do.  Then,
adjustments can be made to allow for other variations.
If speaking rapidly, the mouth open
position should be closer to the mouth closed position.  If slowly, the
mouth open position can be farther from the mouth closed position.

Once the channel limits have been set appropriately, the plugin can be run.

## Running the Plugin

Once the proper audio file has been generated, Hauntimator can run the
plugin to populate the control channel(s).  The user ctrl-left clicks on
the channel or channels to be populated to select them.  Next, click on
Plugins->Phonemes->create_phoneme_channel.  This will bring up a dialog
asking the user to select the audio file to process and what type of
control channel to generate (which column in the conversion file).  The
audio file will default to the main audio file of the animation so do not
forget to select the one that has been processed to the appropriate format
as described above.

In addition to the audio file and channel type selections, the user may also 
choose to populate the Tags pane with the words or phonemes recognized by
the plugin.  If the user selects None, the Tags pane will be unchanged.  If
the user selects Words, the Tags pane will be cleared and repopulated with
a tag for each individual word in the audio and located at the time the word
starts in the audio.  If Phonemes is selected,the Tags pane will be cleared
and repopulated with a tag for each individual phoneme located at the time
of the center or maximum of the phoneme.  If the user is not familiar with
the phonemes, it is likely best to use Words.  The user may then make
adjustments to the channel(s) where the recognized words are incorrect.

Once the selections have been made, select Run and the selected channels will be
populated.  Install the control file on the controller and see if it works.

To improve the speech recognition results, the user can provide a dictionary,
language model, and transcript of the speech to be processed.  This is not
100% effective so the plugin runs a diff on the recognized text and the
transcript and replaces incorrect words.  This can throw off the timing a
bit but guarantees the correct phonemes are in about the correct place.  The
implementation of this requires that the transcript be exactly what is trying
to be recognized.  Thus, if a subwindow of the speech is being processed, the
transcript must be edited to contain only the expected text.  Since this can
be time-consuming, it is generally easier to run the plugin on the entire
audio.

Transcripts can often be found online for various songs and speeches.  The
[Sphinx website](http://www.speech.cs.cmu.edu/tools/lmtool-new.html)
has tools for generating language models and dictionaries
from a transcript.  Dictionaries may even be generated automatically for a 
transcript without the language model or using the website.

The Sphinx website has more details on using pocketsphinx.  Other, perhaps AI-based,
tools are out there for converting speech to text and may be applied here
but pocketsphinx provides timing data that is needed.  If users find this useful
and want more information, I can probably update this with additional stuff.
I know I had more notes on how I did all this but can't find it now, dang it!

***

Copyright 2024 John R. Wright, William R. Douglas - 1031_Systems
