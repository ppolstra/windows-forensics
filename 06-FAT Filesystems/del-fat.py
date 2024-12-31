#!/usr/bin/python3
'''This script will list and optionally attempt
to recover deleted files on a FAT filesystem
given the directory's starting cluster and an
image file.

Created by Dr. Phil Polstra
for PentesterAcademy.com'''

import os.path
import sys
import struct
from mbr import Mbr
from vbr import Vbr
from fat import Fat
from directory import *

__all__=['DeletedEntry', 'DeletedList']

class DeletedEntry(FileEntry):
   '''This class extends the FileEntry class
   to include support for deleted files.  It
   will give the probability of recovery and
   also attempts to recover a deleted file.'''
   def __init__(self, buffer, offset=0, fat32=True, clusterSize=4096):
      '''FAT32 might zero out the high word for the
      starting cluster, so we need to know if this is
      a 32-bit FAT filesystem when attempting recovery.'''
      super().__init__(buffer, offset)
      self._fat32=fat32
      self._clusterSize=clusterSize
      
   def definitelyNotRecoverable(self, fat):
      '''A file is definitely not recoverable if it 
      is a long filename entry or the starting 
      cluster is zero or the starting cluster is
      allocated.'''
      if not self.deleted():
         return True
      if self.hasLongFilename():
         return True
      if not self._fat32 and self.startCluster()==0:
         return True
      if (not self._fat32 and
         fat.isAllocated(self.startCluster()) ):
         return True
      if (self._fat32 and
         self.startCluster()//65536>0 and
         fat.isAllocated(self.startCluster()) ):
         return True
      return False
         
   def definitelyRecoverable(self, fat):
      '''A file is definitely recoverable if it
      is less than a cluster long and the cluster
      is unallocated.  We could also check the 
      RAM slack but that would require access
      to the filesystem image.'''
      if not self.deleted():
         return False
      if (not self._fat32 and
         self.filesize() <= self._clusterSize and 
         not fat.isAllocated(self.startCluster()) ):
         return True
      if (self._fat32 and
         self.startCluster()//65536>0 and
         self.filesize() <= self._clusterSize and
         not fat.isAllocated(self.startCluster()) ):
         return True 
      return False 
      
   def __str__(self):
      '''Method for print.  Will print 
      will print <DEL> before filename.'''
      prefix=''
      if self.deleted():
         prefix='<DEL>'
      return prefix + super().__str__()
      
   def recoverFile(self, imageFile, offset, fat, vbr, hiwordGuess=0):
      '''Attempt to recover the file given the image
      filename, offset to the start of the partition
      in bytes, and the FAT & VBR objects (because you probably
      had it and this will speed up the process).
      Returns the number of candidate files recovered.'''
      # first check that it isn't hopeless
      if self.definitelyNotRecoverable(fat):
         return 0
      if self._fat32:
         return self._recoverFileFat32(imageFile, offset, fat, vbr, hiwordGuess)
      else:
         return self._recoverFileFat16(imageFile, offset, fat, vbr)
         
   def _recoverFileFat16(self, imageFile, offset, fat, vbr):
      '''Recover a file from a FAT16 or FAT12 filesytem.
      Accepts the image filename, offset in bytes to the 
      start of the partition and FAT object.'''
      fname=self.shortFilename()
      # first check for the easy case
      if self.definitelyRecoverable(fat):
         # The file is less than a cluster long
         with open(imageFile, 'rb') as f:
            f.seek(offset + vbr.offsetFromCluster(self.startCluster()))
            fileContent=f.read(self._clusterSize)
         with open(fname, 'wb') as f:
            f.write(fileContent)
         return 1 # one candidate file recovered
      # this check shouldn't be needed unless this is called directly   
      if not self.definitelyNotRecoverable():
         # get the candidate cluster chain
         cchain=self._getCandidateChain(imageFile, offset, fat, vbr, 0)
         if len(cchain)==0: # got nothing
            return 0
         with open(imageFile, 'rb') as f:
            with open(fname, 'wb') as g:
               for i in cchain:
                  f.seek(offset+vbr.offsetFromCluster(i))
                  fileContent=f.read(self._clusterSize)
                  g.write(fileContent)
         return 1
      return 0
         
   def _recoverFileFat32(self, imageFile, offset, fat, vbr, hiwordGuess):
      '''Recover a file from a FAT32 filesytem.
      Accepts the image filename, offset in bytes to the 
      start of the partition and FAT object.'''
      fname=self.shortFilename()
      # first check for the easy case
      if self.definitelyRecoverable(fat):
         # The file is less than a cluster long
         with open(imageFile, 'rb') as f:
            f.seek(offset + vbr.offsetFromCluster(self.startCluster()))
            fileContent=f.read(self._clusterSize)
         with open(fname, 'wb') as f:
            f.write(fileContent)
         return 1 # one candidate file recovered
      # this check shouldn't be needed unless this is called directly   
      if not self.definitelyNotRecoverable(fat):
         # get the candidate cluster chain
         # start with the suggested hiword
         cchain=self._getCandidateChain(imageFile, offset, fat, vbr, hiwordGuess)
         if len(cchain)>0: # got something
            with open(imageFile, 'rb') as f:
               with open(fname, 'wb') as g:
                  for i in cchain:
                     f.seek(offset+vbr.offsetFromCluster(i))
                     fileContent=f.read(self._clusterSize)
                     g.write(fileContent)
            return 1
         # if the best guess hiword is not it, try the next hiword
         cchain=self._getCandidateChain(imageFile, offset, fat, vbr, hiwordGuess+1)
         if len(cchain)>0: # got something
            with open(imageFile, 'rb') as f:
               with open(fname, 'wb') as g:
                  for i in cchain:
                     f.seek(offset+vbr.offsetFromCluster(i))
                     fileContent=f.read(self._clusterSize)
                     g.write(fileContent)
            return 1
         # if we are here then we're getting desperate will
         # cycle through the hiwords
         candidates=0
         for i in range(0, 
            vbr.totalSectors()//vbr.sectorsPerCluster()//65536):
            cchain=self._getCandidateChain(imageFile, offset, fat, vbr, i)
            if len(cchain)>0: # got something
               candidates+=1
               with open(imageFile, 'rb') as f:
                  with open(fname+str(candidates), 'wb') as g:
                     for j in cchain:
                        f.seek(offset+vbr.offsetFromCluster(j))
                        fileContent=f.read(self._clusterSize)
                        g.write(fileContent)
         return candidates
             
      return 0


   def _getCandidateChain(self, imageFile, offset, fat, vbr, hiword):
      '''Given a start cluster hi word this method returns
      a list of cluster numbers for a file.  For FAT12/16
      the hi word should just be zero.  If the hi word is
      not zero then additional checks are performed to
      make sure a bunch of empty clusters at the end
      of the disk are not being matched.'''
      clusters=self.filesize()//self._clusterSize
      if self.filesize()%self._clusterSize !=0:
         clusters+=1 # add a partial cluster
      ramSlack=512-self.filesize()%512
      fileSlack=(self._clusterSize-self.filesize()%self._clusterSize)//512
      candidateChain=[]
      # if the starting cluster is allocated it is a no-go
      if fat.isAllocated(self.startCluster()%65536 +
         hiword*65536):
         return candidateChain
      # short circuit for FAT12/16
      foundClusters=0
      if not self._fat32 or \
         self.startCluster()//65536>0:
         for i in range(self.startCluster(), 
            vbr.totalSectors()//vbr.sectorsPerCluster()):
            if not fat.isAllocated(i):
               candidateChain.append(i)
               foundClusters+=1
            if foundClusters >=clusters:
               break
         return candidateChain
      # if we made it this far it is FAT32
      for i in range(self.startCluster() + 65536*hiword,
         vbr.totalSectors()//vbr.sectorsPerCluster()):
         if not fat.isAllocated(i):
            candidateChain.append(i)
            foundClusters+=1
         if foundClusters >=clusters:
            # now check that none of these clusters is all
            # zeroes - true that could be legit, but it is
            # very unlikely that such a file has any forensic
            # significance
            with open(imageFile, 'rb') as f:
               for j in candidateChain:
                  f.seek(offset + 
                  vbr.offsetFromCluster(j))
                  fileContent=f.read(self._clusterSize)
                  if fileContent==b'\x00'*self._clusterSize:
                     # the entire cluster was blank
                     return []
               #one final check of RAM slack
               f.seek(offset + 
                  vbr.offsetFromCluster(candidateChain[clusters-1]+1)-
                  512 * fileSlack - ramSlack)
               fileContent=f.read(ramSlack)
               if fileContent==b'\x00'*ramSlack:
                  return candidateChain
               else:
                  return []
                     
            
      

class DeletedList(Directory):
   '''This class creates a list of deleted
   files from a raw directory buffer.'''
   
   def __init__(self, buffer, fat32=True, clusterSize=4096):
      self._dirEntries=[]
      # while we haven't hit the end add entries
      offset=0
      while offset < len(buffer):
         if buffer[offset:offset+1]==b'\x00':
            break
         de=FileEntry(buffer, offset)
         if buffer[offset:offset+1]==b'\xE5':
            de=DeletedEntry(buffer, offset, fat32, clusterSize)
            self._dirEntries.append(de)
         offset+=32*de.entries() # skip to next file

        
def usage():
   print("usage " + sys.argv[0] + " <image file> <cluster>\n"+
      "Reads FAT Directory Entries from an image file")
   exit(1)

         
def main():
   if len(sys.argv) < 3: 
     usage()

   notsupParts = [0x05, 0x0f, 0x85, 0x91, 0x9b, 0xc5, 0xe4, 0xee]
   swapParts = [0x42, 0x82, 0xb8, 0xc3, 0xfc]

   # read first sector
   if not os.path.isfile(sys.argv[1]):
      print("File " + sys.argv[1] + " cannot be openned for reading")
      exit(1)

   with open(sys.argv[1], 'rb') as f:
      sector = f.read(512)

   mbr=Mbr(sector) # create MBR object

   if mbr.validSignature():
      print("Looks like a MBR or VBR")
      mbr.prettyPrint()

      for i in range(1,5):
         if not mbr.isEmpty(i):
           if mbr.partitionType(i) in notsupParts:
              print("Sorry GPT and extended partitions are not supported by this script!")
           else:
              if mbr.partitionType(i) in swapParts:
                 print("Skipping swap partition")
              else:
                 # let's try and read the VBR
                 with open(sys.argv[1], 'rb') as f:
                    f.seek(mbr.reservedSectors(i)*512)
                    sector=f.read(512)
                    vbr=Vbr(sector)
                    if vbr.validSignature() and vbr.isFat32():
                       print('Found Volume with type', vbr.filesystemType())
                       print('Volume label:', vbr.volumeLabel())
                       print('Total sectors:', vbr.totalSectors())
                       s=vbr.sectorFromCluster(2)
                       print('Cluster 2:', s)
                       print('Sector:', vbr.clusterFromSector(s))
                       # grab the FAT
                       f.seek(mbr.reservedSectors(i)*512+
                           vbr.sectorFat1()*512)
                       fatRaw=f.read(512*vbr.sectorsPerFat())
                       fat=Fat(fatRaw)
                       # now grab the Directory
                       print('Fetching directory in cluster', sys.argv[2])
                       cchain=fat.clusterChain(int(sys.argv[2]))
                       rdBuffer=b''
                       for clust in cchain:
                           f.seek(mbr.reservedSectors(i)*512+
                              512*vbr.sectorFromCluster(clust))
                           rdBuffer+=f.read(512*vbr.sectorsPerCluster())
                       rd=DeletedList(rdBuffer, vbr.isFat32(), 
                           512*vbr.sectorsPerCluster())
                       for j in range(rd.entries()):
                           delFile=rd.entry(j)
                           print(delFile)
                           if delFile.hasShortFilename():
                              print('\tDefinitelyNotRecoverable:', 
                                 delFile.definitelyNotRecoverable(fat))
                              print('\tDefinitelyRecoverable:',
                                 delFile.definitelyRecoverable(fat))
                           delFile.recoverFile(sys.argv[1], 
                              mbr.reservedSectors(i)*512,
                              fat, vbr, 
                              int(sys.argv[2])//65536)
                           
   else:
      print("Doesn't appear to contain valid MBR")
 
if __name__ == "__main__":
   main()        
         
