#!/usr/bin/python3
# coding=utf8

# PC to C64 image data converter
# Copyright (C) 2012-2017  Thorsten Jordan.
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
import random
from rlencode import RLEncode
import c64fylib
import heapq

color_scale_factor = 1.0 / 255.0	# Color scaling 0-255 to 0.0...1.0
maxchars = 256
dynamic_uv_grey_limit = False	# Adjust it automatically?
uv_dist_limit = 0.2				# max UV distance to 0
enable_dithering = True			# Enable color mixing
adjust_uv = False				# helps for some images
uv_limit_grey = 0.05			# UV distance below this is considered as grey value


# fixme test large sprite generator if it works

# Bilder umwandeln funktioniert, aber:
# Wir brauchen auch eine Teilfunktionalität, die Charsetdaten generiert.
# Also gebe Bild rein, das Vielfache Breite/Höhe von 8 hat (Breite eher 4 wegen Multicolor).
# und gebe an, wieviele Characters generiert werden sollen und ab welcher Nummer.
# Dann werden drei Hauptfarben bestimmt, hier gerne erstmal Bildweites Ausgleichen der
# Helligkeit und Sättigung, das auch als Option.
# Pro 8x8 Teil des Bildes bestimme einen idealen Character. Als vierte Farbe nur 0-7 möglich.
# Idealerweise bestimme auch eine Farbe von 0-7 als Alternative für hohe Auflösung,
# falls das ähnlicher ist zum Block. Also bei beiden Fällen Fehler testen und entsprechend etwas
# generieren. Wenn man statt einer drei Farben pro Block freigibt, kann man denselben Code für
# Multicolor-Bilder verwenden!
# Hat man dann alle Characters generiert und es sind mehr als man nutzen darf, dann zähle, wie
# oft einer benutzt wird, je seltener desto verzichtbarer. Ersetze dann seltene durch häufigere,
# jeweils mit Farbvergleich, also Fehlerfunktion, solange bis es paßt.
#
# Dann eine oder drei Hauptfarben bestimmen.
# Dann pro 8x8 Block umwandeln, bei Char mit HiRes-Option (geht nicht bei Bitmap)
# Bei Char noch Reduktion.
# Dann Daten ausgeben: Char/Color/Bitmap oder Charset/Color/Char
# Versuche später auch Interlace-Mix-Farben zu benutzen, bei halber vertikaler Auflösung.
# Es gibt 7 bzw. 14 Mixfarben, aber nur wenige taugen.

# Original c64 color handling is YUV not HLS, see http://www.pepto.de/projects/colorvic/2001/index.html

# We need a general flag for hires to encode hires bitmaps as well, needed for sprites!
# Handle this with a generic flag for block generation.
# We can do MC blocks, MC blocks with hires single low color (in char mode) and only Hires
# blocks with 0 or 2 fix colors (Bitmap or Sprite).
# Sprite color can be determined automatically from image data or give it from command line.

# Note! blocks with just one color are encoded as multicolor in char mode, rather prefer hires mode?
# otherwise hires backgrounds could have problem, but we can't generalize this...

# Old version was sometimes better, had more details, but darker colors were worse.
# Other colors were used as dark variants.
# New algorithm not always better.
# Old code used YIQ or some mix.
# What is missing here is a mix of 3 or 4 colors to generate 1 color if there are free colors left.
# Maybe one day find out why old version was sometimes better.
# Nearest color for YUV too bad? or rather mix in other color?
# Was contrast higher because no gamma correction was used?
# Increase contrast first? Like e.g. picture of Wehrheim with yellow lawn in foreground -> just one yellow area, no details left!

# Older version didn't really have more detail!
# light green and yellow was used less, but not fully correct. Newer version seems better.
# Mixing any pair of colors is NOT correct! Mixing e.g. white and blue may give in theory a good match but it doesn't look that
# way on screen as both colors don't really mix on screen!

# Note! last ninja picture conversion is not exact because its colors are not correct

# Very much later we could offer FLI modes, but that is out of topic.

def PartToByte(x):
	y = int(x / color_scale_factor + 0.5)
	y = max(0, min(255, y))
	return y

