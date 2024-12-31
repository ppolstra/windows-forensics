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
		self._start=start
		self._count=count
		
	def numberOfClusters(self):
		return self._count
		
	def startingCluster(self):
		return self._start
		
	def clusterList(self):
		retList=[]
		for i in range(self._start, self._start+self._count):
			retList.append(i)
		return retList
		
	def __str__(self):
		return ('Data run start/count: ' + 
					str(self.startingCluster()) + 
					'/' + str(self.numberOfClusters()) )

def bytesToUnsigned(buff, sz, pos=0):
	'''Take a slice of a binary string and
	converts it to an unsigned integer.'''
	paddedStr=buff[pos:pos+sz]
	for x in range(sz, 8):
		paddedStr+=b'\x00'
	return struct.unpack('<Q', paddedStr)[0]
	
def bytesToSigned(buff, sz, pos=0):
	'''Take a slice of a binary string and
	converts it to a signed integer.'''
	paddedStr=buff[pos:pos+sz]
	# is it negative?
	if ord(buff[pos+sz-1:pos+sz]) >= 0x80:
		fillStr=b'\xff'
	else:
		fillStr=b'\x00'
	for x in range(sz, 8):
		paddedStr+=fillStr
	return struct.unpack('<q', paddedStr)[0]	
			
			
def dataRuns(buff, offset=0):
	'''This function will decode a binary stream of
	data runs and return a list of data run objects.'''
	pos=offset
	if pos >= len(buff):
		return
	retList=[]
	startCluster=0	
	# loop till size of next run is zero
	while buff[pos]!=b'\x00' and pos < len(buff):
		# get sizes for run
		size=ord(buff[pos:pos+1])
		if size==0:
			break
		countSize=size & 0x0F
		offsetSize=size >> 4
		pos+=1
		count=bytesToUnsigned(buff, countSize, pos)
		pos+=countSize
		startCluster+=bytesToSigned(buff, offsetSize, pos)
		pos+=offsetSize
		retList.append(DataRun(startCluster, count))
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
			self.__headerTuple=struct.unpack(formatStr, buffer[offset:offset+24])
			if self.hasName():
				self.__name=buffer[offset+self.nameOffset(): offset+self.nameOffset() + self.nameLength()*2]
			else:
				self.__name=None
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
			self.__headerTuple=struct.unpack(formatStr, buffer[offset:offset+64])
			if self.hasName():
				self.__name=buffer[offset+self.nameOffset(): offset+self.nameOffset() + self.nameLength()*2]
			else:
				self.__name=None
			self._dataRuns=dataRuns(buffer, offset+self.__headerTuple[9])
			
	def dataRuns(self):
		if not self.isResident():
			return self._dataRuns
			
	def clusterList(self):
		if not self.isResident():
			retList=[]
			for dr in self._dataRuns:
				print(dr)
				retList+=(dr.clusterList())
			return retList
	
	def firstVcn(self):
		if not self.isResident():
			return self.__headerTuple[7]
			
	def lastVcn(self):
		if not self.isResident():
			return self.__headerTuple[8]
			
	def dataRunOffset(self):
		if not self.isResident():
			return self.__headerTuple[9]
			
	def compression(self):
		if not self.isResident():
			return 2**self.__headerTuple[10]
	
	def physicalSize(self):
		if not self.isResident():
			return self.__headerTuple[12]
			
	def logicalSize(self):
		if not self.isResident():
			return self.__headerTuple[13]
			
	def initializedSize(self):
		if not self.isResident():
			return self.__headerTuple[14]
			
		
	def attributeLength(self):
		if self.isResident():
			return self.__headerTuple[7]

	def attributeOffset(self):
		if self.isResident():
			return self.__headerTuple[8]
			
	def isIndexed(self):
		if self.isResident():
			return self.__headerTuple[9]==0x01
		else:
			return False
						
	def attributeType(self):
		return self.__headerTuple[0]
		
	def totalLength(self):
		return self.__headerTuple[1]
		
	def isResident(self):
		return self.__headerTuple[2]==0
		
	def nameLength(self):
		return self.__headerTuple[3]
		
	def nameOffset(self):
		return self.__headerTuple[4]
		
	def hasName(self):
		return self.__headerTuple[3]!=0
	
	def name(self):
		self.__name
		
	def flags(self):
		return self.__headerTuple[5]
		
	def isCompressed(self):
		return (self.__headerTuple[5] & 0x0001) != 0
		
	def isEncrypted(self):
		return (self.__headerTuple[5] & 0x4000) != 0
		
	def isSparse(self):
		return (self.__headerTuple[5] & 0x8000) != 0
		
	def attributeId(self):
		return self.__headerTuple[6]
		
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
	t -= 11644473600
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

