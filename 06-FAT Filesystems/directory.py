#!/usr/bin/python3

# This is a simple Python script that will
# attempt to read FAT directory entries from an image file.
# Developed for PentesterAcademy by Dr. Phil Polstra

import os.path
import sys
import struct
from mbr import Mbr
from vbr import Vbr
from fat import Fat

__all__=['Directory', 'FileEntry', 'DirEntry', 'timeTupleToString', 
   'dateTupleToString']

# helper functions for conversions
def fatTime(buffer):
   '''This function accepts a byte string
   that should be 2 bytes long and returns
   a tuple (hour, minutes, seconds)'''
   val=struct.unpack('<H', buffer)[0]
   seconds = 2*(val%32) # lowest 5 bits * 2
   hours=val//2048 # top 5 bits
   minutes=(val%2048)//32 # middle 6 bits
   return (hours, minutes, seconds)
   
def fatDate(buffer):
   '''This function accepts a byte string
   that should be 2 bytes long and returns
   a tuple (year, month, day)'''
   val=struct.unpack('<H', buffer)[0]
   day=val%32 # lowest 5 bits
   year=1980 + val//512 # top 7 bits +1980
   month=(val%512)//32 # middle 4 bits
   return (year, month, day)
   
def timeTupleToString(hms):
   '''Covert hour, minute, second tuple to 
   a pretty string'''
   if len(hms)!=3:
      return "None"
   (hour, minute, second)=hms
   if hour:
      return "%02d:%02d:%02d" % (hour, minute, second)
   else:
      return "None"
      
def dateTupleToString(ymd):
   '''Convert year, month, day tuple to
   a pretty string'''
   if len(ymd)!=3:   
      return "None"
   (year, month, day)=ymd
   if year:
      return "%04d-%02d-%02d" % (year, month, day)
   else:
      return "None"

class DirEntry:
   def __init__(self, buffer):
      '''This class represents a raw directory
      entry.  It is created by a buffer that
      should be 32 bytes long'''
      # is this a deleted entry?
      if buffer[0:1]==b'\xE5':
         self._deleted=True
      else:
         self._deleted=False
      # is this a long filename entry?
      if buffer[11:13]==b'\x0F\x00':
         self._longEntry=True
         self._sequenceNumber=struct.unpack('<B', buffer[0:1])[0]
         self._lastEntry=(self._sequenceNumber&0x40!=0)
         self._checksum=struct.unpack('<B', buffer[13:14])[0]
         fn=buffer[1:11]+buffer[14:26]+buffer[28:32]
         # is there an Unicode null in string?
         if fn.find(b'\x00\x00')>0:
            self._filename=fn[:fn.find(b'\x00\x00')+1].decode('utf-16')
         elif fn.find(b'\xFF\xFF')>0:
            self._filename=fn[:fn.find(b'\xFF\xFF')].decode('utf-16')
         else:
            self._filename=fn.decode("utf-16")
      else:
         # this is a short entry
         self._longEntry=False
         # this if is to prevent Unicode decoding errors
         if buffer[0:1]==b'\xE5':
            self._basename='_'+buffer[1:8].decode('utf-8')
         else:
            self._basename=buffer[0:8].decode('utf-8')
         self._extension=buffer[8:11].decode('utf-8')
         self._basename=self._basename.rstrip()
         self._extension=self._extension.rstrip()
         # any nulls in the name?
         if self._basename.find('\x00')>0:
            self._basename=self._basename[:self._basename.find('\x00')]
         if self._extension.find('\x00')>0:
            self._extension=self._extension[:self._extension.find('\x00')]
         self._attributes=struct.unpack('<B', buffer[11:12])[0]
         (self._createHour, self._createMinute, self._createSecond)=\
            fatTime(buffer[14:16])
         (self._createYear, self._createMonth, self._createDay)=\
            fatDate(buffer[16:18])
         (self._accessYear, self._accessMonth, self._accessDay)=\
            fatDate(buffer[18:20])
         self._startCluster=(65536*
            struct.unpack('<H', buffer[20:22])[0] +
            struct.unpack('<H', buffer[26:28])[0])
         (self._modifyHour, self._modifyMinute, self._modifySecond)=\
            fatTime(buffer[22:24])
         (self._modifyYear, self._modifyMonth, self._modifyDay)=\
            fatDate(buffer[24:26])
         self._filesize=struct.unpack('<I', buffer[28:32])[0]
         
   def longEntry(self):
      return self._longEntry
      
   def deleted(self):
      return self._deleted
   
   def attributes(self):
      if self.longEntry():
         return None
      else:
         return self._attributes
      
   def filename(self):
      if self._longEntry:
         return self._filename
      else:
         if len(self._extension)==0 or \
            self._extension=='   ':
            return self._basename
         else:
            return self._basename+'.'+self._extension
            
   def createTime(self):
      if self._longEntry:
         return (None, None, None)
      else:
         return (self._createHour, self._createMinute, self._createSecond)
         
   def createDate(self):
      if self._longEntry:
         return (None, None, None)
      else:
         return (self._createYear, self._createMonth, self._createDay)
         
   def modifyTime(self):
      if self._longEntry:
         return (None, None, None)
      else:
         return (self._modifyHour, self._modifyMinute, self._modifySecond)
         
   def modifyDate(self):
      if self._longEntry:
         return (None, None, None)
      else:
         return (self._modifyYear, self._modifyMonth, self._modifyDay)
         
   def accessDate(self):
      if self._longEntry:
         return (None, None, None)
      else:
         return (self._accessYear, self._accessMonth, self._accessDay)
    
   def startCluster(self):
      if self._longEntry:
         return None
      else:
         return self._startCluster
         
   def filesize(self):
      if self._longEntry:
         return None
      else:
         return self._filesize
         
