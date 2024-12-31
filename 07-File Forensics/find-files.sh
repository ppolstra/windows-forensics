#!/bin/bash
# find-files.sh
#
# Simple script that is used to find files of
# various types in an image file
# A clone of find-files.py, but in bash not Python
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

#echo $findList $clusterSize $imageFilename $offset

#load up the grepArray based on findArray
for (( n=0; n < ${#findArray[*]}; n++))
do
	findArray[n]=$(echo "${findArray[n]}" | xargs) # strip trailing space
	case ${findArray[n]} in
		jpg | jpeg)
			grepArray[n]="JPEG image"
			;;
		png)
			grepArray[n]="PNG image"
			;;
		gif)
			grepArray[n]="GIF image"
			;;
		img | image)
			grepArray[n]="JPEG image|PNG image|GIF image"
			;;
		pdf)
			grepArray[n]="PDF document"
			;;
		exe)
			grepArray[n]="executable"
			;;
		zip)
			grepArray[n]="archive"
			;;
		ppt | powerpoint)
			grepArray[n]="Composite Document File|PowerPoint"
			;;
		doc | word)
			grepArray[n]="Composite Document File|Microsoft Word|Microsoft WinWord"
			;;
		xls | excel)
			grepArray[n]="Composite Document File|Microsoft Excel"
			;;
		ofc | office)
			grepArray[n]="Composite Document File|PowerPoint|Microsoft Word|Microsoft WinWord|Microsoft Excel"
			;;
		*)
			echo \'${findArray[n]}\': unknown file type
			exit 1
			;;
	esac	
			
	echo ${findArray[n]} ${grepArray[n]}
done

#did you give me an image file
if [ -z "$imageFilename" ] 
then
	usage
fi

#Now iterate over the image file
#get file size in sectors
fs=$(($(stat --format="%s" $imageFilename)/512))
echo "Filesize in sectors: $fs"

#calculate the starting sector
csector=0
if [ -n "$offset" ]
then
	csector=$(($offset))
fi
#set cluster size
clustSize=1
if [ -n "$clusterSize" ]
then
	clustSize=$(($clusterSize))
fi

while (( $csector < $fs ))
do
	# run file utility against the sector
	fileInfo=$( dd bs=512 count=1 skip=$csector if=$imageFilename 2>/dev/null | file - 2>/dev/null \
		| awk -F ':' '{print $2}')
	for (( n=0; n < ${#findArray[*]}; n++))
	do
		results=$( dd bs=512 count=1 skip=$csector if=$imageFilename 2>/dev/null | file - 2>/dev/null \
		| awk -F ':' '{print $2}' | egrep -h "${grepArray[n]}" 2>/dev/null )
		if [ $? -eq 0 ]
		then
			printf "Sector 0x%x: %s\n" $csector $results
			exit
		fi
	done
	csector=$(($csector + $clustSize))
done
