import Animatronics

def invert(channelList, theanim):
    retval = False  # Return False if NO channels are modified
    for channel in channelList:
        if ((channel.maxLimit > 1.0e33 and channel.minLimit > -1.0e33) or
            (channel.maxLimit < 1.0e33 and channel.minLimit < -1.0e33)): continue
        retval = True   # Return True if ANY channel is modified
        for key in channel.knots:
            channel.knots[key] = (channel.maxLimit + channel.minLimit) - channel.knots[key]

    return(retval)

channel_modifiers = [invert]
channel_creators = []
channel_viewers = []

