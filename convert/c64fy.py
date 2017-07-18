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

import PIL.Image
import random
import sys
import math
from rlencode import RLEncode

# Some global parameters
enable_mixing = True	# Enable color mixing
adjust_uv = False	# helps for some images
uv_dist_limit = 0.2	# max UV distance to 0
uv_limit_grey = 0.05	# UV distance below this is considered as grey value
dynamic_uv_grey_limit = False	# Adjust it automatically?

# Colors of c64 - y is luminance (0...32), uv as angle (0...16)
# Distance of colors (not grey) to center of yuv space is always 0.1333333.
default_uv_color_distance = 0.1333333
colors_y_uvangle = [
	(0, -1),		# black
	(32, -1),		# white
	(10, 5),		# red
	(20, 13),		# cyan
	(12, 2),		# purple
	(16, 10),		# green
	(8, 0),			# blue
	(24, 8),		# yellow
	(12, 6),		# orange
	(8, 7),			# brown
	(16, 5),		# light red
	(10, -1.0),		# dark grey
	(15, -1.0),		# medium grey
	(24, 10),		# light green
	(15, 0),		# light blue
	(20, -1)		# light grey
]

colors_c64_yuv = []
for c in colors_y_uvangle:
	y = c[0]/32.0
	if c[1] < 0:
		colors_c64_yuv += [(y, 0.0, 0.0)]
	else:
		u = default_uv_color_distance*math.cos(math.pi*2*c[1]/16.0)
		v = default_uv_color_distance*math.sin(math.pi*2*c[1]/16.0)
		colors_c64_yuv += [(y, u, v)]
#print colors_c64_yuv

# Color-Scaling
color_scale_factor = 1.0 / 255.0

infinity = 1000000000.0

# fixme order of color data for hires is not checked if correct

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

# fixme charset option zum aussortieren eher ausbauen

# Original c64 color handling is YUV not HLS, see http://www.pepto.de/projects/colorvic/2001/index.html

# Chardaten direkt aus Bildern zu generieren macht so keinen Sinn.
# Lieber die festen Farben vorgeben bei Char-Umwandlung oder eben optional.
# fixme Ähnlichkeiten von chars testen nur Farbe ab, aber ersetze die austauschbare Farbe durch andere,
# nur so kann man gemeinsame chars finden, brauchen wir erstmal nicht...
# steht unten so auch noch mal im code, wird aber so nicht verwendet, da ja 3 von 4 Farben erstmal
# sowieso gleich sind, es kann aber etwas bringen, das mal durchzuprobieren.

# We need a general flag for hires to encode hires bitmaps as well, needed for sprites!
# Handle this with a generic flag for block generation.
# We can do MC blocks, MC blocks with hires single low color (in char mode) and only Hires
# blocks with 0 or 2 fix colors (Bitmap or Sprite).
# Sprite color can be determined automatically from image data or give it from command line.
# fixme test hires mode for sprites!

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

def RGBToYUV(c):
	r = c[0]
	g = c[1]
	b = c[2]
	y = r *  0.29900 + g *  0.58700 + b *  0.11400
	u = r * -0.14713 + g * -0.28886 + b *  0.43600 + 0.5
	v = r *  0.61500 + g * -0.51499 + b * -0.10001 + 0.5
	return (y, u - 0.5, v - 0.5)	# UV shifted to -0.5...0.5 range

def YUVToRGB(c):
	y = c[0]
	u = c[1] + 0.5	# UV shifted to -0.5...0.5 range
	v = c[2] + 0.5
	# not fully official coefficients but taken from c64 color analyse website
	r = y +                    + (v - 0.5) *  1.140
	g = y + (u - 0.5) * -0.396 + (v - 0.5) * -0.581
	b = y + (u - 0.5) *  2.029
	return (r, g, b)

def AddGammaCorrection(rgb):
	# Apply exponent of 1.136, values are in 0-1 range so no factor needed
	gamma_exp = 1.136
	return (pow(rgb[0], gamma_exp), pow(rgb[1], gamma_exp), pow(rgb[2], gamma_exp))

