'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

import os

def memstats(fs):
    stat = os.statvfs(fs)
    size = stat[1] * stat[2]
    free = stat[0] * stat[3]
    used = size - free

    KB = 1024
    MB = 1024 * 1024

    print('Stats for file system:', fs)
    print("Size : {:,} bytes, {:,} KB, {} MB".format(size, size / KB, size / MB))
    print("Used : {:,} bytes, {:,} KB, {} MB".format(used, used / KB, used / MB))
    print("Free : {:,} bytes, {:,} KB, {} MB".format(free, free / KB, free / MB))
    print()

memstats("/")

print('Root file system contents')
print('/:', os.listdir())
if 'lib' in os.listdir(): print('/lib:', os.listdir('/lib'))
if 'anims' in os.listdir(): print('/anims:', os.listdir('/anims'))
print()

if 'sd' in os.listdir():
    memstats('/sd')
    print('/sd:', os.listdir('/sd'))
else:
    print('Unable to find SD card under /sd')


