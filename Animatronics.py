from Preferences import *
# Utilize XML to read/write animatronics files
import xml.etree.ElementTree as ET
import sys
import os
import wave
import struct
from functools import reduce
import operator
from io import StringIO

#####################################################################
# The AudioChannel class represents the audio channel needed for doing
# animatronics.
#####################################################################
class AudioChannel:
    """
    Class: AudioChannel

    Implements an audio channel for the Animatronics application.  It
    reads a .wav file and provides information on the audio.  It also
    subsamples the audio to speed up plotting of the data.
    ...
    Attributes
    ----------
    audiofile : str
        Name of the audio file
    audio_data : byte array
        Raw binary data from the file
    samplerate : int
        Samples per second
    numchannels : int
        Number of channels (1 for mono, 2 for stereo)
    samplesize : int
        Sample size in bytes
    audiostart : float
        Time at which audio should start playing in overall animation
    audioend : float
        Time at which audio should stop playing in overall animation

    Methods
    -------
    __init__(self, filename=None)
    audioTimeRange(self)
    getPlotData(self, minTime, maxTime, maxCount)
    getAmplitudeData(self, minTime, maxTime, maxCount)
    setAudioFile(self, infilename)
    toXML(self)
    parseXML(self, inXML)
    """

    def __init__(self, filename=None):
        """
        The method __init__
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        filename=None : str
            Name of .wav file to play
        """

        self.audiofile = filename
        self.audio_data = None
        self.samplerate = 44100
        self.numchannels = 1
        self.samplesize = 2
        self.audiostart = 0.0
        self.audioend = 0.0
        if filename is not None:
            self.setAudioFile(filename)

    def audioTimeRange(self):
        """
        The method audioTimeRange returns the audio start and end times,
        in seconds.  End time is just start time plus length of the
        audio.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        """

        """Return the start and end times for the audio"""
        self.audioend = self.audiostart + float(len(self.audio_data))/self.numchannels/self.samplerate/self.samplesize
        return self.audiostart,self.audioend

    def getPlotData(self, minTime, maxTime, maxCount):
        """
        The method getPlotData returns the requested number of samples
        by subsampling the audio data within the requested range.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        minTime : float
            Start of desired time range in seconds
        maxTime : float
            End of desired time range in seconds
        maxCount : int
            Number of samples desired
        """
        if self.numchannels == 1:
            # Process mono data
            structformat = '<h'
            currTime = minTime
            xdata = []
            ydata = []
            startidx = int((minTime-self.audiostart) * self.samplerate * self.numchannels)
            endidx = int((maxTime-self.audiostart) * self.samplerate * self.numchannels)
            if endidx-startidx < maxCount: maxCount = endidx-startidx
            timeStep = (maxTime - minTime) / maxCount
            while currTime <= maxTime:
                sampleindex = int((currTime-self.audiostart) * self.samplerate) * self.numchannels * self.samplesize
                if sampleindex >= 0 and sampleindex <= len(self.audio_data) - self.samplesize*self.numchannels:
                    short = struct.unpack(structformat, self.audio_data[sampleindex:(sampleindex+self.samplesize*self.numchannels)])
                    xdata.append(currTime)
                    ydata.append(float(short[0]))
                currTime += timeStep
            return xdata, ydata, None
        else:
            # Process stereo data
            structformat = '<hh'
            currTime = minTime
            xdata = []
            leftdata = []
            rightdata = []
            startidx = int((minTime-self.audiostart) * self.samplerate * self.numchannels)
            endidx = int((maxTime-self.audiostart) * self.samplerate * self.numchannels)
            if endidx-startidx < maxCount: maxCount = endidx-startidx
            timeStep = (maxTime - minTime) / maxCount
            while currTime <= maxTime:
                sampleindex = int((currTime-self.audiostart) * self.samplerate) * self.numchannels * self.samplesize
                if sampleindex >= 0 and sampleindex <= len(self.audio_data) - self.samplesize*self.numchannels:
                    short = struct.unpack(structformat, self.audio_data[sampleindex:sampleindex+self.samplesize*self.numchannels])
                    xdata.append(currTime)
                    leftdata.append(float(short[0]))
                    rightdata.append(float(short[1]))
                currTime += timeStep
            return xdata, leftdata , rightdata

    def getAmplitudeData(self, minTime, maxTime, maxCount):
        """
        The method getAmplitudeData returns subsampled audio data that
        has been converted to an amplitude by taking the maximum of a 
        local window.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        minTime : float
            Start of desired time range in seconds
        maxTime : float
            End of desired time range in seconds
        maxCount : int
            Number of samples desired
        """

        intSize = 30
        """ Get intSize times as much data as needed, then pick max amplitude in each intSize sample window"""
        xdata, leftdata, rightdata = self.getPlotData(minTime, maxTime, maxCount*intSize)
        outx = []
        outleft = []
        outright = None
        i = 0
        while i < len(leftdata):
            outx.append(xdata[i])
            sumleft = 0.0
            for j in range(intSize):
                if i < len(leftdata):
                    sumleft = max(sumleft, abs(leftdata[i]))
                    i += 1
            outleft.append(sumleft)

        if rightdata is not None:
            outright = []
            i = 0
            while i < len(rightdata):
                outx.append(xdata[i])
                sumright = 0.0
                for j in range(intSize):
                    if i < len(rightdata):
                        sumright = max(sumright, abs(rightdata[i]))
                        i += 1
                outright.append(sumright)

        return outx, outleft, outright

        # Below here is some alternative code that might be better and might not
        """ Get as much data as needed, then pick max amplitude in each intSize sample window"""
        if rightdata is not None:
            outright = []
            minptr = 0
            maxptr = int(intSize/2)
            while minptr < len(leftdata) - int(intSize/2):
                sumleft = 0.0
                for i in range(minptr, maxptr):
                    sumleft = max(sumleft, abs(leftdata[i]))
                outright.append(sumleft)
                if maxptr < len(leftdata): 
                    maxptr += 1
                    if minptr < maxptr - intSize:
                        minptr += 1
                else:
                    minptr += 1

        return xdata, outleft, outright
        

    def setAudioFile(self, infilename):
        """
        The method setAudioFile attempts to open the specified file and,
        if successful, sets all the internal data to that read from
        the file.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        infilename : str
        """
        # Now read the audio data
        if os.path.exists(infilename):
            try:
                audio = wave.open(infilename)
                self.audiofile = infilename
                self.samplerate = audio.getframerate()
                self.numchannels = audio.getnchannels()
                self.samplesize = audio.getsampwidth()
                self.audio_data = audio.readframes(audio.getnframes())
                return True
            except:
                print('Whoops - could not read audio file:', infilename)
                pass
        return False

    def toXML(self):
        """
        The method toXML writes a block of text containing the XML
        representation of the AudioChannel object for writing to a
        file.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        """
        output = StringIO()
        if self.audiofile is not None:
            output.write('<Audio file="%s">\n' % self.audiofile)
            output.write('    <Start time="%f"/>\n' % self.audiostart)
            output.write('</Audio>\n')
        return output.getvalue()

    def parseXML(self, inXML):
        """
        The method parseXML processes an etree object containing parsed
        XML and populates the AudioChannel object.
            member of class: AudioChannel
        Parameters
        ----------
        self : AudioChannel
        inXML : etree Element
        """
        if inXML.tag == 'Audio':
            if 'file' in inXML.attrib:
                self.setAudioFile(inXML.attrib['file'])

            for start in inXML:
                if start.tag == 'Start':
                    if 'time' in start.attrib:
                        self.audiostart = float(start.attrib['time'])
        pass


