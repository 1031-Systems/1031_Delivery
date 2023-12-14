# SPDX-FileCopyrightText: 2023 Guido van Rossum <guido@cwi.nl> and others.
#
# SPDX-License-Identifier: PSF-2.0
"""
`adafruit_wave`
================================================================================

Read and write standard WAV-format files


* Author(s): Jeff Epler

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

# pylint: disable=missing-class-docstring,redefined-outer-name,missing-function-docstring,invalid-name,import-outside-toplevel,too-many-instance-attributes,consider-using-with,no-self-use,redefined-builtin,not-callable,unused-variable,attribute-defined-outside-init,too-many-public-methods,no-else-return
# imports

__version__ = "0.0.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_wave.git"

from collections import namedtuple
import builtins
import struct


__all__ = ["open", "Error", "Wave_read", "Wave_write"]


class Chunk:
    def __init__(self, file, align=True, bigendian=True, inclheader=False):
        self.closed = False
        self.align = align  # whether to align to word (2-byte) boundaries
        if bigendian:
            strflag = ">"
        else:
            strflag = "<"
        self.file = file
        self.chunkname = file.read(4)
        if len(self.chunkname) < 4:
            raise EOFError
        try:
            self.chunksize = struct.unpack_from(strflag + "L", file.read(4))[0]
        except struct.error:
            raise EOFError from None
        if inclheader:
            self.chunksize = self.chunksize - 8  # subtract header
        self.size_read = 0
        try:
            self.offset = self.file.tell()
        except (AttributeError, OSError):
            self.seekable = False
        else:
            self.seekable = True

    def getname(self):
        """Return the name (ID) of the current chunk."""
        return self.chunkname

    def getsize(self):
        """Return the size of the current chunk."""
        return self.chunksize

    def close(self):
        if not self.closed:
            try:
                self.skip()
            finally:
                self.closed = True

    def isatty(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return False

    def seek(self, pos, whence=0):
        """Seek to specified position into the chunk.
        Default position is 0 (start of chunk).
        If the file is not seekable, this will result in an error.
        """

        if self.closed:
            raise ValueError("I/O operation on closed file")
        if not self.seekable:
            raise OSError("cannot seek")
        if whence == 1:
            pos = pos + self.size_read
        elif whence == 2:
            pos = pos + self.chunksize
        if pos < 0 or pos > self.chunksize:
            raise RuntimeError
        self.file.seek(self.offset + pos, 0)
        self.size_read = pos

    def tell(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return self.size_read

    def read(self, size=-1):
        """Read at most size bytes from the chunk.

        If size is omitted or negative, read until the end
        of the chunk.
        """

        if self.closed:
            raise ValueError("I/O operation on closed file")
        if self.size_read >= self.chunksize:
            return b""
        if size < 0:
            size = self.chunksize - self.size_read
        if size > self.chunksize - self.size_read:
            size = self.chunksize - self.size_read
        data = self.file.read(size)
        self.size_read = self.size_read + len(data)
        if self.size_read == self.chunksize and self.align and (self.chunksize & 1):
            dummy = self.file.read(1)
            self.size_read = self.size_read + len(dummy)
        return data

    def skip(self):
        """Skip the rest of the chunk.

        If you are not interested in the contents of the chunk,
        this method should be called so that the file points to
        the start of the next chunk.
        """

        if self.closed:
            raise ValueError("I/O operation on closed file")
        if self.seekable:
            try:
                n = self.chunksize - self.size_read
                # maybe fix alignment
                if self.align and (self.chunksize & 1):
                    n = n + 1
                self.file.seek(n, 1)
                self.size_read = self.size_read + n
                return
            except OSError:
                pass
        while self.size_read < self.chunksize:
            n = min(8192, self.chunksize - self.size_read)
            dummy = self.read(n)
            if not dummy:
                raise EOFError


class Error(Exception):
    pass


WAVE_FORMAT_PCM = 0x0001

_array_fmts = None, "b", "h", None, "i"

_wave_params = namedtuple(
    "_wave_params", "nchannels sampwidth framerate nframes comptype compname"
)


class Wave_read:
    """Used for wave files opened in read mode.

    Do not construct directly, but call `open` instead."""

    def initfp(self, file):
        self._convert = None
        self._soundpos = 0
        self._file = Chunk(file, bigendian=0)
        if self._file.getname() != b"RIFF":
            raise Error("file does not start with RIFF id")
        if self._file.read(4) != b"WAVE":
            raise Error("not a WAVE file")
        self._fmt_chunk_read = 0
        self._data_chunk = None
        while 1:
            self._data_seek_needed = 1
            try:
                chunk = Chunk(self._file, bigendian=0)
            except EOFError:
                break
            chunkname = chunk.getname()
            if chunkname == b"fmt ":
                self._read_fmt_chunk(chunk)
                self._fmt_chunk_read = 1
            elif chunkname == b"data":
                if not self._fmt_chunk_read:
                    raise Error("data chunk before fmt chunk")
                self._data_chunk = chunk
                self._nframes = chunk.chunksize // self._framesize
                self._data_seek_needed = 0
                break
            chunk.skip()
        if not self._fmt_chunk_read or not self._data_chunk:
            raise Error("fmt chunk and/or data chunk missing")

    def __init__(self, f):
        self._i_opened_the_file = None
        if isinstance(f, str):
            f = builtins.open(f, "rb")
            self._i_opened_the_file = f
        # else, assume it is an open file object already
        try:
            self.initfp(f)
        except:
            if self._i_opened_the_file:
                f.close()
            raise

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    #
    # User visible methods.
    #
    def getfp(self):
        """Get the underlying file object"""
        return self._file

    def rewind(self):
        """Go back to the start of the audio data"""
        self._data_seek_needed = 1
        self._soundpos = 0

    def close(self):
        """Close the file"""
        self._file = None
        file = self._i_opened_the_file
        if file:
            self._i_opened_the_file = None
            file.close()

    def tell(self):
        """Get the current position in the audio data"""
        return self._soundpos

    def getnchannels(self):
        """Get the number of channels (1 for mono, 2 for stereo)"""
        return self._nchannels

    def getnframes(self):
        """Get the number of frames"""
        return self._nframes

    def getsampwidth(self):
        """Get the sample width in bytes"""
        return self._sampwidth

    def getframerate(self):
        """Get the sample rate in Hz"""
        return self._framerate

    def setpos(self, pos):
        """Seek to a particular position in the audio data"""
        if pos < 0 or pos > self._nframes:
            raise Error("position not in range")
        self._soundpos = pos
        self._data_seek_needed = 1

    def readframes(self, nframes):
        """Read frames of audio data"""
        if self._data_seek_needed:
            self._data_chunk.seek(0, 0)
            pos = self._soundpos * self._framesize
            if pos:
                self._data_chunk.seek(pos, 0)
            self._data_seek_needed = 0
        if nframes == 0:
            return b""
        data = self._data_chunk.read(nframes * self._framesize)
        if self._convert and data:
            data = self._convert(data)
        self._soundpos = self._soundpos + len(data) // (
            self._nchannels * self._sampwidth
        )
        return data

    #
    # Internal methods.
    #

    def _read_fmt_chunk(self, chunk):
        try:
            (
                wFormatTag,
                self._nchannels,
                self._framerate,
                dwAvgBytesPerSec,
                wBlockAlign,
            ) = struct.unpack_from("<HHLLH", chunk.read(14))
        except struct.error:
            raise EOFError from None
        if wFormatTag == WAVE_FORMAT_PCM:
            try:
                sampwidth = struct.unpack_from("<H", chunk.read(2))[0]
            except struct.error:
                raise EOFError from None
            self._sampwidth = (sampwidth + 7) // 8
            if not self._sampwidth:
                raise Error("bad sample width")
        else:
            raise Error("unknown format: %r" % (wFormatTag,))
        if not self._nchannels:
            raise Error("bad # of channels")
        self._framesize = self._nchannels * self._sampwidth
        self._comptype = "NONE"
        self._compname = "not compressed"


class Wave_write:
    """Used for wave files opened in write mode.

    Do not construct directly, but call `open` instead."""

    def __init__(self, f):
        self._i_opened_the_file = None
        if isinstance(f, str):
            f = builtins.open(f, "wb")
            self._i_opened_the_file = f
        try:
            self.initfp(f)
        except:
            if self._i_opened_the_file:
                f.close()
            raise

    def initfp(self, file):
        self._file = file
        self._convert = None
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = 0
        self._nframeswritten = 0
        self._datawritten = 0
        self._datalength = 0
        self._headerwritten = False

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    #
    # User visible methods.
    #
    def setnchannels(self, nchannels):
        """Set the number of channels (1 for mono, 2 for stereo)"""
        if self._datawritten:
            raise Error("cannot change parameters after starting to write")
        if nchannels < 1:
            raise Error("bad # of channels")
        self._nchannels = nchannels

    def getnchannels(self):
        """Get the number of channels (1 for mono, 2 for stereo)"""
        if not self._nchannels:
            raise Error("number of channels not set")
        return self._nchannels

    def setsampwidth(self, sampwidth):
        """Set the sample width in bytes"""
        if self._datawritten:
            raise Error("cannot change parameters after starting to write")
        if sampwidth < 1 or sampwidth > 4:
            raise Error("bad sample width")
        self._sampwidth = sampwidth

    def getsampwidth(self):
        """Get the sample width in bytes"""
        if not self._sampwidth:
            raise Error("sample width not set")
        return self._sampwidth

    def setframerate(self, framerate):
        """Set the sample rate in Hz"""
        if self._datawritten:
            raise Error("cannot change parameters after starting to write")
        if framerate <= 0:
            raise Error("bad frame rate")
        self._framerate = int(round(framerate))

    def getframerate(self):
        """Get the sample rate in Hz"""
        if not self._framerate:
            raise Error("frame rate not set")
        return self._framerate

    def setnframes(self, nframes):
        if self._datawritten:
            raise Error("cannot change parameters after starting to write")
        self._nframes = nframes

    def getnframes(self):
        return self._nframeswritten

    def setparams(self, params):
        """Set all parameters at once"""
        nchannels, sampwidth, framerate, nframes, comptype, compname = params
        if self._datawritten:
            raise Error("cannot change parameters after starting to write")
        self.setnchannels(nchannels)
        self.setsampwidth(sampwidth)
        self.setframerate(framerate)
        self.setnframes(nframes)

    def tell(self):
        """Get the current position in the audio data"""
        return self._nframeswritten

    def writeframesraw(self, data):
        """Write data to the file without updating the header"""
        if not isinstance(data, (bytes, bytearray)):
            data = memoryview(data).cast("B")
        self._ensure_header_written(len(data))
        nframes = len(data) // (self._sampwidth * self._nchannels)
        if self._convert:
            data = self._convert(data)
        self._file.write(data)
        self._datawritten += len(data)
        self._nframeswritten = self._nframeswritten + nframes

    def writeframes(self, data):
        """Write data to the file and update the header if needed"""
        self.writeframesraw(data)
        if self._datalength != self._datawritten:
            self._patchheader()

    def close(self):
        """Close the file"""
        try:
            if self._file:
                self._ensure_header_written(0)
                if self._datalength != self._datawritten:
                    self._patchheader()
                self._file.flush()
        finally:
            self._file = None
            file = self._i_opened_the_file
            if file:
                self._i_opened_the_file = None
                file.close()

    #
    # Internal methods.
    #

    def _ensure_header_written(self, datasize):
        if not self._headerwritten:
            if not self._nchannels:
                raise Error("# channels not specified")
            if not self._sampwidth:
                raise Error("sample width not specified")
            if not self._framerate:
                raise Error("sampling rate not specified")
            self._write_header(datasize)

    def _write_header(self, initlength):
        assert not self._headerwritten
        self._file.write(b"RIFF")
        if not self._nframes:
            self._nframes = initlength // (self._nchannels * self._sampwidth)
        self._datalength = self._nframes * self._nchannels * self._sampwidth
        try:
            self._form_length_pos = self._file.tell()
        except (AttributeError, OSError):
            self._form_length_pos = None
        self._file.write(
            struct.pack(
                "<L4s4sLHHLLHH4s",
                36 + self._datalength,
                b"WAVE",
                b"fmt ",
                16,
                WAVE_FORMAT_PCM,
                self._nchannels,
                self._framerate,
                self._nchannels * self._framerate * self._sampwidth,
                self._nchannels * self._sampwidth,
                self._sampwidth * 8,
                b"data",
            )
        )
        if self._form_length_pos is not None:
            self._data_length_pos = self._file.tell()
        self._file.write(struct.pack("<L", self._datalength))
        self._headerwritten = True

    def _patchheader(self):
        assert self._headerwritten
        if self._datawritten == self._datalength:
            return
        curpos = self._file.tell()
        self._file.seek(self._form_length_pos, 0)
        self._file.write(struct.pack("<L", 36 + self._datawritten))
        self._file.seek(self._data_length_pos, 0)
        self._file.write(struct.pack("<L", self._datawritten))
        self._file.seek(curpos, 0)
        self._datalength = self._datawritten


def open(f, mode=None):  # pylint: disable=redefined-builtin
    """Open a wave file in reading (default) or writing (``mode="w"``) mode.

    The argument may be a filename or an open file.

    In reading mode, returns a `Wave_read` object.
    In writing mode, returns a `Wave_write` object.
    """
    if mode is None:
        if hasattr(f, "mode"):
            mode = f.mode
        else:
            mode = "rb"
    if mode in ("r", "rb"):
        return Wave_read(f)
    elif mode in ("w", "wb"):
        return Wave_write(f)
    else:
        raise Error("mode must be 'r', 'rb', 'w', or 'wb'")
