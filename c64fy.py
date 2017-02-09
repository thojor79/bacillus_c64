#!/usr/bin/python3
# coding=utf8

# PC to C64 image data converter
# Copyright (C) 2013-2017  Thorsten Jordan.
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

# Some global parameters
enable_mixing = True

# Colors of c64 - y is luminance (0...32), uv as angle (0...16), most similar colors as lest as third parameter
# Distance of colors (not grey) to center of yuv space is always 0.1333333.
default_uv_color_distance = 0.1333333
uv_distance_grey_limit = default_uv_color_distance / 3
colors_y_uvangle_nearest = [
	(0, -1, [11, 6, 9]),		# black, most similar the darkest colors blue, brown and dark grey
	(32, -1, [15, 7, 13, 14]),	# white, most similar light grey and the brightest colors yellow and light green and also light blue
	(10, 5, [8,9,4,10]),		# red, similar orange, brown, purple and light red
	(20, 13, [5,6,13,14,15]),	# cyan, similar green, blue, light green, light blue, light grey
	(12, 2, [2,6,11]),		# purple, similar red, blue, dark grey
	(16, 10, [13,3,6,12]),		# green, similar light green,cyan,blue,medium grey
	(8, 0, [14,4,3,11]),		# blue similar light blue,cyan,purple,dark grey
	(24, 8, [8,15,13,1]),		# yellow similar orange,light grey,light green,white
	(12, 6, [9,7,15,10]),		# Orange similar brown,yellow,rosa,light grey
	(8, 7, [8,2,11,0]),		# brown similar orange,red,dark grey,black
	(16, 5, [8,2,4,15]),		# light red similar orange,red,purple,light grey
	(10, -1.0, [0,12]),		# dark grey similar black,medium grey
	(15, -1.0, [11,15]),		# medium grey similar dark grey,light grey
	(24, 10, [7,5,2,15]),		# light green similar yellow,green,white,light grey
	(15, 0, [6,3,15,13]),		# light blue similar blue,cyan,light grey,light green
	(20, -1, [1,9])			# light grey similar medium grey,white
]

colors_c64_yuv = []
for c in colors_y_uvangle_nearest:
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
# fixme offer hires mode for sprites!

# fixme blocks with just one color are encoded as multicolor in char mode, rather prefer hires mode?
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

# fixme try results of hires bitmap encoding

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

colors_c64_rgb = []
for c in colors_c64_yuv:
	rgb = YUVToRGB(c)
	rgb = AddGammaCorrection(rgb)
	colors_c64_rgb += [(PartToByte(rgb[0]), PartToByte(rgb[1]), PartToByte(rgb[2]))]
	#print hex(PartToByte(rgb[0])), hex(PartToByte(rgb[1])), hex(PartToByte(rgb[2]))

def ErrorInYUV(yuv0, yuv1):
	y = yuv0[0] - yuv1[0]
	u = yuv0[1] - yuv1[1]
	v = yuv0[2] - yuv1[2]
	return y*y + u*u + v*v

def ComputeBlockError(b0, b1):
	error = 0.0
	for i in range(0, len(b0)):
		error += ErrorInYUV(b0[i], b1[i])
	return error

def FindBestColorForYUV(yuv):
	index = 0
	minerror = infinity
	for i in range(0, 16):
		error = ErrorInYUV(yuv, colors_c64_yuv[i])
		if error < minerror:
			minerror = error
			index = i
	return index