#####################################################################
# The Channel class represents the information needed for doing
# animatronics with a single control channel.
#####################################################################
class Channel:
    """
    Class: Channel

    Implements a single editable channel of data of any type.  The
    Channel class stores a set of discrete points or knots representing
    a function such that no two points have the same X (time) value.  It
    provides for interpolating the data points via various methods and
    for reading from and writing to XML.
    ...
    Shared Attributes
    ----------
    DIGITAL = 0     # Digital (on/off) channel limited to 0 and 1
    LINEAR = 1      # Servo/CAN channel with linear interpolation
    SPLINE = 2      # Servo/CAN channel with Lagrange interpolation
    STEP = 3        # Servo/CAN channel with step changes

    Attributes
    ----------
    name : str
        The name of the channel
    knots : dictionary
        Dictionary of floats (Y values) with float keys (X values)
    knottitles : dictionary
        Dictionary of str (Y labels) with float keys (X values)
    type : int
        Enum of DIGITAL, LINEAR, SPLINE, or STEP
    minLimit : float
        Lowest legal Y value
    maxLimit : float
        Highest legal Y value
    port : int
        Index of port on controller for this channel (-1 means unassigned)
    rateLimit : float
        Maximum rate of change allowed for this channel in units per second
    servoType : string
        Index into dictionary of predefined servo types

    Methods
    -------
    __init__(self, inname = '', intype = LINEAR)
    add_knot(self, key, value)
    delete_knot(self, key)
    set_name(self, inname)
    num_knots(self)
    getValueAtTime(self, inTime)
    getKnotData(self, minTime, maxTime, maxCount)
    getPlotData(self, minTime, maxTime, maxCount)
    getValuesAtTimeSteps(self, startTime, endTime, timeStep)
    toXML(self)
    parseXML(self, inXML)
    """
    DIGITAL = 0     # Digital (on/off) channel limited to 0 and 1
    LINEAR = 1      # Servo/CAN channel with linear interpolation
    SPLINE = 2      # Servo/CAN channel with Lagrange interpolation
    STEP = 3        # Servo/CAN channel with step changes

    def __init__(self, inname = '', intype = LINEAR):
        """
        The method __init__
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inname='' : str
            name of channel
        intype=LINEAR : int
            enum type of channel
        """
        self.name = inname
        self.knots = {}
        self.knottitles = {}
        self.type = intype
        if intype == self.DIGITAL:
            self.minLimit = 0.0
            self.maxLimit = 1.0
        elif intype == self.LINEAR or intype == self.SPLINE:
            self.minLimit = SystemPreferences['ServoDefaultMinimum']
            self.maxLimit = SystemPreferences['ServoDefaultMaximum']
        else:
            self.maxLimit = 1.0e34
            self.minLimit = -1.0e34
        self.port = -1
        self.rateLimit = -1.0
        self.servoType = None

    def randomize(self, minTime, maxTime, maxRate=0.0, popRate=1.0):
        if maxRate == 0.0:
            maxRate = (self.maxLimit - self.minLimit)

        # Remove all knots within randomization range
        delknots = []
        for knot in self.knots:
            if knot >= minTime and knot <= maxTime:
                delknots.append(knot)
        for knot in delknots:
            self.delete_knot(knot)

        currTime = minTime
        currValue = (self.maxLimit + self.minLimit) / 2.0
        while currTime <= maxTime:
            if self.type == self.DIGITAL:
                currValue = float(random.randrange(2))
            else:
                currValue += random.uniform(-1.0, 1.0) * maxRate
            if currValue > self.maxLimit: currValue = self.maxLimit
            if currValue < self.minLimit: currValue = self.minLimit
            self.add_knot(currTime, currValue)
            currTime += 1.0/popRate

    def amplitudize(self, minTime, maxTime, signal, maxRate=0.0, cutoff=0.0, popRate=0.0):
        # If maxRate not specified, compute it
        if maxRate == 0.0:
            maxRate = (self.maxLimit - self.minLimit)

        # Make sure we have audio data to process
        if len(signal) > 0:
            if popRate == 0.0:
                # Population rate is number of points to insert per second
                popRate = (maxTime - minTime) / len(signal)
        else:
            return

        # Remove all knots within audio signal range
        delknots = []
        for knot in self.knots:
            if knot >= minTime and knot <= maxTime:
                delknots.append(knot)
        for knot in delknots:
            self.delete_knot(knot)

        currTime = minTime
        topval = max(signal)
        indx = 0
        while currTime <= maxTime:
            if indx >= len(signal): break
            if self.type == self.DIGITAL:
                currValue = 0.0
                if cutoff > 0.0:
                    if signal[indx] > cutoff:
                        currValue = 1.0
                elif signal[indx] > topval/2:
                    currValue = 1.0
            else:
                # Scale from min to max based on amplitude from 0 to topval
                currValue = (signal[indx] / topval) * (self.maxLimit - self.minLimit) + self.minLimit
            # Add knot at center of amplitude bin
            self.add_knot(currTime + 0.5/popRate, currValue)
            currTime += 1.0/popRate
            indx += 1

    def add_knot(self, key, value):
        """
        The method add_knot adds or replaces the Y value associated with
        time (X) key.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        key : float
            Time (X) value for the knot
        value : float
            Data (Y) value for the knot
        """
        self.knots[key] = value

    def delete_knot(self, key):
        """
        The method delete_knot removes the knot at time key.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        key : float
            Time (X) value for the knot to be removed
        """
        if key in self.knots: self.knots.pop(key)
        if key in self.knottitles: self.knottitles.pop(key)

    def set_name(self, inname):
        """
        The method set_name sets the name of the channel to the input value.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inname : str
            New name
        """
        self.name = inname

    def num_knots(self):
        """
        The method num_knots returns the number of knots in the channel.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        """
        return len(self.knots)

    def getValueAtTime(self, inTime):
        """
        The method getValueAtTime may eventually provide single point
        interpolation of the channel but may not.  Not currently used.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inTime : type
        """
        pass

    def getKnotData(self, minTime, maxTime, maxCount):
        """
        The method getKnotData returns arrays containing time (X) and data (Y)
        values for all the knots in the array within the specified time range.
        If there are more knots in the range than maxCount, they are
        subsampled somehow (not implemented yet).

        Currently, ALL knots are returned ALL the time.  Mostly good enough

            member of class: Channel
        Parameters
        ----------
        self : Channel
        minTime : float
            Minimum time, in seconds, of desired time range
        maxTime : float
            Maximum time, in seconds, of desired time range
        maxCount : int
            Maximum number of knots to return (not currently used)
        """

        """Returns up to maxCount of the knots along the visible part of the curve"""
        keys = sorted(self.knots.keys())
        if len(keys) < 1:
            # Return Nones if channel is empty
            return None,None
        if len(keys) < 2:
            # return single values if only one knot in channel
            return [keys[0]], [self.knots[keys[0]]]
        xdata = []
        ydata = []
        if len(keys) < maxCount:
            # Return all of them
            for key in self.knots:
                xdata.append(key)
                ydata.append(self.knots[key])
        else:
            # Weed them out somehow
            # Return all of them for now
            for key in self.knots:
                xdata.append(key)
                ydata.append(self.knots[key])
        return xdata,ydata

    def getPlotData(self, minTime, maxTime, maxCount):
        """
        The method getPlotData returns arrays of interpolated points along
        the channel data curve.  Interpolation is determined by the channel
        type with Step, Linear, and Spline currently supported.  Returns
        a pair of Nones of the channel is empty.

        The QwtPlot class plots curves with lines connecting the points so
        it is not necessary to interpolate in the Linear case.  In the Step
        case, an additional point is inserted just before each knot with
        the previous knots value causing a step function appearance.  For
        Spline, Lagrange interpolation is used to compute up to maxCount
        values along the curve from minTime to maxTime.  The Spline case is
        currently the only one that pays attention to maxCount other than
        the special case of a single knot.  In the latter case, maxCount
        values are returned with the full range of time values but the same
        data value.

            member of class: Channel
        Parameters
        ----------
        self : Channel
        minTime : float
            
        maxTime : type
        maxCount : type
        """

        """Returns up to maxCount points along the visible part of the curve"""
        keys = sorted(self.knots.keys())
        if len(keys) < 1:
            # Return Nones if channel is empty
            return None,None
        if len(keys) < 2:
            # Return a constant value between minTime and maxTime
            xdata = [minTime, maxTime]
            ydata = [self.knots[keys[0]], self.knots[keys[0]]]
        elif self.type == self.LINEAR:
            # Just return the points within the time range plus some on either side
            if len(keys) < maxCount:
                # Just send them all
                xdata = keys
                ydata = [self.knots[key] for key in keys]
            else:
                # Have to weed them out somehow
                # Just send them all for now
                xdata = keys
                ydata = [self.knots[key] for key in keys]
        elif self.type == self.STEP or self.type == self.DIGITAL:
            # To simulate a step function, output a value at the beginning and end
            # of each interval
            # Add value from left side of window to first point (?)
            xdata = [min(minTime, keys[0])]
            ydata = [self.knots[keys[0]]]
            if len(keys) < maxCount:
                xdata.append(keys[0])
                ydata.append(self.knots[keys[0]])
                for i in range(1, len(keys)):
                    xdata.append(keys[i] - 0.0000001)
                    ydata.append(self.knots[keys[i-1]])
                    xdata.append(keys[i])
                    ydata.append(self.knots[keys[i]])
            # Add value from last point to right side of window (?)
            xdata.append(max(maxTime, keys[-1]))
            ydata.append(self.knots[keys[-1]])
        elif self.type == self.SPLINE:
            # Use Lagrangian interpolation of knots
            timeStep = (maxTime - minTime) / maxCount
            currTime = minTime
            xdata = []
            ydata = []
            while currTime < maxTime + timeStep:
                # Find appropriate interval for current time
                # Use while loop so i == len(keys) when currtime greater than all keys
                i = 0
                while i < len(keys) and keys[i] < currTime:
                    i += 1
                # Wants two knots before and two after for best results
                interpKeys = keys[max(0,i-2):min(i+2,len(keys))]
                def _basis(j):
                    """
                    The method _basis
                    Parameters
                    ----------
                    j : int
                        index of basis to be calculated
                    """
                    k = len(interpKeys)
                    p = [(currTime - interpKeys[m])/(interpKeys[j] - interpKeys[m]) for m in range(k) if m != j]
                    return reduce(operator.mul, p)
                weights = []
                for i in range(len(interpKeys)):
                    weights.append(_basis(i))
                xdata.append(currTime)
                ydata.append(sum(weights[j] * self.knots[interpKeys[j]] for j in range(len(interpKeys))))

                currTime += timeStep

        else:
            # Better never get here
            sys.error.write('Whoops - Type is Invalid')
            exit(10)

        # Limit the range of plot data to min and max values
        # Linear and Step curves should be self-limiting so this really
        # applies only to Spline curves
        for i in range(len(ydata)):
            if ydata[i] > self.maxLimit:
                ydata[i] = self.maxLimit
            elif ydata[i] < self.minLimit:
                ydata[i] = self.minLimit

        return xdata,ydata


    def getValuesAtTimeSteps(self, startTime, endTime, timeStep):
        """
        The method getValuesAtTimeSteps interpolates the curve at equal
        sized steps from startTime to endTime.  This is primarily used for
        creating CSV data at regular intervals.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        startTime : float
            Start time in seconds
        endTime : float
            End time in seconds
        timeStep : float
            Time step in seconds
        encode : boolean
            Flag to indicate when to scale data values to duty cycle using servo data
        """

        if len(self.knots) == 0:
            return None

        # Short cut for spline and smooth curves
        if self.type == self.SPLINE:
            maxCount = int((endTime - startTime) / timeStep)
            _, values = self.getPlotData(startTime, endTime, maxCount)
            return values

        # Handle Linear and Step types
        keys = sorted(self.knots.keys())
        currTime = startTime
        nextkeyindex = 1
        values = []
        while currTime <= endTime:
            if currTime < keys[0]:
                if self.type == self.LINEAR or self.type == self.STEP or self.type == self.DIGITAL:
                    values.append(self.knots[keys[0]])
            elif currTime > keys[-1]:
                if self.type == self.LINEAR or self.type == self.STEP or self.type == self.DIGITAL:
                    values.append(self.knots[keys[-1]])
            else:
                # Somewhere in range so find interval
                while nextkeyindex < len(keys) and keys[nextkeyindex] <= currTime:
                    nextkeyindex += 1
                if self.type == self.LINEAR:
                    # interpolate
                    tval = ((self.knots[keys[nextkeyindex]] * (currTime - keys[nextkeyindex-1]) +
                        self.knots[keys[nextkeyindex-1]] * (keys[nextkeyindex] - currTime)) /
                        (keys[nextkeyindex] - keys[nextkeyindex-1]))
                    values.append(tval)
                    pass
                elif self.type == self.STEP or self.type == self.DIGITAL:
                    values.append(self.knots[keys[nextkeyindex-1]])

            currTime += timeStep

        return values

    def toXML(self):
        """
        The method toXML builds a block of XML from the data within the
        Channel and returns a string.
            member of class: Channel
        Parameters
        ----------
        self : Channel
        """
        output = StringIO()
        output.write('<Channel name="%s"' % self.name)
        if self.minLimit >= -1.0e33:
            output.write(' minLimit="%f"' % self.minLimit)
        if self.maxLimit <= 1.0e33:
            output.write(' maxLimit="%f"' % self.maxLimit)
        if self.port >= 0:
            output.write(' channel="%d"' % self.port)
        if self.rateLimit > 0.0:
            output.write(' rateLimit="%f"' % self.rateLimit)
        if self.servoType is not None:
            output.write(' servoType="%s"' % self.servoType)
        if self.type == self.LINEAR:
            output.write(' type="Linear">\n')
        elif self.type == self.SPLINE:
            output.write(' type="Spline">\n')
        elif self.type == self.STEP:
            output.write(' type="Step">\n')
        elif self.type == self.DIGITAL:
            output.write(' type="Digital">\n')
        for ttime in sorted(self.knots.keys()):
            if ttime not in self.knottitles:
                output.write('    <Point time="%f">\n' % ttime)
            else:
                output.write('    <Point time="%f" name="%s">\n' % (ttime, self.knottitles[ttime]))
            output.write('        %f\n' % self.knots[ttime])
            output.write('    </Point>\n')
        output.write('</Channel>\n')
        return output.getvalue()

    def parseXML(self, inXML):
        """
        The method parseXML parses an etree ElementTree and populates the
        channel fields from the XML.
        IFF name is not specified, the Points will be ADDed to the existing channel
            member of class: Channel
        Parameters
        ----------
        self : Channel
        inXML : etree ElementTree
            The preparsed XML object
        """
        if inXML.tag == 'Channel':
            # Populate metadata from attributes
            if 'name' in inXML.attrib:
                # Clean out all current knots only if name is specified
                self.knots = {}
            if 'name' in inXML.attrib and len(self.name) == 0:
                self.name = inXML.attrib['name']
            if 'minLimit' in inXML.attrib:
                self.minLimit = float(inXML.attrib['minLimit'])
            if 'maxLimit' in inXML.attrib:
                self.maxLimit = float(inXML.attrib['maxLimit'])
            if 'rateLimit' in inXML.attrib:
                self.rateLimit = float(inXML.attrib['rateLimit'])
            if 'servoType' in inXML.attrib:
                self.servoType = inXML.attrib['servoType']
            if 'channel' in inXML.attrib and self.port < 0:
                self.port = int(inXML.attrib['channel'])
            if 'type' in inXML.attrib:
                if inXML.attrib['type'] == 'Linear':
                    self.type = self.LINEAR
                elif inXML.attrib['type'] == 'Spline':
                    self.type = self.SPLINE
                elif inXML.attrib['type'] == 'Step':
                    self.type = self.STEP
                elif inXML.attrib['type'] == 'Digital':
                    self.type = self.DIGITAL
                else:
                    raise Exception('Invalid Channel Type:%s' % inXML.attrib['type'])
        else:
            raise Exception('XML is not a Channel')

        # Populate knots from Point blocks
        for point in inXML:
            if point.tag == 'Point':
                if 'time' in point.attrib:
                    ttime = float(point.attrib['time'])
                else:
                    raise Exception('Invalid XML')
                tvalue = float(point.text)
                self.add_knot(ttime, tvalue)
            else:
                raise Exception('Invalid XML')

        pass


