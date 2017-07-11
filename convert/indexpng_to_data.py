#!/usr/bin/python
# coding=utf8
import Image
import sys

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

# We use clever encoding. Bit 7 indicates repeating.
# Bits 0-6 encode count, but for non-repeating the count N is stored as N-1.
# For repeating we have at least 3 repeats so N repeats are stored as (N-3)+128.
# And we use 255 as end marker.
def RLEncode(bytes):
	encoded = []
	count = 0
	elem = -1
	for i in range(0, len(bytes)):
		if bytes[i] == elem:
			count += 1
			if count == 129:	# 126+3, because 255 is special marker.
				# max reached
				encoded += [(count, elem)]
				count = 0
				elem = -1
		else:
			if count > 0:
				encoded += [(count, elem)]
			elem = bytes[i]
			count = 1
	if count > 0:
		encoded += [(count, elem)]
	#print encoded
	result = []
	temp = []
	for e in encoded:
		if e[0] >= 3:
			if len(temp) > 0:
				result += [len(temp)-1]
				result += temp
				temp = []
			result += [e[0] + 128 - 3, e[1]]
		else:
			temp += [e[1]] * e[0]
			if len(temp) > 128:
				result += [127]
				result += temp[:127]
				temp = temp[127:]
	if len(temp) > 0:
		result += [len(temp)-1]
		result += temp
	result += [255]

	#print result
	print('RLE encoded',len(bytes),'bytes to',len(result),'bytes (',len(result)*100/len(bytes),'%).')
	return result

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
