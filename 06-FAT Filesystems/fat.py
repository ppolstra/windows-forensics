#!/usr/bin/python3
# This is a simple Python script that will
# attempt to read FAT entries from an image file.
# Developed for PentesterAcademy by Dr. Phil Polstra

import struct
import sys
import os.path
from mbr import Mbr
from vbr import Vbr

__all__=['Fat']

class Fat:
   def __init__(self, buffer):
      # determine FAT type
      if buffer[1:8]==b'\xFF\xFF\x0F\xFF\xFF\xFF\xFF':
         self._fatBits=32
      elif buffer[1:4]==b'\xFF\xFF\x7F':
         self._fatBits=16
      else:
         self._fatBits=12
      self._fat=buffer
      
   def fatBits(self):
      return self._fatBits
      
   def fatEntry(self, cluster):
      if cluster==None:
         return None
      if self._fatBits==32:
         return struct.unpack('<I',self._fat[cluster*4:cluster*4+4])[0]
      elif self._fatBits==16:
         return struct.unpack('<H',self._fat[cluster*2:cluster*2+2])[0]
      else:
         offset=(cluster//2)*3
         if cluster%2==0: # left entry
            return (struct.unpack('<B',self._fat[offset:offset+1])[0]+
               256*struct.unpack('<B', self._fat[offset+1:offset+2])[0]%16)
         else: # right entry
            return (struct.unpack('<B', self._fat[offset+2:offset+3])[0]*16+
               struct.unpack('<B', self._fat[offset+1:offset+2])[0]//16)
               
   def isAllocated(self, cluster):
      if cluster:
         return self.fatEntry(cluster)!=0
      else:
         return False
      
   def nextCluster(self, cluster):
      if cluster==None:
         return None
      retVal=self.fatEntry(cluster)
      # is this the end of the chain?
      if (retVal==0 or
         (self._fatBits==32 and retVal==0x0FFFFFFF) or
         (self._fatBits==16 and retVal==0xFFFF) or
         (self._fatBits==12 and retVal==0xFFF)):
         return None
      else:
         return retVal
         
   def isEnd(self, cluster):
      return self.nextCluster(cluster)==None     
      
   def clusterChain(self, cluster):
      '''Given a starting cluster, this function
      returns a list of clusters that make up a 
      cluster chain.'''
      chain=[]
      nextC=cluster
      while self.isAllocated(nextC): 
         chain.append(nextC)
         nextC=self.nextCluster(nextC)  
      return chain  
         
def usage():
   print("usage " + sys.argv[0] + " <image file>\n"+
      "Reads FAT Entries from an image file")
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
                    if vbr.validSignature():
                       print('Found Volume with type', vbr.filesystemType())
                       print('Volume label:', vbr.volumeLabel())
                       print('Total sectors:', vbr.totalSectors())
                       s=vbr.sectorFromCluster(14)
                       print('Cluster 14:', s)
                       print('Sector:', vbr.clusterFromSector(s))
                       # grab the FAT
                       f.seek(mbr.reservedSectors(i)*512+
                           vbr.sectorFat1()*512)
                       fatRaw=f.read(512*vbr.sectorsPerFat())
                       fat=Fat(fatRaw)
                       print('Cluster 3 allocated:',fat.isAllocated(3))
                       print('Chain starting at 3:',fat.clusterChain(3))
   else:
      print("Doesn't appear to contain valid MBR")
 
if __name__ == "__main__":
   main()        
                 
   
   
      
      

