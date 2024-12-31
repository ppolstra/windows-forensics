#!/usr/bin/python3
'''Simple script to extract a file or
directory using its MFT entry number.
Create by Dr. Phil Polstra (@ppolstra)
for PentesterAcademy.com.'''

from mft import *
import optparse
from vbr import Vbr

def mftOffset(entry, vbr):
   '''Given a Vbr object and MFT entry number
   this function will return the correct offset
   into a filesystem image assuming the MFT is
   NOT FRAGMENTED.'''
   return (vbr.mftLcn() * # logical cluster number
   vbr.bytesPerSector() * # sector size
   vbr.sectorsPerCluster() + # sectors/cluster
   1024 * entry ) # MFT entry is 1k long

def main():
   parser=optparse.OptionParser()
   parser.add_option("-f", "--file", dest="filename",
               help="image filename")
   parser.add_option("-o", "--offset", dest='offset',
               help='offset in sectors to start of volume')
   parser.add_option("-e", "--entry", dest='entry',
               help='MFT entry number')
   parser.add_option('-d', '--directory', dest='directory',
               help='output directory')
   parser.add_option('-m', '--mft', dest='mftFile',
               help='MFT file')
   parser.add_option('-s', '--slack', dest='indxSlack', action='store_true',
               help='Included INDX buffer slack')
               
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
      
   if options.directory:
      outDir=options.directory
      if outDir[len(outDir)-1]!='/':
         outDir+='/'
   else:
      outDir='./'   
      
   with open(filename, 'rb') as f:
      f.seek(offset)
      buffer=f.read(512)
   
   vbr=Vbr(buffer)
   
   # calculate the offset to the MFT entry
   mOffset = (offset + # offset to start of partition
            mftOffset(entry, vbr))
   
   # did they supply a MFT files?
   # only needed if MFT is fragmented          
   if options.mftFile:
      with open(options.mftFile, 'rb') as f:
         f.seek(entry * 1024)
         buffer=f.read(1024)
   else:
      with open(filename, 'rb') as f:
         f.seek(mOffset)
         buffer=f.read(1024)
   
   mftEntry=MftEntry(buffer)
   # check for fragmented MFT
   if mftEntry.recordNumber()!=entry:
      print('Fragmented MFT detected...Exiting')
      return -1
      
   # get the filename attribute(s)
   filenames=mftEntry.attributesOfType(0x30)
   if len(filenames)==0:
      return
      
   # if there is more than one filename get longest
   if len(filenames) > 0:
      fnLength=0
      for fnEntry in filenames:
         if fnEntry.nameLength() > fnLength:
            fname=fnEntry.filename()
            fnLength=fnEntry.nameLength()
   # take care of special cases
   if fname[0]=='.':
      fname='root'
   elif fname[0]=='$':
      fname='dollar'+fname[1:]         
   # file or directory?
   if filenames[0].isDirectory():
      # get the $I30 file
      indexAllocs=mftEntry.attributesOfType(0xa0)
      if len(indexAllocs) > 0:
         # we don't handle the case of A0 in Attribute list
         # I have never seen this happen
         clusterList=[]
         for indexAlloc in indexAllocs:
            clusterList+=indexAlloc.clusterList()
      bitmaps=mftEntry.attributesOfType(0xb0)
      if len(bitmaps)==1:   
         print('Creating INDX file index-'+str(fname))   
         with open(outDir+'index-'+str(fname), 'wb') as outFile:
            for i in range(len(clusterList)):
               if options.indxSlack or bitmaps[0].inUse(i):
                  outFile.write(vbr.getCluster(clusterList[i], filename))
   else:
      # get the file data
      # check for attribute list case
      attributeLists=mftEntry.attributesOfType(0x20)
      if len(attributeLists) > 0:
         # get the MFT entries that contain $80 attributes
         firstVcn=-1
         mftList=[]
         for attributeList in attributeLists:
            recordList=attributeList.list()
            for record in recordList:
               if record.attributeType()==0x80:
                  if record.vcn()>firstVcn:
                     mftList.append(record.mft())
                     firstVcn=record.vcn()
                  else:
                     mftList.insert(0, record.mft())
         dataAttributes=[]
         for mftNo in mftList:
            # get the MFT
            # calculate the offset to the MFT entry
            eOffset = (offset + # offset to start of partition
                     mftOffset(mftNo, vbr))
            
            if options.mftFile:
               with open(options.mftFile, 'rb') as f:
                  f.seek(mftNo * 1024)
                  buffer2=f.read(1024)
            else:          
               with open(filename, 'rb') as f:
                  f.seek(eOffset)
                  buffer2=f.read(1024)
            tEntry=MftEntry(buffer2)
            # check for fragmented MFT
            if tEntry.recordNumber()!=mftNo:
               print('Fragmented MFT detected...exiting')
               return -1   
            dataAttributes+=tEntry.attributesOfType(0x80)
      else:
         # get the cluster list or inline data
         dataAttributes=mftEntry.attributesOfType(0x80)
      clusterList=[]
      adsClusterList=[]
      adsName=None
      adsData=None
      data=None
      lastVcn=-1
      adsLastVcn=-1
      
      for dataAttr in dataAttributes:
         if dataAttr.hasName():
            # we have an alternate data stream
            adsName=dataAttr.name()
            if dataAttr.data():
               adsData=dataAttr.data()
            else:
               if dataAttr.firstVcn() > adsLastVcn:
                  adsClusterList+=(dataAttr.clusterList())
                  adsLastVcn=dataAttr.lastVcn()
               else:
                  adsClusterList=dataAttr.clusterList()+adsClusterList   
         else:
            # normal data stream
            if dataAttr.data():
               data=dataAttr.data()
            else:
               if dataAttr.firstVcn() > lastVcn:
                  clusterList+=(dataAttr.clusterList())
                  lastVcn=dataAttr.lastVcn()
               else:
                  clusterList=dataAttr.clusterList()+clusterList   
      
      # now write to the file(s)
      print("Extracting file "+str(fname))
      with open(outDir+str(fname), 'wb') as outFile:
         if data:
            outFile.write(data)
         else:
            for cluster in clusterList:
               outFile.write(vbr.getCluster(cluster, filename))
      if adsName:
         print("Extracting alternate data stream", adsName, "for file", fname)
         with open(outDir+str(fname)+'-ads-'+adsName, 'wb') as outFile:
            if adsData:
               outFile.write(adsData)
            else:
               for cluster in adsClusterList:
                  outFile.write(vbr.getCluster(cluster, filename))
   
if __name__=='__main__':
   main()

         
