<!-- john Fri Jun 17 07:35:16 PDT 2023 -->
# Animatronics

This repo contains code and scripts for working with robotic
control data for animatronics.

***

## Description

The general procedure for working with animatronics is to
create control channels that may be synced to an audio stream.
The channels may act as step functions, linear paths, and
smoothed or spline paths.  Each channel is linked to a single
control on a controller.

Step functions hold a continuous value for a time and then
switch to a different value.  A subset of these are only 0 or 1
and control on/off devices like lights.  Linear paths use a
set of knots specifying some values at certain times and the
path is linearly interpolated between knots.  Smooth paths use
a similar set of knots but apply Lagrange interpolation between the
knots for a smoother motion of the controlled device.  Spline
channels use splines for the interpolation, again for a smoother
motion.

***

## Installation

In general, you will need to clone this repo to your local host.
Then, create a virtual environment for the code using venv and
activate it.  Then use pip to install the required libraries in
your virtual environment.  At this point you should be able to 
run Animator.py.  The steps are as follows:

~~~

git clone git@github.com:steelheadj/Animatronics.git
cd Animator
python3 -m virtualenv '.venv'     # Replace .venv with any name you like
source .venv/bin/activate.shname  # Where shname is your shell name
pip install -r ${OSTYPE}-requirements.txt
python ./Animator.py

~~~

Note that there are several shells supported and that bash is the
default and is activated with just .venv/bin/activate with no shell
name specified.

In addition, you may have to find the appropriate requirements file
for your system.  If the OSTYPE environment is set then you can use
the command above.  If not, you will have to replace it with the
appropriate OS type for your system.  If your system is not available,
then you have to manually install PyQt and qwt with the  following:

~~~

pip install PyQt5
pip install qwt
pip freeze -l > ${OSTYPE}-requirements.txt # To save your own config

~~~

On MacOS-darwin, the only test system I have, PyQt5 does not install
but PyQt6 does.  Meanwhile, on my CentOS Linux system, PyQt5 installs
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

Channel data may be exported to a CSV file to be transferred to an
external hardware controller.  In addition, a pipe may be used to
directly signal the controller from the system while it runs
Animator.py.

