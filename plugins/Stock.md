<!-- john Fri Jun 27 07:35:16 PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->


<a name="top">
&nbsp;
</a>

# Help for Stock Plugins

The stock plugins contain Hauntimator that provide useful capabilities that might
be considered standard issue functions.  The list currently includes:

+ [invert](#invert)
+ [repeat](#repeat)
+ [replicate](#replicate)

<a name="invert">
&nbsp;
</a>

### invert

The invert plugin inverts the set of selected channels.  To invert is to mirror
the channel vertically between the current limits.  It performs the same function
as the invert in the individual channel popup but can invert multiple channels in
one execution.

<a name="repeat">
&nbsp;
</a>

### repeat

The repeat plugin is used to copy the knots within a given time range and repeatedly
paste them into the selected channels as many times as specified, each time appending
the new knots later in time.  The user specifies a block of time by start and end
and the plugin repeats that block of time into the future as desired.  For example,
if the start time is 5.0 and the end time is 10.0 and the count is 5, the data in the
range from 5.0 to 10.0 will be repeated in ranges 10.0-15.0, 15.0-20.0, 20.0-25.0,
25.0-30.0, and 30.0-35.0.  This tool is useful for repetitive activities.

<a name="replicate">
&nbsp;
</a>

### replicate

The replicate plugin is used to replicate a channel as many times as desired.  For
example, to create a larsen scanner you need as many digital channels as you want
the scanner to cover.  Rather than creating 8 or 16 empty channels, replicate will
take a single channel and replicate it as many times as specified, incrementing the
port number if it is set and appending the copy number to the channel name.  For
example, replicating channel XYZ with port number 7 a specified 3 times will create
channels XYZ_1, XYZ_2, and XYZ_3 with port numbers 8, 9, and 10 respectively.  All
the knots in channel XYZ will be copied to the new channels as well.
