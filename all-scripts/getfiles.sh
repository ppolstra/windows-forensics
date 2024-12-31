#!/usr/bin/bash
for (( i=42; i<883199; i+=1 ))
do
	if ( ./mft.py -f ~/john-recovery/realMFT -e $i | grep 'Filename: ' | egrep -i '\.jpg|\.jpeg' )
	then
		./extract.py -f /media/phil/18C6E9707726E456/john-cdrive.img -e $i -d ~/john-recovery -m ~/john-recovery/realMFT 
	fi
done