def RemoveGammaCorrection(rgb):
	# Apply exponent of 1/1.136, values are in 0-1 range so no factor needed
	gamma_exp = 1.0/1.136
	return (pow(rgb[0], gamma_exp), pow(rgb[1], gamma_exp), pow(rgb[2], gamma_exp))

def PartToByte(x):
	y = int(x / color_scale_factor + 0.5)
	y = max(0, min(255, y))
	return y

def vecadd(a, b):
	return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vecsub(a, b):
	return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def veclensqr(v):
	return v[0]*v[0] + v[1]*v[1] + v[2]*v[2]

def veclen(v):
	return math.sqrt(veclensqr(v))

def vecmul(a, b):
	return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def vecscal(v, a):
	return (v[0]*a, v[1]*a, v[2]*a)

def ErrorInYUV(yuv0, yuv1):
	d = vecsub(yuv0, yuv1)
	return math.sqrt(vecmul(d, d))

def ComputeBlockError(b0, b1):
	error = 0.0
	for i in range(0, len(b0)):
		error += ErrorInYUV(b0[i], b1[i])
	return error

def FindBestColorForYUV(yuv):
	index = 16
	minerror = infinity
	if max(abs(yuv[1]), abs(yuv[2])) < uv_limit_grey:
		for i in [0, 1, 11, 12, 15]:
			error = ErrorInYUV(yuv, colors_c64_yuv[i])
			if error < minerror:
				minerror = error
				index = i
	else:
		for i in range(0, 16):
			error = ErrorInYUV(yuv, colors_c64_yuv[i])
			if error < minerror:
				minerror = error
				index = i
	return index

def FindBestTwoColorsForYUV(yuv, available_indices):
	index = 16
	index2 = 16
	minerror = infinity
	minerror2 = infinity
	if len(available_indices) > 0:
		for i in available_indices:
			error = ErrorInYUV(yuv, colors_c64_yuv[i])
			if error < minerror:
				minerror2 = minerror
				index2 = index
				minerror = error
				index = i
			elif error < minerror2:
				minerror2 = error
				index2 = i
	elif max(abs(yuv[1]), abs(yuv[2])) < uv_limit_grey:
		for i in [0, 1, 11, 12, 15]:
			error = ErrorInYUV(yuv, colors_c64_yuv[i])
			if error < minerror:
				minerror2 = minerror
				index2 = index
				minerror = error
				index = i
			elif error < minerror2:
				minerror2 = error
				index2 = i
	else:
		for i in range(0, 16):
			error = ErrorInYUV(yuv, colors_c64_yuv[i])
			if error < minerror:
				minerror2 = minerror
				index2 = index
				minerror = error
				index = i
			elif error < minerror2:
				minerror2 = error
				index2 = i
	return (index, index2)

def ComputeBestColorOfTwo(yuv, best_two_colors):
	indexresult = best_two_colors[0]
	if enable_mixing and best_two_colors[1] != 16:
		errormf = ComputeMixFactorAndDistance(yuv, best_two_colors[0], best_two_colors[1])
		# Larger mixfactor means rather 2nd color (index1), and as larger the random range is
		if enable_mixing:
			r = random.random()
			if r < errormf[1]:
				indexresult = best_two_colors[1]
	return indexresult

def FindBestLowIndexColor(index):
	minerror = infinity
	lowindex = 16
	for i in range(0, 8):
		error = ErrorInYUV(colors_c64_yuv[i], colors_c64_yuv[index])
		if error < minerror:
			minerror = error
			lowindex = i
	return lowindex

def BlockHiResToMultiColor(colorblock):
	result = []
	for i in range(0, len(colorblock)//2):
		c0 = colorblock[i*2+0]
		c1 = colorblock[i*2+1]
		c = ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2, (c0[2] + c1[2]) / 2)
		result += [c]
	return result

def BlockMultiColorToHiRes(colorblock):
	result = []
	for i in colorblock:
		result += [i, i]
	return result

