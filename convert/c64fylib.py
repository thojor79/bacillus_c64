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

import random
import math
import sys

#
# Functions to generate static tables
#
def GenerateC64ColorsYUV():
	''' Generate list with YUV values for every C64 color index.
		Could be later extended to also store color mixing YUV values (7+7 more colors)
	'''
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
	return colors_c64_yuv

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
	
def GenerateIndexToIndexErrorTable(colors_c64_yuv):
	# Prepare table with error values
	index_to_index_error = []
	for y in range(0, 16):
		for x in range(0, 16):
			index_to_index_error += [ErrorInYUV(colors_c64_yuv[x], colors_c64_yuv[y])]
	return index_to_index_error

#
# Static tables
#
colors_c64_yuv = GenerateC64ColorsYUV()
index_to_index_error = GenerateIndexToIndexErrorTable(colors_c64_yuv)

#
# Color conversion functions
#
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
	r = y +	                   + (v - 0.5) *  1.140
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

def FindBestColorForYUV(yuv, uv_limit_grey):
	index = 16
	minerror = sys.float_info.max
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

def FindBestTwoColorsForYUV(yuv, available_indices, uv_limit_grey):
	index = 16
	index2 = 16
	minerror = sys.float_info.max
	minerror2 = sys.float_info.max
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

def ComputeBestColorOfTwo(yuv, best_two_colors, enable_dithering):
	indexresult = best_two_colors[0]
	if enable_dithering and best_two_colors[1] != 16:
		errormf = ComputeMixFactorAndDistance(yuv, best_two_colors[0], best_two_colors[1])
		# Larger mixfactor means rather 2nd color (index1), and as larger the random range is
		if enable_dithering:
			r = random.random()
			if r < errormf[1]:
				indexresult = best_two_colors[1]
	return indexresult

def FindBestLowIndexColor(index):
	minerror = sys.float_info.max
	lowindex = 16
	for i in range(0, 8):
		error = index_to_index_error[i*16+index]
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
	if index0 == index1:
		return (0.0, 0.0)
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

# fixme offer function to find most used color(s) also handling alpha channel!		
		
def GenerateBestBlock(colorblock, fixed_indices, charmode, hiresmode, enable_dithering, uv_limit_grey):
	''' This is the core function of the converter. Convert a YUV color block of 8x8 pixels to C64 indices according to format.
		In multicolor mode two pixels horizontally are merged.
		Depending on mode 0-3 colors can be chosen freely, so already fix colors are given (1-4).
		In charmode the only free color may come only from indices 0-7.
		In hires mode we have two free colors (or zero for sprites).
		In multicolor mode, three colors can be chosen freely.
		For charmode iterate over all free colors with index 0-7 and compare block in hires,
		this means compute error to original.
		Note! Maybe later try also color mixing if there are free colors in the block or the used colors in a block
		allow for mixing. Then some input pixels can be represented better.
	'''
	inputblock = colorblock
	num_free_indices = 4 - len(fixed_indices)
	if hiresmode:
		num_free_indices = 2 - len(fixed_indices)
	lowcolorblockerror = sys.float_info.max
	resultindiceslowcolor = []
	lowindex = 16
	if charmode:
		# Find most used color except background in block and use this for comparison
		index_count = [0] * 16
		for i in range(0, 8*8):
			yuv = inputblock[i]
			index = FindBestColorForYUV(yuv, uv_limit_grey)
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
			resultindiceslowcolor += [idx]
			blockerror += min(error0, error1)
		# Half error for comparison with multicolor
		lowcolorblockerror = blockerror * 0.5
	# For multicolor half x resolution!
	if not hiresmode:
		inputblock = BlockHiResToMultiColor(colorblock)
	resultindices = []
	# For every pixel find the two most similar colors and the best mix between them to represent the
	# original color. Either take the best color or mix between the two.
	# Account the finally chosen color for index use counting.
	index_use_count = [0] * 16
	for yuv in inputblock:
		# Find best matching two colors
		btc = FindBestTwoColorsForYUV(yuv, [], uv_limit_grey)
		# Compute best match between them
		indexresult = ComputeBestColorOfTwo(yuv, btc, enable_dithering)
		# Account color index
		index_use_count[indexresult] += 1
	#print(index_use_count)
	# Now take the most used colors that are not already available and set them as fixed colors.
	# Afterwards replace every color that can not be represented by available colors, also with mixing.
	# Take most used color as fix color for this block if there are still free colors available.
	# Color is put at back of fixed_indices so it isn't reused.
	fixed_indices_this_block = list(fixed_indices)
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
				if mui not in fixed_indices_this_block:
					fixed_indices_this_block += [mui]
			else:
				fixed_indices_this_block += [mui]
	# Now fill up fixed_indices_this_block to have always 2 or 4 colors.
	num_free_indices = 4 - len(fixed_indices_this_block)
	if hiresmode:
		num_free_indices = 2 - len(fixed_indices_this_block)
	if num_free_indices > 0:
		# We can chose the remaining indices freely, it doesn't matter.
		# However if we chose a color that is already fixed, rather new
		# indices would be used, which is bad for reuse. So add only
		# indices, that are NOT already used
		for nfi in range(0, num_free_indices):
			for ic in range(0, 16):
				if ic not in fixed_indices_this_block:
					fixed_indices_this_block += [ic]
					break
		# so do NOT:
		#fixed_indices_this_block += [0] * num_free_indices
	# For every pixel determine best two colors from available colors of this block.
	# Compute segment in color-3-space between the two and determine closest position to segment for
	# the given color. The segment parameter determines mixing factor.
	randfactorn = 0
	anycolorblockerror = 0.0
	for yuv in inputblock:
		# Find best two colors out of available ones
		btc = FindBestTwoColorsForYUV(yuv, fixed_indices_this_block, uv_limit_grey)
		indexresult = ComputeBestColorOfTwo(yuv, btc, enable_dithering)
		if charmode:
			anycolorblockerror += ErrorInYUV(yuv, colors_c64_yuv[indexresult])
		resultindices += [indexresult]
	# Put out data
	resultbytes = []
	if charmode and lowcolorblockerror < anycolorblockerror:
		#print('use low color block',lowcolorblockerror,'<',anycolorblockerror)
		resultindices = resultindiceslowcolor
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
		# A block is always 8 bytes (8x8 pixel or 4x8 in multicolor).
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
		resultindices = BlockMultiColorToHiRes(resultindices)
		if charmode and fixed_indices_this_block[3] < 8:
			fixed_indices_this_block[3] += 8	# Set multicolor flag
	# Return image data, encoded bytes and colors used for this block
	return (resultindices, resultbytes, fixed_indices_this_block)
