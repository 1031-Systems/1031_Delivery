<!-- john Tue Apr  2 07:11:17 AM PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL3). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->


# Pico

This installation includes files for using a Raspberry Pi Pico or
clone for your animatronics controller.  The provided software
runs on either a standard Raspberry Pi Pico with 4MB of flash or
on a Pico clone with a 16MB flash memory.  The 16MB can hold
 one to five animations of about
thirty seconds in length each.  These are expected to run when a lucky
trick-or-treater approaches your house.  In order to use the 16MB of
flash available in the clone, firmware must be loaded that supports
the 16MB.  Several versions seem to be available but the only one
that worked with our test clone was the WEACT v1.21.0 one at:

[https://micropython.org/download/WEACTSTUDIO/](https://micropython.org/download/WEACTSTUDIO/)

Feel free to try others with your clone.

If using a regular Pico with only 4MB of flash
or a clone, an external SD card can be used to store the audio and
animation data.  With a big SD card, it can run multiple hours of
animations, audio, flashing lights, etc.  Either the clone or the actual Pico can work with the
standard 4MB firmware v1.21.0 available at:

[https://micropython.org/download/RPI_PICO/](https://micropython.org/download/RPI_PICO/)

Instructions for flashing your Pico with either firmware described above or
others to your liking may be found all over the interweb.

***

## Important Note

Prior to installing the Pico python code on the processor, the user needs to customize the
tables defining the digital and PWM I/O ports.  The customized tables are used to assign
port numbers to the different kinds of control outputs.  To perform this step, copy
Pico/lib/tabledefs_template to Pico/lib/tabledefs and edit Pico/lib/tabledefs according
to the system design.

The default file Pico/lib/tabledefs_template defines 16 digital I/O ports corresponding to
the 16 channels supported by the onboard 74HC595 chips.  It defines no PWM ports as there
are none built into the board.

Read the Pico/lib/tabledefs_template file for more details on how to attach ports to the
various types of output devices and to the GPIO pins from the Pico that are accessible.
Support functions are available to rapidly define digital ports for 74HC595 boards
attached to the system and for rapidly defining PWM ports that utilize PCA9685 boards.
Utilizing the GPIO pins requires a specific method for each port individually.  GPIO
pins may be used for either Digital or PWM control ports.  However, usage of the GPIO
pins may slow down the control cycle of the animatronics.

In addition to the port definitions, tabledefs contains a flag to prefer binary or
ASCII CSV files.  Binary files are preferred for larger system with more than five
PWM controls attached to PCA9685 board(s).  For smaller systems, the flag should be
False to prefer CSV files.  CSV files are generally forward-compatible as more ports
are utilized while binary files are not.  However, binary files run much, much faster
so are necessary for the bigger systems.

Once the tabledefs file has been set, the do_install run described next will validate
tabledefs and then install it, along with everything else, on the Pico.  Once everything
is installed, it is only necessary to run installtable to validate tabledefs, copy
it to the Pico, and validate the installation if further changes are made.

***

The same software runs on either the Pico or the clone and can use
the SD card if installed.  To install the embedded software on either,
do the following:

~~~

cd Pico
do_install

~~~

In the Pico part of the repo there is a file named commlib.py.  This
is the interface library for Hauntimator.py to talk to the hardware.
In order for Hauntimator to load the right commlib, do_install creates a
symbolic link in the Animatronics directory to the local commlib.py file.
However, commlib.py can be relinked to other commlib.py files to support
users developing controllers with other
hardware or programming languages.  commlib.py has the purpose of
decoupling Hauntimator from the hardware specifics.

***

## Pololu Maestro Support

The Animator-I board was originally designed to interface with 74HC595 chips for digital
output and PCA9685 boards for PWM output.  Input/feedback was limited to the three
control inputs Run (Reset), Main, and Trigger.  New code in the Pico libraries now
supports the use of one or more Pololu Maestro boards for PWM and/or digital output
without any interface hardware.  Additionally, some level-shifters on the I2C pins
allows them to be repurposed to UART pins to communicate with the Maestro board(s) to
provide for both output and input.

For output only, the Maestro board(s) should be attached to one of the UART outputs
in the buffered GPIO output block.  The available UART outputs are on GPIO pins 8 and 12.
One of these should be connected to the Rx pin on the Maestro board.  These go through
existing level-shifters to provide +5v signals to the Maestro.

For two-way communication, with output and input, the Maestro board should be connected
to a pair of UART pins.  If not using PCA9685 PWM boards, then GPIO pins 0 and 1 are
available.  The code does not currently support using both Maestro and PCA9685 boards
but it would be possible to connect the PCA9685s to GPIO pins 20 and 21 and the Maestro
to GPIO pins 0 and 1 with software changes.  In either case, level-shifters are required
to convert the 3.3v Pico signals to +5v for the Maestro and back to 3.3v on the inputs.

Maestro boards are designed to be daisy-chained.  The wiring is described at on the
[Pololu website](https://www.pololu.com/docs/0J40/5.g).  The code does not currently
support using multiple UARTs for Maestro boards but they can be easily daisy-chained
off of a single UART port.

As described above, the Pico/lib/tabledefs file is the key configuration file needed
to specify the hardware that the Animator board communicates with.  This file sets up
the specific Maestro communications over UART and what inputs and outputs are utilized.
The following functions used in the tabledefs file configure Maestro usage:

~~~
configureMaestroUART - Specify the UART port for all Maestro(s)
configureMaestroPWM - Specify a block of PWM output ports on a single Maestro board
configureMaestroDigital - Specify a block of digital output ports on a single Maestro board
configureMaestroDigitalInputs - Specify a block of digital inputs on a single Maestro board
~~~

More documentation on these functions may be found in the Pico/lib/tabledefs_template
file, which should be used as a starting point for creating your own tabledefs file.

***

## Top-level Code

### boot.py

The boot.py file is written to the top level of the Pico flash file
system such that it is executed at boot time.  Generally, all this
does is mount the SD card for future use.

### main.py

The main.py file is written to the top level of the Pico flash file
system such that it is executed when the Pico starts up.  This is the
executable for the animatronics.

## Library code

Several libraries are included to support all the functionality.
See the README in the lib directory for more details on those.

## Local functionality

### commlib.py

commlib.py is a small package that allows the Hauntimator executable to
interact with the controller hardware whilst remaining hardware agnostic.
commlib.py encapsulates the communications specifics for communicating
with the Pico.  To allow Hauntimator to make use of it, a symbolic link
to the specific commlib.py package should be included in the Hauntimator
executable directory.

### do_install

do_install is a shell script that installs all the Micropython code on
the Pico as well as the tabledefs file defining the hardware setup.  It
also validates the install.

do_install also optionally installs some demo/diagnostic animations.
These are simple left/right audio, to help get the audio channels hooked
up as expected, and toggling digital channels 0-7 to get those signals
hooked up right.  These go into the Pico's onboard flash memory and will
be executed when the SD card is not in the slot.

### dumpBinary.py

dumpBinary.py is a small program to dump out the contents of a binary
control file in a somewhat human-readable format (CSV so it can be
input to a spreadsheet tool).  It uses the table definitions from the
library to interpret the bits and bytes appropriately.  See the lib
README for more details on how the tables are defined and used.

### installtable

installtable is a shell script that validates the tabledefs file, installs it
on the Pico, and validates the installation.  Run it whenever the tabledefs
file is modified but only after do_install has installed the rest of the
system.

### verifyload.py

verifyload.py is a tool that validates the installation of files on the Pico.
It utilizes a 16-bit CRC checksum to verify that the files on the Pico are
identical to those on the development system.  With no arguments it validates
all files in its internal list, which should be all the files in the system.
Users may specify a specific file to validate with the -f option.

## Files

### Audio Files (.wav)

Audio files used in Hauntimator must be PCM (Wave) files.  These generally have the extension .wav and
may be mono or stereo at most sample rates.  The I2S interface currently working also requires Wave files
on the controller board.

### Comma-Separated Value Control File (.csv)

Control files installed on the controller board will be either comma-separated values or binary files.
The .csv files contain header information associating columns with digital and servo ports.  Playback
on the controller can support either CSV or binary.

### Binary Control Files (.bin)

Control files installed on the controller board in binary format are specialy formatted to contain entries
for every port defined in the tabledefs file.  Thus, they may be much larger than a simple CSV file.
However, on playback they are slammed out to the hardware without reformatting so they perform much faster.

### Animation List Files (animlist)

The animlist file contains a list of animations for the controller to have in its playlist.  The file must
be named animlist and be present where the controller code looks for it, typically in /sd/anims.  This file
contains a list of pairs of filenames in a space-separated value format.  The first value is the control file
and the second value is the audio file.  An optional third column may be included containing the
single word "idle".  If this is present, this particular animation is considered the idle animation that is
played when not playing one of the other animations.  If more than one is labeled idle, only the last one
counts.  Note that the filenames in animlist need to have full paths for the controller to be able to find
and play them.

A non-idle entry in animlist may contain a single string.  In this case, it is considered to be a fileroot
and .wav and either .bin or .csv are appended to it to make the pair of files required for an animation.

At startup, the controller looks in /sd/anims for a file named animlist.  If it is found, it is parsed and
the list of animations to be played is created.  If it is not found, then the /sd/anims directory is scanned
to find matched pairs of control and audio files.  In this mode, only control files of the preferred type
are accepted.  Specifically, the tabledefs file contains a line specifying whether binary files are preferred
or not.  If preferred, only files with the .bin extension are accepted.  If not preferred, only files with
the .csv extension are allowed.  These must be paired with audio files by name with the .wav extension.  Any
files that do not have both a control file of the preferred type and a .wav file are not put in the playback list.
In this mode, any matched pair of files with the rootname "idle" will be considered the idle animation.

When exporting control and audio files from Hauntimator, it defaults to naming them the same as the animation
file, with different extensions, in order to simplify matching them in the controller.  Hauntimator attempts
to write both CSV and binary control files when saving them locally.  This allows them to easily be written
directly to an SD card mounted on the desktop machine to be transferred later to the controller.  Then the
controller will always have the preferred type of control file available.



This software is made available for use under the GNU General Public License (GPL3).
A copy of this license is available within the repository for this software and is
included herein by reference.

***

Copyright 2025 John R. Wright, William R. Douglas - 1031_Systems
