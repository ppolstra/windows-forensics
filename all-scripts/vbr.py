#!/usr/bin/python3
'''
NTFS Volume Boot Record Parser
Created by Dr. Phil Polstra
for PentesterAcademy.com
'''

__all__=['Vbr']

import struct   # for interpreting the VBR
import optparse # for command line options

class Vbr:
	def __init__(self, buffer):
		'''Create a Vbr object from a buffer that is at least
		 512 bytes (1 sector) long.'''
		formatStr=('<3s' + # jump instruction 0
		 	'8s' + 			# OEM name (NTFS) 1
		 	'H'  +			# bytes/sector (512) 2
		 	'B'  +			# sectors/cluster (8) 3
		 	'7s' +			# padding (all zeroes) 4
		 	'B'  +			# media descriptor (F8) 5
		 	'H'  +			# should be 0 6
		 	'H'	 +			# sectors/track 7
		 	'H'  +			# number of heads 8
		 	'L'  +			# hidden sectors (before partition) 9
		 	'L'  + 			# padding 10
		 	'L'  +			# signature (0x80 0x00 0x80 0x00) 11
		 	'Q'  +			# total sectors 12
		 	'Q'  +			# LCN for $MFT 13
		 	'Q'  +			# LCN for $MFTMirr (2) 14
		 	'L'  +			# clusters/file record segment 15
		 	'B'  +			# clusters/index buffer (1) 16
		 	'3s' +			# padding 17
		 	'8s' +			# volume serial number 18
		 	'L'  +			# checksum (unused) 19
		 	'426s' +		# boot code 20
		 	'2s' )			# signature
		self._vbrTuple=struct.unpack(formatStr, buffer[:512])

	def jumpInstruction(self):
		return self._vbrTuple[0]
		
	def oemName(self):
		return self._vbrTuple[1]
		
	def bytesPerSector(self):
		return self._vbrTuple[2]
		
	def sectorsPerCluster(self):
		return self._vbrTuple[3]
		
	def bytesPerCluster(self):
		return self.bytesPerSector() * self.sectorsPerCluster()
		
	def clusterOffset(self, cluster=0):
		return (self.hiddenSectors() * self.bytesPerSector() +
					 self.bytesPerCluster() * cluster )
		
	def mediaDescriptor(self): 
		return self._vbrTuple[5]
		
	def isFloppy(self):
		return self._vbrTuple[5]==0xF0
		
	def isHardDisk(self):
		return self._vbrTuple[5]==0xF8
		
	def sectorsPerTrack(self):
		return self._vbrTuple[7]
		
	def heads(self):
		return self._vbrTuple[8]
		
	def hiddenSectors(self):
		return self._vbrTuple[9]
		
	def totalSectors(self):
		return self._vbrTuple[12]
		
	def mftLcn(self):
		return self._vbrTuple[13]
		
	def mftMirrLcn(self):
		return self._vbrTuple[14]
		
	def clustersPerRecordSegment(self):
		return self._vbrTuple[15]
		
	def clustersPerIndexBuffer(self):
		return self._vbrTuple[16]
		
	def volumeSerialNumber(self):
		return self._vbrTuple[18]
		
	def checksum(self):
		return self._vbrTuple[19]
		
	def bootCode(self):
		return self._vbrTuple[20]
	
	def signature(self):
		return self._vbrTuple[21]
		
	def isSignatureValid(self):
		return self._vbrTuple[21]=='\x55\xaa'
		
	def getCluster(self, cluster, imageFilename):
		'''Opens an image file and retrieves data stored in
		a single cluster.'''
		with open(imageFilename, 'rb') as f:
			f.seek(self.clusterOffset(cluster))
			data=f.read(self.bytesPerCluster())
		return data
		
	def __str__(self):
		retStr=('OEM Name: '			+ str(self.oemName()) +
				'\nBytes/sector: '		+ str(self.bytesPerSector()) +
				'\nSectors/cluster: '	+ str(self.sectorsPerCluster()) +
				'\nMedia descriptor: '	+ str('%X' % self.mediaDescriptor()) +
				'\nSectors/track: '		+ str(self.sectorsPerTrack()) +
				'\nHeads: '				+ str(self.heads()) +
				'\nHidden sectors: '	+ str(self.hiddenSectors()) +
				'\nTotal sectors: '		+ str(self.totalSectors()) +
				'\nMFT LCN: '			+ str(self.mftLcn()) +
				'\nMFT Mirror: '		+ str(self.mftMirrLcn()) +
				'\nClusters/Rec Seg: '	+ str(self.clustersPerRecordSegment()) +
				'\nClusters/INDX: '		+ str(self.clustersPerIndexBuffer()) +
				'\nSerial Number: '		+ str(self.volumeSerialNumber()) +
				'\nChecksum: '			+ str(self.checksum()) )
		return retStr
		
def main():
	parser=optparse.OptionParser()
	parser.add_option("-f", "--file", dest="filename",
					help="image filename")
	parser.add_option("-o", "--offset", dest='offset',
					help='offset in sectors to start of volume')
					
	(options, args)=parser.parse_args()
	filename=options.filename
	if options.offset:
		offset=512 * int(options.offset)
	else:
		offset=0
		
	with open(filename, 'rb') as f:
		f.seek(offset)
		buffer=f.read(512)
	
	vbr=Vbr(buffer)
	print(vbr)
	
	
if __name__=='__main__':
	main()
			
		 
