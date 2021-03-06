#!/usr/bin/python
# coding=utf8
import Image
import sys
from rlencode import RLEncode

###########################################################################################
#
#                  main program
#
###########################################################################################

# load level image
if len(sys.argv) < 2:
	print('Usage: ', sys.argv[0], ' [Options] INPUTFILENAME')
	sys.exit(1)
inputfilename = sys.argv[len(sys.argv) - 1]
inputbasefilename = inputfilename[0:inputfilename.rfind('.')]
outputbasefilename = inputbasefilename

def hexstr(v):
	return '$' + ('00' + hex(v)[2:])[-2:]

def dumpbytes(v):
	n = 0
	z = ''
	while n < len(v):
		m = min(n + 16, len(v))
		z += '!byte '
		for i in range(n, m):
			z += hexstr(v[i]) + ', '
		z = z[:-2] + '\n'
		n += 16
	return z

im = Image.open(inputfilename)
img_w = im.size[0]
img_h = im.size[1]
px = im.getdata()
bytes = []
for y in range(0, img_h):
	for x in range(0, img_w):
		bytes += [ px[y * img_w + x] ]
enc = RLEncode(bytes)

dfl = dumpbytes(bytes)
f = open(outputbasefilename + '_raw.a','wt')
f.writelines(dfl)
f.close()

dfl = dumpbytes(enc)
f = open(outputbasefilename + '_rle.a','wt')
f.writelines(dfl)
f.close()
