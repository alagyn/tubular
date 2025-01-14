#!/bin/bash

SCRIPT_DIR=$(realpath $(dirname $0))

cd $SCRIPT_DIR

cp ../dist/tubular*.whl ./
cp -r ../tubular-frontend/dist ./dist

docker build . -f base.docker -t tubular-base:1
docker build . -f node.docker -t tubular-node:1
docker build . -f ctrl.docker -t tubular-ctrl:1