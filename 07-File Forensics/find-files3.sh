#!/bin/bash
# find-files.sh
#
# Simple script that is used to find files of
# various types in an image file
# A clone of find-files.py, but in bash (using egrep) not Python
# by Dr. Phil Polstra Sr


usage()
{
	echo "Usage: $0 [-s searchList] [-c clusterSize] [-o offset] -i imageFilename" >&2
	exit 1
}


# Parse command line parameters
# set values to empty
findList= clusterSize= imageFilename= offset=
while getopts :s:c:i:o: opt
do
	case $opt in
	s)	findList=$OPTARG
		;;
	c)	clusterSize=$OPTARG
		;;
	i)	imageFilename=$OPTARG
		;;
	o)	offset=$OPTARG
		;;
	'?')	echo "$0: invalid option -$OPTARG" >&2
		usage
		;;
	esac
done

# create an array from the findList
readarray -d ", " -t findArray <<< $findList

grepString=""
#load up the grepString based on findArray
for (( n=0; n < ${#findArray[*]}; n++))
do
	findArray[n]=$(echo "${findArray[n]}" | xargs) # strip trailing space
	case ${findArray[n]} in
		jpg | jpeg)
			grepString+=$'\xff\xd8\xff\xe0..JFIF|\xff\xd8\xff\xe1..Exif|\xff\xd8\xff\xe8..SPIFF|'
			;;
		png)
			grepString+=$'\x89PNG|'
			;;
		gif)
			grepString+="GIF87a|GIF89a|"
			;;
		img | image)
			grepString+=$'\xff\xd8\xff\xe0..JFIF|\xff\xd8\xff\xe1..Exif|\xff\xd8\xff\xe8..SPIFF|\x89PNG|GIF87a|GIF89a|'
			;;
		pdf)
			grepString+="%PDF|"
			;;
		exe)
			grepString+="MZ|"
			;;
		ppt | powerpoint)
			grepString+=$'\x50\x4b\x03\x04\x14|\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1|'
			;;
		doc | word)
			grepString+=$'\x50\x4b\x03\x04\x14|\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1|'
			;;
		xls | excel)
			grepString+=$'\x50\x4b\x03\x04\x14|\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1|'
			;;
		ofc | office)
			grepString+=$'\x50\x4b\x03\x04\x14|\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1|'
			;;
		zip)
			grepString+="PK|"
			;;
		*)
			echo \'${findArray[n]}\': unknown file type
			exit 1
			;;
	esac	
			
done

#eliminate trailing |
grepString=${grepString%?}

echo "grep string is $grepString"

#did you give me an image file
if [ -z "$imageFilename" ] 
then
	usage
fi

#Now iterate over the image file
#get file size in sectors
fs=$(($(stat --format="%s" $imageFilename)/512))
echo "Filesize in sectors: $fs"

if [ -z "$offset" ]
then
	offset="0"
fi

if [ -z "$clusterSize" ]
then
	clusterSize="1"
fi

egrep --byte-offset --only-matching --text "$grepString" "$imageFilename"  | awk -F ':' '{printf "Match found at offset %x : {%s}\n", $1, $2}' | sed -e $'s/\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1/Office Document/' | sed -e $'s/\x50\x4b\x03\x04\x14/Office XML Document or zip file/' | egrep '00 : '
