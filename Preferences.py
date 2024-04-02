# System Preferences Block
SystemPreferences = {
'MaxDigitalChannels':48,        # Maximum number of digital channels controller can handle
'MaxServoChannels':32,          # Maximum number of servo/numeric channels controller cah handle
'ServoDefaultMinimum':0,        # Default minimum servo setting
'ServoDefaultMaximum':4095,     # Default maximum servo setting
'Ordering':'Numeric',           # Ordering for channels in window
'AutoSave':True,                # Perfrom saving automatically flag
'ShowTips':True,                # Show tool tips flag
'ServoDataFile':'servos.csv',   # Name of file containing predefined servos
'UploadCSVFile':'/pyboard/data.csv',     # Name of uploaded CSV file on controller
'UploadAudioFile':'/pyboard/data.wav',   # Name of uploaded audio file on controller
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
'UploadCSVFile':'str',
'UploadAudioFile':'str',
'TTYPortRoot':'str',
}

