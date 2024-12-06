<!-- john Tue Apr  2 07:11:17 AM PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
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

### dumpBinary.py

dumpBinary.py is a small program to dump out the contents of a binary
control file in a somewhat human-readable format (CSV so it can be
input to a spreadsheet tool).  It uses the table definitions from the
library to interpret the bits and bytes appropriately.  See the lib
README for more details on how the tables are defined and used.

This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.

