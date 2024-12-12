'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

# System Preferences Block
SystemPreferences = {
'MaxDigitalChannels':48,        # Maximum number of digital channels controller can handle
'MaxServoChannels':32,          # Maximum number of servo/numeric channels controller cah handle
'ServoDefaultMinimum':0,        # Default minimum servo setting
'ServoDefaultMaximum':65535,    # Default maximum servo setting
'Ordering':'Numeric',           # Ordering for channels in window
'AutoSave':True,                # Perfrom saving automatically flag
'ShowTips':True,                # Show tool tips flag
'ServoDataFile':'servotypes',   # Name of file containing predefined servos
'UploadPath':'/sd/anims/',      # Name of upload directory on controller
'TTYPortRoot':'/dev/ttyACM',    # Root of tty port for usb comm
}
SystemPreferenceTypes = {
'MaxDigitalChannels':'int',
'MaxServoChannels':'int',
'ServoDefaultMinimum':'int',
'ServoDefaultMaximum':'int',
'Ordering':['Alphabetic','Numeric','Creation'], # Alphabetic by name, Numeric by port number, or creation order
'AutoSave':'bool',
'ShowTips':'bool',
'ServoDataFile':'str',
'UploadPath':'str',
'TTYPortRoot':'str',
}