def FindBestLowIndexColor(index):
	minerror = infinity
	lowindex = 0
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
	lowindex = 0
	if charmode:
		# Find most used color except background in block and use this for comparison
		index_count = [0] * 16
		for i in range(0, 8*8):
			yuv = inputblock[i]
			index = FindBestColorForYUV(yuv)
			if index != fixed_indices[0]:
				index_count[index] += 1
		max_count = 0
		index = 0
		for i in range(0, 16):
			if index_count[i] > max_count:
				max_count = index_count[i]
				index = i
		# Find a color of the first 8 that is most similar to index
		lowindex = FindBestLowIndexColor(index)
		# Replace every pixel by background color or by lowindex color
		blockerror = 0
		for i in range(0, 8*8):
			yuv = inputblock[i]
			error0 = ErrorInYUV(colors_c64_yuv[fixed_indices[0]], yuv)
			error1 = ErrorInYUV(colors_c64_yuv[lowindex], yuv)
			idx = lowindex
			if error0 < error1:
				idx = fixed_indices[0]
			resultblocklowcolor += [colors_c64_yuv[idx]]
			resultindiceslowcolor += [idx]
			blockerror += min(error0, error1)
		# Half error for comparison with multicolor
		lowcolorblockerror = blockerror * 0.5
	# For multicolor half x resolution!
	if not hiresmode:
		inputblock = BlockHiResToMultiColor(colorblock)
	# Finde die vier häufigsten Farben im Block, also jeweils passenste und zweitpassenste Farbe ermitteln,
	# deren Verwendung merken (Anteile aufsummieren).
	# Sind feste Farben dabei, nehme die ansonsten freie Farbe(n) auf die nächsthäufigsten setzen.
	# Für jedes Pixel dann beste Mischung aus vorhandenen Farben bestimmen (zwei Werte und Mischfaktor).
	# Farbe ist dann wenn zufällig 0...1 > Mischfaktor eben Farbe 2 sonst Farbe 1.
	# Dafür brauchen wir eine Ähnlichkeitsfunktion für Farben.
	# 3D-Abstand in YUV, wobei Y-Abstand ggf. halbiert
	resultblock = []
	resultindices = []
	index_use_count = [0.0] * 16
	for yuv in inputblock:
		index0 = FindBestColorForYUV(yuv)
		mixfactor = 0.0
		index1 = index0
		# Finde aus ähnlichen Farben, die die am besten paßt (kleinster Fehler)
		# Also berechne jeweils Segment von Farbe1 zu Farbe2 und nächsten Abstand zu Segment,
		# mit Mischfaktor wo auf dem Segment man ist.
		# Je größer mixfactor, desto eher zweite Farbe!
		# wieso nicht einfach mix mit allen Farben probieren?!
		minerror = infinity
		#print('test nearest of',index0,'are',colors_y_uvangle_nearest[index0][2])
		for ci in colors_y_uvangle_nearest[index0][2]:
			errormf = ComputeMixFactorAndDistance(yuv, index0, ci)
			if errormf[0] < minerror:
				minerror = errormf[0]
				index1 = ci
				mixfactor = errormf[1]
		# Zähle nun verwendete Farben mal Mixfaktor
		index_use_count[index0] += 1.0 - mixfactor
		index_use_count[index1] += mixfactor
	# Ersetze verwendete Farben durch verfügbare. Also häufigste Farbe, die noch nicht vorhanden ist,
	# durch freie Farbe ersetzen. Gibt es keine freie mehr, nehme die, die als nächstes paßt,
	# bzw. mach das dann pro Pixel.
	# ergänze einfach fixed_indices-Array
	fixed_indices_this_block = [x for x in fixed_indices]
	for i in range(0, num_free_indices):
		mui = 0
		maxcount = 0.0
		for j in range(0, 16):
			if j not in fixed_indices_this_block:
				if index_use_count[j] > maxcount:
					maxcount = index_use_count[j]
					mui = j
		# Im Charmode ersetze durch ähnlichste Farbe unter den ersten 8.
		if charmode:
			mui = FindBestLowIndexColor(mui)
		fixed_indices_this_block += [mui]
	# Bestimme dann pro Pixel wieder Mixfaktor aus bester und zweitbester Farbe.
	randfactorn = 0
	anycolorblockerror = 0.0
	for yuv in inputblock:
		minerror = infinity
		index0 = 0
		for ci in fixed_indices_this_block:
			error = ErrorInYUV(yuv, colors_c64_yuv[ci])
			if error < minerror:
				minerror = error
				index0 = ci
		minerror = infinity
		mixfactor = 0.0
		index1 = index0
		for ci in fixed_indices_this_block:
			if ci != index0:
				errormf = ComputeMixFactorAndDistance(yuv, index0, ci)
				if errormf[0] < minerror:
					minerror = errormf[0]
					index1 = ci
					mixfactor = errormf[1]
		# Je größer Mixfactor, desto eher zweite Farbe, desto größer auch Random-Bereich
		if enable_mixing:
			r = random.random()
			indexresult = index1
			if r > mixfactor:
				indexresult = index0
		else:
			indexresult = index0
			if charmode:
				anycolorblockerror += ErrorInYUV(yuv, colors_c64_yuv[indexresult])
		resultblock += [colors_c64_yuv[indexresult]]
		resultindices += [indexresult]
	# Ausgeben
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
		fixed_indices_this_block[3] = lowindex
	elif hiresmode:
		# A block is always 8 bytes in a row, so 8x8 pixels.
		for y in range(0, 8):
			byte = 0
			for x in range(0, 8):
				index = resultindices[y*8+x]
				bits = 0
				for i in range(0, 2):
					if fixed_indices_this_block[i] == index:
						bits = i
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
				for i in range(0, 4):
					if fixed_indices_this_block[i] == index:
						bits = i
				byte = byte * 4 + bits
			resultbytes += [byte]
		resultblock = BlockMultiColorToHiRes(resultblock)
		if charmode:
			fixed_indices_this_block[3] += 8	# Set multicolor flag
	if charmode:
		# Return image data, encoded bytes and 1 color in color ram
		return (resultblock, resultbytes, fixed_indices_this_block[3])
	elif hiresmode:
		# Return image data, encoded bytes, 2 colors in char
		return (resultblock, resultbytes, fixed_indices_this_block[0]*16 + fixed_indices_this_block[1])	# fixme order?
	else:
		# Return image data, encoded bytes, 2 colors in char and 1 color in color ram
		return (resultblock, resultbytes, fixed_indices_this_block[1]*16 + fixed_indices_this_block[2], fixed_indices_this_block[3])
	
