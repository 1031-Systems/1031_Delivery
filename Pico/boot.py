'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

import helpers

try:
    helpers.mountSDCard()       # Mount SD card for all data files
except:
    # Ignore errors
    pass

