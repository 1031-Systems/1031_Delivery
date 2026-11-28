<!-- john Thu Nov 26 01:34:26 PM PST 2026 -->
<!-- This software is made available for use under the GNU General Public License (GPL3). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->


# Headless Prop Controllers

As you create various props, it may become desirable to integrate a prop controller
right into the prop itself.  This can reduce the connections to the prop to just
power.  Our system now supports a headless configuration, one that has no monitor
or keyboard, using a Raspberry Pi Zero as a processor and a Pololu Maestro as the
animation controller.  This provides for an off-the-shelf electronics setup for
operating the prop.

The development of this capability was intended to support the Raspberry Pi Zero
specifically.  In fact, it runs just fine on a Raspberry Pi.  Plausibly, it
will work on other processors running Linux such as the Arduino UNO Q.  Less
plausibly it could be ported to non-Linux platforms.  The installation process
is known to work on the Pi systems (not Pico) and is not, in any way, intended
for any others.

Of course, the Pico version of our software is also a headless prop controller,
combining the processor and controller into a single custom board that the user
may build for themselves.  This discussion will focus on a COTS (commercial off-
the-shelf) electronics system.

## Installation

The headless version of our software uses the Maestro_Animator tool to command
the Maestro to operate the prop according to the animation control file.  It runs
on the Zero processor and communicates over the USB to other components.  The Zero
has the Raspberry Pi OS, a version of Linux, installed on it via an SD card.  You
should use the Raspberry Pi Imager to install the lite version of the OS on the
card although it is quite possible to download the OS image and copy it to the card
manually if Imager does not run on your system.  In either case, you want to enable
ssh and create a user account when writing the OS to the SD card.  If using a Pi
Zero W, you can also enable the wifi although I have never done it.  Look online.

We choose the lite version of the OS since we do not expect to use a monitor for
a GUI so we do not need a windowing system.  You can install the full version
but it will likely take longer to boot up and will take up more of the space on
the SD card that you would like to reserve for animations.

Once you have the SD card imaged, insert it in the Zero, attach the Zero to a
powered USB hub, and power it up.  If not a Zero W, also attach a USB to ethernet
dongle to the hub and connect it to your network.  You will need access to the
web for installing the various necessities.

Once the Zero is booted up, login either by ssh or by attaching a monitor and
keyboard and directly logging in.  Either way works.

Unfortunately, the OS image may be somewhat out of data in its tables of repos
and mirror sites for installing libraries and modules.  For this reason, it is
necessary to refresh the databases that the apt tool uses so we will do that
first with these commands:

```
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*
sudo apt update
```

Once the apt databases have been refreshed, we need to install the Direct
Simplemedia Layer libraries.  These libraries support the pygame-ce Python
module we are using for audio playback.  To install these libraries, use
apt as follows:

```
sudo apt-get install -y libsdl2-2.0-0
sudo apt-get install -y libsdl2-mixer-2.0-0
sudo apt-get install -y libsdl2-dev
```

Once the above commands complete (many minutes depending on network
speed), we are ready to download and install the software from 1031_Systems.
We can use wget from the command line or use a browser if you chose to install
the full OS.  If you used ssh to remotely log in to the Zero, you can use a
browser on your PC to get the URL for the LinuxMac zip file of the desired
version and copy/paste it into the wget command.  It should look something
like this:

```
wget https://github.com/1031-Systems/1031_Delivery/releases/download/v0.1.3b/Hauntimator_LinuxMac_v0.1.3b.zip
```

Next unzip the file with:

```
unzip Hauntimator_LinuxMac_v0.1.3b.zip
```

Finally, run the install_headless script that came with the software:

```
./1031_Hauntimator/install_headless
```

This will install the software, remove all the unnecessary tools, rename the
installation to Pololu_headless, set up your virtual environment, install the 
pyserial and pygame-ce modules, and verify the installation.  If our code
installs well, it then installs the services in Linux that support headless
operation.  The whole process takes at least four minutes and maybe more if
your network is slow.

If you already have an installation, it is uninstalled prior to installing
the new one.

### Installing Animation(s)

To install animations on the Zero, the animation files must be copied to the
filesystem on the embedded processor.  During the install_headless process, a
directory named Animations is created (only if it does not already exist) in
the user's home directory.  The Linux service that plays the animations looks
for them there.

Animations, in general, are a pair of files, one containing the audio and one
containing the animation controls.  The audio files are required to be wave files
elsewhere so we assume they are here also but pygame also accepts mp3 and ogg so
it might work with those as well.  The control files are comma-separated value
(CSV) files in ASCII format.