class AttributeItem:
	'''An item in an attribute list.'''
	def __init__(self, buffer, offset=0):
		formatStr=('<L'		+		# Attribute ID 0
					 'H'		+		# record length 1
					 'B'		+		# name length	2
					 'B'		+		# offset to name 3
					 'Q'		+		# VCN	4
					 'Q'		+		# MFT reference 5
					 'H'	)			# attribute ID 6
		self._itemTuple=struct.unpack(formatStr, buffer[offset:offset+26])
		if self._itemTuple[2] > 0:
			self._name=buffer[offset+self._itemTuple[3]:offset+self._itemTuple[3]+2*self._itemTuple[2]]
		else:
			self._name=None
			
	def name(self):
		return self._name
		
	def hasName(self):
		return self._itemTuple[2] > 0
		
	def vcn(self):
		return self._itemTuple[4]
		
	def recordLength(self):
		return self._itemTuple[1]
		
	def attributeType(self):
		return self._itemTuple[0]
	
	def mft(self):
		return self._itemTuple[5] & 0xffffffffffff
		
	def attributeId(self):
		return self._itemTuple[6]
		
	def updateSequence(self):
		return self._itemTuple[5] >> 48

	def __str__(self):
		retStr=('AttributeList type: ' + str('%0X' % self.attributeType()) +
					'\nStored in MFT: ' + str(self.mft()) + '/' + 
					 str(self.updateSequence()) +
					'\nName: ' + str(self.name()) )
		return retStr
					
class AttributeList(Attribute):
	'''Attribute list created from MFT entry
	1024 byte data stream.'''
	def __init__(self, buffer, offset=0):
		super(AttributeList, self).__init__(buffer, offset)
		# standard header is 24 bytes (must be resident)
		pos=offset+24
		self._list=[]
		while pos < offset + self.totalLength():
			item=AttributeItem(buffer, pos)
			pos+=item.recordLength()
			self._list.append(item)
	
	def length(self):
		return len(self._list)
		
	def list(self):
		return self._list		
		
	def __str__(self):
		retStr=Attribute.__str__(self)
		retStr+='\nAttribute List:'
		for i in range(self.length()):
			retStr+='\n\t'+str(self._list[i].__str__())
		return retStr
				
class Filename(Attribute):
   '''This class is used to represent the $30 or Filename
   attribute.  It is created by passing in a MFT entry
   to the class.'''
   def __init__(self, buffer, offset=0):
      super(Filename, self).__init__(buffer, offset)
		# this attribute must be resident
      formatStr=('<L'   +     # MFT entry of parent 0
                  'H'   +     # MFT entry of parent upper 2 bytes 1
                  'H'   +     # Update sequence of parent 2
                  'Q'   +     # Created 3
                  'Q'   +     # Modified 4
                  'Q'   +     # record change 5
                  'Q'   +     # accessed 6
                  'Q'   +     # physical size 7
                  'Q'   +     # logical size 8
                  'L'   +     # flags 9
                  'L'   +     # extended flags 10
                  'B'   +     # filename length 11
                  'B')        # namespace 12   
      self._30Tuple=struct.unpack(formatStr, buffer[offset+24:offset+24+66])
      self._name=buffer[offset+90:offset+90+self._30Tuple[11]*2]
  	   
   def parentMft(self):
      return self._30Tuple[0]
      
   def parentSequenceNumber(self):
	   return self._30Tuple[2]
	
   def creationTime(self):
      return convertFileTime(self._30Tuple[3])

   def modificationTime(self):
      return convertFileTime(self._30Tuple[4])

   def recordChangeTime(self):
      return convertFileTime(self._30Tuple[5])

   def accessTime(self):
      return convertFileTime(self._30Tuple[6])

   def physicalSize(self):
      return self._30Tuple[7]
	
   def logicalSize(self):
	   return self._30Tuple[8]
	
   def flags(self):
	   return self._30Tuple[9]
	
   def isReadOnly(self):
	   return (self.flags() & 0x01) !=0
	
   def isHidden(self):
	   return (self.flags() & 0x02) !=0

   def isSystem(self):
	   return (self.flags() & 0x04) !=0
	
   def isDirectory(self):
	   return (self.flags() & 0x10000000) !=0
	
   def isIndexView(self):
	   return (self.flags() & 0x20000000) !=0
	
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

   def extendedFlags(self):
	   return self._30Tuple[10]
	
   def nameLength(self):
	   return self._30Tuple[11]
	
   def namespace(self):
	   return self._30Tuple[12]
	
   def name(self):
	   return self._name	
			
   def __str__(self):
	   retStr=Attribute.__str__(self)
	   retStr+=('\nFilename: ' 	+	str(self.name().decode('utf-16')) +
			    '\nCreated: ' 		+ str(time.asctime(self.creationTime())) +
			    '\nModified: ' 	+ str(time.asctime(self.modificationTime())) +
			    '\nRec Changed: '	+ str(time.asctime(self.recordChangeTime())) +
			    '\nAccessed: '		+ str(time.asctime(self.accessTime())) +
			    '\nFlags: ' 		+ str('%04X' % self.flags()) +
			    '\nExtended Flags: ' + str('%04X' % self.extendedFlags()) ) 
	   return retStr

