#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program dumpBinary.py
# Created by john
# Created Mon Oct 28 10:09:40 AM PDT 2024
#*********************************/

#/* Import block */
import os
import struct
import glob
import re
import sys
import math
import tables

#/* Define block */
verbosity = False

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose]\n" % name);
    sys.stderr.write("Enter purpose here.\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("-i/-infile file   :name of binary file to process\n");
    sys.stderr.write("\n\n");

#/* Main */
def main():
    global verbosity

    infilename = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        elif sys.argv[i] == '-i' or sys.argv[i] == '-infile':
            i += 1
            if i < len(sys.argv):
                infilename = sys.argv[i]
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    blockSizes = tables.getBinarysizes()
    print('blockSizes:', blockSizes)

    if infilename is None: exit()

    f = open(infilename, 'rb')
    line = f.read(blockSizes[0])
    sys.stdout.write('Time,Digital')
    for i in range(0, blockSizes[3], 4):
        sys.stdout.write(',On%d,Off%d' % (i>>2, i>>2))
    sys.stdout.write('\n')

    while len(line) > 0:
        time = int.from_bytes(line[0:blockSizes[1]], 'little')
        digital = int.from_bytes(line[blockSizes[1]:blockSizes[1] + blockSizes[2]], 'little')
        sys.stdout.write("%8d,'%16x'" % (time, digital))

        for i in range(blockSizes[1] + blockSizes[2], blockSizes[0], 4):
            onval = int.from_bytes(line[i:i+2],
                'little')
            offval = int.from_bytes(line[i+2:i+4],
                'little')
            sys.stdout.write(",'%04x','%04x'" % (onval, offval))

        sys.stdout.write('\n')
        line = f.read(blockSizes[0])


if __name__ == "__main__":
    main()

