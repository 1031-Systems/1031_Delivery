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

if(! -e $infile.png) then
    echo "Whoops - Unable to open file: $infile.png"
    goto usage
endif

# Do the right thing
if ( $OSTYPE == 'linux' ) then
    # Make icons from logo.png files
    mkdir MyIcon.iconset
    # Make various resolution levels
    pngtopam -alphapam $infile.png | pamscale -xysize 256 256 | pamtopng > MyIcon.iconset/icon256.png
    if ( $status ) goto usage
    pngtopam -alphapam $infile.png | pamscale -xysize 128 128 | pamtopng > MyIcon.iconset/icon128.png
    pngtopam -alphapam $infile.png | pamscale -xysize 32 32   | pamtopng > MyIcon.iconset/icon32.png
    pngtopam -alphapam $infile.png | pamscale -xysize 16 16   | pamtopng > MyIcon.iconset/icon16.png
    png2icns $outfile.icns MyIcon.iconset/icon*.png
    if ( $status ) goto usage
    rm -rf MyIcon.iconset
endif

exit

usage:

echo
echo 'Usage:'$0' -i inname [-o outname]'
echo '    This tool converts a png file, of any size, to a MacOS'
echo 'icon file for use on the desktop.'
echo ''
echo '-/-h/-help          :Print this helpful info'
echo '-i inname           :Name of input image without .png'
echo '-o outname          :Name of output icon file without .icns (Defaults to input name)'
echo
echo 'This tool requires installation of the pam image (netpbm) and icnsutils packages.'
echo
