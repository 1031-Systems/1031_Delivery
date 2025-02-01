<!-- john Fri Jun 27 07:35:16 PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->
 

<a name="top">
&nbsp;
</a>

# Help for Hauntimator.py

1.0.0(b)

Hauntimator.py, as you might surmise, is a Python program.  Its general purpose
is to synchronize control signals for animatronics and lighting to each other
and to an audio track.  Hauntimator provides the means for visualizing and
listening to an audio track and then creating and editing control channels
for individual mechanisms in sync with the audio.  Control values are then
output to the hardware controller to operate the mechanisms.

+ A. [Process](#process)
+ B. [Overview](#overview)
+ C. [Menus](#menus)
+ D. [Audio Tracks](#audio-tracks)
+ E. [Channel Panes](#channel-panes)
+ F. [File Types and Extensions](#file-extensions)
+ G. [Specialized Tools](#specialized-tools)
+ H. [Requirements](#requirements)
+ I. [Known Issues and Bugs](#bugs)

<a name="process">
&nbsp;
</a>

## Process

The Hauntimator process is similar to that used by other tools that perform
similar functions.  Generally it is preferred to synchronize mouth, face,
and head movements to audio containing voices, then proceed to synchronize
other movements, lighting controls,  and other activities to the audio.

1. Using an audio editor, create sound files for each character’s dialog, and a separate mix file which contains all of the characters, effects, and background music.
2. Start Hauntimator.
3. Load an audio file to work with
4. Generate the mouth control channel(s).
5. Generate the head motion control channels.
6. Generate the remaining servo and motor channels.
7. Program the lighting channels.
8. Output the control information for use by the hardware controller.

<a name="overview">
&nbsp;
</a>

## Overview

The Hauntimator GUI consists of, from top to bottom, a menubar, audio channel displays,
and control channel displays called panes.  When the user loads an audio file into Hauntimator
it is displayed using one pane for mono or two panes for left and right stereo.  It is not
necessary for there to be an audio file in use and none will be displayed in that case.
However, without an audio file playback will not function.

![Image of User Interface](images/image1.png)

The Hauntimator User Interface

The user then begins to create control channels as desired.  Each channel is named and
will usually be accompanied by metadata including minimum and maximum limits, hardware
port number, control type, and channel type.  These may be specified at creation time or
set or updated later.

Next, the user begins populating one or more channels, either manually or using a helper
tool, with knots representing the state of the controlled mechanism at a specific time.
The user then plays the audio and watches the channel pane to determine how well the
controls follow the audio.  Individual knots may be dragged around to improve the quality
of the synchronization.

Each control channel supports one of two types of hardware controls, either a digital
on/off control typically used for lighting or a numeric value that may be used for servo
positioning, motor speed, brightness, or other types of continuous control.  Hauntimator
does not distinguish the purpose of the channel other than by name so a numeric channel
may be used to control servos via PWM, motors via CAN, and other mechanisms based
entirely on the controller hardware.  However, for better performance of the software
within the controller hardware, Hauntimator sends integer values for all channels.  These
are either 0/1 for digital channels or 0-65535 (user-controllable) for servo channels.

For the numeric channels, Hauntimator supports different types of interpolation between
knots.  The simplest is Step that makes a step transition from one value to the next,
thus holding a set value until the next knot time is reached.  The most common type is
Linear that follows a straight line from knot to knot.  Another
common type is Spline that applies a smoothing interpolation between points for
possibly better appearance.  The example image above shows the appearance of a Linear
channel and a Spline channel.

As the user populates channels, completed channels may be hidden so focus can be on the
current channel under construction and any other channels that may be relevant or helpful.
Channels are generally inserted and displayed from top to bottom but new channels may be
inserted anywhere and the channels may be reordered as desired.

The length of the audio generally determines the length of the animation.  (Although it is
possible to circumvent this limitation, most of this discussion will assume such.)  In
general, particularly once the user is working on the full audio, it will be challenging
to distinguish the synchronization of the knots with the audio.  Thus, the user will
want to zoom in to a smaller subrange of the overall duration to construct, visualize,
and modify the control channels.  Users may do this manually by clicking and dragging
within an audio pane, by setting limits by current playback position within the audio,
or by selecting a range from a markdown entry.  [See here for zoom details.](#zooming)

Once the user has completed some or all of the channels, they may output the control
information to a hardware controller.  This may be done by exporting a CSV file that
contains values for all the channels at a specific timestep (typically 20msec or 50Hz
for PWM servo control).  This file is transferred to the controller via flash drive
or other method and the controller processes it.  Note that channels that do not have
assigned port numbers will not be written to the CSV file.

For larger systems with more control channels, it may be helpful to preprocess the
control file to a binary format for faster updates on the controller.  This may be
done within Hauntimator or in the controller when the CSV file is installed.

Hauntimator is intended to be agnostic to the specific hardware controller the user
chooses.  It has been tested with a Raspberry Pi Pico and a Pico clone running
MicroPython but not with any other devices.  Details of how Hauntimator communicates with
the controller is bundled within a commlib.py file specific to the controller and
compatible with the python code running on the controller.  For users with other
types of controllers, they can use the Pico-specific examples included with Hauntimator
to customize the interface for other systems.  Information on all that may be found
elsewhere.

<a name="menus">
&nbsp;
</a>

## Menus

Hauntimator has a number of dropdown menus available on the menubar at the top
of the Hauntimator main window or at the top of the screen in MacOS.  They are:

1. [File](#file) - to save and load your work
2. [Edit](#editmenu) - to add and delete channels or edit metadata
3. [View](#view) - to fit data to the screen or hide channels currently unneeded
4. [Channels](#channels) - to select, copy, and paste channels
5. [Tags](#tags) - for Tag-related activities
6. [Plugins](#plugins) - to run external tools
7. [Help](#help) - to find out more

<a name="file">
&nbsp;
</a>

### File Menu

![File Menu](images/filemenu.png)

The File menu contains the following options:

+ New Animation - Discard current animation and start from scratch
+ Open Anim File - Open and Load an existing animation file
+ Open Audio file - Open and attach audio file to the current animation (.wav only)
+ Merge Anim File - Open an existing animation and merge new channels into current one
+ Append Anim File - Open an existing animation and append common channels to current one
+ Save Anim File - Save the current animation to the file it was loaded from
+ Save As - Save the current animation under a new filename
+ Export - Export to an alternative file format or send to controller
+ Quit - Duh!

Hauntimator tries to be careful about quitting without saving or overwriting files.

The Merge and Append options are intended to support multiple people or sessions working on
the same animation.  Merge is used to merge animation files that do not share channels, e.g.
different figures in a multi-figure display.  An individual can work on a single figure and
the results can be merged into a single animation for the entire display.  Channels whose names
appear in both files will not be merged.  They are ignored and a warning will appear.

The Append option is intended for animations that are split temporally rather than by
channel.  Multiple persons can focus on different ranges of time while building the same
channels.  These can then be appended to form a single animation for the entire display.
Appended channels must appear in both animations and other channels will be ignored and
a warning presented.  Note that the order of the append is irrelevant.  Prior, successor,
or overlapping time ranges can be appended and they are inserted into the existing channel
at their designated time.

The Export option is generally used to upload the control file to the controller.
To accomplish, the file is written as a CSV (comma-separated values) file and then
copied to the controller.  If the copy is successful, the local CSV file is
deleted.  The Export to CSV option will write a file for the user to peruse that
should be identical to the one uploaded.  The CSV file is sampled at the rate
specified in the Preferences, generally 50Hz.

Note that when the controller is expecting binary control files, it will perform the CSV
to binary conversion on the controller.  This may be very time consuming.  An alternative
is for Hauntimator to use the controller-specific commlib code to convert the file to the
binary format and then write it to a local SD card.  Then the SD card may be transferred
to the controller.

<a name="editmenu">
&nbsp;
</a>

### Edit Menu

![Edit Menu](images/editmenu.png)

The Edit menu contains the following options:

+ Undo - Undo the last editing action
+ Redo - Redo the last editing action that was undone
+ Cut - Copy selected channel(s) to the Clipboard
+ Copy - Copy selected channel(s) to the Clipboard
+ Paste - Paste the clipboard into a single selected channel(s) or insert at first selected channel
+ Insert - Insert the clipboard at first selected channel
+ Edit Metadata - Edit some numeric data for the animation
+ Edit Servo Data - Edit table of available known servo types and associated data
+ Edit Preferences - Edit the preferences settings for Hauntimator

Undo and Redo generally behave as expected with some caveats.  As work progresses, Hauntimator
attempts to save both the state of the animation itself as well as ancillary information such as
which points and channels are selected and what time range is displayed.  This is to attempt to
make it easy to undo an action and then perform an alternative to that action.  However, this
results in sometimes saving a state that is merely a selection change rather than an actual
edit.  Also, when using the arrow keys to shift points, each shift is a separate state save.
This may result in many states being saved that may have to be undone.  Hopefully, this will
not become too annoying.

Cut/Copy/Paste/Insert are not quite as simple as they might seem.  In general they do what you
might expect.  However, what you Cut or Copy depends on what is selected and how you can Paste
or Insert that data depends on what is on the clipboard.  Specifically, the user can Copy either
one or more entire channels or selected points within a single channel.  The user may Cut
one or more entire channels but not points within a channel.  Users may Paste or Insert a set
of points copied from a single channel into one or more selected channels as new points within
those channels.  Users may Paste a single channel into one or more selected channels, replacing
all data within those channels except name and port number.  When Pasting, the user will be given
choice between Pasting or Inserting the copied channel.  If Insert At is selected, the channel
will be inserted at the selected channel with a modified name and the port number cleared if
they are already present in the animation.  If multiple channels have been Cut or Copied, they
may only be inserted at the current selection.  Note that Insert always Inserts and does not
give the option of overwriting the current content of a channel.  Otherwise, it behaves like
Paste.

A note on selection.  To select a channel, the user clicks on the area to the left of the main
data display window in a manner similar to Excel when selecting an entire row.  The user may
use the Control key to toggle selection and may use Shift to select a range of channels.
Clicking within the blue data display does not provide any channel selection capability.  When
a channel is explicitly selected in this manner, the background turns green to identify its
selection status.  Explicitly selected channels take priority in Cut, Copy, Paste, and Insert
operations.  In addition, for quick operation, there is a concept of implicit selection.  If
no channels are explicitly selected, then a channel may be implicitly selected by hovering the
cursor anywhere in its display area.

If individual knots within an implicitly selected channel have been selected, those and only those
points will be copied to the clipboard (they may not be Cut but the user may delete them with the
Del key).  Then those individual points may be Pasted/Inserted into either all explicitly
selected channels or an implicitly selected channel.  Remember that if any channels are explicitly
selected then no channels are implicitly selected.

To select points within a channel, click the left mouse button and drag the mouse left or right,
while continuing to hold down the left mouse button, to select all points within the dragged range.  The
points will turn red to signify their status as being selected.  Points may be similarly selected
within other channels as well and points will remain selected until a single left mouse click 
within the channel pane.  Selected points within a channel may be dragged en masse by left-clicking
on any of the selected points and then dragging it left/right/up/down.  If the clicked point is
within a Digital channel, it can only be dragged left/right.

Power users will note that if the selected, dragged point is within an explicitly selected
channel, then all selected points within all explicitly selected channels will be similarly dragged.
Since the most common use of this feature will be better alignment of activities with audio, left/right
dragging will be most common.  Limiting the mouse movement to left/right only is challenging so two
tricks come into play.  The simplest is to use the left/right arrows to move the selected points
left and right.  Clicking the arrow key once moves the selected points 0.1 seconds.  Holding down
the shift key multiplies by 10 so the movement is 1.0 seconds.  Holding down the control key
divides by 10 and moves 0.01 seconds.  Unfortunately, each arrow click becomes an undoable action
so many undoes may be necessary to undo the motion.  A trick is to create a Digital channel with a
single point in it that is selected and the channel is selected along with any other channels the
user wishes to drag.  Then dragging the single point within the Digital channel allows flexible
dragging limited to left/right that can be undone with a single Undo.

![Animation Metadata Popup](images/animmetadata.png)

Each animation comes with some simple metadata that includes the start time (usually 0.0),
the end time (usually unspecified), and the sample rate (usually 50Hz).  Usually, the
animation playback will begin at time 0, which is when the audio will begin to play.
The metadata can be used to change some behaviors but has not been well-tested so
caveat emptor.  This is discussed in more detail [here](#timeranges).

Hauntimator comes with a list of known servo types typically stored in a file named servotypes.
Each entry specifies the range of motion of that type of servo and its duty cycles.  This
information is used to limit the control outputs appropriately.  New servo types may be
added to this list (and automagically stored) as desired and existing servos may have
their data changed.  In general, only the min and max duty cycles, as a fraction of the
period, are used to set initial values for the limits of the PWM duty cycles for controlling
the servo.  The user will often change them to fit the range of motion of the specific
mechanism the servo operates.

The Preferences specify general information that Hauntimator uses.  Some if this is related
to the hardware being controlled, some control display functionality, and some relates
to files and communication.  The individual preferences are:

+ MaxDigitalChannels - The maximum number of digital channels supported by the hardware.  If the user has installed some number of 74HC595N chips in their hardware, there will be 8 available digital channels per chip.  The port numbers for digital channels begin at 0 and count up.  Additional ports may be assigned to direct GPIO outputs if any are available.
+ MaxServoChannels - The maximum number of servo channels supported by the hardware.  If
 the user has installed some number of PCA9685 boards in their hardware, there will be 16 available servos per board.  The port numbers for servo channels begin at 0 and count up.  Additional ports may be assigned to direct GPIO outputs if any are available.
+ ServoDefaultMinimum - If the user has installed PCA9685 boards in their hardware, they expect values in the range 0 to 4095 for servo control.  Other boards may use other values.  GPIO pins on a Pico assume that servos take a value between 0 and 65535.  Hauntimator treats all servos the same and assumes that the controller software will shift the values to the appropriate range.
+ ServoDefaultMaximum - If the user has installed PCA9685 boards in their hardware, they expect values in the range 0 to 4095 for servo control.  Other boards may use other values.  GPIO pins on a Pico assume that servos take a value between 0 and 65535.  Hauntimator treats all servos the same and assumes that the controller software will shift the values to the appropriate range.  Thus, the typical value here is 65535 and the controller shifts that to a range of 0-4095 prior to entering it into the PCA9685.
+ AutoSave - Controls saving of the animation every time an edit is made.  The saved copy of the animation is stored in a file with the same name as the animation with ".autosave" appended or in a file named "unnamedfile.anim.autosave" if the animation has never been named.
+ ShowTips - Controls the use of popup tool tips within Hauntimator.  Beginning users may find the popup tips helpful while an experienced user may find them bothersome.  Some go away automatically so hopefully they will not prove to be obnoxious.
+ ServoDataFile - The name of the file containing known servo types and their associated information.  The user may rename this file or move it so the preference allows that.  The values in the servo file are used to set initial limits on the channel values.  These are based on the ServoDefaultMaximum and ServoDefaultMinimum and the duty cycle of the servo from the file.  These are NOT used to distinguish servos on GPIO pins from servos on PCA9685 boards.  That is done within the controller.
+ UploadPath - The name of the directory to upload audio and control files to as it is used in the controller software.  The Pico software that accompanies the Hauntimator and is run on the Pico looks for a particular file and this must match that.  This will typically be on the SD card and look like "/sd/anims" to match expectations in the controller software.  If the controller software is edited, this can be changed to match.  Note that this is irrelevant if writing files locally to an SD card to be transferred later to the controller.
+ TTYPortRoot - This is most of the name of the communications port to use to talk to the controller when it is plugged into the USB port on the computer that Hauntimator runs on.  Under linux, this is typically /dev/ttyACM0 but may also be /dev/ttyACM1, 2, ... so the TTYPortRoot is set to /dev/ttyACM.  On a Mac it is more like /dev/tty00bb10 so the TTYPortRoot is set to /dev/tty00bb1.  Under Windows it is something I don't care about.  Note that this is irrelevant if writing files locally to an SD card to be transferred later to the controller and otherwise not using Hauntimator to talk directly to the controller.

<a name="view">
&nbsp;
</a>

### View Menu

![View Menu](images/viewmenu.png)

Hauntimator is designed to support a large number of digital and servo channels over a long
range of time.  Typically, however, the user will work on a small number of channels
over a short span of time, then move to the next section to focus on.  The View menu
is designed to aid in this process.  The View menu contains the following options:

+ Fit to All Data - Fit all audio and channel data to the current window width.  This essentially undoes all zooming.
+ Fit to Audio - Fit the audio to the current window width, hiding any part of the channel data outside the timespan of the audio.
+ Fit to Time Range - Fit the full time range specified in the animation metadata to the window.
+ Set Time Range - Bring up dialog to specify exact visible range desired.
+ Show All Channels - Make all channels visible within the window.  This may make the channel panes microscopically small.
+ Select Viewed Channels - Brings up a selection widget for selecting channels to be visible or hidden.
+ Sort Channels - Sorts channels forward or reverse by name or port number and redisplays them.
+ Show Audio - Controls the display of audio channels.
+ Audio Amplitude - Controls display of audio as amplitude rather than waveform.
+ Toggle Playback Controls - Reveals or hides Stop/Play/Rewind controls for playback.

<a name="zooming">
&nbsp;
</a>

The View menu mostly unzooms the display.  To zoom in to a particular time range, there are
several methods available.  The fastest, wildest, least specific method is to click and
hold the ctrl-left mouse button within the audio pane (either if stereo) and drag.  If the 
cursor is dragged up or down, the entire display zooms in or out around where the user
clicked.  If the cursor is dragged left or right, the entire display pans left and right.
The user may quickly select a reasonable time range upon which to work.

A second method for selecting a smaller time range is to reveal the playback controls
and use Set Left and Set Right buttons.  The user can hit Play and at the desired start
time hit Set Left.  This will immediately set the left edge of the displayed time range
to the playback time when Set Left was clicked.  Set Right does the same thing to the
right edge of the displayed time range.  The user may stop playback before hitting Set
Left or Set Right.  Note that the user may left click within the Audio pane and drag the
green bar to the desired start or end time and them click Set Left or Set Right.

A third method is supported by tags within the animation.  Clicking the left mouse
button on a tag within the tag pane while holding down the Ctrl key will zoom the
display to the duration of the tag.  See the [Tag Menu](#tags) for more details
on the use of tags.

A fourth method is to select View->Set Time Range and enter specific values for the
desired time range to be displayed.

<a name="timeranges">
&nbsp;
</a>

A note on time ranges might be appropriate here.  The time range for an animation comes from
any of several sources and is closely coupled with the hardware controller and its embedded
software.  Generally, the controller will play an animation until both its audio tracks and
its control file have completed playing.  If there are seven seconds of audio and ten
seconds of animation control, it will play for ten seconds.  If there are seven seconds of
audio and five seconds of animation control, it will play for seven seconds.  Thus, the
playback duration is set by the longer of the audio or the CSV file containing the control
values.

Time range within Hauntimator generally refers to the length of the control data in the CSV
file that Hauntimator will export to the controller.  If the user does nothing special, this
will be from time 0.0 to the time of the last control point in any of the control channels.
Each animation starts at time 0.0 in all cases.  The user cannot override the start time for
the animation.  However, the user may override the end time.  In the metadata for the animation,
there is an editable field containing the End Time for the animation and the user may set this
as desired to any value greater than 0.0.  Once the user does this, Hauntimator will output a
CSV control file beginning at time 0.0 and going to the end time set by the user regardless
of the range of the control data.  The "Fit to Time Range" menu item will fit the specified
time range to the current window.  The animation metadata is accessed from the [Edit menu](#editmenu).

The user may undo setting the end time via the standard ctrl-Z mechanism or, if too late for
that, by entering a negative number for the end time and saving the metadata.

Playback within Hauntimator is constrained by the time range displayed.  Playback will commence
at the left edge of the displayed audio pane and continue to the right unless stopped by the user.
When playback reaches the right edge of the display, it automatically rewinds to the beginning
of the displayed range.  However, if the left edge of the display is a time prior to the start
of the audio, playback will jump to the start of the audio and proceed from there.

![Playback Controls](images/playback_controls.png)

As mentioned above, the user may set the playback range by placing the green timebar at the
desired start or end range and then click Set Left or Set Right.  The Play/Pause and Rewind buttons
are probably obvious in function.  A Speed select is available to better assess proper alignment
of behaviors and outputs.  To support this, the Live checkbox is available.  If the Live box is
checked, then any explicitly selected (green background) channels will be output directly to the controller.
Note that this can be very slow so it cannot play back motions very fast and smoothly.  It is intended
for visual correlation.  WARNING - Using this live playback may damage your mechanisms if it is not
set up properly and the initial conditions not set properly.  I wouldn't use it for anything other
than lighting controls.

<a name="channels">
&nbsp;
</a>

### Channels Menu

![Channels Menu](images/channelmenu.png)

The Channels menu is used for operations on channels.  The options are:

+ Select All - Select all channels
+ Deselect All - Deselect all channels
+ New Numeric Channel - Add an empty servo channel to the animation
+ New Digital Channel - Add an empty on/off channel to the animation
+ Delete Channels - Bring up a channel selector to select and delete multiple channels
+ Amplitudize - Fill all selected channels with data points that follow the amplitude of the audio
+ Shift - Shift data points in selected data channels in time
+ Clear - Deleta all knots in selected channels
+ Delete - Delete all selected channels after confirmation

New channels are created and inserted into the display using Ctrl-E for numeric, PWM-type channels
and Ctrl-D for Digital channels.  These pop up a metadata widget so the user may specify initial
values for the metadata, including name, port number, limits, interpolation, etc.  Channel name
validation is performed and existing channel names cannot be reused.  Port number dropdowns do
not contain port numbers that have already been used.

New channels are generally appended to the bottom of the display.  However, if a channel is explicitly
selected, new channels will be inserted at that position, pushing the selected channel and others
down the display.

The Amplitudize function fills the channel with data points based on the amplitude of the audio signal.
By default, it only fills the visible part of the channel but the user may change that as well as the
sampling rate of the new data points.  The dialog for the Amplitudize function also allows a cutoff value
to be specified.  For Digital channels, any value below the cutoff results in a zero digital value while
any value above the cutoff results in a one digital value.

The Shift function is not yet implemented.

The Delete function requests confirmation prior to deleting.  This is because it is difficult but
possible to select and then delete a channel that is hidden such that the user is not immediately
aware that a channel was deleted.  Of course the delete may be undone.  Hauntimator attempts to
deselect any channel that is hidden so you should not have any problems with weird changes happening
to hidden channels.

<a name="tags">
&nbsp;
</a>

### Tags Menu

![Tags Menu](images/tagmenu.png)

Tags are text labels for key points in the animation.  They may be simple strings like "A", "B", "C",
or more descriptive, or represent the dialogue in the audio.  There are multiple ways to add tags to
the animation and some helpful uses for them.  The Tags menu contains the following options:

+ Insert Tag - Insert a tag at the current playback time (designated by the green bar)
+ Tag Selector - Brings up a widget for selecting a tag
+ Import Script - Reads a script file and creates tags
+ Toggle Tag Pane - Toggle visibility of the Tags pane
+ Clear All Tags - Delete all tags and clear the Tags pane

The Insert Tag (ctrl-T) inserts a tag at the current playback time unless a tag is already located at
that time.  If the tag may be inserted, a popup prompts for the text for the tag.  Tags may be inserted
at any time by clicking the left mouse button while holding down the shift key anywhere within the Tags
pane.  Again a popup prompts for the text for the tag unless the selected time exactly matches that of
another tag.

If the cursor is on the bar designating a tag in the Tags pane, the ctrl-left click will select that tag
and zoom the display to the time range of that tag to the next tag rather than inserting an additional
tag.

The Tag selector popup provides a scrollable list of all the tags in the animation with their times.
Clicking on any tag zooms to that tag.

Tags may be deleted by left-clicking on the bar designating the tag in the Tags pane while holding down
the shift key.  This is cumbersome if you want to delete many but is the only method available now.

Tags may be shifted in time by left-clicking on the bar designating the tag in the Tags pane and sliding
left or right.  Currently, only one tag may be shifted at a time.

The Import Script function provides the capability of importing a script file containing the dialogue
contained in the audio.  Each line in the script file becomes an individual tag with the line of text as
the tag's text.  The tags are spaced by a simple algorithm based on the number of characters so as to
maybe approximately align with the spoken dialogue but many shifts are generally required for good
alignment.  

The Phonemes plugin also offers a way to populate the Tags pane.  See the plugin help for more details.

<a name="plugins">
&nbsp;
</a>

### Plugins Menu

![Plugins Menu](images/pluginmenu.png)

The Plugins menu provides access to external functions implemented in Python and installed in the
plugins directory.  Each entry in the Plugins menu refers to one Python file in the plugins directory
and the dropdown menus then access the individual functions provided.  There is one standard set of
plugins provided in the Stock entry.  This implements some useful tools that might be considered
standard to Hauntimator.  There is also a Phonemes plugin provided that is activated if the
pocketsphinx module is installed.  Users may develop or download other plugins at their
convenience.  If Hauntimator does not find a plugins directory to does notfind any suitable Python
files within the plugins directory, the Plugins menu will not appear.

Generally, the Stock plugins operate on the currently selected knots and channels.  However, plugins
have access to pretty much everything in the animation and can mess things up willy-nilly.
Hauntimator does provide Undo capability for plugin actions.

<a name="help">
&nbsp;
</a>

### Help Menu

The Help menu provides access to this helpful information as well as some other helpful information.
In addition, it provides some visibility into the content of the clipboard and the overall animation as
expressed in the XML used for storing the animation information.  This is mostly for my personal
debugging purposes but is available for all to peruse.

If the developer or user has provided help files for the plugins (plugins/plugin_name.md), they will
be automagically added to the Help menu.

<a name="audio-tracks">
&nbsp;
</a>

## Audio Tracks

Currently Hauntimator and the Raspberry Pi Pico system support only .wav (PCM) audio, either mono or stereo.
Hauntimator runs on your desktop or other higher-powered system so it can handle higher sample rates such as
44,100Hz.  The Pico can also handle sample rates of 44,100Hz, 16-bit in stereo as well.  However, the phoneme
plugin only accepts 16,000 Hz mono audio for processing.
This generally requires that the user use a desktop tool such as ffmpeg
to downsample any audio and convert it to .wav format prior to running the phoneme plugin.  More discussion
of this is available in the phoneme-specific help page.

When displaying the audio tracks in Hauntimator, the display detects mono or stereo and displays all the
tracks available.  The user may optionally hide one or both tracks.  This may be useful if the dialogue
for a character is in one track only.  Currently, the system only supports one stereo audio feed that
could support two character's dialogue.  Dialogue for additional characters will require additional
Pico systems and separate animation control files.

Audio channels may be displayed as waveforms or as amplitude and control channels may be autogenerated
from the amplitude.  This can be used to open a mouth more for louder sounds and less for quieter sounds.
It can also be used to simulate a decibel meter effect using several LEDs.

<a name="channel-panes">
&nbsp;
</a>

## Channel Panes

The channel panes contain plots of the data used to control each channel of the controller.  The channels
generally either control servos or digital, on/off signals although there is some support for more general
numeric controls.  Each pane displays the data points, interpolating curves between the data points,
specified limits, and the current playback time.  The data points are enclosed in small squares to allow
the user to easily select them and also identify their position.  Generally, the data points may be inserted
by shift-left-click within the pane and then dragging to the desired position.  Shift-left-click on an
existing point deletes it.  Existing points may be edited
by left-clicking within the square and then dragging the point to its desired position.

Servo/numeric channel panes display red bars to indicate the minimum and maximum allowed values for a 
control point.  Attempting to place a point outside the range will place it at the nearest limit.  Digital
channels are always ranged from 0 to 1 so the limits are not explicitly displayed.  Shift-left-clicking
in a digital channel pane will place the point at the nearest limit, either 0 or 1.

The displayed vertical range of the channel pane can be adjusted by rotating the mouse wheel with the
cursor within the pane.

![Channel Pane Menu](images/channelpopup.png)

The right mouse button brings up a submenu for working with the specific channel.  This submenu contains
the following entries:

+ Metadata - Brings up a secondary dialog for editing all the metadata for the channel.
+ Invert - Inverts (flips vertically) the channel points, useful for two servos operating the same joint but mirrored.
+ Randomize - Fill the channel with randomly generated values at a specified sample rate.
+ Rescale - Fit the upper and lower data limits to the displayed pane.
+ Hide - Remove the pane from the display.  It can be redisplayed via the [View menu](#view).
+ Clear - Delete all the knots in this channel.
+ Delete - Delete this channel from the animation.  Confirmation is requested and can be Undone.

### Metadata

![Channel Metadata Menu](images/channelmetadata.png)

The channel metadata is additional information used for properly controlling the hardware driven by that
channel and for aiding the user in interacting with the channel and associated hardware.  The metadata
includes a name for the channel (which must be unique) and a port number that the controller software
associates with a pin or bit or something to drive the correct hardware.  In addition, the servo channels
also contain a servo type, an interpolation type, and upper and lower limits.  The interpolation type
may be Linear, Spline, or Step.  Linear indicates that the channel values driving the animation will
follow straight lines from one control point to the next.  Spline causes the control points to be more
smoothly interpolated.  Step causes the control value to step up or down instantly to the new value.
Note that Step may not be usable for servos.

The limits on a servo channel are initialized to what the type of servo, if specified, can handle.  If the
user clicks on the Servo selector, a list of known servo types will appear.  If the user selects one, the
upper and lower limits are set to the maximum limits for that type of servo.  Note that the Preferences
also come into play in a manner that is hardware-specific and discussed elsewhere.

Often, the actual animatronic figure may have a reduced range of motion and the limits should be adjusted
to prevent the user from overdriving the servo.  Hauntimator provides a live, interactive control paradigm
for a servo or digital channel.  Clicking the Interactive button brings up another widget customized either
for controlling a digital channel or a servo.  For a digital channel, the widget supports turning the
channel on or off for testing.  For a servo, the widget supports a slider that may be used to set the 
servo interactively if the Live toggle is set.  The user may click the Page Up and Page Down keyboard
buttons to jump or the Up and Down Arrow keys to single step up and down to set the servo to a desired
limit and then the Max or Min button can be clicked to set that limit to the current servo value.

<a name="file-extensions">
&nbsp;
</a>

## File Types and Extensions

Hauntimator has some standard file extensions that it defaults to although the user may pretty much use
any file extensions desired.  Using Hauntimator's defaults just makes things easier.  Hauntimator also
suggests using the same path and basename as the main animation file for all the other files.  This allows
them to be colocated and easier to monitor.

### Animation files (.anim)

Hauntimator's main file type is the .anim file.  These file contain the path to the audio file and the
tags and channel data.  They also contain a variety of metadata to control behavior.  The name of the 
animation file is used as the default root for most other files within the system.

Hauntimator also saves a working copy of the animation file in case of a crash.  This file will have
the same name as the animation file with .autosave appended.  The user can load one of these files into
Hauntimator and then save it as the desired file if work is lost.

### Audio Files (.wav)

Audio files used in Hauntimator must be PCM (Wave) files.  These generally have the extension .wav and
may be mono or stereo at most sample rates.  Hauntimator will default to naming them after the main animation file when
installing them to the board.

If the phoneme tools are installed, they have special requirements for the audio files for sampling and
channels but they also require Wave files.

### Comma-Separated Value Control File (.csv)

Control files installed on the controller board will be either comma-separated values or binary files.
The .csv files contain header information associating columns with digital and servo ports.  Playback
on the controller can support either CSV or binary.

### Binary Control Files (.bin)

Control files installed on the controller board in binary format are specialy formatted to contain entries
for every port defined in the tabledefs file.  Thus, they may be much larger than a simple CSV file.
However, on playback they are slammed out to the hardware without reformatting so they perform much faster.

When exporting control and audio files from Hauntimator, it defaults to naming them the same as the animation
file, with different extensions, in order to simplify matching them in the controller.  Hauntimator attempts
to write both CSV and binary control files when saving them locally.  This allows them to easily be written
directly to an SD card mounted on the desktop machine to be transferred later to the controller.  Then the
controller will always have the preferred type of control file available.  Note that commlib.py must be
available to Hauntimator to support the conversion to binary.

### Other types of file

Hauntimator stores the system preferences in the user's login directory in a file named .animrc.  Normally,
users have no need to access this file directly.

Hauntimator utilizes a database of servo types stored in a file named servotypes.  This file may be renamed
as its name is in the system preferences.  However, changing the preferences only changes where Hauntimator
looks for it, not the filename.  Thus, if changing the preference, the file must be renamed externally OR
the servo data must be resaved within Hauntimator after changing the preference.

If the phoneme tools have been installed, there are a variety of additional files that aid the phoneme
recognition.  These are discussed under those tools.  However, they are generally expected to have the
same file root as the animation file and be colocated.


<a name="specialized-tools">
&nbsp;
</a>

## Specialized Tools

A few specialized tools for aiding in the generation of control channels have been implemented
within Hauntimator, as well as some still on the drawing board.  Implemented tools, generally
introduced elsewhere in this document, include random and amplitude-based control point
generation and inversion of control channels as well as audio-to-phoneme-to-control
point tools.

Random control points may be useful for motions that are not particularly coupled to the
audio such as moving the head/gaze around.  For motions that are coupled to the amplitude of
the audio, such as how far the mouth is open, the Amplitudize tool may be used to generate
points that are proportional the audio amplitude (note that the audio amplitude may be directly
visualized in the audio pane via the View->Audio Amplitude option).  Both random and amplitude
modes accept a start and end time, defaulting to the currently displayed range, and a sampling
rate and populate the channel(s) accordingly.  Note that Randomize applies to the channel pane
corresponding to the channel menu popup so only a single pane is affected.  Amplitudinize is
applied to all selected panes.  Behavior in Digital channels is reasonable in that either a
series of random transitions are generated (some may not actually change the state) or the
channel is on when the audio amplitude is above average and off when below average.

Sometimes, multiple servos may be required to move part of the animatronics.  For example,
a jaw may be hinged on both sides of the skull and a servo may be attached to each side.  In
such a case, the servos may be mounted in a mirror image configuration.  To simplify using
this configuration, the Invert tool may be used.  Create a channel for one servo, then copy
it to a new channel and use the Invert tool in the channel popup menu to invert it.  Then the
two servos will work in unison with each moving opposite of the other.

Some phoneme-based tools are available to truly assist in syncing
voices to animatronic behavior.  The main one is available via the Phonemes plugin on the
plugins menu.  It analyzes an audio file containing voice only and populates a control 
channel with knots for a particular type of motion such as jaw, lips, or cheeks.  See
the specific Help for the Phonemes plugin for more information.

<a name="requirements">
&nbsp;
</a>

## Requirements

Hauntimator uses PyQt and PythonQwt libraries for its graphical user elements.
Use of the Phonemes plugin requires installation of pocketsphinx.  

I like to use rshell
and generally install it with Hauntimator but it is not required.  It or thonny may also
be installed and used elsewhere for transferring files to and from the controller.  Some
such tool is required outside of Hauntimator to install the various software modules on
the controller.

<a name="bugs">
&nbsp;
</a>

## Known Issues and Bugs

There is a known Qt5 bug that causes a message of the form "qt.qpa.xcb: QXcbConnection: XCB error: 3 (BadWindow), sequence: 8564, resource id: 10598470, major code: 40 (TranslateCoords), minor code: 0"
to be output to stderr whenever certain types of windows close.  This seems to
be ignorable.

Some users may use thonny or rshell to upload files to the controller.
Playing the animation in the controller puts it in a state where uploading a control
file is now impossible via rshell and probably thonny.  The user will have to reset
the controller, generally by unplugging it from the USB port and plugging it back in
or by pressing a reset button found on some clones.
Uploading the control and audio files was changed to not use rshell so this problem is
generally obviated when done from inside Hauntimator.  (I strongly suspect this has
something to do with running multiple threads, one for control and one for playing
audio.  If no audio has been played, rshell and thonny can connect fine.  There may be
a way around this but I haven't found it yet.)

Conversely, rshell and thonny interrupt the controller when transferring files to or
from it.  This disrupts the communication between Hauntimator and the main software
running on the controller.  Again the user will need to reset the controller and
allow the main program to start to let Hauntimator reenable communications.

An animation controlling 16 servos and 16 digital channels requires around 7kB per
second of animation so a maximum of 2 to 3 minutes of animation may be stored in
the Pico's 1 MB or so of available flash.

In addition, the python code running on the Pico uses two threads, one for audio
playback and one for animation control.  This requires MicroPython be installed.
Using CircuitPython or C or other embedded environment will change things.  Your
mileage will vary.  Hauntimator has been tested with MicroPython only.

***

Copyright 2024 John R. Wright, William R. Douglas - 1031_Systems


