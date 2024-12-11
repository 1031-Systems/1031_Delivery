<!-- john Tue Apr  2 07:11:17 AM PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->


# Pico/Hardware

This directory contains design and fabrication files for the animatronics controller
board based on the Raspberry Pi Pico and extender boards.  The basic controller board
utilizes a Raspberry Pi Pico processor board (or clone thereof), an SD card slot for
extending memory, and two 74HC595 chips for 16 bits of digital output.  In addition,
there are various connectors and pinouts for triggers, status LEDs, I2S for audio
playback, I2C for servo control on extender boards, and serial output for additional
74HC595s on extender boards.  The files for the main controller board and the 74HC595
digital extender boards are contained herein.  The PCA9685 extender boards for servos
and other PWM controls are available commercially.