class Data(Attribute):
	'''This class represents the data attribute.'''
	def __init__(self, buffer, offset=0):
		super(Data, self).__init__(buffer, offset)
		# is it resident
		if self.isResident():
			self._data=buffer[offset+self.attributeOffset():offset+self.attributeOffset()+self.attributeLength()]
		else:
			self._data=None

	def data(self):
		'''Return data if resident otherwise None'''
		return self._data
		
	def __str__(self):
		retStr=Attribute.__str__(self)
		if self.isResident():
			retStr+='\nData bytes: ' + str(len(self._data))
		else:
			retStr+='\nData runs: ' + str(len(self._dataRuns))
			retStr+='\nData clusters: ' + str(self.clusterList())
		return retStr			

class IndexEntry:
	'''Represents an index entry whether
	or not it is resident.'''
	def __init__(self, buffer, offset=0, resident=False):
		formatStr=('<Q'	+		# MFT ref 0
					  'H'		+		# total record length 1
					  'H'		+		# record length 2
					  'B'		+		# index flag 3
					  '3s' 	+		# padding 4
	   			  'L'   	+     # MFT entry of parent 5
	              'H'   	+     # MFT entry of parent upper 2 bytes 6
	              'H'   	+     # Update sequence of parent 7
	              'Q'   	+     # Created 8
	              'Q'   	+     # Modified 9
	              'Q'   	+     # record change 10
	              'Q'   	+     # accessed 11
	              'Q'   	+     # physical size 12
	              'Q'   	+     # logical size 13
	              'L'   	+     # flags 14
	              'L'   	+     # extended flags 15
	              'B'   	+     # filename length 16
	              'B')        # namespace 17   
		self._entryTuple=struct.unpack(formatStr, buffer[offset:offset+82])
		self._name=buffer[offset+82:offset+82+self._entryTuple[16]*2]
		if not self.isResident():
			# vcn of subentries in last 8 bytes
			self._vcn=struct.unpack('<Q', buffer[offset+self._entryTuple[1]-8:offset+self._entryTuple[1]])
		else:
			self._vcn=None
  	
	def __str__(self):
  		retStr=('Index Entry:' +
  					'\n\tMFT: ' + str(self.mft()) + '/' + str(self.sequenceNumber()) +
  					'\n\tIs Resident: ' + str(self.isResident()) +
  					'\n\tIs Last: ' + str(self.isLast()) +
  					'\n\tParent MFT: ' + str(self.parentMft()) + '/' + str(self.parentSequenceNumber()) +   	
  					'\n\tFilename: ' + str(self.name().decode('utf-16')) )
  		return retStr
  		
	def mft(self):
		return self._entryTuple[0] & 0xffffffffffff
		
	def sequenceNumber(self):
		return self._entryTuple[0] >> 48
		
	def totalLength(self):
		return self._entryTuple[1]
		
	def recordLength(self):
		return self._entryTuple[2]
		
	def indexFlags(self):
		return self._entryTuple[3]
		
	def isResident(self):
		return (self.indexFlags() & 0x01) == 0
		
	def isNonresident(self):
		return (self.indexFlags() & 0x01) != 0
		
	def isLast(self):
		return (self.indexFlags() & 0x02) != 0
		
	def parentMft(self):
		return self._entryTuple[5] + (self._entryTuple[6] & 0xffff) <<32
		
	def parentSequenceNumber(self):
		return self._entryTuple[7]
		
	def creationTime(self):
		return convertFileTime(self._entryTuple[8])
				
	def modificationTime(self):
		return convertFileTime(self._entryTuple[9])
				
	def recordChangeTime(self):
		return convertFileTime(self._entryTuple[10])
				
	def accessTime(self):
		return convertFileTime(self._entryTuple[11])
		
	def physicalSize(self):
		return self._entryTuple[12]
		
	def logicalSize(self):
		return self._entryTuple[13]
		
	def flags(self):
		return self._entryTuple[14]
		
	def isReadOnly(self):
		return (self.flags() & 0x01) !=0
		
	def isHidden(self):
		return (self.flags() & 0x02) !=0
	
	def isSystem(self):
		return (self.flags() & 0x04) !=0
		
	def isDirectory(self):
		return (self.flags() & 0x10000000) !=0
		
	def isIndexView(self):
		return (self.flags() & 0x20000000) !=0
		
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

	def extendedFlags(self):
		return self._entryTuple[15]
		
	def nameLength(self):
		return self._entryTuple[16]
		
	def namespace(self):
		return self._entryTuple[17]
		
	def name(self):
		return self._name	
		
	def childVcn(self):
		return self._vcn

