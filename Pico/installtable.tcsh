#!/bin/csh -f
#set echo

# Set initial/default values
set file=lib/tabledefs
set out=/dev/null

# Parse arguments
set i = 1
while($i <= $#argv)
    if("-" == "$argv[$i]" || "-h" == "$argv[$i]" || "-help" == "$argv[$i]") then
        goto usage
    else if("$argv[$i]" == "-v" || "-verbose" == "$argv[$i]") then
        set out=/dev/stdout
    else
        echo
        echo "Whoops - Unrecognized argument:$argv[$i]"
        goto usage
    endif

    @ i++
end

# Do the right thing

if(! -e $file) then
    echo
    echo Whoops - Unable to find file:$file
    echo
    exit 1
endif

echo Validating local $file
python lib/tables.py -r >& /dev/null
if($status) then
    echo
    echo Whoops - problems with tabledefs file - aborting
    echo Results of check are:
    python lib/tables.py -r -v
    exit
endif

# Get the port used by rshell (we assume it is first in the list)
set port=`rshell -l |& grep -i micropython | sed -e 's/^[^@]*@//' -e 's/ .*//' -e 's%/cu\.%/tty.%'`
echo Using port: $port >& $out

echo Installing $file on Pico
rshell --quiet cp $file /pyboard/$file >& $out

echo Resetting Pico
rshell --quiet repl '~ import machine ~ machine.reset() ~' >& $out
sleep 5

echo Validating install
python3 ./verifyload.py -p $port -f $file
if(! $status) echo Install successful

exit

usage:

echo
echo 'Usage:'$0' [-/-h/-help] [-v/-verbose]'
echo '    This tool installs the tabledefs file on the Pico.'
echo '-/-h/-help          :Print this helpful info'
echo '-v/-verbose         :Run more verbosely'
echo