class FileEntry:
   '''This class represents a file entry
   which may contain multiple raw directory
   entries.  A deleted file with a long
   name will result in multiple file 
   entries.  This is done to avoid problems
   if part of the complete entry gets 
   reused.'''
   def __init__(self, buffer, offset=0):
      '''Takes a buffer containing directory 
      entries with an optional offset.  If
      the first entry encountered is a long
      entry it will scan forward until the
      short entry is found.'''
      self._dirEntries=[]
      # is this an empty slot?
      if buffer[offset:offset+1]==b'\x00':
         return
      # is the first entry deleted?
      de=DirEntry(buffer[offset:offset+32])
      if de.deleted():
         # deleted entries get their own spot
         self._dirEntries.append(de)
         return
      # is this a long entry?   
      if de.longEntry():
         # scan forward till short entry
         oset=offset+32
         while de.longEntry():
            self._dirEntries.append(de)
            if buffer[oset:oset+1]==b'\x00':
               break
            de=DirEntry(buffer[oset:oset+32])
            oset+=32
         # now add the short entry
         self._dirEntries.append(de)
      else:
         # just a short entry
         self._dirEntries.append(de)
         
   def entries(self):
      return len(self._dirEntries)
      
   def empty(self):
      return len(self._dirEntries)==0
      
   def deleted(self):
      # deleted files have a single entry
      if self.empty():
         return False
      else:
         return self._dirEntries[0].deleted()
         
   def hasLongFilename(self):
      if self.empty():
         return False
      else:
         return self._dirEntries[0].longEntry()
         
   def hasShortFilename(self):
      if self.empty():
         return False
      else:
         return not self._dirEntries[self.entries()-1].longEntry()
       
   def longFilename(self):
      if not self.hasLongFilename():
         return None
      else:
         # is this a single deleted entry?
         if self.entries()==1:
            return self._dirEntries[0].filename()
         else:
            # all but the last entry contain the filename
            fn=""
            for i in range(self.entries()-2, -1,-1):
               fn+=self._dirEntries[i].filename()
            return fn
            
   def shortFilename(self):
      if self.empty() or \
         self._dirEntries[self.entries()-1].longEntry():
         return None
      else:
         return self._dirEntries[self.entries()-1].filename()
         
   def attributes(self):
      if self.empty() or \
         self._dirEntries[self.entries()-1].longEntry():
         return None
      else:
         return self._dirEntries[self.entries()-1].attributes()
         
   def readOnly(self):
      if self.attributes():
         return (self.attributes()&0x01)!=0
      else:
         return False
   
   def hidden(self):
      if self.attributes():
         return (self.attributes()&0x02)!=0
      else:
         return False

   def systemFile(self):
      if self.attributes():
         return (self.attributes()&0x04)!=0
      else:
         return False
         
   def volumeLabel(self):
      if self.attributes():
         return (self.attributes()&0x08)!=0
      else:
         return False
         
   def directory(self):
      if self.attributes():
         return (self.attributes()&0x10)!=0
      else:
         return False
            
   def archive(self):
      if self.attributes():
         return (self.attributes()&0x20)!=0
      else:
         return False
   
   def createTime(self):
      if not self.hasShortFilename():
         return (None, None, None)
      else:
         return self._dirEntries[self.entries()-1].createTime()         

   def createDate(self):
      if not self.hasShortFilename():
         return (None, None, None)
      else:
         return self._dirEntries[self.entries()-1].createDate() 
         
   def accessDate(self):
      if not self.hasShortFilename():
         return (None, None, None)
      else:
         return self._dirEntries[self.entries()-1].accessDate()
         
   def modifyTime(self):
      if not self.hasShortFilename():
         return (None, None, None)
      else:
         return self._dirEntries[self.entries()-1].modifyTime()

   def modifyDate(self):
      if not self.hasShortFilename():
         return (None, None, None)
      else:
         return self._dirEntries[self.entries()-1].modifyDate() 
         
   def startCluster(self):
      if not self.hasShortFilename():
         return None
      else:
         return self._dirEntries[self.entries()-1].startCluster()
         
   def filesize(self):
      if not self.hasShortFilename():
         return None
      else:
         return self._dirEntries[self.entries()-1].filesize()
         
   def __str__(self):
      '''Used by print().'''
      if self.hasLongFilename():
         return '<LFN> '+self.longFilename()
      else:
         return self.shortFilename()
         
   def prettyPrint(self):
      if self.empty():
         print('<Empty>')
         return
      print('Deleted:', self.deleted())
      if self.hasLongFilename():
         print('Long filename:', self.longFilename())
      if self.hasShortFilename():
         print('Short filename:', self.shortFilename())
      print('Start cluster:', self.startCluster())
      print('Filesize:', self.filesize())
      if self.attributes():
         print('Attributes: %02X' % self.attributes())
      print('Created:', dateTupleToString(self.createDate()), 
         timeTupleToString(self.createTime()))
      print('Accessed:', dateTupleToString(self.accessDate()))
      print('Modified:', dateTupleToString(self.modifyDate()),
         timeTupleToString(self.modifyTime()))
         
                 
