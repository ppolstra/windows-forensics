#!/usr/bin/python3

import sys
import re
import magic
import os

imageFilename = sys.argv[1]
offset = int(sys.argv[2])
clusterSize = int(sys.argv[3])
searchString = sys.argv[4]

if not os.path.exists(imageFilename):
	print('Image file not found!')
	exit 
	
# now parse through the file
pos=offset * 512
with open(imageFilename, 'rb') as f:
	f.seek(pos)
	buffer=f.read(512*clusterSize)
	while len(buffer)>0:
		mag=str(magic.from_buffer(buffer))
		if re.search(searchString, mag):
			print('Match found at offset 0x%X, sector %d: %s' %
				 (pos, pos//512, mag))
		pos+=512*clusterSize
		buffer=f.read(512*clusterSize)		

