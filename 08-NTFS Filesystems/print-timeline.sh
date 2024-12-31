#!/bin/bash
#
# print-timeline.sh
#
# Simple script to print a timeline
#
# Created by Dr. Phil Polstra (@ppolstra)
# for PentesterAcademy.com

usage () {
	echo "usage: $0 <database> <starting date> [ending date]"
	echo "Simple script to get timeline from the database"
	exit 1
}

if [ $# -lt 2 ] ; then
	usage
fi

# no end date given
if [ $# -lt 3 ] ; then 
	cat << EOF | mysql $1 -u root -p
	select Operation, timeline.source, timeline.date, timeline.time,
	filename, mftEntry, sequenceNumber, filesize, allocatedSize
	from files, timeline
	where timeline.date >= str_to_date("$2", "%Y-%m-%d") and
	files.recno = timeline.recno
	order by timeline.date desc, timeline.time desc;
EOF
else
	cat << EOF | mysql $1 -u root -p
	select Operation, timeline.source, timeline.date, timeline.time,
	filename, mftEntry, sequenceNumber, filesize, allocatedSize
	from files, timeline
	where timeline.date >= str_to_date("$2", "%Y-%m-%d") and
	timeline.date < str_to_date("$3", "%Y-%m-%d") and
	files.recno = timeline.recno
	order by timeline.date desc, timeline.time desc;
EOF
fi