class Directory:
   '''This class represents a directory as a collection
   of fileEntry objects.  The directory is created by
   passing the constructor all of the appropriate clusters.'''
   def __init__(self, buffer):
      self._dirEntries=[]
      # while we haven't hit the end add entries
      offset=0
      while offset < len(buffer):
         if buffer[offset:offset+1]==b'\x00':
            break
         de=FileEntry(buffer, offset)
         offset+=32*de.entries() # skip to next file
         self._dirEntries.append(de)
         
   def entries(self):
      return len(self._dirEntries)
      
   def entry(self, numb):
      if numb >= self.entries():
         return None
      return self._dirEntries[numb]
      
   def list(self):
      for de in self._dirEntries:
         de.prettyPrint()


def usage():
   print("usage " + sys.argv[0] + " <image file>\n"+
      "Reads FAT Directory Entries from an image file")
   exit(1)

         
def main():
   if len(sys.argv) < 2: 
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
                       print('Cluster 2 allocated:',fat.isAllocated(2))
                       print('Chain starting at 2:',fat.clusterChain(2))
                       # now grab the Root Directory
                       cchain=fat.clusterChain(2)
                       rdBuffer=b''
                       for clust in cchain:
                           f.seek(mbr.reservedSectors(i)*512+
                              512*vbr.sectorFromCluster(clust))
                           rdBuffer+=f.read(512*vbr.sectorsPerCluster())
                       rd=Directory(rdBuffer)
                       rd.list()
   else:
      print("Doesn't appear to contain valid MBR")
 
if __name__ == "__main__":
   main()        
   
            
         
        
   
   
   
         
         
            
         
         
