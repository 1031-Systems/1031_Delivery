<!-- john Fri Dec 17 17:35:16 PDT 2024 -->
# images

This section of the repo contains images used in the various help files.
It also contains logo images for the various tools and tools for creating
proper icon files for linux, macOS, and windows.  These tools mostly run
under linux as that is my development environment but macMakeMacIcon.csh
runs on macOS and only creates macOS icons.   All the tools begin with
a PNG image, which is also the icon file for linux.  Then the windows 
and mac icon files are generated from the PNG image.  Usage, on linux,
of the tools is as follows:

- ./makeMacIcon.csh -i pngfile(without extension)
- ./makeWinIcon.csh -i pngfile(without extension)

The first converts name.png to name.icns and the second converts name.png to name.ico.
Note that these tools require the installation of netpbm and icnsutils packages on
linux.

If working on a Mac, use:

- ./macMakeMacIcon.csh -i pngfile(without extension)

which converts name.png to name.icns.  The mac version makes much larger
icon files per the usage directions.

The current set of icon files is:

| Tool | linux | macOS | windows 11 |
|------|-------|-------|------------|
| Hauntimator | Hlogo.png | Hlogo.icns | Hlogo.ico |
| Maestro_Animator | CElogo.png | CElogo.icns | CElogo.ico |
| joysticking | jlogo.png | jlogo.icns | jlogo.ico |

***

This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.

***

Copyright 2025 John R. Wright, William R. Douglas - 1031_Systems
