#!/usr/bin/env python
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

# fixme: generation of char makes strange pixels in upper left corner of every block!
# it could be a bug or maybe it is normal. a block with that feature could be the most
# similar because it has free colors... difficult to check.
# maybe force keeping of one monocolor block per fix color >= 8
# it seems this is no bug, the pixels are in varying positions, depending on image

# It can be executed by selecting the menu option: 'Filters/C64fy'
# or by writing the following lines in the Python console (that can be opened with the
# menu option 'Filters/Python-Fu/Console'):
# >>> image = gimp.image_list()[0]
# >>> layer = image.layers[0]
# >>> gimp.pdb.python_fu_c64fy(image, layer)

from gimpfu import *
import random

enable_mixing = True    # Enable color mixing
infinity = 1000000000.0
default_uv_color_distance = 0.1333333
color_scale_factor = 1.0 / 255.0
uv_limit_grey = 0.05    # UV distance below this is considered as grey value

colors_y_uvangle = [
    (0, -1),		# black
    (32, -1),		# white
    (10, 5),		# red
    (20, 13),		# cyan
    (12, 2),		# purple
    (16, 10),		# green
    (8, 0),		# blue
    (24, 8),		# yellow
    (12, 6),		# orange
    (8, 7),		# brown
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

# Prepare table with error values
index_to_index_error = []
for y in range(0, 16):
	for x in range(0, 16):
		index_to_index_error += [ErrorInYUV(colors_c64_yuv[x], colors_c64_yuv[y])]

def ComputeBlockError(b0, b1):
	error = 0.0
	for i in range(0, len(b0)):
		error += index_to_index_error[b0[i] * 16 + b1[i]]
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

def GenerateBestBlock(colorblock, fixed_index):
	# For multicolor half x resolution!
	inputblock = BlockHiResToMultiColor(colorblock)
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
	# Now take the most used colors that are not already available and set them as fixed colors.
	# Afterwards replace every color that can not be represented by available colors, also with mixing.
	# Take most used color as fix color for this block if there are still free colors available.
	# Color is put at back of fixed_indices so it isn't reused.
	fixed_indices_this_block = [fixed_index]
	for i in range(0, 3):
		mui = 16
		maxcount = 0
		for j in range(0, 16):
			if j not in fixed_indices_this_block:
				if index_use_count[j] > maxcount:
					maxcount = index_use_count[j]
					mui = j
		if mui != 16:
			fixed_indices_this_block += [mui]
	# For every pixel determine best two colors from available colors of this block.
	# Compute segment in color-3-space between the two and determine closest position to segment for
	# the given color. The segment parameter determines mixing factor.
	randfactorn = 0
	anycolorblockerror = 0.0
	for yuv in inputblock:
		# Find best two colors out of available ones
		btc = FindBestTwoColorsForYUV(yuv, fixed_indices_this_block)	# fixme list length < 4 ok?
		indexresult = ComputeBestColorOfTwo(yuv, btc)
		resultindices += [indexresult]
	resultindices = BlockMultiColorToHiRes(resultindices)
	return resultindices

def c64fy(img, layer) :
    ''' Converts a layer to a C64 compatible bitmap format (RGB or RGBA).
    Horizontally two pixels are merged.
    
    Parameters:
    img : image The current image.
    layer : layer The layer of the image that is selected.
    '''
    # Indicates that the process has started.
    gimp.progress_init("C64fying " + layer.name + "...")

    # Set up an undo group, so the operation will be undone in one step.
    pdb.gimp_image_undo_group_start(img)

    # Get the layer position.
    pos = 0;
    for i in range(len(img.layers)):
        if(img.layers[i] == layer):
            pos = i
    
    # Create a new layer to save the results (otherwise is not possible to undo the operation).
    newLayer = gimp.Layer(img, layer.name + " c64fied", layer.width, layer.height, layer.type, layer.opacity, layer.mode)
    img.add_layer(newLayer, pos)
    layerName = layer.name
    
    # Clear the new layer.
    pdb.gimp_edit_clear(newLayer)
    newLayer.flush()
    
    # fixme check for existence of alpha channel. need to add alpha value of pixel from input to output!
    # as best change alpha to transparent or not transparent switch, and treat all transparent pixels
    # like one color that is NOT used in the image (or used at least). For these pixels store that index,
    # then convert normally. Force background color (fix index) to be that color!
    # Later set all pixels back to transparent that use this color.
    
    try:
        # Convert all pixels to closest C64 color index and count mostly used index
        # fixme: by accessing tiles it would be faster than get_pixel, but images that are
        # not multiple sizes of (64,64) (tile size) we can't access the outer pixels.
        index_use = [0] * 16
        for ty in range(layer.height):
            for tx in range(layer.width):
            	pixel = layer.get_pixel(tx, ty)
            	rgb = (pixel[0] * color_scale_factor, pixel[1] * color_scale_factor, pixel[2] * color_scale_factor)
                rgb = RemoveGammaCorrection(rgb)
                yuv = RGBToYUV(rgb)
                index = FindBestColorForYUV(yuv)
                index_use[index] += 1
        most_used_index = 16
        most_index_use = 0
        for i in range(0, 16):
            if index_use[i] > most_index_use:
                most_index_use = index_use[i]
                most_used_index = i
        
        tiles_x = layer.width // 8
        tiles_y = layer.height // 8
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                # Update the progress bar.
                gimp.progress_update(float(ty*tiles_x + tx) / float(tiles_x*tiles_y))
                colorblock = []
                for yy in range(0, 8):
      		    for xx in range(0, 8):
	            	pixel = layer.get_pixel(tx*8+xx, ty*8+yy)
        	    	rgb = (pixel[0] * color_scale_factor, pixel[1] * color_scale_factor, pixel[2] * color_scale_factor)
        		rgb = RemoveGammaCorrection(rgb)
        		yuv = RGBToYUV(rgb)
        		colorblock += [yuv]
		color_indices = GenerateBestBlock(colorblock, most_used_index)
                for yy in range(0, 8):
       		    for xx in range(0, 8):
       		    	yuv = colors_c64_yuv[color_indices[yy*8+xx]]
                        rgb = YUVToRGB(yuv)
       	                rgb = AddGammaCorrection(rgb)
			# fixme handle transparent background like own color!                       
                        # If the image has an alpha channel (or any other channel) copy his values.
       	                #if(len(pixel) > 3):
               	        #    for k in range(len(pixel)-3):
                       	#        res += pixel[k+3]
                       	pixel = (int(rgb[0] / color_scale_factor), int(rgb[1] / color_scale_factor), int(rgb[2] / color_scale_factor))
                       	newLayer.set_pixel(tx*8+xx, ty*8+yy, pixel)
        
        # Update the new layer.
        newLayer.flush()
        newLayer.merge_shadow(True)
        newLayer.update(0, 0, newLayer.width, newLayer.height)
        
        # Remove the old layer.
        img.remove_layer(layer)
        
        # Change the name of the new layer (two layers can not have the same name).
        newLayer.name = layerName
    except Exception as err:
        gimp.message("Unexpected error: " + str(err))
    
    # Close the undo group.
    pdb.gimp_image_undo_group_end(img)
    
    # End progress.
    pdb.gimp_progress_end()

register(
    "python_fu_c64fy",
    "C64fy image",
    "Converts a layer to C64 multicolor bitmap compatible format.",
    "Thorsten Jordan",
    "Open source (GPL v2)",
    "2017",
    "<Image>/Filters/C64fy",
    "RGB, RGB*",
    [],
    [],
    c64fy)

main()
