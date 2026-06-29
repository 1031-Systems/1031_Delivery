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
if ( $OSTYPE == 'linux' ) then
    # Make icons from logo.png files
    mkdir MyIcon.iconset
    # Make various resolution levels
    pngtopam -alphapam $infile.png | pamscale -xysize 64 64 > MyIcon.iconset/icon.pam
    pngtopam -alphapam $infile.png | pamscale -xysize 48 48 >> MyIcon.iconset/icon.pam
    pngtopam -alphapam $infile.png | pamscale -xysize 32 32 >> MyIcon.iconset/icon.pam
    pngtopam -alphapam $infile.png | pamscale -xysize 16 16 >> MyIcon.iconset/icon.pam
    pamtowinicon -truetransparent MyIcon.iconset/icon.pam > $outfile.ico
    rm -rf MyIcon.iconset
endif

exit

usage:

echo
echo 'Usage:'$0' -i inname [-o outname]'
echo '    This tool converts a png file, of any size, to a Windows'
echo 'icon file for use on the desktop.'
echo ''
echo '-/-h/-help          :Print this helpful info'
echo '-i inname           :Name of input image without .png'
echo '-o outname          :Name of output icon file without .ico (Defaults to input name)'
echo