def ComputeMixFactorAndDistance(yuv, index0, index1):
	yuv0 = colors_c64_yuv[index0]
	yuv1 = colors_c64_yuv[index1]
	delta = vecsub(yuv1, yuv0)
	deltasqrlen = veclensqr(delta)
	delta2 = vecsub(yuv, yuv0)
	d = vecmul(delta, delta2) / deltasqrlen
	limit = 0.4
	if d <= limit:
		return (veclen(delta2), 0.0)
	elif d >= 1.0 - limit:
		return (veclen(vecsub(yuv, yuv1)), 1.0)
	else:
		return (veclen(vecsub(yuv, vecadd(yuv0, vecscal(delta, d)))), d)

def GenerateBestBlock(colorblock, fixed_indices, charmode, hiresmode):
	# Input is a block of 8x8=64 RGB colors (for multicolor mode use only every second value)
	# Zero, one, two or three colors can be chosen freely, depending on the mode.
	# In charmode the only free color may come only from indices 0-7.
	# In hires mode we have two free colors (or zero for sprites).
	# In multicolor mode, three colors can be chosen freely.
	# For charmode iterate over all free colors with index 0-7 and compare block in hires,
	# this means compute error to original.
	inputblock = colorblock
	num_free_indices = 4 - len(fixed_indices)
	if hiresmode:
		num_free_indices = 2 - len(fixed_indices)
	lowcolorblockerror = infinity
	resultblocklowcolor = []
	resultindiceslowcolor = []
	lowindex = 16
	if charmode:
		# Find most used color except background in block and use this for comparison
		index_count = [0] * 16
		for i in range(0, 8*8):
			yuv = inputblock[i]
			index = FindBestColorForYUV(yuv)
			if index != fixed_indices[0]:
				index_count[index] += 1
		max_count = 0
		index = 16
		for i in range(0, 16):
			if index_count[i] > max_count:
				max_count = index_count[i]
				index = i
		# Find a color of the first 8 that is most similar to index
		if index != 16:
			lowindex = FindBestLowIndexColor(index)
		# Replace every pixel by background color or by lowindex color
		blockerror = 0
		for i in range(0, 8*8):
			yuv = inputblock[i]
			error0 = ErrorInYUV(colors_c64_yuv[fixed_indices[0]], yuv)
			error1 = error0
			idx = fixed_indices[0]
			if lowindex != 16:
				error1 = ErrorInYUV(colors_c64_yuv[lowindex], yuv)
				if error1 < error0:
					idx = lowindex
			resultblocklowcolor += [colors_c64_yuv[idx]]
			resultindiceslowcolor += [idx]
			blockerror += min(error0, error1)
		# Half error for comparison with multicolor
		lowcolorblockerror = blockerror * 0.5
	# For multicolor half x resolution!
	if not hiresmode:
		inputblock = BlockHiResToMultiColor(colorblock)
	resultblock = []
	resultindices = []
	# For every pixel find the two most similar colors and the best mix between them to represent the
	# original color. Either take the best color or mix between the two.
	# Account the finally chosen color for index use counting.
	index_use_count = [0] * 16
	for yuv in inputblock:
		# Find best matching two colors
		btc = FindBestTwoColorsForYUV(yuv, [])
		# Compute best match between them
		indexresult = ComputeBestColorOfTwo(yuv, btc)
		# Account color index
		index_use_count[indexresult] += 1
	#print(index_use_count)
	# Now take the most used colors that are not already available and set them as fixed colors.
	# Afterwards replace every color that can not be represented by available colors, also with mixing.
	# Take most used color as fix color for this block if there are still free colors available.
	# Color is put at back of fixed_indices so it isn't reused.
	fixed_indices_this_block = [x for x in fixed_indices]
	for i in range(0, num_free_indices):
		mui = 16
		maxcount = 0
		for j in range(0, 16):
			if j not in fixed_indices_this_block:
				if index_use_count[j] > maxcount:
					maxcount = index_use_count[j]
					mui = j
		# In charmode replace it by most similar low index color.
		if mui != 16:
			if charmode:
				mui = FindBestLowIndexColor(mui)
			fixed_indices_this_block += [mui]
	# For every pixel determine best two colors from available colors of this block.
	# Compute segment in color-3-space between the two and determine closest position to segment for
	# the given color. The segment parameter determines mixing factor.
	randfactorn = 0
	anycolorblockerror = 0.0
	for yuv in inputblock:
		# Find best two colors out of available ones
		btc = FindBestTwoColorsForYUV(yuv, fixed_indices_this_block)
		indexresult = ComputeBestColorOfTwo(yuv, btc)
		if charmode:
			anycolorblockerror += ErrorInYUV(yuv, colors_c64_yuv[indexresult])
		resultblock += [colors_c64_yuv[indexresult]]
		resultindices += [indexresult]
	# Put out data
	resultbytes = []
	if charmode and lowcolorblockerror < anycolorblockerror:
		#print('use low color block',lowcolorblockerror,'<',anycolorblockerror)
		resultblock = resultblocklowcolor
		for y in range(0, 8):
			byte = 0
			for x in range(0, 8):
				i = resultindiceslowcolor[y*8+x]
				bit = 1
				if i == fixed_indices_this_block[0]:
					bit = 0
				byte = byte * 2 + bit
			resultbytes += [byte]
		if len(fixed_indices_this_block) == 4:
			fixed_indices_this_block[3] = lowindex
	elif hiresmode:
		# A block is always 8 bytes in a row, so 8x8 pixels.
		for y in range(0, 8):
			byte = 0
			for x in range(0, 8):
				index = resultindices[y*8+x]
				bits = -1
				for i in range(0, 2):
					if fixed_indices_this_block[i] == index:
						bits = i
						break
				if bits < 0:
					raise ValueError('invalid data for hires encoding, invalid colors.')
				byte = byte * 2 + bits
			resultbytes += [byte]
	else:
		# Ein Block sind immer 8 Byte übereinander, also 8x8 Pixel (4x8 im Multicolor).
		# Daten sind immer 8 Byte für Bitmap, Farben 1,2 falls individuell und Farbe 3 als Colorcode.
		# Also 11 bzw. 9 Int-Werte für Bitmap/Charmode
		for y in range(0, 8):
			byte = 0
			for x in range(0, 4):
				index = resultindices[y*4+x]
				bits = 0
				for i in range(0, len(fixed_indices_this_block)):
					if fixed_indices_this_block[i] == index:
						bits = i
				byte = byte * 4 + bits
			resultbytes += [byte]
		resultblock = BlockMultiColorToHiRes(resultblock)
		if charmode:
			if len(fixed_indices_this_block) < 4:
				fixed_indices_this_block += [0] * (4 - len(fixed_indices_this_block))
			fixed_indices_this_block[3] += 8	# Set multicolor flag
	if charmode:
		# Return image data, encoded bytes and 1 color in color ram
		if len(fixed_indices_this_block) < 4:
			fixed_indices_this_block += [0] * (4 - len(fixed_indices_this_block))
		return (resultblock, resultbytes, fixed_indices_this_block[3])
	elif hiresmode:
		# Return image data, encoded bytes, 2 colors in char
		if len(fixed_indices_this_block) < 2:
			fixed_indices_this_block += [0] * (2 - len(fixed_indices_this_block))
		return (resultblock, resultbytes, fixed_indices_this_block[0]*16 + fixed_indices_this_block[1])
	else:
		# Return image data, encoded bytes, 2 colors in char and 1 color in color ram
		if len(fixed_indices_this_block) < 4:
			fixed_indices_this_block += [0] * (4 - len(fixed_indices_this_block))
		return (resultblock, resultbytes, fixed_indices_this_block[1]*16 + fixed_indices_this_block[2], fixed_indices_this_block[3])
	
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
#                  Hauptprogramm
#
###########################################################################################

