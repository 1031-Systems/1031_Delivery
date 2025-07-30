<!-- john Tue Jun  3 07:11:17 AM PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL3). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->


# Pololu

This installation includes files for using one or more Pololu Maestro servo controllers
for operating animatronics in conjunction with other tools from 1031-Systems.  These
include Hauntimator and Animator-I.

As always, there are many variations in the implementation and utilization of the
Maestro controllers, either with or without the Animator-I, Pico-based controller.  The
primary concerns are the number of PWM and digital outputs to be supported, what
inputs or triggers are needed, and what system will handle the audio.  This writeup 
will discuss three different approaches and how each deals with the concerns above.
One of the key requirements is to work well with Hauntimator so the use paradigm will
be tailored to be similar to that of the Pico-based Animator-I even if the Maestro is
used standalone.

Note that within this document the word Maestro or Maestro controller is used to 
denote any number of Maestro controllers daisy-chained so as to appear to be a single
Maestro that has more inputs and outputs than any single Maestro product.  The limit
is bound by how fast the PWM states can be transmitted to the Maestro via the USB
serial protocol.  At 200kbaud, that is about 65 digital or PWM output channels at a
50Hz update rate.  At the autodetect limit of 115kbaud, that is about 38 channels.

## Running with Animator-I and Pico

There are two main uses for the Maestro when used with Animator-I and a Pico system.
The first is an output-only version where a single buffered GPIO pin from a UART on the
Pico goes through a level shifter to provide a 5v signal and is then connected to
the Maestro.  This can drive outputs but cannot be used to sample the inputs.
GPIO pins 8 and 12 are UART TX pins and are available via buffering on a connector
on Animator-I with no additional components.

The second configuration replaces the I2C connection mainly used for the PCA9685
servo boards with a connection to the Maestro.  Essentially, the Maestro becomes a
drop-in replacement for the PCA9685.  In this configuration, inputs to the Maestro
are supported as well as feedback on servo position and other information.  This
configuration does require additional level shifters to those present on the
Animator-I board.  These level shifters will have to be mounted on a protoboard or
other substrate and powered and connected appropriately.

In both of these configurations, Animator-I is responsible for the audio allowing
a stand-alone system to be built that does not need a PC for operation.

Details on how to implement and use these configurations is available in the Pico
section as these are extensions of the Pico implementation.

## Running Standalone

This configuration is likely most similar to how the Pololu Maestro controllers are
typically used.  The USB port on the Maestro is connected to the USB port on a PC.
The PC streams the channel values over USB to the Maestro and is also responsible for
handling the audio playback.  Trigger or other inputs to the Maestro are sent back to
the PC which adapts its output to what comes in.

To maintain the board-agnosticity of Hauntimator, it will not directly interface to
the Maestro.  Instead, a separate application will perform the functions provided by
the Pico on Animator-I.  These include identifying the animations to be played, the
idle animation if any, handling the audio, providing the reset, main, and
trigger functions, file I/O, and other capabilities.  A custom version
of commlib.py will provide Hauntimator with the basic interface to the Maestro.

The Trigger on the Pico serves a different purpose than the
Main input and has different behavior.  The Main input is a master control
that can abort playback of an animation and also trigger continuous playback mode.
On the Pico, the Trigger can only trigger a playback when an animation
is not playing, except for the idle animation.  It cannot abort a playback nor can
it initiate continuous mode.  Its expected use is to register a visitor and begin
playback when that occurs.  Multiple visitors should not cause interruption of a
playing animation.  The Main input is a master control that is expected to be
used to initiate the system or to abort a playback that is having problems and
should be triggered by you when necessary.  This triggering paradigm will be
maintained with the Maestros.

The standalone application is named control_emulator.py.  This Python program uses
pygame to handle keyboard input and audio output.  Additional code sends and receives
data to and from the Maestro controller via USB.  Chained Maestro controllers add
more input and out channels and communicate via the Tx/Rx pins on the Maestros.

### control_emulator.py

The control_emulator.py application emulates most of the functionality of the
Pico-based Animator-I while running on a desktop machine.  This includes a local
filesystem that contains an anims directory and an sd/anims directory containing
animations and associated audio files.  It supports an identical animList file
format allowing specific animations to be ordered and linked to specific inputs.
It supports messages from commlib to set servos and digital outputs and to trigger
the next animation.  It supports continuous playback mode as well as idle mode
where a specific animation is run if no other animation has been triggered.  It
also handles audio playback via the pygame library.

The control_emulator.py application  also makes use of a tabledefs file to 
specify the functionality of the Maestro inputs and outputs.  This file maps the
port IDs designated in Hauntimator and referenced in the animation control files
to specific Maestro boards and channels.

It is somewhat different from Animator-I.  It does not currently support a binary
file mode.  The PCA9685 typically used with Animator-I for larger projects has a
specific data format that allows the control data to be streamed into it very
rapidly.  The Maestro does not.  Thus, binary file mode is not as useful.  However,
the binary mode would allow more rapid unpacking of the animation files so it may
be useful in the future.

There are no software files that need to be loaded for the Maestros as there are
for Animator-I so it does not support checksumming of installed files.

Since the control_emulator.py application runs on a desktop type of machine, it
adds support for keyboard control of the application as well as text output of
playback state.  This may be disabled if input buttons designated for the main
control functions are available attached directly to the Maestros.  However, it
is very useful for development and debugging purposes.  Trust me on this!

## Installing the Maestro(s)

In general, the MaestroControlCenter application from Pololu must be used to set
up all of the Maestros to be used in the system.  Each one must be connected via
USB to the desktop and its specific settings properly initialized.  The specific
settings to be set via MaestroControlCenter are:

### Serial Settings Tab

