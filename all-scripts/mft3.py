#!/usr/bin/python3

'''Set of classes to read and interpret 
MFT entries.  Each MFT entry is created
by passing in a 1024 byte binary string.
Created by Dr. Phil Polstra
for PentesterAcademy.com'''

import struct 	# for interpreting entries
import optparse # command line options
import time		# time conversion functions
from vbr import Vbr

class MftHeader:
	def __init__(self, buffer):
		'''Expects a 1024-byte buffer
		containing a MFT record.'''
		formatStr=(	'<4s' 	+		# FILE id 0
					'H'	 	+		# update seq offset (0x30) 1
					'H'		+		# size of update seq (3) 2
					'Q'		+		# log file seq number 3
					'H'		+		# sequence number 4
					'H'		+		# hard link count 5
					'H'		+		# start of attributes 6
					'H'		+		# flags b0=used b1=directory 7
					'L'		+		# logical MFT record size 8
					'L'		+		# physics MFT rec size (1024) 9
					'Q'		+		# MFT base file reference 10
					'H'		+		# next attribute ID 11
					'2s'	+		# padding 12
					'L'		+		# MFT Record number 13
					'6s'	)		# update seq array 14
		self._headerTuple=struct.unpack(formatStr, buffer[:54])
		
	def updateSequenceOffset(self):
		return self._headerTuple[1]
		
	def updateSequenceSize(self):
		return self._headerTuple[2]
		
	def updateSequenceArray(self):
		return self._headerTuple[14]
		
	def logFileSequenceNumber(self):
		return self._headerTuple[3]	
		
	def sequenceNumber(self):
		return self._headerTuple[4]
		
	def hardLinkCount(self):
		return self._headerTuple[5]
		
	def attributeStart(self):
		return self._headerTuple[6]
		
	def flags(self):
		return self._headerTuple[7]
		
	def inUse(self):
		return (self._headerTuple[7] & 0x01) != 0
		
	def isDirectory(self):
		return (self._headerTuple[7] & 0x02) != 0	
		
	def logicalRecordSize(self):
		return self._headerTuple[8]
		
	def physicalRecordSize(self):
		return self._headerTuple[9]
		
	def baseFileReference(self):
		return self._headerTuple[10]
		
	def baseFileMft(self):
		return self._headerTuple[10] & 0x0000FFFFFFFFFFFF
		
	def baseFileSequenceNumber(self):
		return self._headerTuple[10] >> 48
		
	def nextAttributeId(self):
		return self._headerTuple[11]
	
	def recordNumber(self):
		return self._headerTuple[13]
		
	def __str__(self):
		retStr=('MFT entry: ' + str(self.recordNumber()) + '/' + str(self.sequenceNumber()) +
			'\n\tSize: ' + str(self.logicalRecordSize()) + '/' + str(self.physicalRecordSize()) +
			'\n\tBase Record: ' + str(self.baseFileMft()) + '/' + str(self.baseFileSequenceNumber()) )
		return retStr

class DataRun:
	'''This class represents a single data run.
	it is little more than a wrapper around 
	the range object.'''
	def __init__(self, start, count):
		self._range=range(start, count+1)
		
	def numberOfClusters(self):
		return len(self._range)
		
	def startingCluster(self):
		return self._range[0]
		
	def clusterList(self):
		retList=[]
		for i in self._range:
			retList.append(i)
		return retList

def bytesToUnsigned(buffer, bytes, pos=0):
	'''Take a slice of a binary string and
	converts it to an unsigned integer.'''
	paddedStr=buffer[pos:pos+bytes]
	for x in range(bytes, 8):
		paddedStr+='\x00'
	return struct.unpack('Q', paddedStr)[0]
	
def bytesToSigned(buffer, bytes, pos=0):
	'''Take a slice of a binary string and
	converts it to a signed integer.'''
	paddedStr=buffer[pos:pos+bytes]
	# is it negative?
	if ord(buffer[pos+bytes-1]) >= 0x80:
		fillStr='\xff'
	else:
		fillStr='\x00'
	for x in range(bytes, 8):
		paddedStr+=fillStr
	return struct.unpack('q', paddedStr)[0]	
			
			
def dataRuns(buffer, offset=0):
	'''This function will decode a binary stream of
	data runs and return a list of data run objects.'''
	pos=offset
	if pos >= len(buffer):
		return
	retList=[]
	startCluster=0	
	# loop till size of next run is zero
	while buffer[pos]!='\x00' and pos < len(buffer):
		# get sizes for run
		countSize=ord(buffer[pos]) & 0x0F
		offsetSize=ord(buffer[pos]) >> 4
		pos+=1
		count=bytesToUnsigned(buffer[pos:pos+countSize], countSize)
		pos+=countSize
		startCluster+=bytesToSigned(buffer[pos:pos+offsetSize], offsetSize)
		pos+=offsetSize
		retlist.append(DataRun(startCluster, count))
	return retList
	  	
		