In addition to the animation files, there may be an animList file and a tabledefs
file.  The animList file described a bit more down below, specifies playback
order, allows animations without audio and audio without animations, and assigns
animations to inputs.  The tabledefs file maps logical ports used in Hauntimator 
and contained in the CSV file to physical pins for channels on the Maestro.  The
default tabledefs file is embedded in the installed software so it is often
simpler to include a tabledefs file to be used with its associated animations.

From Linux or Mac systems, it is easiest to use the scp command to copy all the
animation files over to the Zero, like this:

```
scp [filelist] userID@raspberrypi:/home/userID/Animations
```

To make the process simpler and more automated, set up a mirror Animations
directory on your desktop machine and copy everything at once with:

```
scp Animations/* userID@raspberrypi:/home/userID/Animations
```

If using Windows, you can install the OpenSSH client and run the same commands
as above in a Powershell window, or install WinSCP and PuTTY and use a GUI-based
process.

## Maestro_Animator.py

The Maestro_Animator.py application emulates most of the functionality of the
Pico-based Animator-I while running on a PC or our headless machine.  This includes a local
filesystem that contains an Animations directory containing
animations and associated audio files.  It supports an animList file
format allowing specific animations to be ordered and linked to specific inputs.
It supports continuous playback mode as well as idle mode
where a specific animation is run if no other animation has been triggered.  It
also handles audio playback via the pygame module.

The Maestro_Animator.py application also makes use of a tabledefs file to 
specify the functionality of the Maestro inputs and outputs.  This file maps the
port IDs designated in Hauntimator and referenced in the animation control files
to specific Maestro boards and channels.

### Desktop

If the Maestro_Animator.py application is run on a desktop type of machine, it
adds support for keyboard control of the application as well as text output of
playback state.  This may be disabled if input buttons designated for the main
control functions are available attached directly to the Maestros.  However, it
is very useful for development and debugging purposes.  Trust me on this!

The easiest way to run Maestro_Animator is to drag and drop a directory containing
the desired animations to be played onto the Maestro_Animator desktop icon.  Note
that if there is no Maestro controller attached to the system the software will
generally crash and burn.

### Remote

If using ssh to log into another system, either another PC or our headless system,
the Maestro_Animator.py application may be run from the command line.  There are
two necessary arguments, -nohead and -a.  The -nohead argument specifies not to
attempt to use a windowing system to display information when running.  The -a
argument specifies the path to the directory containing the animations.  The
command might look like this:

```
install_directory/Maestro_Animator -nohead -a /home/userID/Animations
```

### Headless

When running the system as an embedded controller with no interface at all, there
is a Linux service that is set up to run Maestro_Animator.py at startup.  This
service is set up when you run install_headless with references to the installation
created and the userID under which it is run.  When the processor boots up, it runs
Maestro_Animator.py with -nohead and pointing to the Animations directory in the
user's home directory.  Thus, once the processor is fully booted up, the animations
for the prop are ready to run.

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
input is supported within the Maestros but not in the Maestro_Animator.py
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
supported in software.

The tabledefs file is executable Python code that calls functions to specify
the mapping of ports to inputs and outputs.  Each function maps 1 or more port
numbers to channels on the Maestros.

### Archived tabledefs files

Oftimes, the tabledefs file is specific to a selection of animations such as for
Halloween or Christmas.  The user may copy the tabledefs file associated with a set
of animations to the SD card or flash memory directory containing the animations.
This preserves the specific table definitions associated with those animations.  When
loading the animations, any file named tabledefs in the directory where the animations
are located will override those in lib/tabledefs.  The point of this feature is to 
allow switching of hardware and the associated SD card without having to attach to
a computer to install the needed tabledefs changes.  It also allows the user to load
the animations and tabledefs on the SD card from the PC and then load it into the
Zero for proper use.  However, because it does override the tabledefs in lib, the user
should be aware that any changes should be applied to the tabledefs file that is
actually currently in use.

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
outputs usually through relays.  Here is an example of how to define a block of
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
configureMaestroTriggerInput(boardid=14, firstchannel=3, Level=True)
```

Each of the above lines defines the Maestro channel to be mapped to a specific
input.  The first line maps channel 1 of board 14 to the Reset input.  Reset performs
a reset, stopping playback of even the idle animation, and refreshing the list
of available animations, leaving the system in a Stopped state.  The second line
maps the Main input to channel 2 of board 14.  The Main input initiates
playback of the next animation if in Stopped or Idle mode and Stops playback of
the current animation if in Play mode, switching to Idle or Stopped mode.  The
third line maps channel 3 of board 14 to the Trigger input.  Additionally, it
specifies that the active level is high (True) on the input line while low (False)
is the default for all inputs. 
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


***

This software is made available for use under the GNU General Public License (GPL3).
A copy of this license is available within the repository for this software and is
included herein by reference.

***

Copyright 2026 John R. Wright, William R. Douglas - 1031_Systems

