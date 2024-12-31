#!/bin/bash
#
# print-timeline.sh
#
# Simple script to print a timeline on a
# file-by-file basis.
#
# Created by Dr. Phil Polstra (@ppolstra)
# for PentesterAcademy.com

usage () {
	echo "usage: $0 <database> [mft record ID]"
	echo "Simple script to get timeline from the database"
	echo "on a file-by-file basis."
	exit 1
}

if [ $# -lt 1 ] ; then
	usage
fi

# no MFT record given
if [ $# -lt 2 ] ; then 
	cat << EOF | mysql $1 -u root -p
	select Operation, timeline.source, timeline.date, timeline.time,
	filename, mftEntry, sequenceNumber, filesize, allocatedSize
	from files, timeline
	where files.recno = timeline.recno
	order by mftEntry, timeline.date, timeline.time;
EOF
else
	cat << EOF | mysql $1 -u root -p
	select Operation, timeline.source, timeline.date, timeline.time,
	filename, mftEntry, sequenceNumber, filesize, allocatedSize
	from files, timeline
	where files.recno = timeline.recno and 
	files.mftEntry = $2
	order by mftEntry, timeline.date, timeline.time;
EOF
fi
