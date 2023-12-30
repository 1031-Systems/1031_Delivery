<!-- john Wed Aug  2 17:01:44 PDT 2023  -->
<a name="top">
&nbsp;
</a>

# Animator QuickStart

![Animator Main Window](images/allpanes.png)

Animator is a tool for creating servo, digital, and other control
channels to synchronize animatronic movements to each other and to
an optional audio soundtrack.  The general strategy is to load the
audio and then create control channels one at a time until you have
what you want.  Then you will upload the control data to a
controller that will play back the actions using your devices.

## Load the Audio (Optional but Usual)

Go to File->Open Audio File to bring up a file browser.  Select the
desired audio file (limited to .wav format for now) and click Open.
The audio channel(s) will be displayed in a pane at the top of the
window.

## Add Control Channels

Animator supports any number of digital (on/off), servo (angles), and
numeric (real numbers) channels.  As you add them, each channel will occupy
a pane all the way across the window and they will be stacked from top
to bottom.  Add a channel for all the devices you wish to control and
populate the channels with control points.

### Add a Digital Channel

To add a digital channel to control a device that is either on or off,
hit Ctrl-D (Digital).  A popup will appear requesting a name for the
channel and an optional channel number.  A unique name is required.
The channel number may be skipped for now but the system will be
unable to control the channel until the number is supplied but this can
be done later.  Click Save to create the empty channel, which will 
appear in a pane on the display.

To populate the digital channel, hold down the Shift key and click the
left mouse button within the blue area.  If you click below the 
midpoint the system will insert a 0 (Off) at that time.  If above the
midpoint a 1 (On) will be inserted.  You may drag the cursor, keeping
the left button pressed (you may release the Shift) left or right to
change the time or up or down to change from On to Off.  Generally
you will want to insert a control point at time 0 as the initial state
of the device, either On or Off.  Continue adding control points at
appropriate times to turn the device on or off at those times in the
playback.

### Add a Servo or Numeric Channel

To add a servo or numeric channel, hit Ctrl-N (Numeric).  A popup
will appear demainding a unique Name and other, mostly optional,
information (referred to as metadata).  You must supply the name.
If you are controlling a servo and know the model, you may select 
it from the Servo dropdown list.  This will automatically set
appropriate limits for the channel.  If you don't know the model or
you are defining a numeric channel, do not select a servo model.

For now, do not bother with any other entries in this widget and
click Save.  All the fields will default to reasonable values and
all may be changed later.  Only the name remains the same.  The
empty channel pane will appear with red lines near the top and
bottom signifying limits, defaulting to 0 and 180 degrees if the
servo type was specified and 0 and 4095 otherwise.  Note that 0
and 4095 are generally NOT good limits for servos.  See the main
Help pane for more detail on setting and using the limits.

Populate the channel with control points by holding down the Shift
key and clicking the Left mouse button.  This will insert a point
where the mouse was clicked (or at the nearest limit if outside
the valid range).  You can drag the point up/down or left/right to
position it as you wish.  Generally a point should be inserted at
time 0 as the initial value for the playback.  This value should be
the rest or nominal servo position.  Additional points are added
over the time range to define the animation.  The last point in the
channel should be chosen to end at the same value as the channel
begins with.

## Syncing with Audio

For now, synchronizing playback with audio is a visual process.
Hit Ctrl-P to start and stop playback of the audio.  As the audio is
playing, observe the vertical green bar as it crosses all the
channel panes.  The green bar is synced with the time and (SHOULD)
also with the audio.  Note that the audio playback and the displayed
bar position are totally separate processes so they often get out
of sync when first playing.  Just stop playback and restart it and
the sync should be good.  You can often tell how good the sync is
by observing the bar on the audio channel while listening.

As you play the audio, you can stop it at critical junctures and then
adjust the control points to match the time.  You can also adjust the
magnitudes of the control signals.  To edit any control point,
simply left click on the box around the point and drag it as you like.

## Animating your Devices

To complete the process there are a few steps.  The first is to assign
channel numbers to all the
channels.  Once that is done, the control file is uploaded to the
controller via File->Export->Upload to Controller.  Finally, the
controller is started via its start mechanism.  Stuff should happen.

## Saving Your Work

Saving your current state, with the audio filename and the control
channels, use File->Save or File->Save As to bring up a file browser
to select a filename and path to save your work.  Conversely, use
File->Open to open a file or use the -f filename option on the
command line.

