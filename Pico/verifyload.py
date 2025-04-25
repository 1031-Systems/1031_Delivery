#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program verifyload.py
# Created by john
# Created Wed Feb 19 10:06:38 AM PST 2025
#*********************************/

#/* Import block */
import os
import sys

# Set up search path so we can find commlib and associated files
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

sys.path.append(application_path)

# Import commlib for my board
try:
    import commlib
except:
    sys.stderr.write('\n\nWhoops - commlib is unavailable - aborting\n\n')
    sys.exit(10)

usedPyQt = None


#/* Define block */
verbosity = False

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose] [-f/-file filename]\n")
    sys.stderr.write("    This tool validates that file(s) installed on the Pico are identical\n");
    sys.stderr.write("to those on the development system.  Returned status is zero if all files\n");
    sys.stderr.write("match and nonzero otherwise.\n");
    sys.stderr.write("    It uses a 16-bit CRC to test for identicalness.  Note that the Pico\n");
    sys.stderr.write("must be running the standard animatronics installation.\n");
    sys.stderr.write("\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("-f/-file filename :file to validate (Default: all in standard installation)\n")
    sys.stderr.write("\n\n");

#/* Main */
def main():
    global verbosity

    # Initialize
    filename = None
    allfiles = [
        'lib/servo.py',
        'lib/wave.py',
        'lib/pca9685.py',
        'lib/sdcard.py',
        'lib/memstats.py',
        'lib/tables.py',
        'lib/tabledefs',
        'lib/helpers.py',
        'boot.py',
        'main.py',
    ]

    returncode = 0  # Happy

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        elif sys.argv[i] == '-f' or sys.argv[i] == '-file':
            i += 1
            if i < len(sys.argv):
                filename = sys.argv[i]
        elif sys.argv[i] == '-p' or sys.argv[i] == '-port':
            i += 1
            if i < len(sys.argv):
                port = sys.argv[i]
                commlib.portRoot = port
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    if filename is not None:
        allfiles = [filename]

    for fname in allfiles:
        if verbosity: print('Processing file:', fname)

        # Generate the checksum for the local file
        lsum = commlib.filecrc16(fname)
        if verbosity: print('Local file checksum:', lsum)

        # Get the Pico's reported checksum
        rsum = commlib.getFileChecksum(fname)
        if verbosity: print('Installed file checksum:', rsum)

        # And compare them, outputting appropriate reporting verbiage
        if lsum == -1:
            print('Local file not found:', fname)
            returncode = 3  # Unhappy
        if rsum == -1:
            print('Installed file not found:', fname)
            returncode = 3  # Unhappy
        if lsum != rsum and lsum >= 0 and rsum >= 0:
            print('Local and installed files do not match:', fname)
            returncode = 3  # Unhappy

    return returncode

if __name__ == "__main__":
    code = main()
    sys.exit(code)