random.seed()

# Bild laden
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
			if numchars < 1 or numchars > 256 or firstchar + numchars > 256:
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
			enable_mixing = int(p1) != 0
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

colors_c64_rgb = []
for c in colors_c64_yuv:
	rgb = YUVToRGB(c)
	rgb = AddGammaCorrection(rgb)
	colors_c64_rgb += [(PartToByte(rgb[0]), PartToByte(rgb[1]), PartToByte(rgb[2]))]
	#print hex(PartToByte(rgb[0])), hex(PartToByte(rgb[1])), hex(PartToByte(rgb[2]))

index_to_index_error = []
if charmode:
	for y in range(0, 16):
		for x in range(0, 16):
			index_to_index_error += [ErrorInYUV(colors_c64_rgb[x], colors_c64_rgb[y])]

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
	rgb = RemoveGammaCorrection(rgb)
	yuv = RGBToYUV(rgb)
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
	rgb = RemoveGammaCorrection(rgb)
	yuv = RGBToYUV(rgb)
	yuv = (yuv[0], yuv[1] * uv_scale, yuv[2] * uv_scale)
	pxyuv += [yuv]
	# Finde passensten Index nach Farbzuordnung
	index = FindBestColorForYUV(yuv)
	pxnearest += [colors_c64_rgb[index]]
	closestcolorindices += [index]
	index_use_count[index] += 1
	
