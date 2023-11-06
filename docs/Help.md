<!-- john Fri Jun 27 07:35:16 PDT 2023 -->
<a name="top">
&nbsp;
</a>

# Help for Animator.py

1.0.0(a)

Animator.py, as you might surmise, is a Python program.  Its general purpose
is to synchronize control signals for animatronics and lighting to each other
and to an audio track.  Animator provides the means for visualizing and
listening to an audio track and then creating and editing control channels
for individual mechanisms in sync with the audio.  Control values are then
output to the hardware controller to operate the mechanisms.

+ x. [Process](#process)
+ x. [Overview](#overview)
+ x. [Menus](#menus)
+ x. [Audio Tracks](#audio-tracks)
+ x. [Channel Panes](#channel-panes)
+ x. [Specialized Tools](#specialized-tools)
+ x. [Requirements](#requirements)
+ x. [Known Issues and Bugs](#bugs)

<a name="process">
&nbsp;
</a>

## Process

The Animator process is similar to that used by other tools that perform
similar functions.  Generally it is preferred to synchronize mouth, face,
and head movements to audio containing voices, then proceed to synchronize
other movements, lighting controls,  and other activities to the audio.

1. Using an audio editor, create sound files for each character’s dialog, and a separate mix file which contains all of the characters, effects, and background music.
2. Start Animator.
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

The Animator GUI consists of, from top to bottom, a menubar, audio channel displays,
and control channel displays called panes.  When the user loads an audio file into Animator
it is displayed using one pane for mono or two panes for left and right stereo.  It is not
necessary for there to be an audio file in use and none will be displayed in that case.

![Image of User Interface](docs/image1.png)

The Animator User Interface

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
positioning, motor speed, brightness, or other types of continuous control.  Animator
does not distinguish the purpose of the channel other than by name so a numeric channel
may be used to control servos via PWM, motors via CAN, and other mechanisms based
entirely on the controller hardware.  However, for better performance of the software
within the controller hardware, Animator sends integer values for all channels.  These
are either 0/1 for digital channels or 0-4095 (user-controllable) for servo channels.

For the numeric channels, Animator supports different types of interpolation between
knots.  The simplest is Step that makes a step transition from one value to the next,
thus holding a set value until the next knot time is reached.  The most common type is
Linear that follows a straight line from knot to knot.  Another
common type is Spline that applies a smoothing interpolation between points for
possibly better appearance.  The example image above shows the appearance of a Linear
channel and a Spline channel.

As the user populates channels, completed channels may be hidden so focus can be on the
current channel under construction and any other channels that may be relevant or helpful.
Channels are ordered on the display initially in the order of creation from top to bottom.

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
or other method and the controller processes it.  The user may also send similar data
directly to the controller a line at a time at the same 50Hz rate. See details on
driving the hardware [here](#drivers).

<a name="menus">
&nbsp;
</a>

## Menus

Animator has a number of dropdown menus available on the menubar at the top
of the Animator main window or at the top of the screen in MacOS.  They are:

1. [File](#file) - to save and load your work
2. [Edit](#edit) - to add and delete channels or edit metadata
3. [View](#view) - to fit data to the screen or hide channels currently unneeded
4. [Channels](#channels) - to select, copy, and paste channels
5. [Tags](#tags) - for Tag-related activities
6. [Help](#help) - to find out more

<a name="requirements">
&nbsp;
</a>

### Requirements
Animator uses PyQt and PythonQwt libraries for its graphical user elements.

<a name="bugs">
&nbsp;
</a>

### Known Issues and Bugs

There is a known Qt5 bug that causes a message of the form "qt.qpa.xcb: QXcbConnection: XCB error: 3 (BadWindow), sequence: 8564, resource id: 10598470, major code: 40 (TranslateCoords), minor code: 0"
to be output to stderr whenever certain types of windows close.  This seems to
be ignorable.

Playing the animation in the controller puts it in a state where uploading a control
file is now impossible.  The user will have to reset
the controller, generaly by unplugging it from the USB port and plugging it back in.
Thus, it is generally a good idea to always reset the controller immediately prior to
uploading the control file.

The Raspberry Pi Pico used for development and testing has a limited ability to
support this functionality, primarily in the use of an SD card.  In general, the
audio track needs to be sampled at 11025 Hz or lower in stereo 16-bit mode or
22050 Hz in mono 16-bit mode due to the slowness of reading from the SD card.
Higher sampling rates lead to breakups and skips in the audio playback.  Additionally,
putting the control file on the SD card is problematic due to the audio playback
taking all the read cycles.  Thus, generally the audio is stored on the SD card at
a lower sample rate and the control file is stored in the limited flash memory.
Smaller animations of a few seconds may be stored completely in flash memory and
do not seem to suffer the same problems.  Pico clones with larger flash memory
may also be used.
An animation controlling 16 servos and 16 digital channels requires around 7kB per
second of animation so a maximum of 2 to 3 minutes of animation may be stored in
the Pico's 1 MB or so of available flash.

In addition, the python code running on the Pico uses two threads, one for audio
playback and one for animation control.  This requires MicroPython be installed.
Using CircuitPython or C or other embedded environment will change things.  Your
mileage will vary.  Animator uses rshell to upload control files and control some
things and has been tested with MicroPython only.

***

Copyright 2023 John R. Wright, William Douglas