class IndexRoot(Attribute):
	'''Index root $90 including any entries.'''
	def __init__(self, buffer, offset=0):
		super(IndexRoot, self).__init__(buffer, offset)
		formatStr=('<L'		+		# attribute type 0
					  'L'			+		# collation rule 1
					  'L'			+		# buffer size 2
					  'L'			+		# clusters/indx 3
					  'L'			+		# offset to 1st entry 4
					  'L'			+		# logical size 5
					  'L'			+		# physical size 6
					  'L' )				# 00/01 resident/not 7
		self.__headerTuple=struct.unpack(formatStr, buffer[offset+self.attributeOffset():offset+self.attributeOffset()+32])
		pos=offset+self.attributeOffset()+16+self.__headerTuple[4]
		self._indexEntries=[]
		# we only care about indexed filenames
		if self.__headerTuple[0] !=0x30:
			return
		while pos < offset+self.logicalIndexSize():
			entry=IndexEntry(buffer, pos, True)
			self._indexEntries.append(entry)
			pos+=entry.totalLength()
			if entry.isLast():
				break

	def indexedAttributeType(self):
		return self.__headerTuple[0]
		
	def collationRule(self):
		return self.__headerTuple[1]
		
	def indexBufferSize(self):
		return self.__headerTuple[2]
		
	def clustersPerIndexBuffer(self):
		return self.__headerTuple[3]
		
	def offsetToFirstEntry(self):
		return self.__headerTuple[4]
		
	def logicalIndexSize(self):
		return self.__headerTuple[5]
		
	def physicalIndexSize(self):
		return self.__headerTuple[6]
		
	def isIndexResident(self):
		return self.__headerTuple[7]==0
		
	def isIndexNonresident(self):
		return self.__headerTuple[7]==1
		
	def indexEntries(self):
		return self._indexEntries
		
	def numberOfIndexEntries(self):
		return len(self._indexEntries)
		
	def __str__(self):
		retStr=Attribute.__str__(self)
		retStr+=('\nIndexed Type: ' + str('%0X' % self.indexedAttributeType())	+
					'\nIndex Entries: ' + str(self.numberOfIndexEntries()) )
		for i in range(self.numberOfIndexEntries()):
			retStr+= '\n' + self._indexEntries[i].__str__()
		return retStr
		
class IndexBuffer:
	'''This class is used to process a
	4096 byte index buffer.'''
	def __init__(self, buffer, offset=0):
		# process the header
		formatStr=('<4s' 	+		# INDX 0
					  'H'		+		# offset to update seq 1
					  'H'		+		# update seq size in words 2
					  'Q'		+		# log file seq number 3
					  'Q'		+		# VCN 4
					  'L'		+		# offset to entries 5
					  'L'		+		# logical size 6
					  'L'		+		# physical size 7
					  'L'		+		# flags 00/01 leaf/parent 8
					  'H'		+		# update seq 9
					  '8H'	)		# update seq array 10
		self._headerTuple=struct.unpack(formatStr, buffer[offset:offset+58])
		# copy data to new buffer so we can apply fix up codes
		self._data=buffer[offset:]
		for i in range(0, self._headerTuple[2]):
		   replaceIndex = offset + 512 * i + 510
		   self._data = self._data[0: replaceIndex] + self._data[42+i*2:42+i*2+2] + self._data[replaceIndex + 2: ]
		# now read the entries
		pos=offset+self._headerTuple[5]
		self._entries=[]
		while pos < offset + self._headerTuple[6]:
			entry=IndexEntry(data, pos)
			self._entries.append(entry)
			pos+=entry.totalLength()
			if entry.isLast():
				break
	
	def isValid(self):
		return self._headerTuple[0]=='INDX'
		
	def updateSequenceOffset(self):
		return self._headerTuple[1]
		
	def updateSequenceSize(self):
		return self._headerTuple[2]
		
	def logFileSequence(self):
		return self._headerTuple[3]
		
	def vcn(self):
		return self._headerTuple[4]
		
	def offsetToEntries(self):
		return self._headerTuple[5]
		
	def logicalSize(self):
		return self._headerTuple[6]
		
	def physicalSize(self):
		return self._headerTuple[7]
		
	def flags(self):
		return self._headerTuple[8]
		
	def isLeaf(self):
		return (self.flags() & 0x01) == 0
		
	def hasChildren(self):
		return (self.flags() & 0x01) == 1
	
	def entries(self):
		return self._entries

