#!/usr/bin/env bash

# Save first argument and cwd
filename=$1
cwd=$PWD
folder=$cwd"/.versiondir/"$filename

if [ ! -f $folder ]; then
	echo "File specified not found!"
	exit 1
fi

for file in $folder
do
  echo $file
done;