def GetPixelsFromCodeMC(blockcode, colors):
	# decode multicolor block
	# blockcode must be list with 8 byte values!
	# colors is list with four entries.
	pixels = [0] * 64
	idx = 0
	for i in range(0, 8):
		b = blockcode[i]
		for j in range(0, 4):
			c = colors[(b >> (6 - j * 2)) & 3]
			pixels[idx] = c
			pixels[idx+1] = c
			idx += 2
	return pixels

def GetPixelsFromCodeHR(blockcode, colors):
	# decode hires block
	# blockcode must be list with 8 byte values!
	# colors is list with 4 entries, first/last is used.
	pixels = [0] * 64
	idx = 0
	for i in range(0, 8):
		b = blockcode[i]
		for j in range(0, 8):
			pixels[idx] = colors[(b >> (7 - j)) & 1]
			idx += 1
	return pixels
	
def GetPixelsFromCodeBlock(blockcode, colors, hiresmode, charmode):
	if hiresmode:
		colorshr = [colors[0], colors[1]]
		return GetPixelsFromCodeHR(blockcode, colorshr)
	if charmode:
		if colors[3] >= 8:	# Color >= 8 enables Multicolor!
			colorsmc = [colors[0], colors[1], colors[2], colors[3] - 8]
			return GetPixelsFromCodeMC(blockcode, colorsmc)
		else:
			colorshr = [colors[0], colors[3]]
			return GetPixelsFromCodeHR(blockcode, colorshr)
	# bitmap mode
	return GetPixelsFromCodeMC(blockcode, colors)
		
# Show image enlarged
def Show(im):
	im2 = im.resize((im.size[0] * 2, im.size[1] * 2), PIL.Image.NEAREST)
	im2.show()

# Sprites have different encoding, swap bit-values (11 and 10)
# not for hires!
swaptable = [0, 1, 3, 2]
def sprite_recode_byte(b, hiresmode):
	if hiresmode:
		return b
	bresult = 0
	for i in range(0, 4):
		b2 = (b >> (i*2)) & 3
		b2 = swaptable[b2]
		bresult += b2 << (i * 2)
	return bresult

###########################################################################################
#
#				  Main program
#
###########################################################################################

random.seed()

# Read options from command line
hiresmode = False
charmode = False

firstchar = 0
numchars = 0
spritemode = False
spriteneutralindex = 0
givencolors = []
quiet = False
tilex = 2
tiley = 2
usedatalabels = True
appendzeros = True
reducechars = True
if len(sys.argv) < 2:
	print('Usage: ', sys.argv[0], ' [Options] INPUTFILENAME')
	print('INPUTFILENAME is a picture. Without any further arguments it is converted')
	print('to a C64 multicolor bitmap.')
	print('Options:')
	print('-hires N\t\tTurn hires mode on/off (default off)')
	print('-charset N\t\tConvert to a charset with N characters (no scaling of input, must be multiple of 8)')
	print('-firstchar N\t\tUse this as first char number.')
	print('-tilewidth N\t\tUse this width of tile in chars in charmode.')
	print('-tileheight N\t\tUse this as height of tile in chars in charmode.')
	print('-sprite N\t\tConvert to a sprite (input must be 24x21 pixel), neutral color is N.')
	print('-color N\t\tUse color number N as fix color - for sprites best define all!')
	print('-quiet N\t\tEnable/Disable output.')
	print('-mixing N\t\tEnable/Disable pixel mixing.')
	print('-maxuv F\t\tMax value if UV to be used in [0...0.5] range, higher values are clamped.')
	print('-dynamicgreylimit N\tenable or disable dynamic grey limit for UV values.')
	print('-datalabels\t\tUse label names before data, for char/sprite mode (default on).')
	print('-reducechars N\t\tTurn char reducing on/off (default on)')
	print('-appendzeros N\t\tWhen data labels are off fill up by appending zeros (default on)')
	sys.exit(1)
