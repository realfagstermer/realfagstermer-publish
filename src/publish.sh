#!/bin/bash

#==========================================================
# Setup environment 
#==========================================================

if [ "$(basename "$(pwd)")" == "src" ]; then
    cd ..
fi

function install_deps
{
    echo Installing/updating dependencies
    pip install -U rdflib pytz python-dateutil requests configparser
    pip install git+git://github.com/danmichaelo/skosify.git
    xc=$?

    if [ $xc != 0 ]; then
        echo
        echo -----------------------------------------------------------
        echo ERROR:
        echo Could not install dependencies using pip
        echo -----------------------------------------------------------
        exit 1
    fi
}

if [ ! -f ENV/bin/activate ]; then

    echo
    echo -----------------------------------------------------------
    echo Virtualenv not found. Trying to set up
    echo -----------------------------------------------------------
    echo
    virtualenv ENV
    xc=$?

    if [ $xc != 0 ]; then
        echo
        echo -----------------------------------------------------------
        echo ERROR:
        echo Virtualenv exited with code $xc.
        echo You may need to install or configure it.
        echo -----------------------------------------------------------
        exit 1
    fi

    echo Activating virtualenv
    . ENV/bin/activate

    install_deps

else

    echo Activating virtualenv
    . ENV/bin/activate

fi

#==========================================================
# Produce RDF
#==========================================================

python -m src.publish
xc=$?
if [ $xc != 0 ]; then
    echo Exiting
    exit 0
fi

#==========================================================
# Commit changes to git repo
#==========================================================

if [ ! -d realfagstermer ]; then

    git clone git@github-bot:realfagstermer/realfagstermer.git
    xc=$?
    if [ $xc != 0 ]; then
        echo
        echo -----------------------------------------------------------
        echo ERROR:
        echo Could not clone realfagstermer git repo
        echo -----------------------------------------------------------
        exit 1
    fi
fi

cd realfagstermer
git config user.name "ubo-bot"
git config user.email "danmichaelo+ubobot@gmail.com"
git checkout master
git pull
xc=$?

if [ $xc != 0 ]; then

    echo
    echo -----------------------------------------------------------
    echo ERROR:
    echo Could not git pull. Conflict?
    echo -----------------------------------------------------------
    exit 1

fi

cp ../realfagstermer.ttl ./

git add realfagstermer.ttl
git commit -m "Update realfagstermer.ttl"
git push --mirror origin  # locally updated refs will be force updated on the remote end !

cd ..


#==========================================================
# Update triple store 
#==========================================================

python src/update_triple_store.py


#==========================================================
# Publish compressed dumps
#==========================================================

BASENAME=realfagstermer
DUMPS_DIR=/projects/data.ub.uio.no/dumps

echo Preparing dumps
bzip2 -k $BASENAME.nt
bzip2 -k $BASENAME.rdf.xml
bzip2 -k $BASENAME.ttl

zip $BASENAME.nt.zip $BASENAME.nt
zip $BASENAME.rdf.xml.zip $BASENAME.rdf.xml
zip $BASENAME.ttl.zip $BASENAME.ttl

cp $BASENAME.nt.bz2 $DUMPS_DIR/
cp $BASENAME.rdf.xml.bz2 $DUMPS_DIR/
cp $BASENAME.ttl.bz2 $DUMPS_DIR/

cp $BASENAME.nt.zip $DUMPS_DIR/
cp $BASENAME.rdf.xml.zip $DUMPS_DIR/
cp $BASENAME.ttl.zip $DUMPS_DIR/

cp $BASENAME.nt $DUMPS_DIR/
cp $BASENAME.rdf.xml $DUMPS_DIR/
cp $BASENAME.ttl $DUMPS_DIR/

rm *.bz2 *.zip

#==========================================================
# Publish stats
#==========================================================


if [ ! -d realfagstermer.github.io ]; then

    git clone git@github.com:realfagstermer/realfagstermer.github.io.git
    xc=$?
    if [ $xc != 0 ]; then
        echo
        echo -----------------------------------------------------------
        echo ERROR:
        echo Could not clone realfagstermer.github.io git repo
        echo -----------------------------------------------------------
        exit 1
    fi
fi

cd realfagstermer.github.io
git checkout master
git pull
xc=$?

if [ $xc != 0 ]; then

    echo
    echo -----------------------------------------------------------
    echo ERROR:
    echo Could not git pull. Conflict?
    echo -----------------------------------------------------------
    exit 1

fi

cp ../stats_current.json _data/
cp ../stats.json _data/
git add _data/stats_current.json _data/stats.json
git commit -m "Update stats"
git push --mirror origin  # locally updated refs will be force updated on the remote end !
