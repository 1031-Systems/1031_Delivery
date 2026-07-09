import serial
from serial.tools import list_ports

import sys
from sys import version_info

PY2 = version_info[0] == 2   #Running Python 2.x?

"""
Cross-platform detection of a Pololu Maestro's Command Port.

Strategy (checked in order, first hit wins):
  1. USB interface number, read from `hwid` (Windows "MI_00"/"MI_01") or
     from `location` (Linux "1-3:1.0", and Windows on pyserial >= ~3.5
     "1-4:x.0"). Interface 0 is always the Command Port, interface 1 the
     TTL Port, on every platform where the OS exposes it.
  2. Windows text fallback: `description`/`product` containing "Command"
     or "TTL", which Pololu's own Windows driver sets as the friendly name.
  3. Final fallback (used for macOS, where neither of the above is
     available): the numerically-lowest /dev/cu.usbmodem* device, since
     Pololu's docs state the Command Port always gets the lower number.
"""

import re

POLOLU_VID = 0x1FFB


def _interface_number(port):
    """Return the USB interface number (0 or 1) if we can determine it, else None."""
    m = re.search(r"MI_(\d+)", port.hwid or "", re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\.(\d+)$", port.location or "")
    if m:
        return int(m.group(1))
    return None


def _natural_sort_key(device):
    """Sort device paths/names by their trailing number so 'COM9' < 'COM10', etc."""
    m = re.search(r"(\d+)$", device)
    return (int(m.group(1)) if m else -1, device)


def find_maestro_command_port(vid=POLOLU_VID, pid=None, serial_number=None):
    """
    Find the Command Port of a connected Pololu Maestro.

    Args:
        vid: USB vendor ID to match (default: Pololu's 0x1FFB).
        pid: USB product ID to match, or None to match any Maestro model.
        serial_number: Board serial number to match, needed if multiple
            Maestros are connected, to avoid mixing up their ports.

    Returns:
        The device string (e.g. '/dev/ttyACM0', 'COM4',
        '/dev/cu.usbmodem14201') for the Command Port, or None if no
        matching Maestro was found.
    """
    candidates = [
        p for p in list_ports.comports()
        if p.vid == vid
        and (pid is None or p.pid == pid)
        and (serial_number is None or p.serial_number == serial_number)
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0].device

    # 1. Interface-number based detection (Linux, and Windows when exposed).
    numbered = [(_interface_number(p), p) for p in candidates]
    numbered = [(n, p) for n, p in numbered if n is not None]
    if numbered:
        numbered.sort(key=lambda t: t[0])
        return numbered[0][1].device

    # 2. Windows friendly-name fallback.
    if sys.platform.startswith("win"):
        for p in candidates:
            text = f"{p.description or ''} {p.product or ''}".lower()
            if "command" in text:
                return p.device

    # 3. macOS (and any other platform lacking the above info): lowest device name.
    return sorted(candidates, key=lambda p: _natural_sort_key(p.device))[0].device

#
#---------------------------
# Maestro Servo Controller
#---------------------------
#
# Support for the Pololu Maestro line of servo controllers
#
# Steven Jacobs -- Aug 2013
# https://github.com/FRC4564/Maestro/
#
# These functions provide access to many of the Maestro's capabilities using the
# Pololu serial protocol
#
class Controller:
    # When connected via USB, the Maestro creates two virtual serial ports
    # usually /dev/ttyACM0 for commands and /dev/ttyACM1 for communications.
    # Be sure the Maestro is configured for "USB Chained Port" serial mode.
    # "USB Dual Mode" will work as well, but only for a single Maestro, not a chain.
    #
    # Pololu protocol allows for multiple Maestros to be connected to a single
    # serial port. Each connected device is then indexed by number.
    def __init__(self,ttyStr=None,device=0x0c):
        # Command lead-in and device number are sent for each Pololu serial command.
        self.boardID = device
        self.PololuCmd = chr(0xaa) + chr(device)
        # Track target position for each servo. The function isMoving() will
        # use the Target vs Current servo position to determine if movement is
        # occuring.  Upto 24 servos on a Maestro, (0-23). Targets start at 0.
        self.Targets = [0] * 24
        # Servo minimum and maximum targets can be restricted to protect components.
        self.Mins = [0] * 24
        self.Maxs = [0] * 24
        self.commands = []

        # Find the Pololu Command Port
        if ttyStr is None:
            try:
                ttyStr = find_maestro_command_port()
            except:
                pass
            if ttyStr is None:
                sys.stderr.write('\nWHOOPS - Could not find Maestro Command Port\n')
                return
        else:
            # Needs methods to verify also
            sys.stderr.write('\nWarning - Could not verify specified command device:' + ttyStr + ' is a Maestro Command Port\n')
            sys.stderr.write('Using anyway!!!\n')

        print('Device:', ttyStr)
        # Open the command port without timeout for normal operations
        self.usb = serial.Serial(ttyStr, baudrate=115200)
        self.usb.close()

    # Cleanup by closing USB serial port
    def close(self):
        self.usb.close()

    # Reopen the USB serial port
    def open(self):
        self.usb.open()

    # Set the board id for the current device
    def setBoard(self, device):
        if device != self.boardID:
            self.boardID = device
            self.PololuCmd = chr(0xaa) + chr(device)

    # Do everything to send a single command to current device
    def sendOneCmd(self, cmd):
        cmdStr = self.PololuCmd + cmd
        self.open()
        if PY2:
            self.usb.write(cmdStr)
        else:
            # print('Sending:', bytes(cmdStr,'latin-1'))
            self.usb.write(bytes(cmdStr,'latin-1'))
        self.close()

    # Send a Pololu command out the serial port to current device
    def sendCmd(self, cmd):
        cmdStr = self.PololuCmd + cmd
        if PY2:
            self.usb.write(cmdStr)
        else:
            # print('Sending:', bytes(cmdStr,'latin-1'))
            self.usb.write(bytes(cmdStr,'latin-1'))

    # Send a stream of commands while holding the port open
    # Defaults to sending the internal command list
    def sendCmds(self, cmds=None):
        if cmds is None:
            cmds = self.commands
        self.open()
        for brd,cmd in cmds:
            self.setBoard(brd)
            cmdStr = self.PololuCmd + cmd
            # print('Sending from cmd list:', bytes(cmdStr,'latin-1'))
            self.usb.write(bytes(cmdStr,'latin-1'))
        self.close()
        self.clearCmds()

    # Clear the current command list
    def clearCmds(self):
        self.commands = []

    # Add a command to the command list
    def addCmd(self, cmd):
        self.commands.append((self.boardID, cmd))

    # Set channels min and max value range.  Use this as a safety to protect
    # from accidentally moving outside known safe parameters. A setting of 0
    # allows unrestricted movement.
    #
    # ***Note that the Maestro itself is configured to limit the range of servo travel
    # which has precedence over these values.  Use the Maestro Control Center to configure
    # ranges that are saved to the controller.  Use setRange for software controllable ranges.
    def setRange(self, chan, min, max):
        self.Mins[chan] = min
        self.Maxs[chan] = max

    # Return Minimum channel range value
    def getMin(self, chan):
        return self.Mins[chan]

    # Return Maximum channel range value
    def getMax(self, chan):
        return self.Maxs[chan]

    # Set channel to a specified target value.  Servo will begin moving based
    # on Speed and Acceleration parameters previously set.
    # Target values will be constrained within Min and Max range, if set.
    # For servos, target represents the pulse width in of quarter-microseconds
    # Servo center is at 1500 microseconds, or 6000 quarter-microseconds
    # Typcially valid servo range is 3000 to 9000 quarter-microseconds
    # If channel is configured for digital output, values < 6000 = Low ouput
    def setTarget(self, chan, target):
        # if Min is defined and Target is below, force to Min
        if self.Mins[chan] > 0 and target < self.Mins[chan]:
            target = self.Mins[chan]
        # if Max is defined and Target is above, force to Max
        if self.Maxs[chan] > 0 and target > self.Maxs[chan]:
            target = self.Maxs[chan]
        #
        lsb = target & 0x7f #7 bits for least significant byte
        msb = (target >> 7) & 0x7f #shift 7 and take next 7 bits for msb
        cmd = chr(0x04) + chr(chan) + chr(lsb) + chr(msb)
        self.addCmd(cmd)
        # Record Target value
        self.Targets[chan] = target

    # Set speed of channel
    # Speed is measured as 0.25microseconds/10milliseconds
    # For the standard 1ms pulse width change to move a servo between extremes, a speed
    # of 1 will take 1 minute, and a speed of 60 would take 1 second.
    # Speed of 0 is unrestricted.
    def setSpeed(self, chan, speed):
        lsb = speed & 0x7f #7 bits for least significant byte
        msb = (speed >> 7) & 0x7f #shift 7 and take next 7 bits for msb
        cmd = chr(0x07) + chr(chan) + chr(lsb) + chr(msb)
        self.addCmd(cmd)

    # Set acceleration of channel
    # This provide soft starts and finishes when servo moves to target position.
    # Valid values are from 0 to 255. 0=unrestricted, 1 is slowest start.
    # A value of 1 will take the servo about 3s to move between 1ms to 2ms range.
    def setAccel(self, chan, accel):
        lsb = accel & 0x7f #7 bits for least significant byte
        msb = (accel >> 7) & 0x7f #shift 7 and take next 7 bits for msb
        cmd = chr(0x09) + chr(chan) + chr(lsb) + chr(msb)
        self.addCmd(cmd)

    # Get the current position of the device on the specified channel
    # The result is returned in a measure of quarter-microseconds, which mirrors
    # the Target parameter of setTarget.
    # This is not reading the true servo position, but the last target position sent
    # to the servo. If the Speed is set to below the top speed of the servo, then
    # the position result will align well with the acutal servo position, assuming
    # it is not stalled or slowed.
    def getPosition(self, chan):
        cmd = chr(0x10) + chr(chan)
        self.open()
        self.sendCmd(cmd)
        lsb = ord(self.usb.read())
        msb = ord(self.usb.read())
        self.close()
        return (msb << 8) + lsb

    # Test to see if a servo has reached the set target position.  This only provides
    # useful results if the Speed parameter is set slower than the maximum speed of
    # the servo.  Servo range must be defined first using setRange. See setRange comment.
    #
    # ***Note if target position goes outside of Maestro's allowable range for the
    # channel, then the target can never be reached, so it will appear to always be
    # moving to the target.
    def isMoving(self, chan):
        if self.Targets[chan] > 0:
            if self.getPosition(chan) != self.Targets[chan]:
                return True
        return False

    # Have all servo outputs reached their targets? This is useful only if Speed and/or
    # Acceleration have been set on one or more of the channels. Returns True or False.
    # Not available with Micro Maestro.
    def getMovingState(self):
        cmd = chr(0x13)
        self.open()
        self.sendCmd(cmd)
        readval = self.usb.read()
        self.close()
        if readval == chr(0):
            return False
        else:
            return True

    # Run a Maestro Script subroutine in the currently active script. Scripts can
    # have multiple subroutines, which get numbered sequentially from 0 on up. Code your
    # Maestro subroutine to either infinitely loop, or just end (return is not valid).
    def runScriptSub(self, subNumber):
        cmd = chr(0x27) + chr(subNumber)
        # can pass a param with command 0x28
        # cmd = chr(0x28) + chr(subNumber) + chr(lsb) + chr(msb)
        self.open()
        self.sendCmd(cmd)
        self.close()

    # Stop the current Maestro Script
    def stopScript(self):
        cmd = chr(0x24)
        self.open()
        self.sendCmd(cmd)
        self.close()


if __name__ == "__main__":
    port = find_maestro_command_port()
    if port:
        print(f"Maestro Command Port: {port}")
    else:
        print("No Pololu Maestro found.")