class Attribute:
	def __init__(self, buffer, offset=0):
		'''Accept a buffer and optional offset to
		interpret an attribute header.  This is normally
		called when creating an attribute object, in
		which case the buffer is probably a 1K MFT entry.'''
		# header starts the same for resident/not
		formatStr=('<L' +	# Attribute type 0
					'L' +	# total attribute length 1
					'B' +	# flag 00/01 resident/not 2
					'B' +	# name length 3
					'H' +	# offset to name 4
					'H' +	# flags 5
					'H')	# attribute ID 6
		# if this is resident header continues			
		if buffer[offset+8:offset+9]==b'\x00':
			formatStr+=('L' + 	# length of attribute 7
						'H' +	# offset to start of attribute 8
						'B' +	# indexed? 9
						'B') 	# padding 10
			self._headerTuple=struct.unpack(formatStr, buffer[offset:offset+24])
			if self.hasName():
				self._name=buffer[offset+self.nameOffset(): offset+self.nameOffset() + self.nameLength()*2]
			else:
				self._name=None
		else:
			# non-resident attribute
			formatStr+=('Q'	+	# first VCN 7
						'Q'	+	# last VCN 8
						'H'	+	# offset to data runs 9
						'H' +	# compression 2^x 10
						'4s' + 	# padding 11
						'Q' +	# physical size of attribute 12
						'Q'	+	# logical size of attribute 13
						'Q')	# initialized size of stream 14
			self._headerTuple=struct.unpack(formatStr, buffer[offset:offset+64])
			if self.hasName():
				self._name=buffer[offset+self.nameOffset(): offset+self.nameOffset() + self.nameLength()*2]
			else:
				self._name=None
			self._dataRuns=dataRuns(buffer, offset+self._headerTuple[9])

	def dataRuns(self):
		if not self.isResident():
			return self._dataRuns
			
	def clusterList(self):
		if not self.isResident():
			retList=[]
			for dr in self._dataRuns:
				retList+=dr.clusterList()
			return retList
	
	def firstVcn(self):
		if not self.isResident():
			return self._headerTuple[7]
			
	def lastVcn(self):
		if not self.isResident():
			return self._headerTuple[8]
			
	def dataRunOffset(self):
		if not self.isResident():
			return self._headerTuple[9]
			
	def compression(self):
		if not self.isResident():
			return 2**self._headerTuple[10]
	
	def physicalSize(self):
		if not self.isResident():
			return self._headerTuple[12]
			
	def logicalSize(self):
		if not self.isResident():
			return self._headerTuple[13]
			
	def initializedSize(self):
		if not self.isResident():
			return self._headerTuple[14]
			
		
	def attributeLength(self):
		if self.isResident():
			return self._headerTuple[7]

	def attributeOffset(self):
		if self.isResident():
			return self._headerTuple[8]
			
	def isIndexed(self):
		if self.isResident():
			return self._headerTuple[9]==0x01
		else:
			return False
						
	def attributeType(self):
		return self._headerTuple[0]
		
	def totalLength(self):
		return self._headerTuple[1]
		
	def isResident(self):
		return self._headerTuple[2]==0
		
	def nameLength(self):
		return self._headerTuple[3]
		
	def nameOffset(self):
		return self._headerTuple[4]
		
	def hasName(self):
		return self._headerTuple[3]!=0
	
	def name(self):
		self._name
		
	def flags(self):
		return self._headerTuple[5]
		
	def isCompressed(self):
		return (self._headerTuple[5] & 0x0001) != 0
		
	def isEncrypted(self):
		return (self._headerTuple[5] & 0x4000) != 0
		
	def isSparse(self):
		return (self._headerTuple[5] & 0x8000) != 0
		
	def attributeId(self):
		return self._headerTuple[6]
		
	def __str__(self):
		retStr=('Attribute Type: ' + '%02X' % self.attributeType() +
				'\nAttribute Length: ' + '%04X' % self.totalLength() + 
				'\nResident: ' + str(self.isResident()) +
				'\nName: ' + str(self.name()) + 
				'\nAttribute ID: ' + str(self.attributeId()) )
		return retStr

def convertFileTime(stupid):
	'''Converts idiotic Win32 filetimes to something reasonable.'''
	t = stupid * 100/ 1000000000
	t -= 11644473600 # seconds from 1/1/1601 to 1/1/1970
	if t > 0:
		return time.gmtime(t)
	else:
		return time.gmtime(0)
		
