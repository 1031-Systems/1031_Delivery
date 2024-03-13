<!-- john Fri Dec 17 17:35:16 PDT 2023 -->
# Animatronics

This repo contains code and scripts for working with robotic
control data for animatronics.  It is designed to work with
board designs created by Bill Douglas and available for
download at [Somewhere](https://www.google.com).

This codebase contains an application, ANimator, for creating control
channel data for directing the animatronics and code for
executing on a Raspberry Pi Pico for performing the animations.
The Animator application is intended to be board-agnostic so
users may develop code for different processors such as 
Arduino or other Raspberry Pi versions.

***

## Description

The general procedure for working with animatronics is to
create control channels that may be synced to an audio stream.
The channels may act as step functions, linear paths, and
smoothed or spline paths.  Each channel is linked to a single
control on a controller.

![Animator Main Window](docs/images/allpanes.png)

Once the control channels have been created and validated to be
synchronized with the audio, they are installed on the control
hardware in flash memory or on an SD card.  Then the software
on the control board runs to perfrom the animations and play 
the audio.

***

## Installation

The currently available version is 1.0.0(b).  It is totally beta.
Seems to work for me but I know the ins and outs.  Previous 
versions may someday be available.

In general, you will need to clone this repo to your local host.
Then, create a virtual environment for the code using venv and
activate it.  Then use pip to install the required libraries in
your virtual environment.  At this point you should be able to 
run Animator.py.  The steps are as follows:

~~~

git clone git@github.com:steelheadj/Animatronics.git
cd Animatronics
python3 -m venv '.venv'     # Replace .venv with any name you like
source .venv/bin/activate.shname  # Where shname is your shell name
pip install --upgrade pip
pip install -r ${OSTYPE}-requirements.txt
python ./Animator.py

~~~

Note that there are several shells supported. bash is the
default and is activated with just .venv/bin/activate with no shell
name specified.

In addition, you may have to find the appropriate requirements file
for your system.  If the OSTYPE environment is set then you can use
the command above.  If not, you will have to replace it with the
appropriate OS type for your system.  If your system is not available,
then you have to manually install PyQt and qwt with the  following:

~~~

pip install PyQt5 # (or PyQt6, whichever will actually install)
pip install PythonQwt
pip install rshell
pip freeze -l > ${OSTYPE}-requirements.txt # To save your own config

~~~

On darwin, the only MacOS test system I have, PyQt5 does not install
but PyQt6 does.  Meanwhile, on my Rocky 9 test system, PyQt5 installs
just fine whilst PyQt6 does not.  You will have to install whichever
works for you.  Animator.py is written to work with either PyQt5 or
PyQt6.


***

## Details

### Animator.py

Animator.py is the visual user interface for creating and editing the
control channels.  It displays a stack of channels, typically with 
audio at the top, in which all channels display the same time range.
During audio playback, a red bar moves across all channels so that
the user may visually align behaviors between channels and the audio
track.

Step functions hold a continuous value for a time and then
switch to a different value.  A subset of these are only 0 or 1
and control on/off devices like lights.  Linear paths use a
set of knots specifying some values at certain times and the
path is linearly interpolated between knots.  Smooth paths use
a similar set of knots but apply Lagrange interpolation between the
knots for a smoother motion of the controlled device.  Spline
channels use splines for the interpolation, again for a smoother
motion.

Channel data may be exported to a CSV file to be transferred to an
external hardware controller.  In addition, a pipe may be used to
directly signal the controller from the system while it runs
Animator.py.

### Pico

This installation includes files for using a Raspberry Pi Pico or
clone for your animatronics controller.  This comes in two flavors:
Halloween and Christmas.  The Halloween version uses a Pico clone
with a 16MB flash memory to hold one to five animations of about
thirty seconds in length each.  These are expected to run when a lucky
trick-or-treater approaches your house.  In order to use the 16MB of
flash available in the clone, firmware must be loaded that supports
the 16MB.  Several versions seem to be available but the only one
that worked with our test clone was the WEACT v1.21.0 one at:

[https://micropython.org/download/WEACTSTUDIO/](https://micropython.org/download/WEACTSTUDIO/)

Feel free to try others with your clone.

The Christmas version can use a regular Pico with only 2MB of flash
or a clone and uses an external SD card to store the audio and
animation data.  This version is expected to run multiple hours of
animations, audio, flashing lights, etc. so the external memory is
required.  Either the clone or the actual Pico can work with the
standard 2MB firmware v1.21.0 available at:

[https://micropython.org/download/RPI_PICO/](https://micropython.org/download/RPI_PICO/)

The interfaces to the servos and digital controls are different
for the two versions so the helper libraries are specific to each.
The correct libraries should be loaded depending on the desired
functionality.  Helpful scripts, based on rshell, may be used to
install the correct versions.

To install the Christmas version, the only one working right now do:

~~~

cd Pico
install_Christmas
cd ..

~~~

In the Pico part of the repo there is a file named commlib.py.  This
is the interface library for Animator.py to talk to the hardware.
In order for Animator to load the right commlib, there should be a
symbolic link in the Animatronics directory to the appropriate
commlib.py file to support users developing controllers with other
hardware or programming languages.  commlib.py has the purpose of
decoupling Animator from the hardware specifics.

Animator's direct communication with the hardware is optional and
Animator will function without commlib.  In this case, the audio and
control files will need to be transferred to the hardware via rshell,
thonny, direct copy to SD card, or other mechanism.  Animator can
output the CSV control files locally for separate transfer and the
audio files must already exist on the system.
