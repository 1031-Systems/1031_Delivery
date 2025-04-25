<!-- john Fri Jun 27 07:35:16 PDT 2024 -->
<!-- This software is made available for use under the GNU General Public License (GPL). -->
<!-- A copy of this license is available within the repository for this software and is -->
<!-- included herein by reference. -->

# Hot Key Cheat Sheet
---
## Normal Keys
- Space - Play/Pause Playback
- P - Toggle Playback controls display
- T - Toggle Tag panel display
- Del - Delete selected point(s) or channel(s)

## Control Keys
- Ctrl-+ - Zoom In around Cursor
- Ctrl- - - Zoom Out around Cursor
- Ctrl-A - Select All Channels
- Ctrl-Shift-A - Deselect All Channels
- Ctrl-C - Copy selected channel(s)
- Ctrl-D - Insert a New Digital channel
- Ctrl-F - Fit all data to display
- Ctrl-I - Insert at
- Ctrl-N - New animation
- Ctrl-O - Open animation file
- Ctrl-P - Insert a New PWM channel
- Ctrl-Shift-P - Send Play command to Hardware
- Ctrl-Q - Quit
- Ctrl-R - Restore channel under cursor display range to default
- Ctrl-S - Save animation file
- Ctrl-Shift-S - Save animation file with another name
- Ctrl-T - Add Tag at green bar
- Ctrl-V - Paste (Overwrite or Insert)
- Ctrl-X - Cut selected channel(s)
- Ctrl-Z - Undo
- Ctrl-Shift-Z - Redo

### In Help widgets, some of the hot keys are remapped as follows:
- Ctrl-F - Open/Close the finder tool within the Help widget
- Ctrl-P - Print the contents of the Help widget
- Ctrl-W - Close the Help widget

Most other hot keys do not work in the Help widgets when running on Linux.
However, Mac OSX routes all key events to the menubar first so most of the hot
keys work in all windows.  This will be confusing.

## Arrow Keys
- Left Arrow - Shift selected knots in channel 0.1 secs to left
- Right Arrow - Shift selected knots in channel 0.1 secs to right
- Up Arrow - Shift selected knots in channel 128 units up
- Down Arrow - Shift selected knots in channel 128 units down
- Ctrl - Modifies to shift 0.1x
- Shift - Modifies to shift 10x

## Mouse Actions
### In Control Channel Pane
- Shift-Left - Insert or delete control point in channel
- Ctrl-Left - Toggle selection of channel
- Left - Select to modify control point(s) or Click-n-drag to select multiple points
- Right - Bring up channel submenu
- Wheel - Zoom vertical range of channel

### In Tag Pane
- Shift-Left on tag - Delete tag
- Shift-Left off tag - Insert tag
- Ctrl-Left on tag - Zoom display to tag
- Left on tag - Select to modify tag time
- Left Drag Side to Side - Move selected tag left and right

### In Audio Pane
- Left - Set current playback to click position
- Left Drag - Continue setting current playback to drag position
- Ctrl-Left Drag Up and Down - Zoom time range
- Ctrl-Left Drag Side to Side - Pan time range left and right

---
## General Mouse Usage
The left mouse button is used for most activities.  Without Shift or
Control, it is used for editing tags or control points.  With Shift
it is used for inserting or deleting tags or control points.  With
Control it is used to Select or Deselect a channel, adding it to or
removing it from the set of selected channels, when clicked on the
channel title region.

Within an audio pane, the left mouse button without shift or 
control, selects the current cursor position as the playback time.
With Ctrl, it zooms and pans the time range for the entire display.

Within a channel pane, the wheel zooms the vertical data range about
the location of the cursor.  The right mouse button brings up the
tools menu for the channel pane.

***

Copyright 2025 John R. Wright, William R. Douglas - 1031_Systems
