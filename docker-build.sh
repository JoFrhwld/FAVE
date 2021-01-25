#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR

# Docker build
if [ -e "$DIR/Dockerfile" ]
then
 docker build -t fave:latest $DIR
else
 echo "Did not find Dockerfile"
fi
