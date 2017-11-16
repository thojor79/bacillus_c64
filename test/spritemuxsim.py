#!/usr/bin/python3
# coding=utf8

# Simulate sprite multiplexer
# Copyright (C) 2017  Thorsten Jordan.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# Note: for char mode it is often not good enough to take the three most used colors as
# fix colors, as we can use only the darker colors 0-7 as individual colors per block.
# A rather often used bright color should be used as fix color rather even if it is not
# used as one of the top three colors - but we can't determine that automatically...
# rather let the user enter a fix color.
# Example image of landscape with a tree, if we define three bright colors that appear
# in the image the result is dramatically better.

import PIL.Image
import sys

if len(sys.argv) < 2:
	print('Usage: ', sys.argv[0], ' [Options] INPUTFILENAME.vsf')
	print('INPUTFILENAME.vsf is a VICE snapshot file.')
	print('Options:')
	sys.exit(1)
inputfilename = sys.argv[len(sys.argv) - 1]

# Screen mask has upper left corner at 136,51. There sprite coordinates 24,50 are.
# Size is 504,312.
offset_x = 136-24
offset_y = 51-50
# Note! These colors are that dark, that is correct!
colors_c64 = [(0, 0, 0), (255, 255, 255), (104, 55, 43), (112, 164, 178), (111, 61, 134), (88, 141, 67), (53, 40, 121), (184, 199, 111), (111, 79, 37), (67, 57, 0), (154, 103, 89), (68, 68, 68), (108, 108, 108), (154, 210, 132), (108, 94, 181), (150, 150, 150)]

# show image
def Show(im):
	im2 = im.resize((im.size[0] * 2, im.size[1] * 2), PIL.Image.NEAREST)
	im2.show()

def RenderSprite(im, x, y, c):	# fixme data later maybe
	px = list(im.getdata())
	for yy in range(0, 21):
		for xx in range(0, 24):
			px[(y+yy+offset_y)*504+(x+xx+offset_x)] = colors_c64[c]
	im.putdata(px)
	return im

def AddRasterlineMarker(im, rl):
	px = list(im.getdata())
	for xx in range(0, 320+2*24):
		c = px[rl*504+(xx+offset_x)]
		c = (255-c[0], 255-c[1], 255-c[2])
		px[rl*504+(xx+offset_x)] = c
	im.putdata(px)
	return im

im = PIL.Image.open('screenmask.png')

f = open(inputfilename, 'rb')
d = f.read()
f.close()

# find start address of memory dump
marker_string = 'C64MEM\x00'
memory_start = 0
for i in range(0, len(d)):
	match = True
	for j in range(0, len(marker_string)):
		if d[i+j] != ord(marker_string[j]):
			match = False
			break
	if match:
		memory_start = i+26
if memory_start == 0:
	print('No memory dump found!')
	sys.exit(0)
print('Memory dump starts in .vsf file at offset', memory_start)
# Start address of sprite data is at offset 2069 (LSB/MSB)
address = d[memory_start+2069]+d[memory_start+2070]*256
print('Sprite data start at',address)

# Count number of sprites (count up to end marker)
nr_vsprites = 0
while d[memory_start+address+nr_vsprites] != 255:
	nr_vsprites += 1
print('Number of virtual sprites:',nr_vsprites)
databegin = memory_start+address

# Read data to arrays
# Y coords (+1 stop marker)
# xl/xh
# ptr/c - we could read data and color and show them correct (later)
ycoords = []
xcoords = []
pointers = []
colors = []
for i in range(0, nr_vsprites):
	ycoords += [d[databegin + i]]
	xcoords += [d[databegin + nr_vsprites + 1 + i] + 256 * d[databegin + nr_vsprites*2 + 1 + i]]
	pointers += [d[databegin + nr_vsprites*3 + 1 + i]]
	colors += [d[databegin + nr_vsprites*4 + 1 + i]]
#print(ycoords)
#print(xcoords)

# Now simulate the muxer: sort by y coordinates
indices = [i for i in range(0, nr_vsprites)]
#print(indices)
# Sort per insertion sort as in game
for i in range(1, nr_vsprites):
	v = indices[i]
	j = i
	while j > 0 and ycoords[indices[j-1]] > ycoords[v]:
		indices[j] = indices[j-1]
		j -= 1
	indices[j] = v
#print(indices)
ysorted = []
xsorted = []
psorted = []
csorted = []
for i in indices:
	ysorted += [ycoords[i]]
	xsorted += [xcoords[i]]
	psorted += [pointers[i]]
	csorted += [colors[i]]
print('Sorted Y coordinates:')
print(ysorted)
#print(xsorted)
#print(psorted)
#print(csorted)

# get the sorted y coordinates from dump
sort_order_c64 = []
ysorted_c64 = []
for i in range(0, nr_vsprites):
	sort_order_c64 += [d[memory_start+63+i]]
	ysorted_c64 += [d[memory_start+64+i+nr_vsprites]]
print('Sorted Y coordinates by C64 (with y > MINY!):')
print(ysorted_c64)
print('Sort index by C64:')
print(sort_order_c64)
rasterlines_c64 = []
xhigh_c64 = []
for i in range(0, nr_vsprites-8):
	offset = memory_start+64+nr_vsprites*3+i
	if d[offset] == 0:
		break
	rasterlines_c64 += [d[offset]]
	xhigh_c64 += [d[offset - nr_vsprites]]
print('Rasterlines for IRQs by C64:')
print(rasterlines_c64)
print('XHigh values by C64:')
print(xhigh_c64)

# Ok now simulate display: reject sprites that are too low
miny = 30
maxy = 250
sort_index = 0
while ysorted[sort_index] < miny:
	sort_index += 1
# The first 8 sprites can be displayed as normal.
# Now go round and round and assign to slots, check for 9th sprite on a line
# and place them in the image
# This just renders all sprites without checks!
while sort_index < nr_vsprites and ysorted[sort_index] < maxy:
	im = RenderSprite(im, xsorted[sort_index], ysorted[sort_index], csorted[sort_index])
	sort_index += 1
for i in rasterlines_c64:
	im = AddRasterlineMarker(im, i)

# Show result how it should look like
Show(im)

