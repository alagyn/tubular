#!/bin/bash

SCRIPT_DIR=$(realpath $(dirname $0))
cd $SCRIPT_DIR

export TUBULAR_WORKSPACE=test-workspace
export TUBULAR_CONFIG_REPO=ssh://git@elara-station:2222/alagyn/tubular-config.git

python -m tubular_controller