class IndexAllocation(Attribute):
	'''This class represents the $A0 attribute.
	This attribute is really just a list of
	data runs.'''
	def __init__(self, buffer, offset=0):
		super(IndexAllocation, self).__init__(buffer, offset)
		self._entries=None
		
	def __str__(self):
		retStr=Attribute.__str__(self)
		retStr+='\nIndex Buffer Data runs: ' + str(len(self._dataRuns))
		retStr+='\nNumber of Index Buffers: ' + str(self.numberOfIndexBuffers())
		retStr+='\nIndex Buffer Clusters: ' + str(self.clusterList())
		return retStr			

	def numberOfIndexBuffers(self):
		return self.lastVcn()+1
		
	def getEntries(self, i30buffer):
		'''Returns the entire list of index entries
		stored in this $A0 attribute.  
		Warning: This list can be quite large!
		Entries are returned in the order in
		which they are stored in index buffers which
		may not be the correct order per the collation
		rule.'''
		self._entries=[]
		for i in range(self.numberOfIndexBuffers()):
			indexBuffer=IndexBuffer(i30buffer, i*4096)
			self._entries+=indexBuffer.entries()
	
	def hasEntries(self):
		'''Have the entries been retrieved?'''
		return self._entries!=None
		
	def numberOfEntries(self):
		if self.hasEntries():
			return len(self._entries)
		else:
			return 0
			
	def entries(self):
		return self._entries
		
	def entry(self, index):
		if self._entries:
			return self._entries[index]
			
class Bitmap(Attribute):
	'''This class is used to decode a $Bitmap ($B0) attribute.
	This attribute is normally used to keep track of index
	buffer allocation.'''
	def __init__(self, buffer, offset):
		super(Bitmap, self).__init__(buffer, offset)
		self._bitmap=buffer[offset+self.attributeOffset():offset+self.attributeOffset()+self.attributeLength()]
		
	def inUse(self, cluster):
		if cluster > len(self._bitmap) * 8:
			return False
		byteNumber = cluster // 8
		bitNumber = cluster % 8
		bitmapByte = self._bitmap[byteNumber]
		return (bitmapByte & 2**bitNumber) != 0
		
	def clustersInMap(self):
		return 8 * len(self._bitmap)
		
	def clustersInUse(self):
		inuse=0
		for i in range(self.clustersInMap()):
			if self.inUse(i):
				inuse+=1
		return inuse
		
	def __str__(self):
		retStr=Attribute.__str__(self)
		retStr+='\nClusters in use/bitmap: ' + str(self.clustersInUse()) + '/' + str(self.clustersInMap())
		return retStr

def getAttribute(buffer, offset=0):
	'''create a MFT attribute from
	a buffer and offset.  Will create
	a specific type if possible or 
	a generic attribute if not.'''
	if buffer[offset:offset+4]==b'\xff\xff\xff\xff':
		return
	attr=Attribute(buffer, offset)
	if attr.attributeType() == 0x10:
		attr=StandardInfo(buffer, offset)
	elif attr.attributeType() == 0x30:
		attr=Filename(buffer, offset)
	elif attr.attributeType() == 0x80:
		attr=Data(buffer, offset)
	return attr				
		
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
	pos = mftHeader.attributeStart()
	while pos < mftHeader.logicalRecordSize():
		attr=getAttribute(buffer, pos)
		if not attr:
			break
		print(attr)
		pos+=attr.totalLength()
	
if __name__=='__main__':
	main()

			
