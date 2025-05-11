#!/bin/csh -f
#set echo

# Set initial/default values
set verbosity = 0
set DeliveryRepo = 1031_Hauntimator

# Parse arguments
set i = 1
while($i <= $#argv)
    if("-" == "$argv[$i]" || "-h" == "$argv[$i]" || "-help" == "$argv[$i]") then
        goto usage
    else if("$argv[$i]" == "-v" || "$argv[$i]" == "-verbose" ) then
        set verbosity = 1
    else if("$argv[$i]" == "-f" || "$argv[$i]" == "-local" ) then
        set local = 1
    else if("$argv[$i]" == "-V" || "$argv[$i]" == "-Version" ) then
        @ i++
        if ($i <= $#argv) then
            set vnum = $argv[$i]
        endif
    else
        echo
        echo "WHOOPS - Unrecognized argument:$argv[$i]"
        goto usage
    endif

    @ i++
end

# Check that you are in the (some) virtual environment
if (! $?VIRTUAL_ENV ) then
    echo
    echo WHOOPS - Must be in python virtual environment to build
    goto usage
endif

# Check that required arguments are provided
if (! ${?vnum} ) then
    echo
    echo WHOOPS - the release version was not provided
    goto usage
endif

# Set system-specific values
if ( ${OSTYPE} == 'darwin' ) then
else if ( ${OSTYPE} == 'linux' ) then
else
    echo WHOOPS - No idea how to handle os type:${OSTYPE}
    exit
endif

# Get the latest from the repo
if ( ! $?local ) then
    if($verbosity) echo Pulling latest from github repo
    # Update to latest
    git pull origin main
    if($status) then
        echo WHOOPS - Problem pulling from github
        echo Better sort things out first
        exit 10
    endif
endif

# Check to see if this release has been previously generated
set tagcount = `git tag | wc -l`
if ( $tagcount ) then
    set tags = `git tag`
    foreach ltag ( $tags)
        if ${vnum}_${OSTYPE} == $ltag then
            echo
            echo WHOOPS - Version ${vnum}_${OSTYPE} has already been tagged
            goto usage
        endif
        if ${vnum} == $ltag then
            # Note that global release was tagged, probably elsewhere
            set globaltag = ${vnum}_${OSTYPE}
        endif
    end
endif

# Make sure nothing is being edited and that we are on main branch
set bad = `find . -name '*.swap' | wc -l`
if ($bad) then
    echo
    echo WHOOPS - Files are open for editing
    echo Save your work and try again
    goto usage
endif
git branch | grep '\* main' >& /dev/null
if ($status) then
    echo
    echo WHOOPS - Not on main branch
    goto usage
endif

if ( ! $?local ) then
    # Tag the release
    if($verbosity) echo Tagging the local release as ${vnum}_${OSTYPE}
    git tag -a ${vnum}_${OSTYPE} -m "Local build version ${vnum}_${OSTYPE}"
else
    if ($verbosity) then
        echo Would tag release as ${vnum}_${OSTYPE} in local repo
        echo and as ${vnum} in remote repo
    endif
endif

# Set up Delivery directory
rm -rf $DeliveryRepo
mkdir $DeliveryRepo
rm -f ${vnum}*.zip
rm -f ${vnum}_${OSTYPE}.tar.gz

if ( 0 ) then   # Skip the pyinstaller steps
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
endif

# Also copy over the support files
cp servotypes $DeliveryRepo
sed "s/__VERSION__/$vnum/g" Delivery_README > $DeliveryRepo/README.md
foreach f (*.dist-info)
    mkdir $DeliveryRepo/$f
    foreach g ($f/*)
        sed "s/__VERSION__/$vnum/g" $g > $DeliveryRepo/$g
    end
end

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
    if ( ${OSTYPE} == 'darwin' ) then
        sed -i '' "s/__VERSION__/$vnum/g" $f
    else if ( ${OSTYPE} == 'linux' ) then
        sed -i "s/__VERSION__/$vnum/g" $f
    endif
    # Make a plain text version of markdown files
    set bname = `echo $f | sed 's/md$/txt/'`
    pandoc -f markdown -t plain $f -o $bname
end

# Zip up the delivery
if($verbosity) then
    echo Zipping up the executables for delivery
endif
zip -qry ${vnum}_${OSTYPE}.zip $DeliveryRepo
tar czf ${vnum}_${OSTYPE}.tar.gz $DeliveryRepo

# Copy over everything needed for the basics delivery
if($verbosity) then
    echo Building basics delivery
endif
# Clean up Pico directory
rm -rf $DeliveryRepo/Pico Pico/*~ Pico/lib/*~
foreach f (`find . -name '__pycache__'`)
    rm -rf $f
end

mkdir -p $DeliveryRepo/src
cp  Animatronics.py \
    Hauntimator.py \
    joysticking.py \
    MainWindow.py \
    Widgets.py \
    $DeliveryRepo/src

cp -r docs \
    plugins \
    appdir.zip \
    $DeliveryRepo/servotypes \
    $DeliveryRepo/*.dist-info \
    $DeliveryRepo/src

cp -r COPYING \
    $DeliveryRepo/LICENSE

cp -r Pico \
    install \
    uninstall \
    $DeliveryRepo

# Update all the versions in the code and help files and dist info
if($verbosity) echo Updating all the version IDs in the release files
foreach f (`find ${DeliveryRepo} -name '*.md'`)
    if ( ${OSTYPE} == 'darwin' ) then
        sed -i '' "s/__VERSION__/$vnum/g" $f
    else if ( ${OSTYPE} == 'linux' ) then
        sed -i "s/__VERSION__/$vnum/g" $f
    endif
    # Make a plain text version of markdown files
    if(`basename $f` == README.md) then
        set bname = `echo $f | sed 's/md$/txt/'`
        pandoc -f markdown -t plain $f -o $bname
    endif
end

# Clean up leftover vi backup files
foreach f (`find ${DeliveryRepo} -name '*~'`)
    rm -f $f
end
# Clean up some other unwanted files
rm -f ${DeliveryRepo}/Pico/installtable*
rm -f ${DeliveryRepo}/Pico/dumpBinary.py
rm -f ${DeliveryRepo}/Pico/.portid

rm -f Hauntimator_${vnum}.zip
zip -qry Hauntimator_${vnum}.zip \
    $DeliveryRepo/src \
    $DeliveryRepo/LICENSE \
    $DeliveryRepo/README.* \
    $DeliveryRepo/Pico \
    $DeliveryRepo/appdir.zip \
    $DeliveryRepo/install \
    $DeliveryRepo/uninstall

# Clean up
if($verbosity) then
    echo Cleaning up build areas
endif
rm -rf dist
rm -rf build
rm -rf $DeliveryRepo

# Commit the delivery
if ( ! $?local ) then
    if (! $?globaltag) then
        if($verbosity) echo Pushing delivery tag $vnum to github
        git tag -a ${vnum} -m "Release version ${vnum}"
        git push origin $vnum
    else
        if($verbosity) echo Release $vnum already tagged in remote repo
    endif
else
    if($verbosity) echo Would tag release as $vnum in remote repo
endif

exit

usage:

echo
echo 'Usage:'$0' [-v/-verbose] -V version [-local]'
echo '    This tool packages up a release for Hauntimator and joysticking'
echo 'and related stuff and delivers it to the public repo.'
if ($verbosity) then
    echo ''
    echo '    It verifies conditions, pulls all the latest for the main branch,'
    echo 'checks to see if tags have been used before, removes previous delivery'
    echo 'products with the same tags, runs pyinstaller on the desired packages,'
    echo 'copies what is needed to the delivery area, zips and tars up the entire'
    echo 'delivery area, cleans up, and puts the release tag in the remote repo.'
    echo '    This also updates version numbers in all the docs and'
    echo 'executables to the tag value.'
endif
echo '-/-h/-help          :Print this helpful info'
echo '-v/-verbose         :Make this more verbose'
echo '-V/-Version version :Specifies the version string of the release'
echo '-local              :Build with current files and no repo updates local or remote'
echo
if ($verbosity) then
    echo 'Tagging strategy (when not running local):'
    echo 'Version of the form vn.m.l[a-z] (e.g. v0.0.7) is the global tag for the'
    echo 'release and is tagged in the remote repo from whence the actual release'
    echo 'is performed.  For each platform, a local tag is generated which has the'
    echo 'form vn.m.l[a-z]_platformname (e.g. v0.0.7_linux) and which is tagged'
    echo 'only in the local repo and not propagated to the remote repo.  The global'
    echo 'tag is, of course, also tagged in the local repo.  I think this pattern'
    echo 'will prevent accidentally overwriting tags, simplify attaching releases'
    echo 'to tags in github, avoid too many tags in the remote repo, and allow the'
    echo 'build on multiple platforms for the same version without conflict.  It'
    echo 'does not prevent code changes between releases on different platforms'
    echo 'so that could be a problem.'
    echo ''
endif