inputfilename = sys.argv[len(sys.argv) - 1]
inputbasefilename = inputfilename[0:inputfilename.rfind('.')]
outputbasefilename = inputbasefilename
if len(sys.argv) > 2:
	ic = 1
	while ic + 1 < len(sys.argv):
		p0 = sys.argv[ic]
		p1 = sys.argv[ic + 1]
		ic += 2
		if p0 == '-hires':
			hiresmode = int(p1) != 0
		elif p0 == '-charset':
			if spritemode:
				print('Illegal parameters.')
				sys.exit(0)
			charmode = True
			numchars = int(p1)
			if numchars < 1 or numchars > maxchars or firstchar + numchars > maxchars:
				print('Illegal parameters.')
				sys.exit(0)
		elif p0 == '-sprite':
			if charmode:
				print('Illegal parameters.')
				sys.exit(0)
			spritemode = True
			spriteneutralindex = int(p1)
			givencolors = [spriteneutralindex] + givencolors
		elif p0 == '-color':
			n = int(p1)
			if n < 0 or n > 15:
				print('Illegal parameters.')
				sys.exit(0)
			givencolors += [n]
		elif p0 == '-quiet':
			quiet = int(p1) != 0
		elif p0 == '-mixing':
			enable_dithering = int(p1) != 0
		elif p0 == '-firstchar':
			firstchar = int(p1)
			if firstchar + numchars > 256:
				print('Illegal parameters.')
				sys.exit(0)
		elif p0 == '-tilewidth':
			tilex = int(p1)
		elif p0 == '-tileheight':
			tiley = int(p1)
		elif p0 == '-maxuv':
			adjust_uv = True
			uv_dist_limit = min(0.5, max(0.0, float(p1)))
		elif p0 == '-dynamicgreylimit':
			dynamic_uv_grey_limit = int(p1) != 0
		elif p0 == '-datalabels':
			usedatalabels = int(p1) != 0
		elif p0 == '-reducechars':
			reducechars = int(p1) != 0
		elif p0 == '-appendzeros':
			appendzeros = int(p1) != 0
		else:
			print('Illegal parameters.')
			sys.exit(0)
print('Inputfile:',inputfilename)
if charmode:
	print('Generating character set of', numchars, 'characters.')
elif spritemode:
	print('Generating sprite, neutral color:', spriteneutralindex)
elif hiresmode:
	print('Generating HiRes Bitmap.')
else:
	print('Generating MultiColor Bitmap.')

im = PIL.Image.open(inputfilename)

##########################################################
#
# Prepare color data
#
##########################################################

colors_c64_rgb = []	# fixme to converter class?!
for c in c64fylib.colors_c64_yuv:
	rgb = c64fylib.YUVToRGB(c)
	rgb = c64fylib.AddGammaCorrection(rgb)
	colors_c64_rgb += [(PartToByte(rgb[0]), PartToByte(rgb[1]), PartToByte(rgb[2]))]
	#print(hex(PartToByte(rgb[0])), hex(PartToByte(rgb[1])), hex(PartToByte(rgb[2])))

