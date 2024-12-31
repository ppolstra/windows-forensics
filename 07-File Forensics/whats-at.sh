#!/bin/bash
# simple script that uses file utility
# to determine what is at an offset in
# a filesystem image
# by Dr. Phil Polstra

usage()
{
	echo "Usage: $0 <offset> <imagefile>"
	exit 1
}

if [ $# -ne 2 ]
then
	usage
fi

dd bs=512 count=4096 skip=$(("$1"/512)) if="$2" 2>/dev/null | file - 2>/dev/null
