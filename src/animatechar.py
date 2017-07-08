#!/usr/bin/python
# coding=utf8
import Image
import random
import sys
import math

###########################################################################################
#
#                  Hauptprogramm
#
###########################################################################################

# Tile is 2*2 chars in multicolor 8*16 pixels, two columns are connected,
# so we have 4 columns and 16 rows.
# But made of two chars shown repeated in two lines.
# So scroll down 8 lines until animation repeats.
# Can we compute this ingame?
# It is like having 8 bytes with data for left nibble and 8 bytes with data for right nibble.
# Or using 4 columns that make 4*8 bytes and we have to mix them with shift and or.
# should be much easier...
# but would be easier to have for every char N frames and just take animcounter mod N
# and read and write it. How do we generate it?
# we do it here for rain.
# 32 frames for 8 rows means 1/4 speed minimum.
# There are 2*4 = 8 columns.

columnspeeds = [8, 8, 4, 4, 2, 2, 4, 4, 8, 8, 2, 2, 4, 4, 2, 2]	# 8 = 1 pixel per phase
width = len(columnspeeds)
phases = 32
columnoffsets = [0] * width

# Bild laden
if len(sys.argv) < 2:
	print 'Usage: ', sys.argv[0], ' [Options] INPUTFILENAME'
	sys.exit(1)
inputfilename = sys.argv[len(sys.argv) - 1]

im = Image.open(inputfilename)
img_w = im.size[0]
img_h = im.size[1]
if img_w != width or img_h != 8:
	print 'wrong image size'
	sys.exit(0)

px = im.getdata()
pxnew = [0] * (width*8*phases)
for i in range(0, phases):
	for x in range(0, len(columnspeeds)):
		# shift columns
		for y in range(0, 8):
			yr = (y + phases * 8 - columnoffsets[x] / 8) % 8
			pxnew[(y+i*8)*width+x] = px[yr*width+x]
		columnoffsets[x] += columnspeeds[x]

im = im.resize((width, 8*phases), Image.NEAREST)
im.putdata(pxnew)

#write image
im.save(inputfilename + '_phases.png')

