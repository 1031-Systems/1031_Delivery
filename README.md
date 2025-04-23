<!-- john Fri Dec 17 17:35:16 PDT 2023 -->
# Animatronics

This repo contains code and scripts for working with robotic
control data for animatronics.  It is designed to work with
board designs created by Bill Douglas and available for
download with this repo at [Pico/Hardware](Pico/Hardware/).

This codebase contains an application, Hauntimator, for creating control
channel data for directing the animatronics and code for
executing on a Raspberry Pi Pico for performing the animations.
The Hauntimator application is intended to be board-agnostic so
users may develop code for different processors such as 
Arduino or other Raspberry Pi versions.

It also contains a utility application, joysticking.py, for recording
joystick actions into Hauntimator channels.

***

## Description

The general procedure for working with animatronics is to
create control channels that may be synced to an audio stream.
The channels may act as step functions, linear paths, and
smoothed or spline paths.  Each channel is linked to a single
control on a controller.

![Hauntimator Main Window](docs/images/allpanes.png)

Once the control channels have been created and validated to be
synchronized with the audio, they are installed on the control
hardware in flash memory or on an SD card.  Then the software
on the control board runs to perform the animations and play 
the audio.

***

## Installation

This README accompanies version __VERSION__.  It is totally beta.
Seems to work for me but I know the ins and outs.  Someday this 
may be a previous version that may be available.

To install this software, simply unzip the zip file and it should
be ready to run.  The zip files are identified with their version
number and the OS type they were built for.

The Hauntimator and joysticking applications generally work best
when they are able to communicate with and control the animatronics
controller hardware.  This requires the following steps to install
the embedded software into the flash memory of the Raspberry Pi
Pico (currently the only supported controller):

- Plug a USB cable into the Pico board and this PC
- Install an appropriate MicroPython image on the board (see Pico/README)
- cd to the Pico/lib directory
- copy tabledefs_template to tabledefs and edit it as needed (see Pico/lib/README)
- cd to the Pico directory
- run "do_install" to install all the embedded software on the Pico
- run "verifyload" to verify that all the necessary files made it

Note that it is not necessary for Hauntimator and joysticking to
communicate with the Pico.  It is perfectly possible to create
animation control files, write them to an SD card on the PC, and 
then transfer the SD card to the controller.  However, a direct
connection provides for more rapid iterations when developing and
testing an animation.

***

## Details

### Hauntimator

Hauntimator is the visual user interface for creating and editing the
control channels.  It displays a stack of channels, typically with 
audio at the top, in which all channels display the same time range.
During audio playback, a red bar moves across all channels so that
the user may visually align behaviors between channels and the audio
track.

Step functions hold a continuous value for a time and then
switch to a different value.  A subset of these are only 0 or 1
and control on/off devices like lights.  Linear paths use a
set of knots specifying some values at certain times and the
path is linearly interpolated between knots.  Spline paths use
a similar set of knots but apply Lagrange interpolation between the
knots for a smoother motion of the controlled device.

Channel data may be exported to a CSV file to be transferred to an
external hardware controller.  In addition, a pipe may be used to
directly signal the controller from the system while it runs
Hauntimator.

### joysticking

joysticking is a GUI application for recording joystick actions into
Hauntimator channels.  It reads an animation file created by Hauntimator
and provides an interface for mapping joystick axes and buttons to
channels in the animation.  Then it enables recording of the joystick
actions into those channels, playback of the channels, and saving of
the animation file for Hauntimator to read.

### Pico

This installation includes files for using a Raspberry Pi Pico or
clone for your animatronics controller.  The provided software is in 
the Pico directory.  See the README there for more details.

In the Pico part of the repo there is a file named commlib.py.  This
is the interface library for Hauntimator to talk to the hardware.
In order for Hauntimator to load the right commlib, there should be a
symbolic link in the Animatronics directory to the appropriate
commlib.py file to support users developing controllers with other
hardware or programming languages.  commlib.py has the purpose of
decoupling Hauntimator from the hardware specifics.  Note that the
do_install script used to install the embedded software on the Pico
creates this link so you don't have to do it explicitly.

Hauntimator's direct communication with the hardware is optional and
Hauntimator will function without commlib.  In this case, the audio and
control files will need to be transferred to the hardware via rshell,
thonny, direct copy to SD card, or other mechanism.  Hauntimator can
output the CSV control files locally for separate transfer and the
audio files must already exist on the system.

## Caveat

This package is intended to support creating animations and running
them on the type of board specified in the Pico/Hardware section of the
repo.  Due to the nature of the embedded software, it is quite possible
to modify any of the code that runs on the Pico.  However, there is no
mechanism for pushing changes back to the repo.  In addition, the main
applications are built with pyinstaller such that they can be run in
most environments without the user needing to set up virtual environments,
installing all the required packages, etc.  It is intended to simplify
the process.  It does not provide access to the source code.

We are fervent supporters of free and open software.  Anyone who wishes to
access the Hauntimator and joysticking source code is welcome to it.  You
may join the development team or you may download the code from its repo.
Drop me a line at SW.1031_Systems at gmail.com.  Note that I am generally
clueless about running a repo with more than one developer so a repo
manager would be extremely useful.

This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.

***

Copyright 2025 John R. Wright, William R. Douglas - 1031_Systems
