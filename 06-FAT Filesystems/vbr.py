#!/usr/bin/python3
# This is a simple Python script that will
# attempt to read VBR(s) from an image file.
# Developed for PentesterAcademy by Dr. Phil Polstra

import struct
import sys
import os.path
from mbr import Mbr

__all__=['Vbr']

class Vbr:
   def __init__(self, buffer):
      self.getVbr(buffer)

   def jumpCode(self):
      return self._vbrTuple[0]

   def oemName(self):
      return self._vbrTuple[1]

   def bytesPerSector(self):
      return self._vbrTuple[2]

   def sectorsPerCluster(self):
      return self._vbrTuple[3]

   def reservedSectors(self):
      return self._vbrTuple[4]

   def copiesOfFat(self):
      return self._vbrTuple[5]

   def rootDirectoryEntries(self):
      return self._vbrTuple[6]

   def totalSectors(self):
      if self._vbrTuple[7]==0:
         return self._vbrTuple[13]
      else:
         return self._vbrTuple[7]

   def mediaDescriptor(self):
      return self._vbrTuple[8]

   def sectorsPerFat(self):
      if self._vbrTuple[9]==0:
         return self._vbrTuple[14]
      else:
         return self._vbrTuple[9]

   def sectorsPerTrack(self):
      return self._vbrTuple[10]

   def heads(self):
      return self._vbrTuple[11]

   def hiddenSectors(self):
      return self._vbrTuple[12]

   def mirrorFlags(self):
      return self._vbrTuple[15]

   def filesystemVersion(self):
      if self._fat32:
         return self._vbrTuple[16]
      else:
         return None

   def rootDirectoryCluster(self):
      if self._fat32:
         return self._vbrTuple[17]
      else:
         return None

   def fsinfoSector(self):
      if self._fat32:
         return self._vbrTuple[18]
      else:
         return None

   def backupBootSector(self):
      if self._fat32:
         return self._vbrTuple[19]
      else:
         return None

   def logicalDrive(self):
      if self._fat32:
         return self._vbrTuple[21]
      else:
         return self._vbrTuple[14]

   def serialNumber(self):
      if self._fat32:
         return self._vbrTuple[24]
      else:
         return self._vbrTuple[17]

   def volumeLabel(self):
      if self._fat32:
         return self._vbrTuple[25]
      else:
         return self._vbrTuple[18]

   def filesystemType(self):
      if self._fat32:
         return self._vbrTuple[26]
      else:
         return self._vbrTuple[19]

   def bootCode(self):
      if self._fat32:
         return self._vbrTuple[27]
      else:
         return self._vbrTuple[20]

   def validSignature(self):
      if self._fat32:
         return self._vbrTuple[28]==b'\x55\xAA'
      else:
         return self._vbrTuple[21]==b'\x55\xAA'
      
   def isFat32(self):
      return self._fat32

   def mirrorFlags(self):
      if self._fat32:
         return self._vbrTuple[15]
      else:
         return None
         
   def sectorFromCluster(self, cluster):
      '''Given a cluster number returns a sector number
      relative to the start of the volume.  The sector
      for cluster 2 is first calculated'''
      sector=(self.copiesOfFat()*self.sectorsPerFat()+
         self.reservedSectors()+
         self.rootDirectoryEntries()//16) #FAT12/16
      sector+=(cluster-2)*self.sectorsPerCluster()
      return sector
   
   def offsetFromCluster(self, cluster):
      '''Gives offset within volume image for a given
      cluster number'''
      return (self.bytesPerSector()
      		* self.sectorFromCluster(cluster))
      
   def clusterFromSector(self, sector):
      cluster=(sector-self.copiesOfFat() 
      	 * self.sectorsPerFat()-
          self.reservedSectors()-
          self.rootDirectoryEntries()//16)//(
          self.sectorsPerCluster())+2
      return cluster
   
   def clusterFromOffset(self, offset):
      return self.clusterFromSector(offset//
      		self.bytesPerSector()) 
     
   def sectorFat1(self):
      return self.reservedSectors()
      
   def sectorFat2(self):
      return self.reservedSectors()+self.sectorsPerFat() 

   def getVbr(self, buffer):
      # first 28 bytes are common to all formats
      fmtStart=('<3s' + # 0 jump to bootstrap
         '8s' + # 1 OEM name
         'H' +  # 2 bytes/sector
         'B' +  # 3 sectors/cluster
         'H' +  # 4 reserved sectors
         'B' +  # 5 copies of FAT
         'H' +  # 6 root directory entries (0 for FAT32)
         'H' +  # 7 total number of sectors if <32MB
         'B' +  # 8 media descriptor (F8 or F0)
         'H' +  # 9 sectors/FAT for FAT12/16 or 0 for FAT32
         'H' +  # 10 sectors per track
         'H' )  # 11 number of heads
      fmt32=(	    # The end part for FAT32
         'I' +  # 12 hidden sectors
         'I' +  # 13 total number of sectors if >32MB
         'I' +  # 14 sectors/FAT for FAT32
         'H' +  # 15 mirror flags B7=1 single FAT in B0-3
         'H' +  # 16 filesystem version
         'I' +  # 17 root directory cluster (normally 2)
         'H' +  # 18 FSINFO sector (usually 1)
         'H' +  # 19 backup boot sector (usually 6)
         '12s' +# 20 reserved
         'B' +  # 21 logical drive (0x80, 0x81, etc)
         's' +  # 22 reserved
         'B' +  # 23 if 0x29 next 3 fields are present
         '4s' + # 24 serial number
         '11s' +# 25 volume label
         '8s' + # 26 filesystem type as string
         '420s'+# 27 boot code
         '2s')  # 28 should be 0x55 0xaa
      fmt1216=(   # The end part for FAT12/16
         'I' + # 12 Number of hidden sectors
         'I' + # 13 Total number of sectors (>32MB)
         'B' + # 14 Logical drive number (0x80, 0x81,...)
         'B' + # 15 Unused
         'B' + # 16 Extended boot signature (0x29).  
         '4s' +# 17 Serial number of partition
         '11s'+# 18 Volume Label or “No Name”
         '8s' +# 19 File system type (FAT12, etc.)
         '448s'+# 20 Bootstrap
         '2s') # 21 Signature 0x55 0xAA
      # is this FAT32?  If reserved sectors !=1 ->FAT32
      self._fat32=(struct.unpack('<H', buffer[14:16])!=1) 
      if self._fat32:
         fmt = fmtStart + fmt32
      else:
         fmt = fmtStart + fmt1216

      self._vbrTuple=struct.unpack(fmt, buffer)

def usage():
   print("usage " + sys.argv[0] + " <image file>\n"+
      "Reads VBR(s) from an image file")
   exit(1)

def main():
   if len(sys.argv) < 2: 
     usage()

   notsupParts = [0x05,0x0f,0x85,0x91,0x9b,0xc5,0xe4,0xee]
   swapParts = [0x42, 0x82, 0xb8, 0xc3, 0xfc]

   # read first sector
   if not os.path.isfile(sys.argv[1]):
      print("File " + sys.argv[1] + 
      	" cannot be openned for reading")
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
              print("Sorry GPT and extended partitions" +
              		" are not supported by this script!")
           else:
              if mbr.partitionType(i) in swapParts:
                 print("Skipping swap partition")
              else:
                 # let's try and read the VBR
                 with open(sys.argv[1], 'rb') as f:
                    f.seek(mbr.reservedSectors(i)*512)
                    sector=f.read(512)
                    vbr=Vbr(sector)
                    if vbr.validSignature():
                       print('Found Volume with type', 
                       			vbr.filesystemType())
                       print('Volume label:', vbr.volumeLabel())
                       print('Total sectors:', vbr.totalSectors())
                       s=vbr.sectorFromCluster(14)
                       print('Cluster 14:', s)
                       print('Sector:', vbr.clusterFromSector(s))
   else:
      print("Doesn't appear to contain valid MBR")
 
if __name__ == "__main__":
   main()        
        