# Scale/Crop image
img_w = im.size[0]
img_h = im.size[1]
num_sprites_x = 0
num_sprites_y = 0
if charmode:
	img_w = (img_w // 8) * 8
	img_h = (img_h // 8) * 8
	im = im.crop((0, 0, img_w, img_h))
elif spritemode:
	img_w2 = (img_w // 24) * 24
	img_h2 = (img_h // 21) * 21
	if img_w != img_w2 or img_h != img_h2:
		print('Invalid sprite image inputfile.')
		sys.exit(0)
	# Later extend every 24x21 block to 24x24 blocks.
	num_sprites_x = img_w // 24
	num_sprites_y = img_h // 21
elif hiresmode:
	# scale to 320x200
	im = im.resize((320, 200), PIL.Image.BICUBIC)
	img_w = 320
	img_h = 200
else:
	# scale to 160x200, later up to 320x200 for generic comparison
	im = im.resize((160, 200), PIL.Image.BICUBIC).resize((320, 200), PIL.Image.NEAREST)
	img_w = 320
	img_h = 200
if not quiet:
	Show(im)

# Get pixel data
px = im.getdata()

# If we should adjust UV values, compute coefficients first
uv_scale = 1.0
meanuvdist = 0.0
maxuvdist = 0.0
for p in px:
	rgb = (p[0] * color_scale_factor, p[1] * color_scale_factor, p[2] * color_scale_factor)
	rgb = c64fylib.RemoveGammaCorrection(rgb)
	yuv = c64fylib.RGBToYUV(rgb)
	meanuvdist += abs(yuv[1]) + abs(yuv[2])
	maxuvdist = max(max(maxuvdist, abs(yuv[1])), abs(yuv[2]))
meanuvdist /= len(px) * 2	#  * 2 for count
print('Mean UV distance', meanuvdist, ' Max UV distance', maxuvdist)
# If max UV is larger than 0.2 scale it down
if adjust_uv and maxuvdist > uv_dist_limit:
	uv_scale = uv_dist_limit / maxuvdist
	maxuvdist = uv_dist_limit
if dynamic_uv_grey_limit:
	uv_limit_grey = max(0.02, maxuvdist / 5.0)

# Find best matching color for every pixel and show it
pxnearest = []
closestcolorindices = []
index_use_count = [0] * 16
pxyuv = []
for p in px:
	rgb = (p[0] * color_scale_factor, p[1] * color_scale_factor, p[2] * color_scale_factor)
	rgb = c64fylib.RemoveGammaCorrection(rgb)
	yuv = c64fylib.RGBToYUV(rgb)
	yuv = (yuv[0], yuv[1] * uv_scale, yuv[2] * uv_scale)
	pxyuv += [yuv]
	# Finde passensten Index nach Farbzuordnung
	index = c64fylib.FindBestColorForYUV(yuv, uv_limit_grey)
	pxnearest += [colors_c64_rgb[index]]
	closestcolorindices += [index]
	index_use_count[index] += 1
	
im.putdata(pxnearest)
if not quiet:
	Show(im)

#fixme this is part of the converter!

# fixme do this as function!
# Count which color or which three are used mostly
num_most_used_indices = 1
fixindices = []
if charmode:
	num_most_used_indices = 3
	enable_dithering = False
	dynamicgreylimit = False
elif spritemode:
	num_most_used_indices = 4
	if hiresmode:
		num_most_used_indices = 2
	enable_dithering = False
	dynamicgreylimit = False
	# add three lines of neutral colors to make sprite fit in block with neutral color,
	# for every row of sprites.
	pxyuv_extended = []
	ptr = 0
	for yr in range(0, num_sprites_y):
		for yl in range(0, 21):
			for x in range(0, img_w):
				pxyuv_extended += [pxyuv[ptr]]
				ptr += 1
		pxyuv_extended += [c64fylib.colors_c64_yuv[spriteneutralindex]] * (img_w * 3)
	pxyuv = pxyuv_extended
	img_h = num_sprites_y * 24
	im = im.resize((img_w, img_h), PIL.Image.NEAREST)
	# fixme later we can chose one sprite color for every sprite as free color,
	# may help for large sprites
elif hiresmode:
	# We can chose two colors freely every char, no background color!
	num_most_used_indices = 0
fixindices += givencolors
if num_most_used_indices > len(fixindices):
	for j in range(0, num_most_used_indices - len(fixindices)):
		mui = -1
		for i in range(0, 16):
			if (mui < 0 or index_use_count[i] > index_use_count[mui]) and index_use_count[i] > 0 and i not in fixindices:
				mui = i
		if mui >= 0:
			fixindices += [mui]
print('Fix indices for image:', fixindices)

# Iterate over all 8x8 blocks and compute best fit block with c64 coding rules with
# fix and free colors and mixing if enabled.
stretchedcolors = [(0, 0, 0)] * len(pxyuv)
codeblocks = []		# in charmode blocks to be used for characters, lists of 8 bytecodes each!
bitmapbytes = []	# Bytes für Bitmap
chardata = []		# character data bytes for bitmap (0-255)
colordata = []		# color data bytes for bitmap or charmode (bit 3 as multicolor marker for charmode) (0-15)
backgroundindex = 16
charnumbers = []	# for every imageblock the codeblock index to use in charmode
numreusedchars = 0
if not hiresmode:
	backgroundindex = fixindices[0]
imageblocks = []	# the color data for every imageblock (in charmode)

# fixme generating the color blocks must be in file reader or in gimp plugin, collecting data in file reader... so this is part of the reader
for y in range(0, img_h//8):
	for x in range(0, img_w//8):
		colorblock = []
		for yy in range(0, 8):
			for xx in range(0, 8):
				colorblock += [pxyuv[(y * 8 + yy) * img_w + (x * 8 + xx)]]
		bbd = c64fylib.GenerateBestBlock(colorblock, fixindices, charmode, hiresmode, True, enable_dithering, uv_limit_grey)
		bitmapbytes += bbd[1]
		if charmode:
			freecolor = bbd[2][3]
			colordata += [freecolor]
			# remove MC flag
			if freecolor >= 8:
				freecolor -= 8
			# check in existing blocks if there is already one with same byte coding
			blockfound = False
			charnumber = len(codeblocks)
			if reducechars:
				for i in range(0, len(codeblocks)):
					# it is always sufficient to check wether the encoded bytes are the same!
					# Either individual colors differ then (no problem) or differ (reuse char!)
					# so do NOT compare bbd[0] but bbd[1]
					if bbd[1] == codeblocks[i]:
						blockfound = True
						charnumber = i
						#print('imageblock',len(imageblocks),' uses existing codeblock',i)
						numreusedchars += 1
						break
			if not blockfound:
				codeblocks += [bbd[1]]
			charnumbers += [charnumber]
			imageblocks += [bbd[0]]	# only bbd[0], colordata has color.
		elif hiresmode:
			chardata += [bbd[2][0] * 16 + bbd[2][1]]
		else:
			chardata += [bbd[2][1] * 16 + bbd[2][2]]
			colordata += [bbd[2][3]]
		n = 0
		# decode codeblock data here and show it for control!
		pixels = GetPixelsFromCodeBlock(bbd[1], bbd[2], hiresmode, charmode)
		for yy in range(0, 8):
			for xx in range(0, 8):
				rgb = colors_c64_rgb[pixels[n]]	# already with gamma!
				stretchedcolors[(y * 8 + yy) * img_w + (x * 8 + xx)] = rgb
				n += 1
if charmode:
	print('Some chars could be reused, an 8x8 image tile did not need its own char',numreusedchars,'times.')
# Show best result blocks (for bitmap mode already final result)
im.putdata(stretchedcolors)
if not quiet:
	Show(im)

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

# In charmode reduce all "code" blocks to the given maximum number.
# Try to reduce overall error when replacing codeblocks by others.
# Codeblocks are already unique from byte coding.
# So several "image" blocks may already use the same codeblock (same byte encoding, not color!).
# For every image block we need to compute which block replaces it with least error,
# more an order sorted by error (a heap structure!). Takes O(N^2).
# Note that the order in that heap never changes, it is only reduced by removing the head of the
# heap. Erased codeblocks are marked separately and skipped while traversing the heap.
# For every codeblock compute the error if it would be removed by going over its imageblock list
# and for every imageblock get the error of the 2nd best codeblock to use and sum them up.
# Put all of these codeblock errors in another heap.
# Then remove the codeblock with least error. The imageblocks associated with it are appended at
# the lists of the 2nd best codeblocks for every imageblock, and error values for all codeblocks
# touched have to be updated, the error heap has to be reheapified. Heap for every imageblock using
# the removed codeblock has to pop off the head of their heaps.
# Note that two imageblocks using the same codeblock may have different codeblocks as 2nd best
# candidates, so replacement is not 1:1.
# Very slow because of O(N^2) but seems to work roughly.
# Another idea: every imageblock has a color for any pixel of the 8x8 block (works for hires and MC).
# So account for every color for every pixel a use count.
# Try to find a set of characters that gives the highest use count (least error to use count).
# Not really easy to do so.
def Compute2ndBestBlockError(myheap, removedflags, idx):
	if idx >= len(myheap):
		return 1000000.0
	# if the entry is not removed, return its error, otherwise check children
	if removedflags[myheap[idx][1]]:
		e0 = Compute2ndBestBlockError(myheap, removedflags, idx*2+1)
		e1 = Compute2ndBestBlockError(myheap, removedflags, idx*2+2)
		return min(e0, e1)
	return myheap[idx][0]

if charmode and len(codeblocks) > numchars:
	# for every image block have a list (heap) of tuples, containing the error, codeblock index and color to use.
	errors_image_to_codeblocks = []
	imageblock_indices = []
	is_codeblock_removed = [False] * len(codeblocks)
	for i in codeblocks:
		imageblock_indices += [[]]
	print('Compute imageblock to codeblock errors (takes a while)')	# longest process
	iter_step = len(imageblocks) // 10
	iter_count = 0
	print('Generating all codeblocks with all colors')
	codeblockcolors = list(fixindices)
	for i in range(len(fixindices), 4):
		codeblockcolors += [0]
	all_possible_codeblock_pixels = []
	for j in range(0, len(codeblocks)):
		all_possible_codeblock_pixels += [[]]
		for c in range(0, 16):
			codeblockcolors[3] = c;
			all_possible_codeblock_pixels[-1] += [GetPixelsFromCodeBlock(codeblocks[j], codeblockcolors, False, True)]
	print('Done')
	# The free color of every codeblock can be chosen from 8 low colors, either as hires or as multicolor.
	# Sensible values for it are the free colors of the imageblock (in hires and mc mode),
	# and also the fix colors (background and multicolor global #1 and #2) if they are low colors,
	# so we can e.g. create a monocolor block of a low color even with bit combinations.
	# colors to try define once, set only once per imageblock.
	colors_to_try = []
	for i in fixindices:
		if i < 8:
			colors_to_try += [i + 8]	# try all fix colors as free color with mc flag
	colors_to_try += [0]	# free place for hires test
	colors_to_try += [0]	# free place for mc test
	# fixme a try to make it faster, less compares etc. doesn't seem to help much.
	# try to measure and show time.
	# try multithreading here.
	# https://stackoverflow.com/questions/19322079/threading-in-python-for-each-item-in-list
	print('Remaining number of blocks:',len(imageblocks),'-',numreusedchars,'=',len(imageblocks)-numreusedchars)
	for ib_idx in range(0, len(imageblocks)):
		errors = []
		freecolor = colordata[ib_idx] & 7
		# try freecolor in hires and mc version
		colors_to_try[-2] = freecolor + 8
		colors_to_try[-1] = freecolor
		for cb_idx in range(0, len(codeblocks)):
			minerror = 1000000.0
			minerror_c = -1
			for c in colors_to_try:
				totalerror = 0.0
				for i in range(0, 64):
					cbc = all_possible_codeblock_pixels[cb_idx][c][i]
					totalerror += index_to_index_error[cbc * 16 + imageblocks[ib_idx][i]]
				if totalerror < minerror:
					minerror = totalerror
					minerror_c = c
			errors += [(minerror, cb_idx, minerror_c)]
		heapq.heapify(errors)
		# remember for best codeblock to use that imageblock
		imageblock_indices[errors[0][1]] += [ib_idx]
		errors_image_to_codeblocks += [errors]
		iter_count += 1
		ic = iter_count // iter_step
		if ic * iter_step == iter_count:
			print('Computed',iter_count*100/len(imageblocks),'%')
	errors_for_codeblock_removal = []
	for cb_idx in range(0, len(codeblocks)):
		error_to_remove_cb = 0.0
		for ib_idx in imageblock_indices[cb_idx]:
			error = heapq.nsmallest(2, errors_image_to_codeblocks[ib_idx])[1][0]
			error_to_remove_cb += error
		errors_for_codeblock_removal += [(error_to_remove_cb, cb_idx)]
	heapq.heapify(errors_for_codeblock_removal)
	#print(errors_for_codeblock_removal)
	# Now repeatedly remove codeblock with least error
	print('Removing codeblocks...')
	usedcodeblocks = len(codeblocks)
	while usedcodeblocks > numchars:
		least_error_element = heapq.heappop(errors_for_codeblock_removal)
		least_error_codeblock_idx = least_error_element[1]
		print('Removing codeblock',least_error_codeblock_idx)
		is_codeblock_removed[least_error_codeblock_idx] = True
		usedcodeblocks -= 1
		# all imageblocks using that codeblock need to pop off their heap heads
		# (and also further removed blocks if there) and the now 2nd best codeblocks
		# must get the imageblock indices and also have their error recomputed
		codeblock_idx_to_recompute_error = []
		for ib_idx in imageblock_indices[least_error_codeblock_idx]:
			# Note that if we remove too much blocks, heaps could run empty here,
			# all codeblocks of the heap are flagged as removed, causing an exception.
			# but only theoretical if all codeblocks were removed
			while is_codeblock_removed[errors_image_to_codeblocks[ib_idx][0][1]]:
				heapq.heappop(errors_image_to_codeblocks[ib_idx])
			next_codeblock_idx = errors_image_to_codeblocks[ib_idx][0][1]
			codeblock_idx_to_recompute_error += [next_codeblock_idx]
			imageblock_indices[next_codeblock_idx] += [ib_idx]
		# now make the codeblock_idx list unique
		codeblock_idx_to_recompute_error = set(codeblock_idx_to_recompute_error)
		for cb_idx in codeblock_idx_to_recompute_error:
			totalerror = 0.0
			for ib_idx in imageblock_indices[cb_idx]:
				# compute error if that imageblock would use 2nd best codeblock and
				# sum up the errors
				# get error of 2nd best codeblock in heap, that has not been removed
				error = Compute2ndBestBlockError(errors_image_to_codeblocks[ib_idx], is_codeblock_removed, 0)
				totalerror += error
			# fixme: that search may be avoidable
			for j in range(0, len(errors_for_codeblock_removal)):
				if errors_for_codeblock_removal[j][1] == cb_idx:
					errors_for_codeblock_removal[j] = (totalerror, cb_idx)
					break
		# re-heap
		heapq.heapify(errors_for_codeblock_removal)
	# regenerate char list (charnumbers)
	remaining_codeblocks = []
	new_codeblock_indices = [-1] * len(codeblocks)
	new_codeblocks = []
	for j in range(0, len(codeblocks)):
		if not is_codeblock_removed[j]:
			new_codeblock_indices[j] = len(remaining_codeblocks)
			remaining_codeblocks += [j]
			new_codeblocks += [codeblocks[j]]
	print('Remaining code blocks:',remaining_codeblocks)
	# For every image block remove removed codeblock indices from top, first heap entry is then
	# the codeblock to use.
	for i in range(0, len(imageblocks)):
		while is_codeblock_removed[errors_image_to_codeblocks[i][0][1]]:
			heapq.heappop(errors_image_to_codeblocks[i])
		codeblock_to_use = errors_image_to_codeblocks[i][0][1]
		charnumbers[i] = new_codeblock_indices[codeblock_to_use]
		colordata[i] = errors_image_to_codeblocks[i][0][2]
	codeblocks = new_codeblocks
	print('Number of blocks reduced!')

if charmode:
	# use codeblocks here!
	nn = 0
	codeblockcolors = list(fixindices)
	for i in range(len(fixindices), 4):
		codeblockcolors += [0]
	for y in range(0, img_h//8):
		for x in range(0, img_w//8):
			codeblockcolors[3] = colordata[nn]
			thisblockindices = GetPixelsFromCodeBlock(codeblocks[charnumbers[nn]], codeblockcolors, False, True)
			n = 0
			for yy in range(0, 8):
				for xx in range(0, 8):
					rgb = colors_c64_rgb[thisblockindices[n]]
					stretchedcolors[(y * 8 + yy) * img_w + (x * 8 + xx)] = rgb
					n += 1
			nn += 1
	# Show image composed of remaining blocks
	im.putdata(stretchedcolors)
	if not quiet:
		Show(im)
	charsetbytes = []
	for b in codeblocks:
		charsetbytes += b
	if not usedatalabels and appendzeros:
		# we need to fill up the space with zeros so data is correctly sized!
		restsize = (256 - firstchar) * 8 - len(charsetbytes)
		charsetbytes += [0] * restsize
	dfl = ''
	if usedatalabels:
		dfl += inputbasefilename + '_fixcolors\n'
	dfl += '!byte '
	dfl += hexstr(fixindices[0]) + ', ' + hexstr(fixindices[1]) + ', ' + hexstr(fixindices[2]) + '\n'
	f = open(outputbasefilename + '_fixcolors.a','wt')
	f.writelines(dfl)
	f.close()
	dfl = ''
	if usedatalabels:
		dfl += '\n!align 255,0\n' + inputbasefilename + '_charsetdata\n'
	if firstchar > 0:
		dfl += '!src "' + inputbasefilename + '_chardata0_' + str(firstchar-1) +'.a"\n'
	dfl += dumpbytes(charsetbytes)
	f = open(outputbasefilename + '_chardata.a','wt')
	f.writelines(dfl)
	f.close()
	dfl = ''
	# Combine NxM blocks to tiles
	num_char_x = img_w // 8
	num_char_y = img_h // 8
	num_tiles_x = num_char_x // tilex
	num_tiles_y = num_char_y // tiley
	num_tiles = num_tiles_x * num_tiles_y
	print('Tile count',num_tiles_x,'*',num_tiles_y,', #CharBlocks',len(codeblocks),'of max',num_char_x*num_char_y)
	tiledata = []
	for y in range(0, num_tiles_y):
		for x in range(0, num_tiles_x):
			tilecolordata = []
			for yy in range(0, tiley):
				for xx in range(0, tilex):
					idx = (y*tiley+yy)*num_char_x+(x*tilex+xx)
					bn = charnumbers[idx]			# take charnumber from codeblock!
					tiledata += [bn + firstchar]
					tilecolordata += [colordata[idx]]	# take colordata from imageblock!
			tiledata += tilecolordata
	if True:
		# dump tiledata in separate tables
		numtables = tilex*tiley*2
		for i in range(0, numtables):
			if usedatalabels:
				dfl += '\n' + inputbasefilename + '_tiledata_' + str(i) + '\n'
			nthcopy = []
			count = len(tiledata) // numtables
			for j in range(0, count):
				nthcopy += [tiledata[j * numtables + i]]
			dfl += dumpbytes(nthcopy)
	else:
		if usedatalabels:
			dfl += '\n!align 255,0\n' + inputbasefilename + '_tiledata\n'
		dfl += dumpbytes(tiledata)
	f = open(outputbasefilename + '_tiledata.a','wt')
	f.writelines(dfl)
	f.close()
elif spritemode:
	# Sprite-mode, output the first 63 bytes as data, complete with one null byte to get 64 in total
	# Order of bytes is different than in bitmaps, 3 bytes every line, 21 lines, then next sprite in row.
	spritebytes = []
	for sy in range(0, num_sprites_y):
		for sx in range(0, num_sprites_x):
			for y in range(0, 21):
				yr = y % 8
				for x in range(0, 3):
					blocknr = (sy * 3 + y // 8) * (num_sprites_x * 3) + sx * 3 + x
					spritebytes += [sprite_recode_byte(bitmapbytes[blocknr * 8 + yr], hiresmode)]
			# last byte: low nibble is sprite color, bit 7 is multicolor flag!
			lastbyte = fixindices[1]
			if not hiresmode:
				lastbyte = fixindices[3] + 128
			spritebytes += [lastbyte]
	# Generate .a data file
	dfl = ''
	if usedatalabels:
		dfl += '!align 63, 0\n' + inputbasefilename + '_data\n'
	dfl += dumpbytes(spritebytes)
	f = open(outputbasefilename + '_sprdata.a','wt')
	f.writelines(dfl)
else:
	# Bitmap-Mode: Show data as RGB image and save as binary data
	# for bitmaps we don't need separate files (yet).
	im.resize((320, 200), PIL.Image.NEAREST).save(outputbasefilename + '_c64.png')
	# Generate .a data file
	dfl = ''
	if not hiresmode:
		dfl += inputbasefilename + '_backgroundcolor\n!byte '
		dfl += hexstr(backgroundindex)
	dfl += '\n\n' + inputbasefilename + '_bitmapdata\n'
	dfl += dumpbytes(bitmapbytes)
	dfl += '\n\n' + inputbasefilename + '_chardata\n'
	dfl += dumpbytes(chardata)
	if not hiresmode:
		dfl += '\n\n' + inputbasefilename + '_colordata\n'
		dfl += dumpbytes(colordata)
	f = open(outputbasefilename + '_bmpdata.a','wt')
	f.writelines(dfl)
	f.close()
	# RLE encoding of data
	rlebytes0 = RLEncode(bitmapbytes)
	rlebytes1 = RLEncode(chardata)
	rlebytes2 = []
	if not hiresmode:
		rlebytes2 = RLEncode(colordata)
	totallen = len(rlebytes0)+len(rlebytes1)+len(rlebytes2)
	print('Total:',totallen,'bytes of 10000.')
	dfl = ''
	if not hiresmode:
		dfl += inputbasefilename + '_backgroundcolor\n!byte '
		dfl += hexstr(backgroundindex)
	dfl += '\n\n' + inputbasefilename + '_bitmapdata_rle\n'
	dfl += dumpbytes(rlebytes0)
	dfl += '\n\n' + inputbasefilename + '_chardata_rle\n'
	dfl += dumpbytes(rlebytes1)
	if not hiresmode:
		dfl += '\n\n' + inputbasefilename + '_colordata_rle\n'
		dfl += dumpbytes(rlebytes2)
	f = open(outputbasefilename + '_bmpdata_rle.a','wt')
	f.writelines(dfl)
	f.close()
