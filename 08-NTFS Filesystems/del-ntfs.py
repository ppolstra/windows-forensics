#!/usr/bin/python2

"""
Simple script to parse a raw image
file or a file containining the MFT
and print out MFT entries that
might have deleted files in them.
by Dr. Phil Polstra (@ppolstra)
"""

import sys, os.path, struct

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

def usage():
  print("usage " + sys.argv[0] + "<image file> [offset in sectors]")
  exit(1)

def checkForDeleted(buff):
  if buff[0:4] == 'FILE':
    for i in range (0, 4):
      offset = i * 1024
      if buff[offset:offset+4] == 'FILE':
        # are the flags zero or two
        try:
          flags = getU16(buff, offset+22)
        except:
          pass
        if flags == 0 or flags == 2:
          mft = getU32(buff, offset+44)
          if mft != 0: 
            # is it totally blank?
            if getU32(buff, offset+152) == 48:
              nameLen = getU8(buff, offset+240)
              if nameLen > 0:
                filename = buff[offset+242: offset+242 + nameLen * 2]
                if flags == 0:
                  print("Found potential deleted file %s at MFT %s" % (filename, mft))
                else:
                  print("Found potential deleted directory %s at MFT %s" % (filename, mft))

def main():
  if len(sys.argv) < 2:
    usage()

  # read file
  if not os.path.isfile(sys.argv[1]):
    print("File " + sys.argv[1] + " connot be openned for reading")
    exit(1)
 
  if len(sys.argv) > 2:
    offset = int(sys.argv[2]) * 512 # offset was given
  else:
    offset = 0
  # read 512 byte chunks till MFT entry is found
  # then read 4096 byte chunks = 4 MFT entries at a time
  foundMFT = False
  with open(str(sys.argv[1]), 'rb') as f:
    f.seek(offset)
    while not foundMFT: 
      buff = str(f.read(512))
      if buff[0:4] == 'FILE':
        foundMFT = True
        break
      offset+=512
  # now that we are properly aligned get a cluster at a time
  # if searching through a raw image we may encounter MFT
  # fragments before the start of the MFT
  with open(str(sys.argv[1]), 'rb') as f:
    f.seek(offset)
    while buff:
      buff = str(f.read(4096))
      if buff[0:4] == 'FILE':
        checkForDeleted(buff)
      offset += 4096

if __name__ == '__main__':
  main()



