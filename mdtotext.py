#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program mdtotext.py
# Created by john
# Created Wed Apr 23 07:49:00 AM PDT 2025
#*********************************/

#/* Import block */
import os
import re
import sys

#/* Define block */
verbosity = False

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose]\n" % name);
    sys.stderr.write("Enter purpose here.\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("\n\n");

#/* Main */
def main():
    global verbosity

    filename = None

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
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    # Process from file or stdin
    if filename is not None:
        infile = open(filename, 'r')
    else:
        infile = sys.stdin

    section = 0
    subsection = 0

    line = infile.readline()
    while len(line) > 0:
        newline = line
        m = re.search('^###(.*)', line)
        if m is not None:
            subsection += 1
            newline = ('%d.%d' % (section, subsection)) + m.group(1) + '\n'
        else:
            m = re.search('^##(.*)', line)
            if m is not None:
                section += 1
                subsection = 0
                newline = ('%d.%d' % (section, subsection)) + m.group(1) + '\n'
            else:
                m = re.search('^#(.*)', line)
                if m is not None:
                    newline = m.group(1) + '\n'
        m = re.search('^\*\*\*', line)
        m2 = re.search('^~~~', line)
        if m is not None or m2 is not None:
            newline = ('----------------------------------------'
                       '----------------------------------------\n')
        m = re.search('\.png\)', line)
        if m is not None:
            newline = ''
        sys.stdout.write(newline)
        line = infile.readline()

if __name__ == "__main__":
    main()

