import Animatronics

def invert(channelList, theanim):
    for channel in channelList:
        if ((channel.maxLimit > 1.0e33 and channel.minLimit > -1.0e33) or
            (channel.maxLimit < 1.0e33 and channel.minLimit < -1.0e33)): continue

        for key in channel.knots:
            channel.knots[key] = (channel.maxLimit + channel.minLimit) - channel.knots[key]

    return(True)

def statistics(channelList):
    return True

channel_modifiers = [invert]
channel_creators = []
channel_analyzers = []

