<!-- john Tue Apr  2 07:11:17 AM PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->


# Pico

This section of the repo mostly contains code that runs on a Raspberry Pi Pico
or clone thereof to perform animatronics based on the control and audio
data provided by Hauntimator.

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

