#!/usr/bin/python3
#
# mount-image-gpt.py
#
# This is a simple Python script that will
# attempt to mount partitions from an image file.
# This script is for GUID partions only.
# Images are mounted read-only.  
#
# Developed for PentesterAcademy by Dr. Phil Polstra

import sys
import os.path
import subprocess
import struct

supportedParts = ["EBD0A0A2-B9E5-4433-87C0-68B6B72699C7",
"37AFFC90-EF7D-4E96-91C3-2D7AE055B174", 
"0FC63DAF-8483-4772-8E79-3D69D8477DE4", 
"8DA63339-0007-60C0-C436-083AC8230908", 
"933AC7E1-2EB4-4F13-B844-0E14E2AEF915", 
"44479540-F297-41B2-9AF7-D131D5F0458A", 
"4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709",  
"B921B045-1DF0-41C3-AF44-4C6F280D3FAE", 
"3B8F8425-20E0-4F3B-907F-1A25A76F98E8", 
"E6D6D379-F507-44C2-A23C-238F2A3DF928", 
"516E7CB4-6ECF-11D6-8FF8-00022D09712B",  
"83BD6B9D-7F41-11DC-BE0B-001560B84F0F", 
"516E7CB5-6ECF-11D6-8FF8-00022D09712B", 
"85D5E45A-237C-11E1-B4B3-E89A8F7FC3A7", 
"516E7CB4-6ECF-11D6-8FF8-00022D09712B", 
"824CC7A0-36A8-11E3-890A-952519AD3F61", 
"55465300-0000-11AA-AA11-00306543ECAC", 
"516E7CB4-6ECF-11D6-8FF8-00022D09712B", 
"49F48D5A-B10E-11DC-B99B-0019D1879648", 
"49F48D82-B10E-11DC-B99B-0019D1879648", 
"2DB519C4-B10F-11DC-B99B-0019D1879648", 
"2DB519EC-B10F-11DC-B99B-0019D1879648", 
"49F48DAA-B10E-11DC-B99B-0019D1879648", 
"426F6F74-0000-11AA-AA11-00306543ECAC", 
"48465300-0000-11AA-AA11-00306543ECAC", 
"52414944-0000-11AA-AA11-00306543ECAC", 
"52414944-5F4F-11AA-AA11-00306543ECAC", 
"4C616265-6C00-11AA-AA11-00306543ECAC", 
"6A82CB45-1DD2-11B2-99A6-080020736631", 
"6A85CF4D-1DD2-11B2-99A6-080020736631", 
"6A898CC3-1DD2-11B2-99A6-080020736631", 
"6A8B642B-1DD2-11B2-99A6-080020736631", 
"6A8EF2E9-1DD2-11B2-99A6-080020736631", 
"6A90BA39-1DD2-11B2-99A6-080020736631", 
"6A9283A5-1DD2-11B2-99A6-080020736631", 
"75894C1E-3AEB-11D3-B7C1-7B03A0000000", 
"E2A1E728-32E3-11D6-A682-7B03A0000000", 
"BC13C2FF-59E6-4262-A352-B275FD6F7172", 
"42465331-3BA3-10F1-802A-4861696B7521", 
"AA31E02A-400F-11DB-9590-000C2911D1B8", 
"9198EFFC-31C0-11DB-8F78-000C2911D1B8", 
"9D275380-40AD-11DB-BF97-000C2911D1B8", 
"A19D880F-05FC-4D3B-A006-743F0F84911E"]

def printGuid(packedString):
   if len(packedString) == 16:
      outstr = format(struct.unpack('<L', packedString[0:4])[0], 'X').zfill(8) + "-" + \
         format(struct.unpack('<H', packedString[4:6])[0], 'X').zfill(4) + "-" + \
         format(struct.unpack('<H', packedString[6:8])[0], 'X').zfill(4) + "-" + \
         format(struct.unpack('>H', packedString[8:10])[0], 'X').zfill(4) + "-" + \
         format(struct.unpack('>Q', b"\x00\x00" + packedString[10:16])[0], 'X').zfill(12)
   else:
       outstr = "<invalid>" 
   return outstr

class GptRecord():
   def __init__(self, recs, partno):
      self.partno = partno
      offset = partno * 128
      self.empty = False
      # build partition type GUID string
      self.partType = printGuid(recs[offset:offset+16])
      if self.partType == "00000000-0000-0000-0000-000000000000":
         self.empty = True
      self.partGUID = printGuid(recs[offset+16:offset+32]) 
      self.firstLBA = struct.unpack('<Q', recs[offset+32:offset+40])[0]
      self.lastLBA = struct.unpack('<Q', recs[offset+40:offset+48])[0]
      self.attr = struct.unpack('<Q', recs[offset+48:offset+56])[0]
      nameIndex = recs[offset+56:offset+128].find(b'\x00\x00')
      if nameIndex != -1:
         self.partName = recs[offset+56:offset+56+nameIndex].decode("utf-8", "replace")
      else:
         self.partName = recs[offset+56:offset+128].decode("utf-8", "replace")

   def printPart(self):
      if not self.empty:
         outstr = str(self.partno) + ":" + str(self.partType) + ":" + str(self.partGUID) + \
            ":" + str(self.firstLBA) + ":" + str(self.lastLBA) + ":" + \
            str(self.attr) + ":" + self.partName
         print(outstr)


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

  # read first sector
  if not os.path.isfile(sys.argv[1]):
     print("File " + sys.argv[1] + " cannot be openned for reading")
     exit(1)
  with open(sys.argv[1], 'rb') as f:
    sector = f.read(512)
  mbr=Mbr(sector)  
  if mbr.validSignature():
     if mbr.partitionType(1) != 0xee:
        print("Failed protective MBR sanity check")
        exit(1)
	# check the header as another sanity check
     with open(sys.argv[1], 'rb') as f:
        f.seek(512)
        sector = f.read(512)
     if sector[0:8] != b"EFI PART":
        print("You appear to be missing a GUI header")
        exit(1)
     print("Valid protective MBR and GUI partion table header found")
     with open(sys.argv[1], 'rb') as f:
        f.seek(1024)
        partRecs = f.read(512 * 32)
     parts = [ ]
     for i in range(0, 128):
         p = GptRecord(partRecs, i)
         if not p.empty:
            p.printPart()
            parts.append(p)
     for p in parts:
        if p.partType in supportedParts:
           print("Partition %s seems to be supported attempting to mount" % str(p.partno))
           mountpath = '/media/part%s' % str(p.partno)
           if not os.path.isdir(mountpath):
              subprocess.call(['mkdir', mountpath])
                 mountopts = 'loop,ro,noatime,offset=%s,sizelimit=%s' % (
                 str(p.firstLBA * 512), str((p.lastLBA-p.firstLBA)*512))
           subprocess.call(['mount', '-o', mountopts, sys.argv[1], mountpath])
                  

if __name__ == "__main__":
   main()