class StandardInfo(Attribute):
	'''This class is use to represent the $10 Standard Info
	attribute.  It is created from a buffer containing the 
	MFT entry (1024 bytes) and an offset to the start of 
	the attribute.'''
	def __init__(self, buffer, offset=0):
		super(StandardInfo, self).__init__(buffer, offset)
		# $10 is always resident so header is 24 bytes
		formatStr=('<Q' +	# creation 0
				   'Q' +	# modification 1
				   'Q' +	# record change 2
				   'Q' +	# access	3
				   'L' +	# flags 4
				   'L' +	# highest version 5
				   'L' +	# version number 6
				   'L' +	# class ID (XP) 7
				   'L' +	# owner ID (xp) 8
				   'L' +	# security ID (xp) 9
				   'Q' +	# quota disk size (xp) 10
				   'Q')		# update sequence (xp) 11
		self._10Tuple=struct.unpack(formatStr, buffer[offset+24:offset+24+72])
		
	def creationTime(self):
		return convertFileTime(self._10Tuple[0])
				
	def modificationTime(self):
		return convertFileTime(self._10Tuple[1])
				
	def recordChangeTime(self):
		return convertFileTime(self._10Tuple[2])
				
	def accessTime(self):
		return convertFileTime(self._10Tuple[3])
		
	def flags(self):
		'''Flags are
		0123456789ABCDE-bits
		RHS0DADSTSRCONE
		Oiy0iretmpeofon
		 ds0rcvdpapmftc
		 nt0thi  raplir'''
		return self._10Tuple[4]
	
	def isReadOnly(self):
		return (self.flags() & 0x01) !=0
		
	def isHidden(self):
		return (self.flags() & 0x02) !=0
	
	def isSystem(self):
		return (self.flags() & 0x04) !=0
		
	def isDirectory(self):
		return (self.flags() & 0x10) !=0
		
	def isArchive(self):
		return (self.flags() & 0x20) !=0
		
	def isStandardFile(self):
		return (self.flags() & 0x80) !=0
		
	def isTemporaryFile(self):
		return (self.flags() & 0x100) !=0
		
	def isSparseFile(self):
		return (self.flags() & 0x200) !=0
		
	def isReparsePoint(self):
		return (self.flags() & 0x400) !=0
		
	def isCompressed(self):
		return (self.flags() & 0x800) !=0
		
	def isOffline(self):
		return (self.flags() & 0x1000) !=0
		
	def isNotIndexed(self):
		return (self.flags() & 0x2000) !=0
		
	def isEncrypted(self):
		return (self.flags() & 0x4000) !=0
			
	def highestVersion(self):
		return self._10Tuple[5]
		
	def versionNumber(self):
		return self._10Tuple[6]
		
	def hasVersioning(self):
		return self._10Tuple[5]!=0
		
	def classID(self):
		return self._10Tuple[7]
		
	def ownerID(self):
		return self._10Tuple[8]
		
	def securityID(self):
		return self._10Tuple[9]
		
	def quota(self):
		return self._10Tuple[10]
		
	def updatedSequenceNumber(self):
		return self._10Tuple[11]
		
	def __str__(self):
		retStr=Attribute.__str__(self)
		retStr+=('\nCreated: ' 		+ str(time.asctime(self.creationTime())) +
				 '\nModified: ' 	+ str(time.asctime(self.modificationTime())) +
				 '\nRec Changed: '	+ str(time.asctime(self.recordChangeTime())) +
				 '\nAccessed: '		+ str(time.asctime(self.accessTime())) +
				 '\nFlags: ' 		+ str('%04X' % self.flags()) +
				 '\nHas Versioning: ' + str(self.hasVersioning()) ) 
		return retStr

		
def main():
	parser=optparse.OptionParser()
	parser.add_option("-f", "--file", dest="filename",
					help="image filename")
	parser.add_option("-o", "--offset", dest='offset',
					help='offset in sectors to start of volume')
					
	parser.add_option("-e", "--entry", dest='entry',
					help='MFT entry number')
					
	(options, args)=parser.parse_args()
	filename=options.filename
	if options.offset:
		offset=512 * int(options.offset)
	else:
		offset=0
	if options.entry:
		entry=int(options.entry)
	else:
		entry=0	
		
	with open(filename, 'rb') as f:
		f.seek(offset)
		buffer=f.read(512)
	
	vbr=Vbr(buffer)
	print(vbr)
	
	# calculate the offset to the MFT entry
	mftOffset = (offset + # offset to start of partition
				vbr.mftLcn() * # logical cluster number
				vbr.bytesPerSector() * # sector size
				vbr.sectorsPerCluster() + # sectors/cluster
				1024 * entry ) # 
	with open(filename, 'rb') as f:
		f.seek(mftOffset)
		buffer=f.read(1024)
	mftHeader=MftHeader(buffer)
	print(mftHeader)
	stdInfo=StandardInfo(buffer, mftHeader.attributeStart())
	print(stdInfo)
	
	
if __name__=='__main__':
	main()

			
