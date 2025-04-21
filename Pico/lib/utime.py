'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

import time
import threading

def sleep_ms(ms):
    time.sleep(float(ms)/1000.0)

def sleep_us(us):
    time.sleep(float(us)/1000000.0)

def ticks_ms():
    return int(time.clock_gettime_ns(time.CLOCK_MONOTONIC) / 1000000)

def ticks_us():
    return int(time.clock_gettime_ns(time.CLOCK_MONOTONIC) / 1000)

def ticks_diff(now, then):
    return now-then
