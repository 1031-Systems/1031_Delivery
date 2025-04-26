#!/bin/bash -f

file=lib/tabledefs
out=/dev/null

# Determine which rshell to use
rshell=rshell
if ! which rshell >& /dev/null; then
    if [ -f ../rshell ]; then
        rshell='../rshell'
    else
        echo Whoops - Unable to find rshell tool needed for installation
        exit 10
    fi
fi

port=`${rshell} -l | grep -i micropython | sed -e 's/^[^@]*@//' -e 's/ .*//' -e 's%/cu\.%/tty.%'`

${rshell} --quiet cp $file /pyboard/$file >& $out

${rshell} --quiet repl '~ import machine ~ machine.reset() ~' >& $out
# Sleep long enough for Pico to reboot
sleep 5

if [ -f ../verifyload ]; then
    ../verifyload -p $port -f $file
else
    python3 verifyload.py -p $port -f $file
fi

