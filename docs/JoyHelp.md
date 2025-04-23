<!-- john Wed Mar 26 11:56:50 AM PDT 2025 -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->

<a name="top">
&nbsp;
</a>

# Help for joysticking.py

__VERSION__

***

joysticking.py, as you might surmise, is a Python program.  Its general purpose is to
populate channels in an animation using a joystick rather than a mouse in Hauntimator.
joysticking.py provides multipass capability to support populating many more channels
than is practicable with a single joystick.  It also supports the use of multiple
joysticks to allow multiple individuals to collaborate on a single animation.

+ A. [Process](#process)
+ B. [Overview](#overview)
+ C. [Menus](#menus)
+ D. [Audio](#audio-tracks)
+ E. [Channel Panes](#channel-panes)
+ F. [File Types and Extensions](#file-extensions)
+ G. [Requirements](#requirements)
+ H. [Known Issues and Bugs](#bugs)

<a name="process">
&nbsp;
</a>

## Process

The joysticking.py utility is used to populate channels in an animation created by 
Hauntimator.  joysticking.py does not create animation files, it only modifies them.
The process is as follows:

+ Load an Animation File
+ Map Controls to Channels
+ Set Active Time Range
+ Record Channels
+ Play Back Recorded Activities
+ Save the Resulting Animation Data

<a name="overview">
&nbsp;
</a>

## Overview

![Image of User Interface](images/JoyUI.png)

The joysticking.py User Interface

To perform the process described above, this is how to accomplish each step:

### Load the Animation File (Required)

joysticking requires a preexisting animation file created by Hauntimator.
This file specifies all the possible channels that may be controlled and
recorded.  The animation file may be specified on the command line at
startup using the -a option or may be loaded from the File menu.

Go to File->Open Anim File to bring up a file browser.  Select the
desired animation file, with extension .anim, and click Open.

### Map Control to Channels

joysticking requires the use of a button on an attached joystick for
enabling recording and playback.  My preference is to hold the joystick
in one hand with my finger over the trigger button while activating the
other joystick controls with my other hand.  Unless you are very 
experienced, it is difficult to control more than three axes and one or
two buttons with one hand.  Thus, you may often find yourself performing
multiple recording passes to record more channels than can be easily
recorded in a single pass.  Alternatively, you may wish to enlist more
than one person to control as many channels as you wish with multiple
joysticks.  That's up to you.

In any case, one button on one joystick enables recording and playback.
This button must be selected to enable recording.  On the Record Button
Mapping tab under the Channel Mapping tab the user must select a joystick
and a button to initiate recording and playback.

![Record Button Mapping tab](images/JoyRecordSet.png)

Note that the joystick dropdown is always initialized to the first found
joystick, the only one if there is a single joystick attached.  The
button dropdown is populated when the joystick is selected to match the
available buttons on that particular joystick.  Always select the joystick
first so the button dropdown is populated correctly.

The user must select a button to enable initiation of recording.  This can
be done by selecting any of the button indices in the dropdown menu.  However,
the specific button to index mapping may not be obvious.  In this case, merely
position the mouse cursor on the button dropdown and then press the desired
button on the joystick.  This will select the appropriate index.  This feature
works on all the button dropdowns.

Next, select the Numeric Channel Mapping tab.  This tab will be populated with
joystick and axis dropdowns for all the numeric channels in the animation
file.  Select the joystick and axis for each channel you wish to record.  Do
not select axes for more channels than you can control.  If you are unsure of
which axis goes with which index, position the mouse cursor over the axis
dropdown and then move the joystick along the desired axis to the limit.  This
will autoselect the appropriate axis.

Next, select the Digital Channel Mapping tab.  This tab will be populated with
joystick and button dropdowns for all the digital channels in the animation
file.  Select the joystick and button for each channel you wish to record.  Do
not select buttons for more channels than you can control.  If you are unsure of
which buttons match which index, position the cursor over the button dropdown
and press the desired button on the joystick.  The index will be autoselected.

Once all the desired mappings have been specified, the mapping may be saved to
a file via the File->Save Map File option.  This file may then be loaded later
via the -t command line option at startup or via the File->Open Mapping File
option.  It is important to note that the mapping table is by index.  If the
next session switches or removes joysticks or the joysticks have different buttons,
the mapping file will generally be useless.

### Set Active Time Range

Once the channel mapping is complete, recording or playback may be initiated.
Switch to the Recording tab to perform this action.  By default, the time range
is initialized to the length of the audio file specified in the animation file.
The start and end times may be changed by double-clicking on the start and end
time widgets and entering a new time.  This time may be entered as a floating
point number of seconds or as minutes and seconds separated by colons.

![Image of User Interface](images/JoyUI.png)

Note that it is possible to set the end time to a value after the end of the
audio and joysticking will record or play to that time.  However, the start
time may not be set to a value less than zero and the audio always starts at
zero.  Specifying a start time greater than zero will skip into the audio
playback to play at the specified time.

### Record Channels

To enable recording, click on the Enable Recording button.  If it is grayed out
it indicates that the record button has not been selected via the mapping.  For
safety, recording will not begin until the selected record button has been pressed.

Note that the mode display will show Recording Enabled with a red background to
indicate that dangerous things may happen.  As an additional safety measure, recording
and playback become disabled if the mouse cursor leaves the Record tab.

It is quite possible to record channels without any visible feedback.  However,
for most of us it will be preferable to see the mechanisms moving as the controls
are activated.  For this, the controller must be attached to the computer via
USB and power must be on.  Further discussion will generally assume this is the
case.

While recording is enabled but prior to beginning recording, the joystick controls
may be activated to move the mechanisms to their initial state.

To activate recording, press and hold the selected joystick button.  The audio 
will begin to play, the time display will start counting, and the mechanisms
will move.  Any mechanisms that have data in their channels will be activated
even if they are not being recorded.  For those channels that have been mapped
to a joystick control, the states of the associated mechanisms will be recorded
into those channels.

Recording will continue until either the user releases the joystick button or
the end time is reached, whichever comes first.  Note that when recording 
terminates, recording is disabled.  You have to reenable it to record again.

### Play Back Recorded Activities

Playback works in a similar way to recording.  The user clicks on Enable
Playback, then presses and holds down the specified record button on the
joystick.  Playback will begin at the specified start time and run until the
end time is reached or the button is released.

Note that the mode display will show Playback Enabled with a yellow background to
indicate that dangerous things may happen.  Playback will be disabled when it
terminates and must be reenabled.  As an additional safety measure, recording
and playback become disabled if the mouse cursor leaves the Record tab.

If the Enable Playback button is grayed out, it indicates that joysticking
cannot connect to the controller, most likely because the USB cable is not
connected.  If the playback button is active but nothing seems to happen, it
may be because no data has been recorded in any channels or the controller may
not have the external power it needs to drive the mechanisms.

### Save the Resulting Animation Data

To save your current animation, with the control
channels, use File->Save or File->Save As to bring up a file browser
to select a filename and path to save your work.  It is often a good idea to
save the animation data to a new file for validation rather than writing over
your existing animation file.  Save As will do this and keep the filename so
additional Save actions will continue to write to the new file.

To save the channel mapping to joystick controls, use File->Save Map File to
select a file to save to.  Since the user may want different mappings for
different purposes, Save Map File always prompts for a filename to map to
rather than defaulting to any previously used filename.


<a name="menus">
&nbsp;
</a>

## Menus

Hauntimator has a number of dropdown menus available on the menubar at the top
of the Hauntimator main window or at the top of the screen in MacOS.  They are:

1. [File](#file) - to save and load your work
2. [Help](#help) - to find out more

<a name="file">
&nbsp;
</a>

### File Menu

![File Menu](images/JoyFileMenu.png)

The File menu contains the following options:

+ Open Anim File - Open and Load an existing animation file
+ Save Anim File - Save the current animation to the file it was loaded from
+ Save As - Save the current animation under a new filename
+ Open Mapping File - Load a channel mapping table file
+ Save Map File - Save current settings to a channel mapping table file
+ Quit - Duh!

joysticking.py tries to be careful about quitting without saving or overwriting files.

<a name="help">
&nbsp;
</a>

### Help Menu

![Help Menu](images/JoyHelpMenu.png)

The Help menu provides access to this helpful information as well as some other helpful information.
In addition, it provides some visibility into the content of the overall animation as
expressed in the XML used for storing the animation information.  This is mostly for my personal
debugging purposes but is available for all to peruse.

<a name="audio-tracks">
&nbsp;
</a>

## Audio

joysticking.py will play the audio file associated with the animation file during recording and
playback.  It is played during recording to aid the user in aligning actions with the audio and
during playback to aid evaluation of the alignment.  It is not necessary to have associated audio
but the end time will need to be specifically set greater than the start time to enable any
recording or playback.

<a name="file-extensions">
&nbsp;
</a>

## File Types and Extensions

joysticking.py has some standard file extensions that it defaults to although the user may pretty much use
any file extensions desired.  Using joysticking.py defaults just makes things easier.  joysticking.py also
suggests using the same path and basename as the main animation file for all the other files.  This allows
them to be colocated and easier to monitor.

### Animation files (.anim)

Hauntimator's main file type is the .anim file.  These files contain the path to the audio file and the
tags and channel data.  They also contain a variety of metadata to control behavior.  joysticking.py
uses the same animation file for its work.

### Audio Files (.wav)

Audio files used in Hauntimator must be PCM (Wave) files.  These generally have the extension .wav and
may be mono or stereo at most sample rates.  joysticking.py will load and play the audio specified in the
animation file, if any.

### Channel Mapping Files (.map)

When saving or loading a channel mapping file, the extension defaults to .map.  In addition, when saving,
the filename will default to that of the animation file.  Thus, mapping files are associated with their
animation files.  If multiple mappings are desired due to multipass recording, append a number or other
indicator after the defaulted filename.

<a name="requirements">
&nbsp;
</a>

## Requirements

joysticking.py uses PyQt and PythonQwt libraries for its graphical user elements.
joysticking.py also uses pygame to interact with the joystick and play the audio.

<a name="bugs">
&nbsp;
</a>

## Known Issues and Bugs

There is a known Qt5 bug that causes a message of the form "qt.qpa.xcb: QXcbConnection: XCB error: 3 (BadWindow), sequence: 8564, resource id: 10598470, major code: 40 (TranslateCoords), minor code: 0"
to be output to stderr whenever certain types of windows close.  This seems to
be ignorable.

There is a known Qt5 issue that arises when the main window class is included in the file with the main
function that causes a message of the form "joysticking.py:723: DeprecationWarning: sipPyTypeDict() is deprecated, the extension module should use sipPyTypeDictRef() instead" to be output when the
program is run.  This seems to be ignorable.

***

Copyright 2025 John R. Wright, William R. Douglas - 1031_Systems
