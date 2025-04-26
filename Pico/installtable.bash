#!/bin/bash -f

file=lib/tabledefs
out=/dev/null

set port=`rshell -l | grep -i micropython | sed -e 's/^[^@]*@//' -e 's/ .*//' -e 's%/cu\.%/tty.%'`

rshell --quiet cp $file /pyboard/$file >& $out

rshell --quiet repl '~ import machine ~ machine.reset() ~' >& $out

if [ -f ../verifyload ]; then
    ../verifyload -p $port -f $file
else
    python3 verifyload.py -p $port -f $file
fi

