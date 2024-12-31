#!/usr/bin/python

"""
Simple NTFS INDX parser program.
by Dr. Phil Polstra
"""

import sys, os.path, subprocess, struct, time
from math import log

def getU32(data, offset=0):
  return struct.unpack('<L', data[offset:offset+4])[0]

def getU16(data, offset=0):
  return struct.unpack('<H', data[offset:offset+2])[0]

def getU8(data, offset=0):
  return struct.unpack('B', data[offset:offset+1])[0]

def getU64(data, offset=0):
  return struct.unpack('<Q', data[offset:offset+8])[0]

def getU48(data, offset=0):
  return struct.unpack('<Q', data[offset:offset+6]+"\x00\x00")[0]

# converts Windows FILETIMES (100 nanoseconds since 1/1/1601 to a proper time)
def convertFiletime(stupid):
  # convert to seconds
  t = long(stupid) * 100 / 1000000000
  # subtract seconds from 1/1/1601 to epoch
  t -= 11644473600
  if t > 0:
    return time.gmtime(t)
  else:
    return time.gmtime(0)

class IndxHeader:
  def __init__(self, data):
    if data[0:4] == 'INDX':
      self.valid = True
      self.updateSeqOffset = getU16(data, 4)
      self.updateSeqSize = getU16(data, 6)
      self.logfileSeqNo = getU64(data, 8)
      self.vcn = getU64(data, 16)
      self.entriesStart = getU32(data, 24)
      self.entriesEnd = getU32(data, 28)
      self.buffSize = getU32(data, 32)
      self.hasChildren = (getU32(data, 36)==1)
      self.updateSeqNo = getU16(data, 40)
      self.updateSeq = []
      for i in range(0, self.updateSeqSize):
        self.updateSeq.append(getU16(data, self.updateSeqOffset + i * 2))
    else:
      self.valid = False

  def prettyPrint(self):
    for k, v in sorted(self.__dict__.iteritems()):
      print k+":", v

  # This function substitutes correct codes for update seq in each sector
  def fixupIndx(self, data):
    temp = data
    for i in range(0, self.updateSeqSize):
      replaceIndex = 512 * i + 510
      temp = temp[0: replaceIndex] + struct.pack('<H', self.updateSeq[i]) + temp[replaceIndex + 2: ]
    return temp  
                                                       
    

class IndxRecord:
  def __init__(self, data, offset=0):
    self.mft = getU48(data, offset)
    self.mftSeq = getU16(data, offset + 6)
    self.recSize = getU16(data, offset+8)
    self.filenameOffset = getU16(data, offset + 10)
    self.flags = getU16(data, offset + 12)
    self.parentMft = getU48(data, offset + 16)
    self.parentSeq = getU16(data, offset + 22)
    self.createdTS = getU64(data, offset + 24)
    self.createdTime = convertFiletime(self.createdTS)
    self.modifiedTS = getU64(data, offset + 32)
    self.modifiedTime = convertFiletime(self.modifiedTS)
    self.entryTS = getU64(data, offset + 40)
    self.entryTime = convertFiletime(self.entryTS)
    self.accessedTS = getU64(data, offset + 48)
    self.accessedTime = convertFiletime(self.accessedTS)
    self.physicalSize = getU64(data, offset + 56)
    self.logicalSize = getU64(data, offset + 64)
    self.attributes = getU64(data, offset + 72)
    self.nameLen = getU8(data, offset + 80)
    self.namespace = getU8(data, offset +81)
    if self.nameLen > 0:
      try:
        self.filename = unicode(data[offset+82:offset+82+2*self.nameLen]).decode('utf-16')
      except (UnicodeEncodeError, UnicodeDecodeError):
        self.filename = "<Unkown>"
    else:
      self.filename = ""
    # does this have children?  if so, get the child VCN
    if self.flags == 1:
      self.childVcn = getU64(data, offset + self.recSize - 8)
      self.hasChildren = True
    else:
      self.childVcn = 0
      self.hasChildren = False
      
  def printHeader(self):
    temp =""
    for k, v in sorted(self.__dict__.iteritems()):
      temp += k+","
    print (temp)

  def printCsv(self):    
    temp = ""
    for k, v in sorted(self.__dict__.iteritems()):
      if k == 'modifiedTime' or k == 'createdTime' or k == 'entryTime' or k == 'accessedTime':
        temp += time.asctime(v) + ","
      else:
        try:
          temp += str(v) + ","
        except (UnicodeEncodeError, UnicodeDecodeError):
          temp += "<Unicode Error>,"
    print (temp)

  def prettyPrint(self):
    for k, v in sorted(self.__dict__.iteritems()):
      if k == 'modifiedTime' or k == 'createdTime' or k == 'entryTime' or k == 'accessedTime':
        print k+":", time.asctime(v)
      else:
        try:
          print k+":", v
        except (UnicodeEncodeError, UnicodeDecodeError):
          print k+":", "<Unicode error>"

def usage():
  print("usage " + sys.argv[0] + "$I30 file")
  exit(1)

def main():
  if len(sys.argv) < 2:
    usage()

  buffs = []
  recs = []

  # read file
  if not os.path.isfile(sys.argv[1]):
    print("File " + sys.argv[1] + " connot be openned for reading")
    exit(1)

  indexSize = os.path.getsize(sys.argv[1])
  indexClusters = indexSize / 4096
 
  for vcn in range (0, indexClusters):
    with open(str(sys.argv[1]), 'rb') as f:
      f.seek(4096 * vcn)
      buff = str(f.read(4096))

    currHeader = IndxHeader(buff)
    if currHeader.valid:
      currIndx = currHeader.fixupIndx(buff)
      recOffset = currHeader.entriesStart + 24
      while recOffset < (currHeader.entriesEnd + 24):
        currRec = IndxRecord(currIndx, recOffset)
        recs.append(currRec)    
        recOffset += currRec.recSize


  recs[0].printHeader()
  for r in recs:
    r.printCsv()

if __name__ == '__main__':
  main()



