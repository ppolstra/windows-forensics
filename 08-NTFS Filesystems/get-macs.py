#!/usr/bin/python3
'''Simple script to extract timeline info.
This script will extract just infomation
found in MFT or also include index buffers
if an image file is given.
Create by Dr. Phil Polstra (@ppolstra)
for PentesterAcademy.com.'''

from mft import *
import optparse
from vbr import Vbr
import time

def printHeader():
   '''Prints the header listing columns.'''
   print('Source;AccessDate;AccessTime;ModifyDate;ModifyTime;'
         'CreateDate;CreateTime;RecordChangeDate;RecordChangeTime;'
         'MftEntry;UpdateSequence;'
         'Attributes;FileSize;AllocatedSize;Filename')

def printLine(source, accessTs, modifyTs, createTs, recordChangeTs,
               mftNo, updateSeq,
               attributes, fileSize=0, allocatedSize=0, filename='<unknown>'):
   '''This function creates the CSV line.'''
   print(source,             # where is this from
         time.strftime('%Y-%m-%d', accessTs), 
         time.strftime('%H:%M:%S', accessTs),
         time.strftime('%Y-%m-%d', modifyTs), 
         time.strftime('%H:%M:%S', modifyTs),
         time.strftime('%Y-%m-%d', createTs), 
         time.strftime('%H:%M:%S', createTs),
         time.strftime('%Y-%m-%d', recordChangeTs), 
         time.strftime('%H:%M:%S', recordChangeTs),
         mftNo, updateSeq,
         attributes, fileSize, allocatedSize, '"'+str(filename)+'"', 
         sep=';')
   
def main():
   parser=optparse.OptionParser()
   parser.add_option("-f", "--file", dest="filename",
               help="image filename")
   parser.add_option("-o", "--offset", dest='offset',
               help='offset in sectors to start of volume')
   parser.add_option('-m', '--mft', dest='mftFile',
               help='MFT file')
               
   (options, args)=parser.parse_args()
   filename=options.filename
   if options.offset:
      offset=512 * int(options.offset)
   else:
      offset=0
      
   # if we have an image file grab VBR
   if options.filename:   
      with open(options.filename, 'rb') as f:
         f.seek(offset)
         buffer=f.read(512)
   
      vbr=Vbr(buffer)


   # MFT file is a required option
   if not options.mftFile:
      print('Sorry, this script requires an MFT file')
      return -1
         
   # now open the MFT file and get all the info for each entry
   with open(options.mftFile, 'rb') as mftF:
      buffer=mftF.read(1024)
      printHeader()
      while buffer:
         mftEntry=MftEntry(buffer)
         # do filenames first
         fnames = mftEntry.attributesOfType(0x30)
         if len(fnames)>0:
            for fnameAttr in fnames:
               printLine('F', fnameAttr.accessTime(), 
                  fnameAttr.modificationTime(),
                  fnameAttr.creationTime(),
                  fnameAttr.recordChangeTime(),
                  mftEntry.recordNumber(), mftEntry.sequenceNumber(),
                  fnameAttr.flags(),
                  fnameAttr.logicalSize(),
                  fnameAttr.physicalSize(), 
                  fnameAttr.filename())
            # now get the standard info
            # this is done second so we can get size and filename
            for stdInfo in mftEntry.attributesOfType(0x10):
               printLine('S', stdInfo.accessTime(), 
                  stdInfo.modificationTime(),
                  stdInfo.creationTime(),
                  stdInfo.recordChangeTime(),
                  mftEntry.recordNumber(), mftEntry.sequenceNumber(),
                  stdInfo.flags(),
                  fnameAttr.logicalSize(),
                  fnameAttr.physicalSize(), 
                  fnameAttr.filename())
            # now get the index buffers, but only if you gave
            # me an image file
            if options.filename and mftEntry.isDirectory():
               indexAllocs=mftEntry.attributesOfType(0xA0)
               for indexAlloc in indexAllocs:
                  # we don't handle the case of A0 in Attribute list
                  # I have never seen this happen
                  clusterList=[]
                  clusterList+=indexAlloc.clusterList()
                  # build $I30 file in memory
                  indxBuffer=b''
                  for clusterNo in clusterList:
                     indxBuffer+=vbr.getCluster(clusterNo, filename)
                  indexAlloc.getEntries(indxBuffer)
                  for i in range(indexAlloc.numberOfEntries()):
                     indexEntry=indexAlloc.entry(i)
                     printLine('I', indexEntry.accessTime(), 
                        indexEntry.modificationTime(),
                        indexEntry.creationTime(),
                        indexEntry.recordChangeTime(),
                        indexEntry.mft(), indexEntry.sequenceNumber(),
                        indexEntry.flags(),
                        indexEntry.logicalSize(),
                        indexEntry.physicalSize(), 
                        indexEntry.filename())
         buffer=mftF.read(1024)
                                 
   
if __name__=='__main__':
   main()

         
