#!/bin/bash

SCRIPT_DIR=$(realpath $(dirname $0))
cd $SCRIPT_DIR

export TUBULAR_WORKSPACE=test-workspace
export TUBULAR_CONFIG_REPO=ssh://git@elara-station:2222/alagyn/tubular-config.git
export TUBULAR_PORT=8007

python -m tubular_node