#####################################################################
# The Animatronics class represents the information needed for doing
# animatronics synced with an audio file.
#####################################################################
class Animatronics:
    """
    Class: Animatronics

    Implements the entire Animatronics construct with audio, data channels,
    tags, and useful metadata.
    ...
    Attributes
    ----------
    filename : str
        Name of file parsed for this object (None if newly created)
    newAudio : AudioChannel
        An object holding the audio information
    channels : dictionary
        A dictionary of channels keyed to the channel name
    tags : dictionary
        A dictionary of strings keyed to time
    start : float
        Start time of the animation (ALWAYS 0.0)
    end : float
        End time of the animation (defaults to end of audio)
    sample_rate : float
        Sample rate in samples per second (defaults to 50Hz)
        Used for writing CSV files and for real-time control whenever done
    csvUploadFile : str
        Pathname to csv file when uploaded to controller
    audioUploadFile : str
        Pathname to audio file when uploaded to controller

    Methods
    -------
    __init__(self)
    parseXML(self, inXMLFilename)
    fromXML(self, testtext)
    toXML(self)
    set_audio(self, infilename)
    """
    def __init__(self):
        """
        The method __init__
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        """
        self.filename = None
        self.newAudio = None
        self.tags = {}
        self.channels = {}
        self.start = 0.0
        self.end = -1.0
        self.sample_rate = 50.0
        self.csvUploadFile = SystemPreferences['UploadCSVFile']
        self.audioUploadFile = SystemPreferences['UploadAudioFile']

    def clearTags(self):
        self.tags = {}

    def addTag(self, name, time):
        self.tags[time] = name

    def parseXML(self, inXMLFilename):
        """
        The method parseXML accepts a filename of an XML file containing an
        Animatronics specification and parses it, preserving the filename
        for later saves.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        inXMLFilename : str
            Filename of XML file to read
        """
        with open(inXMLFilename, 'r') as infile:
            testtext = infile.read()
            self.fromXML(testtext)
            self.filename = inXMLFilename

    def fromXML(self, testtext):
        """
        The method fromXML parses a block of XML text and populates the
        class members, deleting all existing data.  It is used both for
        parsing files and for parsing Undo and Redo state information.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        testtext : type
        """
        # Clean up existing stuff
        self.newAudio = None
        self.channels = {}
        self.clearTags()
        self.sample_rate = 50.0
        self.csvUploadFile = SystemPreferences['UploadCSVFile']
        self.audioUploadFile = SystemPreferences['UploadAudioFile']

        # Scan the XML text
        root = ET.fromstring(testtext)
        # Get the attributes from the XML
        if 'endtime' in root.attrib:
            self.end = float(root.attrib['endtime'])
        if 'csvUploadFile' in root.attrib:
            self.csvUploadFile = root.attrib['csvUploadFile']
        if 'audioUploadFile' in root.attrib:
            self.audioUploadFile = root.attrib['audioUploadFile']

        for child in root:
            if child.tag == 'Audio':
                self.newAudio = AudioChannel()
                self.newAudio.parseXML(child)
            elif child.tag == 'Channel':
                tchannel = Channel()
                tchannel.parseXML(child)
                self.channels[tchannel.name] = tchannel
            elif child.tag == 'Control':
                if 'rate' in child.attrib:
                    self.sample_rate = float(child.attrib['rate'])
            elif child.tag == 'Tags':
                for tag in child:
                    if tag.tag == 'Tag':
                        if 'time' in tag.attrib:
                            time = float(tag.attrib['time'])
                            self.addTag(tag.text.strip(), time)


    def toXML(self):
        """
        The method toXML creates and returns a block of XML text from 
        the object's members.  The text may be written to a file or saved
        as state for Undo and Redo.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        """
        output = StringIO()
        output.write('<?xml version="1.0"?>\n')
        output.write('<Animatronics starttime="%f"' % self.start)
        if self.end > self.start:
            output.write(' endtime="%f"' % self.end)
        if self.csvUploadFile is not None:
            output.write(' csvUploadFile="%s"' % self.csvUploadFile)
        if self.audioUploadFile is not None:
            output.write(' audioUploadFile="%s"' % self.audioUploadFile)
        output.write('>\n')
        output.write('<Control rate="%f"/>\n' % self.sample_rate)
        if self.newAudio is not None:
            output.write(self.newAudio.toXML())
        if len(self.tags) > 0:
            output.write('<Tags>\n')
            for tag in self.tags:
                output.write('    <Tag time="%f">\n' % tag)
                output.write(self.tags[tag] + '\n')
                output.write('    </Tag>\n')
            output.write('</Tags>\n')
        for channel in self.channels.values():
            output.write(channel.toXML())
        output.write('</Animatronics>\n')
        return output.getvalue()

    def set_audio(self, infilename):
        """
        The method set_audio accepts the specified audio filename and
        creates a new AudioChannel object for that audio file.  This
        associates the audio file with this animation.
            member of class: Animatronics
        Parameters
        ----------
        self : Animatronics
        infilename : type
        """
        self.newAudio = AudioChannel(infilename)

if __name__ == "__main__":
    # Run some self tests
    anim = Animatronics()
    anim.parseXML(sys.argv[1])
