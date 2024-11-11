#!/bin/bash

SCRIPT_DIR=$(realpath $(dirname $0))
cd $SCRIPT_DIR

rm -rf test-workspace/ctrl/*
rm -rf test-workspace/node/*