<!-- john Tue Apr  2 07:11:17 AM PDT 2024
-->
# Plugins

This section of the repo contains code and cwfilesscripts for enhancing
the built-in capabilities of Animator.  Any python file in this directory
that is recognized by pkgutils will be checked.  If it conforms to the
protocol described below, it is incorporated into Animator's menus.

***

## Protocol

The protocol for the plugins is very simple.  Plugin functions are passed
a list of the currently selected channels in Animator and the Animatronics
object that represents the entire animation.  Currently the plugins cannot
access the UI of the main window.  The plugins may make any modifications
desired to the channels in the selected list or to the Animatronics
object itself.

The plugin functions are classified as modifiers, creators,
or viewers.  Modifiers generally operate on the list of selected
channels and only those channels are redrawn after the function returns.
Creators add channels to the animation or otherwise modify it such that
the entire application must be redrawn.  Viewers make no changes to the
animation and no redraw is required.  Functions return True if changes
have been made that require redraw and False otherwise.

In the plugin's .py file. the various function's types are identified
in lists with fixed names of channel_modifiers, channel_creators, and
channel_viewers.  This is an example of the format of a plugin file:

~~~

import Animatronics

def invert(channelList, theanim):
    for channel in channelList:
        if ((channel.maxLimit > 1.0e33 and channel.minLimit > -1.0e33) or
            (channel.maxLimit < 1.0e33 and channel.minLimit < -1.0e33)): continue

        for key in channel.knots:
            channel.knots[key] = (channel.maxLimit + channel.minLimit) - channel.knots[key]

    return(True)

channel_modifiers = [invert]
channel_creators = []
channel_viewers = []

~~~

This example implements a single function invert that inverts the knots
for all selected channels.  The selected channels are passed in as the
channellist argument and the entire animation is passed in as the theanim
argument although this function only accesses the selected channel list.

The Animatronics module is imported to allow access to all the data
structures and the function type (modifier) is identified at the bottom.
Note that the empty lists are not required to be present.

***

## Plugins Currently Available

### install.py

The install.py plugin contains generic functions that are useful for
all users.  The invert example above is from the install.py plugin.
Other functions in the plugin are TBD.

### phonemes.py

The phonemes.py plugin is a helper intended to aid in aligning movement
with voice audio.  It uses pocketsphinx, from Carnegie-Mellon, to
analyze speech and generate phonemes with timing and then generates channels
to match the phonemes.  It requires pocketsphinx to be installed in your
virtual environment via:

~~~

pip install pocketsphinx

~~~

There is an accompanying data file named phonemes.csv that serves as a
translator between phonemes and channel values.  For example, the jaw
should be open to its maximum when pronouncing an ah sound and should
be closed when pronouncing an m sound.  To accomplish this, the csv
file contains a percentage value for each phoneme for each type of
movement.  Currently the only type of movement is Jaw but this can be 
extended to support lips or cheeks.  The percentage value is mapped
to the min-max range of the channel.  The ah sound is mapped to 100%
while the m sound is mapped to 0%.  Other phonemes are mapped to
intermediate values.  Users may adjust the value in the csv file to
their specific application.

Speech recognition does mess up sometimes so caveat emptor.  A common
problem is that the extent of a movement for a phoneme is based on how
fast the speaker is talking.  Rapid speech requires small movements
of the jaw while slow, enunciated speech can support larger movements.
Users can adjust for this by changing the minimum and/or maximum values
for the channel they are populating.

One other issue with pocketsphinx in particular is that it requires an
audio file sampled at 16 kHz, 16 bits per sample, mono to work correctly.
If the audio file contains singing with music, or any sound other than
speech, the recognition is crappy.  One way around this problem is to
record an appropriately sampled file of the user speaking the words to
a song in sync with the actual music and running that through the
plugin.
