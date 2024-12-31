#!/usr/bin/python3
# This is a simple Python script that will
# attempt to mount partitions from an image file.
# Images are mounted read-only.  
#
# Developed for PentesterAcademy by Dr. Phil Polstra

import sys
import os.path
import subprocess
import struct

class Mbr():
   ''' Master Boot Record class
   Accepts a sector (512 bytes) and creates an MBR object.
   The MBR object can be queried for its attributes.
   The data is stored in a tuple using struct.unpack.'''
   def __init__(self, sector):
      '''This constructor expects a 512-byte MBR sector.
      It will populate the ._mbrTuple.'''
      fmt=('<446s' + # Boot code
         # partition 1
         'B' + # Active flag 0x80 is active (bootable)
         'B' + # Start head
         'B' + # Start sector only bits 0-5 bits 6-7 for cylinder
         'B' + # Start cylinder (upper 2 bits in previous byte)
         'B' + # partition type code
         'B' + # End head
         'B' + # End sector
         'B' + # End cylinder
         'I' + # Sectors preceeding partition
         'I' + # Sectors in partition
         # partition 2
         'B' + # Active flag 0x80 is active (bootable)
         'B' + # Start head
         'B' + # Start sector only bits 0-5 bits 6-7 for cylinder
         'B' + # Start cylinder (upper 2 bits in previous byte)
         'B' + # partition type code
         'B' + # End head
         'B' + # End sector
         'B' + # End cylinder
         'I' + # Sectors preceeding partition
         'I' + # Sectors in partition
         # partition 3
         'B' + # Active flag 0x80 is active (bootable)
         'B' + # Start head
         'B' + # Start sector only bits 0-5 bits 6-7 for cylinder
         'B' + # Start cylinder (upper 2 bits in previous byte)
         'B' + # partition type code
         'B' + # End head
         'B' + # End sector
         'B' + # End cylinder
         'I' + # Sectors preceeding partition
         'I' + # Sectors in partition
         # partition 4
         'B' + # Active flag 0x80 is active (bootable)
         'B' + # Start head
         'B' + # Start sector only bits 0-5 bits 6-7 for cylinder
         'B' + # Start cylinder (upper 2 bits in previous byte)
         'B' + # partition type code
         'B' + # End head
         'B' + # End sector
         'B' + # End cylinder
         'I' + # Sectors preceeding partition
         'I' + # Sectors in partition
         '2s') # Signature should be 0x55 0xAA
      self._mbrTuple=struct.unpack(fmt, sector)

   def isActive(self, partno):
      return self._mbrTuple[1+10*(partno-1)]==0x80

   def startHead(self, partno):
      return self._mbrTuple[2+10*(partno-1)]

   def startSector(self, partno):
      # return lower 6 bits of sector
      return self._mbrTuple[3+10*(partno-1)] % 64 

   def startCylinder(self, partno):
      # add in the upper 2 bits if needed
      return (self._mbrTuple[4+10*(partno-1)] +
         256 * self._mbrTuple[3+10*(partno-1)]//64)

   def partitionType(self, partno):
      return self._mbrTuple[5+10*(partno-1)]

   def isEmpty(self, partno):
      return self.partitionType(partno)==0

   def endHead(self, partno):
      return self._mbrTuple[6+10*(partno-1)]

   def endSector(self, partno):
      # return lower 6 bits of sector
      return self._mbrTuple[7+10*(partno-1)] % 64 

   def endCylinder(self, partno):
      # add in the upper 2 bits if needed
      return (self._mbrTuple[8+10*(partno-1)] +
         256 * self._mbrTuple[7+10*(partno-1)]//64)

   def reservedSectors(self, partno):
      '''Sectors preceeding this partition'''
      return self._mbrTuple[9+10*(partno-1)]

   def totalSectors(self, partno):
      return self._mbrTuple[10+10*(partno-1)]

   def validSignature(self):
      return self._mbrTuple[41]==b'\x55\xAA'

   def prettyPrint(self):
      print('MBR signature valid:', self.validSignature())
      for i in range(1, 5):
         print('Partition', i, 'information:')
         if self.isEmpty(i):
            print('\tEntry is empty.')
         else:
            print('\tBootable:', self.isActive(i))
            print('\tStart head:', self.startHead(i))
            print('\tStart sector:', self.startSector(i))
            print('\tStart cylinder:', self.startCylinder(i))
            print('\tPartition type:', self.partitionType(i))
            print('\tEnd head:', self.endHead(i))
            print('\tEnd sector:', self.endSector(i))
            print('\tEnd cylinder:', self.endCylinder(i))
            print('\tReserved sectors:', self.reservedSectors(i))
            print('\tTotal sectors:', self.totalSectors(i))


def usage():
   print("usage " + sys.argv[0] + " <image file>\nAttempts to mount partitions from an image file")
   exit(1)

def main():
   if len(sys.argv) < 2: 
     usage()

   notsupParts = [0x05, 0x0f, 0x85, 0x91, 0x9b, 0xc5, 0xe4, 0xee]
   swapParts = [0x42, 0x82, 0xb8, 0xc3, 0xfc]

   # read first sector
   if not os.path.isfile(sys.argv[1]):
      print("File " + sys.argv[1] + " cannot be opened for reading")
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
                 mountpath = '/media/part%s' % str(i)
                 if not os.path.isdir(mountpath):
                    subprocess.call(['mkdir', mountpath])
                 mountopts = ('loop,ro,noatime,offset=%s,sizelimit=%s'
                  ) % (str(mbr.reservedSectors(i) * 512),str(mbr.totalSectors(i) * 512))
                 subprocess.call(['mount', '-o', mountopts,
                   sys.argv[1], mountpath])
   else:
      print("Doesn't appear to contain valid MBR")
 
if __name__ == "__main__":
   main()
