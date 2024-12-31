#!/usr/bin/python
'''Simple Python script to find
various types of files from an
image file.  Sectors are searched
directly and the offset and sector number
are returned.

As developed by Dr. Phil Polstra
for PentesterAcademy.com.'''

# import the file info library
# note this is Python 2.x only
# and that is why this script is 
# in Python2
import magic
# process command line options
import optparse
# Regular Expressions
import re
# file existance
import os

'''Base class for file finder
merely defines some methods.'''
class FileFinder:
	def matches(self, buffer):
		return False
	def fileType(self):
		return 'Generic'


'''JPEG Finder'''
class JpegFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("JPEG image", str(mag)):
			return True
		else:
			return False
	def fileType(self):
		return 'JPEG'

'''PNG Finder'''
class PngFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("PNG image", str(mag)):
			return True
		else:
			return False
	def fileType(self):
		return 'PNG'
			
'''GIF Finder'''
class GifFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("Gif image", str(mag)):
			return True
		else:
			return False
	def fileType(self):
		return 'GIF'

'''BMP Finder'''
class BmpFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("PC bitmap", str(mag)):
			return True
		else:
			return False
	def fileType(self):
		return 'Bitmap'

'''Image Finder works will all image types'''
class ImageFinder(FileFinder):
	def __init__(self):
		self.finders=[]
		self.finders.append(JpegFinder())
		self.finders.append(PngFinder())
		self.finders.append(GifFinder())
		self.finders.append(BmpFinder())
		
	def matches(self, buffer):
		for finder in self.finders:
			if finder.matches(buffer):
				return True
		return False
	def fileType(self):
		return 'Image'
		
'''PDF Finder'''
class PdfFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("PDF document", str(mag)):
			return True
		else:
			return False
	def fileType(self):
		return 'PDF'

'''EXE Finder'''
class ExeFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("executable", str(mag)):
			return True
		else:
			return False
	def fileType(self):
		return 'Executable'

'''Zip Finder'''
class ZipFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("archive", str(mag)):
			return True
		else:
			return False
	def fileType(self):
		return 'Zip'

'''Powerpoint Finder'''
class PptFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("Composite Document File", str(mag)):
			return True
		elif re.search("PowerPoint", str(mag)):
		   return True
		else:
			return False
	def fileType(self):
		return 'Powerpoint'

'''Word Finder'''
class DocFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("Composite Document File", str(mag)):
			return True
		elif re.search("Microsoft Word", str(mag)):
		   return True
		elif re.search("Microsoft WinWord", str(mag)):
		   return True
		else:
			return False
	def fileType(self):
		return 'Word'

'''Excel Finder'''
class XlsFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("Composite Document File", str(mag)):
			return True
		elif re.search("Microsoft Excel", str(mag)):
		   return True
		else:
			return False
	def fileType(self):
		return 'Excel'

'''Office Finder
any MS office document'''
class OfcFinder(FileFinder):
	def matches(self, buffer):
		mag=magic.from_buffer(buffer)
		if re.search("Composite Document File", str(mag)):
			return True
		elif (re.search("PowerPoint", str(mag)) or
		   re.search("Microsoft Word", str(mag)) or
		   re.search("Microsoft WinWord", str(mag)) or
		   re.search("Microsoft Excel", str(mag))):
		   return True
		else:
			return False
	def fileType(self):
		return 'Office'




def main():
	# parse command line options
	parser=optparse.OptionParser(
    	'usage %prog [-s searchList] [-c clusterSize] <-i imageFile>  [-o offset]')
	parser.add_option('-s', '--search', dest='findList', 
		help='comma separated list of things to search for')
	parser.add_option('-c', '--cluster', dest='clusterSize',
		help='sectors to search at a time')
	parser.add_option('-i', '--image', dest='imageFilename',
		help='image file (raw format) to search')
	parser.add_option('-o', '--offset', dest='offset',
		help='offset to start of filesystem in sectors')
	(options, args)=parser.parse_args()
	imageFilename=options.imageFilename
	if options.offset:
		offset=int(options.offset)
	else:
		offset=0
	if options.clusterSize:
		clusterSize=int(options.clusterSize)
	else:
		clusterSize=1
	# parse comma separated search list
	findList=options.findList.split(',')
	finders=[] # start with empty list
	for f in findList:
		if f=='jpeg' or f=='jpg':
			finders.append(JpegFinder())
		elif f=='png':
			finders.append(PngFinder())
		elif f=='gif':
			finders.append(GifFinder())
		elif f=='bmp':
			finders.append(BmpFinder())
		elif f=='img' or f=='image':
			finders.append(ImageFinder())
		elif f=='pdf':
		   finders.append(PdfFinder())
		elif f=='exe':
		   finders.append(ExeFinder())
		elif f=='zip':
		   finders.append(ZipFinder())
		elif f=='ppt' or f=='powerpoint':
		   finders.append(PptFinder())
		elif f=='doc' or f=='word':
		   finders.append(DocFinder())
		elif f=='xls' or f=='excel':
		   finders.append(XlsFinder())
		elif f=='ofc' or f=='office':
		   finders.append(OfcFinder())
			
	if not os.path.exists(imageFilename):
		print('Image file not found!')
		return(1)
	# now parse through the file
	pos=offset * 512
	with open(imageFilename, 'rb') as f:
		f.seek(pos)
		buffer=f.read(512*clusterSize)
		while len(buffer)>0:
			for finder in finders:
				if finder.matches(buffer):
					print('Matching %s found at offset 0x%X, sector %d' %
					 (finder.fileType(),pos, pos//512))
					break
			pos+=512*clusterSize
			buffer=f.read(512*clusterSize)		
		
			
if __name__=='__main__':
	main()
		
