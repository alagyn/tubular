#!/bin/bash

SCRIPT_DIR=$(realpath $(dirname $0))
cd $SCRIPT_DIR

if [[ -z "$VIRTUAL_ENV" ]]
then
    source $SCRIPT_DIR/venv/bin/activate
fi

fastapi dev tubular_controller/controller_router.py