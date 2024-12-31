#!/usr/bin/python3
# This is a simple Python script that will
# attempt to mount partitions inside an extended
# partition from an image file.
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
   print("usage " + sys.argv[0] + \
       " <image file>\nAttempts to mount extended partitions from an image file")
   exit(1)

def main():
   if len(sys.argv) < 2: 
      usage()

   extParts = [0x05, 0x0f, 0x85, 0x91, 0x9b, 0xc5, 0xe4]
   swapParts = [0x42, 0x82, 0xb8, 0xc3, 0xfc]

   # read first sector
   if not os.path.isfile(sys.argv[1]):
      print("File " + sys.argv[1] + " cannot be openned for reading")
      exit(1)

   with open(sys.argv[1], 'rb') as f:
      sector = f.read(512)

   mbr=Mbr(sector) # create MBR object

   for i in range(1,5):
      if not mbr.isEmpty(i):
         if mbr.partitionType(i) in extParts:
            print("Found an extended partion at sector %s" % str(mbr.reservedSectors(i)))
            bottomOfRabbitHole = False
            extendPartStart = mbr.reservedSectors(i)
            extPartNo = 5
            while not bottomOfRabbitHole:
               # get the linked list MBR entry
               f=open(sys.argv[1], 'rb')
               f.seek(extendPartStart * 512) 
               llSector = f.read(512)
               f.close()
               if len(llSector)==512:
                  extMbr=Mbr(llSector)
                  # try and mount the first partition
                  if extMbr.partitionType(1) in swapParts:
                     print("Skipping swap partition")
                  else:
                     mountpath = '/media/part%s' % str(extPartNo)
                     if not os.path.isdir(mountpath):
                        subprocess.call(['mkdir', mountpath])
                     mountopts = 'loop,ro,noatime,offset=%s' \
                        % str((extMbr.reservedSectors(1) + extendPartStart) * 512)
                     print("Attempting to mount extend part type %s at sector %s" \
                        % (hex(extMbr.partitionType(1)), \
                        str(extendPartStart + extMbr.reservedSectors(1)))) 
                     subprocess.call(['mount', '-o', mountopts, sys.argv[1], mountpath])
                  if extMbr.isEmpty(2):
                     bottomOfRabbitHole = True
                     print("Found the bottom of the rabbit hole")
                  else:
                     extendPartStart += extMbr.reservedSectors(2)
                     extPartNo += 1
 
if __name__ == "__main__":
   main()
