#!/bin/bash
# find-files.sh
#
# Simple script that is used to find files of
# various types in an image file
# A clone of find-files.py, but in bash (mostly) not Python
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
			grepString+="JPEG image|"
			;;
		png)
			grepString+="PNG image|"
			;;
		gif)
			grepString+="GIF image|"
			;;
		img | image)
			grepString+="JPEG image|PNG image|GIF image|"
			;;
		pdf)
			grepString+="PDF document|"
			;;
		exe)
			grepString+="executable|"
			;;
		zip)
			grepString+="archive|"
			;;
		ppt | powerpoint)
			grepString+="Composite Document File|PowerPoint|"
			;;
		doc | word)
			grepString+="Composite Document File|Microsoft Word|Microsoft WinWord|"
			;;
		xls | excel)
			grepString+="Composite Document File|Microsoft Excel|"
			;;
		ofc | office)
			grepString+="Composite Document File|PowerPoint|Microsoft Word|Microsoft WinWord|Microsoft Excel|"
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

./read-chunk.py $imageFilename $offset $clusterSize $grepString