- Serial Mode - The first Maestro in the daisy-chain, even if it is the only one,
needs to be in USB Chained mode.  This allows the desktop to control the Maestro
over USB while it also forwards commands over the Tx/Rx pins to other Maestros
in the chain.  For ease of use, the remaining Maestros in the daisy-chain should
be set to UART, detect baud rate, the default.

- Device Number - The device numbers need to be unique within a daisy-chain.  If
more than one Maestro is being used, all but one need to have the Device Number
changed from 12, the default, to a different number.

### Channel Settings Tab

Under the Channel Settings Tab are the specific settings for each channel on the
Maestro.  Each channel should be set to Servo (the default) for channels attached
to servos, Output for channels that provide a digital output, and Input for
control inputs.  Any pin on any Maestro may be used for digital input.  Analog
input is supported within the Maestros but not in the control_emulator.py
application.

More details on how to use MaestroControlCenter are available on Pololu's
[website](https://www.pololu.com/docs/0J40/all#4).

Once all the individual Maestros have been initialized, they may be wired into
the daisy-chain via directions on the [Pololu website](https://www.pololu.com/docs/0J40/5.g).
Since there are AND gates built into all the Maestro models except the Micro, it
is easiest to put the Micro only at the end of the daisy-chain and to never have
more than one.  Then it is unnecessary to add external logic to the chain.

As you develop your overall system, it is important to make note of what Maestro
boards will be utilized for what purposes.  Then setting up the system will be
relatively straightforward.

## Using tabledefs

The tabledefs file is used to map logical port numbers used in Hauntimator to
physical ports on the hardware.  The Maestro controllers support servo (PWM) and
digital outputs and analog and digital inputs.  Currently, analog inputs are not
supported.

The tabledefs file is executable Python code that calls functions to specify
the mapping of ports to inputs and outputs.  Each function maps 1 or more port
numbers to channels on the Maestros.

### Mapping Servo Ports

Typically, most channels will be used to control servos and digital outputs in
an animatronics installation.  It will be simpler to use a block of channels for
servo outputs, another block for digital outputs, and another block for inputs.
This is an example of how to specify a block of servo channels:

```
configureMaestroPWM(boardid=12, firstport=21, count=4, firstchannel=2)
```

This configures 4 (count=4) ports, numbered 21 (firstport=21) through 24, on
Maestro board 12 (boardid=12), beginning with channel 2 (firstchannel=2) of the
Maestro channels.  If the Maestro is a micro, this will be channels 2-5, leaving
channels 0 and 1 for other purposes.

Note that if the servo channels on the Maestros are not consecutive or are split
over multiple boards, multiple configureMaestroPWM calls will be needed.  Each
call can handle one contiguous block of channels on one board.

### Mapping Digital Output Ports

Animatronics systems often control lights and other props controlled by digital
outputs usualy through relays.  Here is an example of how to define a block of
contiguous digital output channels on a Maestro board:

```
configureMaestroDigital(boardid=13, firstport=0, firstchannel=0, count=10)
```

This configures ten digital outputs on board 13 using the first 10 channels on
the board and mapping those to digital ports 0-9.  Note that this would be an
error if board 13 is a Maestro Micro as it only has 6 outputs.  Also,
MaestroControlCenter must have been used to specify that channels 0-9 of board 13
are Outputs, not Servo or Input channels.

### Mapping Digital Input Ports

The Animator-I system from 1031-Systems has three standard inputs.  These are Reset,
Trigger, and Main.  The tabledefs supports these three standard
inputs via the following:

```
configureMaestroResetInput(boardid=14, firstchannel=1)
configureMaestroMainInput(boardid=14, firstchannel=2)
configureMaestroTriggerInput(boardid=14, firstchannel=3)
```

Each of the above lines defines the Maestro channel to be mapped to a specific
input.  The first line maps channel 1 of board 14 to the Reset input.  Reset performs
a reset, stopping playback of even the idle animation, and refreshing the list
of available animations, leaving the system in a Stopped state.  The second line
maps the Main input to channel 2 of board 14.  The Main input initiates
playback of the next animation if in Stopped or Idle mode and Stops playback of
the current animation if in Play mode, switching to Idle or Stopped mode.  The
Trigger input initiates playback of the next animation if in Idle
or Stopped mode but does not interrupt playback if in Play mode.  This functionality
matches that of the three inputs on Animator-I.

Only one input may be mapped to each of the three standard controls described
above.  If any of the functions is run more than once, the last one will take
precedence.

One additional function is triggered when the Main input is held down for
more than 5 seconds.  In this case, playback enters continuous mode, animations
are played one after the other, and the idle animation is never played.  Pressing
the Main button again leaves continuous mode.

In addition to the three standard inputs, additional inputs may also be defined.
These inputs are indexed and are mappable to specific animations.  This example
illustrates this:

```
configureMaestroDigitalInputs(boardid=14, firstindex=0, firstchannel=4, count=4)
```

Here we define four inputs, indexed 0-3, on board 14, channels 4-7.  This sets up
four additional inputs that may be mapped to run specific animations via the
animList file.  This is an example animList file illustrating how the inputs
may be mapped to animations:

```
first.csv,first.wav
second.csv,second.wav,0
third.csv,third.wav,2
,theRaven.wav,idle
```

This animList file specifies three playable animations and an idle animation.  The
first animation is triggerable by the Trigger or Main inputs.  The
second one will be played in order after the first if the standard triggers are used
or may be triggered specifically by input 0, which is mapped to board 14, channel 4.
The third animation may be specifically triggered by input 2, which is mapped to
board 14, channel 6.  The fourth animation in the list is the idle animation that
will be played when no other animation is playing.  In this case, the idle animation
has been specified with audio but no animation.  Note that the idle animation
is optional and if not specified will result in no action between other animations.