# Bild vergrößert anzeigen
def Show(im):
	im2 = im.resize((im.size[0] * 2, im.size[1] * 2), PIL.Image.NEAREST)
	im2.show()

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
	sys.exit(1)
inputfilename = sys.argv[len(sys.argv) - 1]
inputbasefilename = inputfilename[0:inputfilename.rfind('.')]
outputbasefilename = 'output/' + inputbasefilename
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

# skalieren/zuschneiden
img_w = im.size[0]
img_h = im.size[1]
if charmode:
	img_w = (img_w // 8) * 8
	img_h = (img_h // 8) * 8
	im = im.crop((0, 0, img_w, img_h))
elif spritemode:
	if img_w != 24 or img_h != 21:
		print('Invalid sprite image inputfile.')
		sys.exit(0)
	img_h = 24
elif hiresmode:
	# Skaliere auf 320x200
	im = im.resize((320, 200), PIL.Image.BICUBIC)
	img_w = 320
	img_h = 200
else:
	# Skaliere auf Multicolor, dann wieder auf korrekte Größe, für generischen Vergleich
	im = im.resize((160, 200), PIL.Image.BICUBIC).resize((320, 200), PIL.Image.NEAREST)
	img_w = 320
	img_h = 200
if not quiet:
	Show(im)

# Finde nächste Farbe jeweils auf YUV bezogen und zeige das an
px = im.getdata()
pxnearest = []
closestcolorindices = []
index_use_count = [0] * 16
pxyuv = []
for p in px:
	rgb = (p[0] * color_scale_factor, p[1] * color_scale_factor, p[2] * color_scale_factor)
	rgb = RemoveGammaCorrection(rgb)
	yuv = RGBToYUV(rgb)
	pxyuv += [yuv]
	# Finde passensten Index nach Farbzuordnung
	index = FindBestColorForYUV(yuv)
	pxnearest += [colors_c64_rgb[index]]
	closestcolorindices += [index]
	index_use_count[index] += 1
	
im.putdata(pxnearest)
if not quiet:
	Show(im)

# Zähle welche Farbe am häufigsten ist, bzw welche drei
num_most_used_indices = 1
fixindices = []
if charmode:
	num_most_used_indices = 3
	enable_mixing = False
elif spritemode:
	num_most_used_indices = 4
	enable_mixing = False
	fixindices += [spriteneutralindex]
	# add three lines of neutral colors to make sprite fit in block
	addlines = [colors_c64_yuv[spriteneutralindex]] * (24 * 3)
	pxyuv += addlines
	im = im.resize((24, 24), PIL.Image.NEAREST)
elif hiresmode:
	# We can chose two colors freely every char, no background color!
	num_most_used_indices = 0
fixindices += givencolors
if num_most_used_indices > len(fixindices):
	for j in range(0, num_most_used_indices - len(fixindices)):
		mui = 0
		for i in range(0, 16):
			if index_use_count[i] > index_use_count[mui] and i not in fixindices:
				mui = i
		fixindices += [mui]
print('Fix indices for image:', fixindices)

# Gehe dann über alle Blöcke und berechne jeweils ähnlichsten Block mit den
# festen und freien Farben unter Verwendung von Mischmustern.
stretchedcolors = [(0, 0, 0)] * len(pxyuv)
blocks = []
blockusecount = []
numblockstotal = 0
bitmapbytes = []	# Bytes für Bitmap
chardata = []		# Passende Character-Daten für Bitmap (0-255)
colordata = []		# Colorcode für Bitmap/Char 11 (Mit Bit4 als MC-Marker bei Char) (0-15)
backgroundindex = 0
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
# Zeige ideale Blöcke (für Bitmap schon Ergebnis)
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

# Im Charmode sortiere noch Blöcke aus (Verringere auf vorfügbare Zahl)
# Idealerweise Daten gleich als acme source ausgeben für's Einbinden!
# fixme hier wird direkt nach Farben geguckt, aber jeder vorhandene Block an Indices wäre auch ok,
# man kann ja einfach Farben tauschen! Wobei nur eine Farbe getauscht werden kann im char mode.
# das fehlt hier wohl noch!
if charmode:
	print('Num Chars initial',len(blocks),'of',numblockstotal)
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
	dfl = 'fixcolors\n!byte '
	dfl += hexstr(fixindices[0]) + ', ' + hexstr(fixindices[1]) + ', ' + hexstr(fixindices[2]) + '\n'
	dfl += '\n!align 255,0\ncharsetdata\n'
	if firstchar > 0:
		dfl += '!src "' + inputbasefilename + '_chardata0_' + str(firstchar-1) +'.a"\n'
	dfl += dumpbytes(charsetbytes)
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
			dfl += '\ntiledata_' + str(i) + '\n'
			nthcopy = []
			count = len(tiledata) // numtables
			for j in range(0, count):
				nthcopy += [tiledata[j * numtables + i]]
			dfl += dumpbytes(nthcopy)
	else:
		dfl += '\n!align 255,0\ntiledata\n'
		dfl += dumpbytes(tiledata)
	f = open(outputbasefilename + '_chardata.a','wt')
	f.writelines(dfl)
elif spritemode:
	# Sprite-mode, output the first 63 bytes as data, complete with one null byte to get 64 in total
	spritebytes = []
	for y in range(0, 21):
		yl = y // 8
		ysl = y % 8
		for x in range(0, 3):
			spritebytes += [sprite_recode_byte(bitmapbytes[yl * 24 + x * 8 + ysl], hiresmode)]
	spritebytes += [0]
	# Generate .a data file
	dfl = '!align 63, 0\n' + inputbasefilename + '_data\n'
	dfl += dumpbytes(spritebytes)
	f = open(outputbasefilename + '_sprdata.a','wt')
	f.writelines(dfl)
else:
	# Bitmap-Mode: Gebe Daten aus (als RGB Bild) und als PRG für Bitmap-Modus
	im.resize((320, 200), PIL.Image.NEAREST).save(outputbasefilename + '_c64.png')
	# Generate .a data file
	dfl = ''
	if not hiresmode:
		dfl += 'backgroundcolor\n!byte '
		dfl += hexstr(backgroundindex)
	dfl += '\n\nbitmapdata\n'
	dfl += dumpbytes(bitmapbytes)
	dfl += '\n\nchardata\n'
	dfl += dumpbytes(chardata)
	if not hiresmode:
		dfl += '\n\ncolordata\n'
		dfl += dumpbytes(colordata)
	f = open(outputbasefilename + '_bmpdata.a','wt')
	f.writelines(dfl)
	f.close()
	# Versuch: RLE-Encoding der Daten
	rlebytes0 = RLEncode(bitmapbytes)
	rlebytes1 = RLEncode(chardata)
	rlebytes2 = []
	if not hiresmode:
		rlebytes2 = RLEncode(colordata)
	totallen = len(rlebytes0)+len(rlebytes1)+len(rlebytes2)
	print('Total:',totallen,'bytes of 10000.')
	dfl = ''
	if not hiresmode:
		dfl += 'backgroundcolor\n!byte '
		dfl += hexstr(backgroundindex)
	dfl += '\n\nbitmapdata_rle\n'
	dfl += dumpbytes(rlebytes0)
	dfl += '\n\nchardata_rle\n'
	dfl += dumpbytes(rlebytes1)
	if not hiresmode:
		dfl += '\n\ncolordata_rle\n'
		dfl += dumpbytes(rlebytes2)
	f = open(outputbasefilename + '_bmpdata_rle.a','wt')
	f.writelines(dfl)
	f.close()

