#!/usr/bin/python3
# coding=utf8
import sys
from rlencode import RLEncode

###########################################################################################
#
#                  main program
#
###########################################################################################

# load data
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

# read input file
f = open(inputfilename, 'rt')
ifl = f.readlines()
f.close()

# generate byte array
bytes = []
for i in ifl:
	nbrs = i[:-1].split('$')[1:]
	for x in nbrs:
		bytes += [int(x[0:2], 16)]

enc = RLEncode(bytes)

dfl = dumpbytes(enc)
f = open(outputbasefilename + '_rle.a','wt')
f.writelines(dfl)
f.close()
