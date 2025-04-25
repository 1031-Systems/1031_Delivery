<!-- john Tue Apr  2 07:11:17 AM PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL3). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->


# Pico/lib

This section of the repo mostly contains code that runs on a Raspberry Pi Pico
or clone thereof to perform animatronics based on the control and audio
data provided by Hauntimator.  This section of the repo contains the Python
libraries loaded onto the Pico and called directly or indirectly from boot.py
or main.py.  Some of the libraries are included to support desktop testing
and are NOT installed on the Pico.

***

## Libraries installed on the Pico controller

Several libraries are included and installed on the Pico to support all the functionality. 

### helpers.py

helpers.py is a grabbag of utility functions used by main.py for a variety of purposes.

The primary block of code implements the WavePlayer class.  The WavePlayer is mostly a
standard class for reading a PCM file and sending the audio data over I2S to a sound card.
However, it has a few additional features.  One is that it spawns a new thread to perform
all the data reads.  Another is that it allocates fixed-size binary data
buffers upfront and reuses them to avoid garbage collection.  Another is that it also
performs reads on the animation control file and provides the data to the animation
control thread.  If the animation control data is in binary format, it uses fixed-size,
preallocated buffers to avoid garbage collection.

Another helpers.py function is supporting data transfer over USB from the desktop.  It
contains a polling method that can be called from the main loop to see if data has
arrived.  If so, another method may be called to handle that input.  Generally, the desktop
system sends a character to indicate the function, then additional ASCII data to specify
the complete action.

Another useful method in helpers.py is findAnimFiles.  This method searches the specified
directory on the Pico, either in local flash or on an installed SD card, and returns a
list of available animations following a set of rules.  Thus, the user can write a set of
files to an SD card, insert it into the card slot, reboot the Pico, and then play the
animations without changing the code on the Pico.

helpers.py also contains some hooks for accessing servos and digital ports via the tables.py
library.

### memstats.py

memstats.py is a simple module that, when imported, prints out some statistics on the
onboard flash memory system and the SD card filesystem if it is mounted.  It is imported
from a command line tool accessing the Pico to display the info for the user.  It is NOT
imported by the regular controller software.

### pca9685.py

pca9685.py contains an implementation of a PCA9685 class.  The pca9685 is a commercially
available package
that supports up to 16 PWM outputs per package via an I2C interface.  The class provides
the interface to the pca9685.  It is based on a fairly simple package by Kevin McAleer
with extensions to feed binary data in much faster that the previous methods.

### sdcard.py

sdcard.py is an implementation of a class to support an SD card.  It is pretty standard
with no additions for this project.

### servo.py

servo.py is an implementation of a class to support a set of servos driven from a pca9685
package.  It is mostly obviated by a derived class in tables.py that directly pushes
binary data to the pca9685 bypassing this class.  However, when setting single servos,
it does go through this class.

### tabledefs (derived from tabledefs_template)

The tabledefs file contains the configuration information for which logical ports for
both PWM and digital outputs are attached to which pins and interfaces on the Pico
controller board.  These are then interpreted within the tables.py library to properly
route values to the appropriate controls.  The tabledefs file also contains a flag to
signal the standard use of either ASCII CSV control files or binary-encoded files.  In
general, for small applications of less than 5 outputs, a CSV file is adequate.  For
larger systems containing up to 64 PWM outputs and 96 digital outputs, the binary file
format is required for performance to meet the 50 Hz update rate desirement.

In general, changing the tabledefs file makes existing binary files incompatible with
the new configuration (there are exceptions but you have to understand what's going on).
Thus, it is best to define the configuration with room to grow and then build animations
that utilize a subset of the existing configuration.

The tabledefs file is manually produced by editing the tabledefs_template file to match
the user's hardware system and saving it as tabledefs.  Within tabledefs, the assignment
of servo port numbers to PCA9685 boards and GPIO pins and the assignment of digital
port numbers to 595 bits and GPIO pins is made.  Hauntimator associates ports with
channels and the embedded software, via tabledefs, associates ports with pins.  Thus,
channel values referenced by port number are properly routed to the correct pin.

The tabledefs file also has a flag to prefer binary control files over ASCII CSV files
when set to True.  If this flag is True, the embedded software will automagically convert
CSV files to binary when sent of the USB connection.  CSV files will generally work
okay when there are fewer than about 5 channels of control data.  For more than that,
it is best to use binary files to maintain the desired cycle time of under 20msec.

The tabledefs file is typically installed on the controller from the user's system and
is thus typically the same file on both the embedded system and the desktop system
running Hauntimator.  Hauntimator uses commlib.py which uses tables.py which uses
tabledefs to allow Hauntimator to write binary files on the desktop.  This only works
properly when the embedded and desktop tabledefs are in sync.  Users are required to
make sure this is the case.

### tables.py

tables.py is a library that supports the use of the tabledefs file for specifying the
ports that are available for use by the Pico.  This is a somewhat complicated topic
so suffice it to say that the user can specify the number of availabe PWM and digital
ports and how they are connected to the control pins and interfaces on the controller
board via a fairly short file named tabledefs.  tables.py interprets the content of
tabledefs at import time to then support that configuration.

tables.py also contains a main program that runs a variety of self-tests on the
configuration to make sure the user has not done something too foolish.  It also has
a hook to convert CSV control files to the binary format specific to the configuration
specified.  These may be run on the desktop for validation and to create control files
to be written to an SD card mounted on the desktop prior to installation on the Pico
controller board.

### wave.py

wave.py is a fairly standard PCM (Wave) audio file library with an addition to support
reading into fixed-size, previously allocated buffers.  To maintain high performance
within the animatronics process and meet our 50 Hz update desirement, using previously
allocated buffers over and over eliminates a LOT of garbage collection.  The readinto
method is the key addition for this purpose.

## Libraries NOT installed on the Pico

There are some libraries that are provided to mimic the behavior of the associated
libraries available within the Pico's standard set.  These are provided so that some
code may be run/tested in the desktop environment prior to installing it on the Pico.

### machine.py

machine.py implements a few of the functions and definitions in the machine library
for defining Pins, PWM operations, I2S interfaces, and I2C interfaces.  It is barely
enough to get the code to execute and performs very little activity.  It does print
the state of a Pin when it is accessed so users may be able to track what is going on.

### utime.py

utime.py is a wrapper for time.py such that some (many?) functions may be run and
actually perform their expected function.  In particular, utime contains sleep functions
in units of msec and usec as well as functions for measuring duration of activites in
msec or usec.  Of course, timing of activities in the desktop environment will vary
wildly from the Pico's values.

***

This software is made available for use under the GNU General Public License (GPL3).
A copy of this license is available within the repository for this software and is
included herein by reference.

***

Copyright 2025 John R. Wright, William R. Douglas - 1031_Systems
