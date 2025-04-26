#!/bin/csh -f
#set echo

# Set initial/default values
set verbosity = 0
set DeliveryRepo = temp_Delivery

# Parse arguments
set i = 1
while($i <= $#argv)
    if("-" == "$argv[$i]" || "-h" == "$argv[$i]" || "-help" == "$argv[$i]") then
        goto usage
    else if("$argv[$i]" == "-v" || "$argv[$i]" == "-verbose" ) then
        set verbosity = 1
    else if("$argv[$i]" == "-f" || "$argv[$i]" == "-local" ) then
        set local = 1
    else if("$argv[$i]" == "-f" || "$argv[$i]" == "-force" ) then
        set force = 1
    else if("$argv[$i]" == "-V" || "$argv[$i]" == "-Version" ) then
        @ i++
        if ($i <= $#argv) then
            set vnum = $argv[$i]
        endif
    else
        echo
        echo "Whoops - Unrecognized argument:$argv[$i]"
        goto usage
    endif

    @ i++
end

# Check that required arguments are provided
if (! ${?vnum} ) then
    echo
    echo Whoops - the release version was not provided
    goto usage
endif

set vnum = ${vnum}_${OSTYPE}

# Set system-specific values
if ( ${OSTYPE} == 'darwin' ) then
    set sed_flags = '-I ""'
else if ( ${OSTYPE} == 'linux' ) then
    set sed_flags = '-i'
else
    echo WHOOPS - No idea how to handle os type:${OSTYPE}
    exit
endif

# Check to see if this release has been previously generated
set tagcount = `git tag | wc -l`
if ( $tagcount ) then
    set tags = `git tag`
    foreach ltag ( $tags)
        if $vnum == $ltag then
            echo
            echo Whoops - Version $vnum has already been tagged
            goto usage
        endif
    end
endif

# Make sure nothing is being edited and that we are on main branch
set bad = `find . -name '*.swap' | wc -l`
if ($bad) then
    echo
    echo Whoops - Files are open for editing
    echo Save your work and try again
    goto usage
endif
git branch | grep '\* main' >& /dev/null
if ($status) then
    echo
    echo Whoops - Not on main branch
    goto usage
endif

if ( ! $?local ) then
    # Update to latest
    git pull origin main
    if($status && ! $?force) then
        echo Whoops - Problem pulling from github
        echo Better sort things out first
        exit 10
    endif

    # Tag the release
    if($verbosity) echo Tagging the release files
    git tag -a $vnum -m "Release version $vnum"
endif

# Set up Delivery directory
rm -rf $DeliveryRepo
mkdir $DeliveryRepo

# Build the single directory distributions
foreach package (Ha jo rshell verifyload)
    if($verbosity) then
        echo Building the package $package
        pyinstaller ${package}.spec --noconfirm >& /dev/null
    else
        pyinstaller ${package}.spec --noconfirm >& /dev/null
    endif
end

# Move the important stuff to the delivery directory
rm -rf $DeliveryRepo/_internal
mv -f dist/Hauntimator/Hauntimator $DeliveryRepo
mv -f dist/Hauntimator/_internal $DeliveryRepo
mv -f dist/joysticking/joysticking $DeliveryRepo
mv -f dist/rshell $DeliveryRepo
mv -f dist/verifyload/verifyload $DeliveryRepo

# Also copy over the support files
cp servotypes $DeliveryRepo
sed "s/__VERSION__/$vnum/g" Delivery_README > $DeliveryRepo/README.md

# Build the single directory tools for each hardware type
foreach hw (Pico)
    if($verbosity) then
        echo Working on hardware package $hw
    endif
    # First copy everything in repo in that directory to the Delivery area
    foreach f (`git ls-tree -r --name-only HEAD | grep "^$hw"`)
        set dname = `dirname $f`
        mkdir -p ${DeliveryRepo}/${dname}
        cp $f ${DeliveryRepo}/${dname}
    end
end

# Update all the versions in the code and help files and dist info
if($verbosity) echo Updating all the version IDs in the release files
foreach f (`find ${DeliveryRepo} -name '*.md'`)
    sed $sed_flags "s/__VERSION__/$vnum/g" $f 
    # Make a plain text version of markdown files
    set bname = `echo $f | sed 's/md$/txt/'`
    ./mdtotext.py < $f > $bname
end
foreach f (`find ${DeliveryRepo} -name METADATA`)
    sed $sed_flags "s/__VERSION__/$vnum/g" $f
end

# Zip up the delivery
zip -qr ${vnum}.zip $DeliveryRepo

# Clean up
if($verbosity) then
    echo Cleaning up build areas
endif
rm -rf dist
rm -rf build

# Commit the delivery
if ( ! $?local ) then
    if($verbosity) echo Pushing delivery tag to github
    #git commit -m "Delivery of Release $vnum" -a
    git push origin $vnum
endif

exit

usage:

echo
echo 'Usage:'$0' [-v/-verbose] -V version'
echo '    This tool packages up a release for Hauntimator or joysticking'
echo 'and delivers it to the public repo.'
if ($verbosity) then
    echo 'It uses pyinstaller to build a few files for distribution.'
    echo 'That requires a spec file named for the packages.  Then it'
    echo 'copies all the necessary stuff to the delivery repo and'
    echo 'pushes it up to github.'
    echo '    This also updates version numbers in all the docs and'
    echo 'executables to a single value.'
endif
echo '-/-h/-help          :Print this helpful info'
echo '-v/-verbose         :Make this more verbose'
echo '-V/-Version version :Specifies the version string of the release'
echo