im.putdata(pxnearest)
if not quiet:
	Show(im)

# Count which color or which three are used mostly
num_most_used_indices = 1
fixindices = []
if charmode:
	num_most_used_indices = 3
	enable_mixing = False
	dynamicgreylimit = False
elif spritemode:
	num_most_used_indices = 4
	if hiresmode:
		num_most_used_indices = 2
	enable_mixing = False
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
		pxyuv_extended += [colors_c64_yuv[spriteneutralindex]] * (img_w * 3)
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
		if mui < 0:
			raise ValueError("illegal index use count")
		fixindices += [mui]
print('Fix indices for image:', fixindices)

# Iterate over all 8x8 blocks and compute best fit block with c64 coding rules with
# fix and free colors and mixing if enabled.
stretchedcolors = [(0, 0, 0)] * len(pxyuv)
blocks = []
blockusecount = []
numblockstotal = 0
bitmapbytes = []	# Bytes für Bitmap
chardata = []		# Passende Character-Daten für Bitmap (0-255)
colordata = []		# Colorcode für Bitmap/Char 11 (Mit Bit4 als MC-Marker bei Char) (0-15)
backgroundindex = 16
if not hiresmode:
	backgroundindex = fixindices[0]
for y in range(0, img_h//8):
	for x in range(0, img_w//8):
		numblockstotal += 1
		colorblock = []
		for yy in range(0, 8):
			for xx in range(0, 8):
				colorblock += [pxyuv[(y * 8 + yy) * img_w + (x * 8 + xx)]]
		bbd = GenerateBestBlock(colorblock, fixindices, charmode, hiresmode)
		bitmapbytes += bbd[1]
		if charmode:
			colordata += [bbd[2]]
		elif hiresmode:
			chardata += [bbd[2]]
		else:
			chardata += [bbd[2]]
			colordata += [bbd[3]]
		if charmode:
			blockfound = False
			for i in range(0, len(blocks)):
				if bbd[0] == blocks[i][0]:
					blockusecount[i] += 1
					blockfound = True
					break # print('Reusable char found!')
			if not blockfound:
				blocks += [bbd]
				blockusecount += [1]
		n = 0
		for yy in range(0, 8):
			for xx in range(0, 8):
				ci = bbd[0][n]
				rgb = YUVToRGB(ci)
				rgb = AddGammaCorrection(rgb)
				r = int(rgb[0] / color_scale_factor)
				g = int(rgb[1] / color_scale_factor)
				b = int(rgb[2] / color_scale_factor)
				stretchedcolors[(y * 8 + yy) * img_w + (x * 8 + xx)] = (r, g, b)
				n += 1
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

# In charmode reduce all used blocks to the given number.
# Compare every pair of blocks and replace one where pair has least error.
# However replace that one that is used less.
# Hmm blocks that are often used should not be replaced...
# here we can implement some strategy...
# Sum up errors by comparing indices.
# Replace free color of one block by 8 possible low color indices for comparison.
# Compare two blocks of 8x8 pixels (64 indices) with other blocks by looking up
# the errors in the matrix and summing them up.
# Fastest way to do it - but how to eleminate blocks?
# If error is low between two blocks but both are often used, rather keep both
# of them.
# Here a good strategy is missing but we don't really need that mode...

# alt:
# Im Charmode sortiere noch Blöcke aus (Verringere auf vorfügbare Zahl)
# Idealerweise Daten gleich als acme source ausgeben für's Einbinden!
# fixme hier wird direkt nach Farben geguckt, aber jeder vorhandene Block an Indices wäre auch ok,
# man kann ja einfach Farben tauschen! Wobei nur eine Farbe getauscht werden kann im char mode.
# das fehlt hier wohl noch!
if charmode:
	print('Num Chars initial',len(blocks),'of',numblockstotal,'numchars',numchars)
	while len(blocks) > numchars:
		# Finde seltensten Block
		mincount = 10000000
		bi = 0
		for i in range(0, len(blocks)):
			if blockusecount[i] < mincount:
				mincount = blockusecount[i]
				bi = i
		# Gehe über alle anderen Blöcke außer dem und finde ähnlichsten
		minerror = infinity
		bai = 0
		for i in range(0, len(blocks)):
			if i != bi:
				error = ComputeBlockError(blocks[i][0], blocks[bi][0])
				if error < minerror:
					minerror = error
					bai = i
		# Ersetze bi durch bai
		print('Replace',bi,'by',bai,' Num blocks:',len(blocks)-1,'of',numchars,'remain.')
		newblocks = blocks[0:bi] + blocks[bi+1:]
		blockusecount[bai] += blockusecount[bi]
		newblockusecount = blockusecount[0:bi] + blockusecount[bi+1:]
		blocks = newblocks
		blockusecount = newblockusecount
	print('Block use count:', blockusecount)
	# Gehe dann wieder über alle Blöcke und finde den am besten passensten Block
	charnumbers = []
	for y in range(0, img_h//8):
		for x in range(0, img_w//8):
			colorblock = []
			for yy in range(0, 8):
				for xx in range(0, 8):
					colorblock += [pxyuv[(y * 8 + yy) * img_w + (x * 8 + xx)]]
			minerror = infinity
			bestchar = 0
			for i in range(0, len(blocks)):
				error = ComputeBlockError(blocks[i][0], colorblock)
				if error < minerror:
					minerror = error
					bestchar = i
			bestblock = blocks[bestchar][0]
			charnumbers += [firstchar + bestchar]
			#print('Using Char',bestchar,'for block')
			n = 0
			for yy in range(0, 8):
				for xx in range(0, 8):
					ci = bestblock[n]
					rgb = YUVToRGB(ci)
					rgb = AddGammaCorrection(rgb)
					r = int(rgb[0] / color_scale_factor)
					g = int(rgb[1] / color_scale_factor)
					b = int(rgb[2] / color_scale_factor)
					stretchedcolors[(y * 8 + yy) * img_w + (x * 8 + xx)] = (r, g, b)
					n += 1
	# Zeige Bild durch Blöcke an!
	im.putdata(stretchedcolors)
	if not quiet:
		Show(im)
	# charnumbers sind schonmal die Daten des Bildes.
	# Die Blöcke bilden den Teil des Zeichensatzes
	#print charnumbers
	#print [b[1] for b in blocks]
	#print [b[2] for b in blocks]
	charsetbytes = []
	for b in blocks:
		charsetbytes += b[1]
	if not usedatalabels:
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
	# Fasse nun immer NxM Blöcke zu Tiles zusammen
	num_char_x = img_w // 8
	num_char_y = img_h // 8
	num_tiles_x = num_char_x // tilex
	num_tiles_y = num_char_y // tiley
	num_tiles = num_tiles_x * num_tiles_y
	print('Tile count',num_tiles_x,'*',num_tiles_y,', #CharBlocks',len(blocks),'of max',num_char_x*num_char_y)
	tiledata = []
	for y in range(0, num_tiles_y):
		for x in range(0, num_tiles_x):
			tilecolordata = []
			for yy in range(0, tiley):
				for xx in range(0, tilex):
					idx = (y*tiley+yy)*num_char_x+(x*tilex+xx)
					bn = charnumbers[idx] - firstchar
					tiledata += [bn + firstchar]
					tilecolordata += [blocks[bn][2]]
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

