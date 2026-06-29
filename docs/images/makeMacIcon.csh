#!/bin/csh
#set echo

# Set initial/default values

# Parse arguments
set i = 1
while($i <= $#argv)
    if("-" == "$argv[$i]" || "-h" == "$argv[$i]" || "-help" == "$argv[$i]") then
        goto usage
    else if("$argv[$i]" == "-i" ) then
        @ i++
        if($i <= $#argv) then
            set infile=$argv[$i]
            if(! $?outfile) set outfile=$infile
        endif
    else if("$argv[$i]" == "-o" ) then
        @ i++
        if($i <= $#argv) then
            set outfile=$argv[$i]
        endif
    else
        echo
        echo "Whoops - Unrecognized argument:$argv[$i]"
        goto usage
    endif

    @ i++
end

# Do the right thing
if ( $OSTYPE == 'darwin' ) then
    # Make icons from logo.png files
    mkdir MyIcon.iconset
    ln -s ${infile}.png Icon1024.png
    cp Icon1024.png MyIcon.iconset/icon_512x512@2x.png
    sips -z 16 16     Icon1024.png --out MyIcon.iconset/icon_16x16.png
    sips -z 32 32     Icon1024.png --out MyIcon.iconset/icon_16x16@2x.png
    sips -z 32 32     Icon1024.png --out MyIcon.iconset/icon_32x32.png
    sips -z 64 64     Icon1024.png --out MyIcon.iconset/icon_32x32@2x.png
    sips -z 64 64     Icon1024.png --out MyIcon.iconset/icon_64x64.png
    sips -z 128 128   Icon1024.png --out MyIcon.iconset/icon_64x64@2x.png
    sips -z 128 128   Icon1024.png --out MyIcon.iconset/icon_128x128.png
    sips -z 256 256   Icon1024.png --out MyIcon.iconset/icon_128x128@2x.png
    sips -z 256 256   Icon1024.png --out MyIcon.iconset/icon_256x256.png
    sips -z 512 512   Icon1024.png --out MyIcon.iconset/icon_256x256@2x.png
    sips -z 512 512   Icon1024.png --out MyIcon.iconset/icon_512x512.png
    iconutil -c icns MyIcon.iconset
    mv MyIcon.icns ${outfile}.icns
    rm -rf MyIcon.iconset Icon1024.png
endif

exit

usage:

echo
echo 'Usage:'$0' -i inname [-o outname]'
echo '    This tool converts a png file, assumed to be 1024x1024, to a MacOS'
echo 'icon file for use on the desktop.'
echo ''
echo '-/-h/-help          :Print this helpful info'
echo '-i inname           :Name of input image without .png'
echo '-o outname          :Name of output icon file without .icns (Defaults to input name)'
echo
