#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program csvtoanim.py
# Created by john
# Created Mon May 19 01:45:26 AM PDT 2025
#*********************************/

#/* Import block */
import os
import re
import sys
import Animatronics

#/* Define block */
verbosity = False

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose] -f/-file csvfilename\n" % name);
    sys.stderr.write("    This tool converts a comma-separated value (CSV) file of the\n");
    sys.stderr.write("form output by Hauntimator into an Animatronics file in XML format\n");
    sys.stderr.write("suitable for import into Hauntimator.\n");
    sys.stderr.write("    It expects the same number of columns in each row of the file\n");
    sys.stderr.write("but columns may be empty.  The first column is always the sample\n");
    sys.stderr.write("time in msec.  The first row should contain channel type and port number\n");
    sys.stderr.write("identifiers of the form Dn or Sn, the same format used by\n");
    sys.stderr.write("Hauntimator as output to the controller.  If characters 2-n in the name\n");
    sys.stderr.write("do not form an integer, then the port is not set in the channel.  If the\n");
    sys.stderr.write("first character in the name is not D then a PWM channel is created.\n");
    sys.stderr.write("    Output is to a file named csvfilename with .anim appended.\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("-f csvfilename    :name of CSV file to process\n");
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
            sys.stderr.write("\nWHOOPS - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    if filename is None:
        sys.stderr.write("\nWHOOPS - No CSV filename specified.\n")
        print_usage(sys.argv[0]);
        sys.exit(10);

    # Create a new Animatronics object to populate
    animation = Animatronics.Animatronics()

    with open(filename, 'r') as f:
        # Read the header line from the CSV file
        line = f.readline()

        # Split it at the commas (Could use pandas but no real need)
        channelNames = line.split(',')

        # Create an array for quick lookup later
        channels = []
        mins = []
        maxes = []

        # Create all the channels in the animatronics except time in column 0
        for name in channelNames[1:]:
            # We expect each name to be of the form Dn or Sn
            # Dn indicates a Digital channel attached to port n
            # Sn indicates a Servo or PWM channel attached to port n
            # If the name does not match this form, the port is not set and the channel is assumed to be PWM
            name = name.strip()
            if name[0] == 'D':
                channel = Animatronics.Channel(inname=name, intype=Animatronics.Channel.DIGITAL)
            else:
                channel = Animatronics.Channel(inname=name, intype=Animatronics.Channel.LINEAR)
            animation.insertChannel(channel)
            try:
                port = int(name[1:])
                channel.port = port
            except:
                # Ignore error if the name is not of form Dn or Sn
                pass
            # Save the channel in the dictionary
            channels.append(channel)
            mins.append(65535)
            maxes.append(0)
            if verbosity: print('Created a channel with name:', name)

        # Now populate the channels with the data from the CSV file
        if verbosity: print('Processing channel data')
        line = f.readline()
        while len(line) > 0:
            values = line.split(',')
            time = float(values[0]) / 1000.0    # Convert from msec to sec
            values = values[1:]
            for indx in range(len(values)):
                try:
                    value = float(values[indx])
                    # Conserve space by outputting only changes for Digital channels
                    if channels[indx].num_knots() > 0 and channels[indx].type == Animatronics.Channel.DIGITAL:
                        currvalue = channels[indx].getValueAtTime(time)
                        if currvalue is None or currvalue != value:
                            channels[indx].add_knot(time, value)
                    else:
                        channels[indx].add_knot(time, value)
                    if value < mins[indx]: mins[indx] = value
                    if value > maxes[indx]: maxes[indx] = value
                except:
                    # Ignore failures to allow for empty columns
                    pass
            line = f.readline()
            # Just in case this is the last line, set the end time
            animation.end = time

        # Set the channel limits to the min and max values found
        for indx in range(len(values)):
            if mins[indx] < maxes[indx]:
                channels[indx].minLimit = mins[indx]
                channels[indx].maxLimit = maxes[indx]

        # All done so write out the anim file
        outfilename = filename + '.anim'
        if verbosity: print('Writing to file:', outfilename)
        theXML = animation.toXML()
        with open(outfilename, 'w') as of:
            of.write(theXML)

if __name__ == "__main__":
    main()

