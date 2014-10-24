#!/bin/bash

if [ "$(basename "$(pwd)")" == "src" ]; then
    cd ..
fi

function install_deps
{
    echo Installing/updating dependencies
    pip install -U rdflib pytz python-dateutil requests
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

if [ ! -f env/bin/activate ]; then

    echo
    echo -----------------------------------------------------------
    echo Virtualenv not found. Trying to set up
    echo -----------------------------------------------------------
    echo
    virtualenv env
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
    . env/bin/activate

    $(install_deps)

else

    echo Activating virtualenv
    . env/bin/activate

fi


python src/publish.py
xc=$?
if [ $xc != 0 ]; then
    echo Exiting
    exit 0
fi

if [ ! -d realfagstermer ]; then

    git clone git@github.com:realfagstermer/realfagstermer.git
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

cd ..
cp realfagstermer.ttl realfagstermer/
cd realfagstermer
git add realfagstermer.ttl
git commit -m "Update realfagstermer.ttl"
git push --mirror origin  # locally updated refs will be force updated on the remote end !

python src/update_triple_store.py

