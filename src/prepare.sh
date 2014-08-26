#!/bin/bash

pwd


if [ ! -f env/bin/activate ]; then

    echo Virtualenv not found. Trying to set up
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

    echo Installing dependencies
    pip install -r requirements.txt

else

    echo Activating virtualenv
    . env/bin/activate

fi

python src/prepare.py
