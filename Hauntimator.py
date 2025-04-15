#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program Hauntimator.py
# Created by John R. Wright
# Created Tue Jun 13 17:35:31 PDT 2023
#*********************************/
'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

#/* Import block */
import os
import sys

import Animatronics
import MainWindow

# Utilize XML to read/write animatronics files
import xml.etree.ElementTree as ET

usedPyQt = None

try:
    # PyQt5 import block for all widgets
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5 import QtMultimedia as qm
    usedPyQt = 5
except:
    try:
        # PyQt6 import block for all widgets
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        from PyQt6.QtWidgets import *
        from PyQt6 import QtMultimedia as qm
        usedPyQt = 6
    except:
        sys.stderr.write('Whoops - Unable to find PyQt5 or PyQt6 - Quitting\n')
        exit(10)

import importlib
import importlib.metadata
# print('Version:', importlib.metadata.version('Hauntimator'))

#/* Define block */
verbosity = False

#/* Usage method */
def print_usage(name):
    """
    The method print_usage prints the standard usage message.
    Parameters
    ----------
    name : str
        The name of the application from argv[0]
    """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-f/-file infilename]\n")
    sys.stderr.write("Create and edit animatronics control channels.\n");
    sys.stderr.write("-/-h/-help             :show this information\n");
    sys.stderr.write("-V/-version            :print version information and exit\n")
    sys.stderr.write("-f/-file infilename    :Input anim file\n")
    sys.stderr.write("\n\n");

def print_module_version(module_name):
    try:
        import importlib
        import importlib.metadata
        version = importlib.metadata.version(module_name)
        print(module_name + ':', version)
        exitcode = 0
    except:
        print('Version information not available')
        exitcode = 1
    return exitcode

#/* Main */
def doAnimatronics():
    """
    The method doAnimatronics is the main function of the application.
    It parses the command line arguments, handles them, and then opens
    the main window and proceeds.
    """

    # Local Variables to support parsing an Animatronics file specified
    # on the command line
    infilename = None
    exitcode = 0

    # Parse arguments
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(exitcode);
        elif sys.argv[i] == '-V' or sys.argv[i] == '-version':
            exitcode = print_module_version('Hauntimator')
            sys.exit(exitcode)
        elif sys.argv[i] == '-f' or sys.argv[i] == '-file':
            i += 1
            if i < len(sys.argv):
                infilename = sys.argv[i]
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    # Create the global main window
    app = QApplication(sys.argv)
    main_win = MainWindow.MainWindow()
    MainWindow.PreferencesWidget.readPreferences()

    # Start with empty animation by default but AFTER Preferences have been read
    animation = Animatronics.Animatronics()

    # If an input file was specified, parse it or die trying
    if infilename is not None:
        if os.path.isfile(infilename):
            # Do not update state if we read here
            main_win.saveStateOkay = False
            try:
                animation.parseXML(infilename, uploadpath=MainWindow.SystemPreferences['UploadPath'])

            except Exception as e:
                sys.stderr.write("\nWhoops - Error reading input file %s\n" % infilename)
                sys.stderr.write("Message: %s\n" % e)
                sys.exit(11)

            main_win.saveStateOkay = True
        elif not os.path.exists(infilename):
            animation.filename = infilename
        else:
            sys.stderr.write("\nWhoops - Unable to use %s as a file\n" % infilename)
            sys.exit(11)

    # Open the main window and process events
    main_win.setAnimatronics(animation)
    main_win.show()
    app.exec_()


if __name__ == "__main__":
    doAnimatronics()

