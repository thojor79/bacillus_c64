#!/usr/bin/env python
# coding=utf8

# PC to C64 image data converter - GIMP plugin
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



# preprocess image data then.

# alpha values need to be converted to spare index after finding most used index,
# only replaced later.

# maybe add options for plugin like fixed color indices, char mode etc.


# It can be executed by selecting the menu option: 'Filters/C64fy'
# or by writing the following lines in the Python console (that can be opened with the
# menu option 'Filters/Python-Fu/Console'):
# >>> image = gimp.image_list()[0]
# >>> layer = image.layers[0]
# >>> gimp.pdb.python_fu_c64fy(image, layer)

from gimpfu import *
import c64fylib
#from array import array

# for debug output
#import sys
#sys.stderr = open('./gimpstderr.txt', 'w')
#sys.stdout = open('./gimpstdout.txt', 'w')

def c64fy(img, layer, fix_index_0, fix_index_1, fix_index_2, hiresmode, multicolorscaledown, enable_dithering, enable_mixing) :
	''' Converts a layer to a C64 compatible bitmap format (RGB or RGBA).
	Horizontally two pixels are merged.
	
	Parameters:
	img : image The current image.
	layer : layer The layer of the image that is selected.
	'''

	color_scale_factor = 1.0 / 255.0		# Color scaling 0-255 to 0.0...1.0
	maxchars = 256
	dynamic_uv_grey_limit = False   # Adjust it automatically?
	uv_dist_limit = 0.2	 # max UV distance to 0
	adjust_uv = False	   # helps for some images
	uv_limit_grey = 0.05	# UV distance below this is considered as grey value
	charmode = False

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
	
	# Create pixel regions - doesn't work on assignment and is NOT faster
	#source_region = layer.get_pixel_rgn(0, 0, layer.width, layer.height, False, False)
	#source_pixels = array("B", source_region[0:layer.width, 0:layer.height])
	#dest_region = newLayer.get_pixel_rgn(0, 0, layer.width, layer.height, True, True)
	#pixel_size = len(source_region[0,0])
	#dest_pixels = array("B", "\x00" * (layer.width * layer.height * pixel_size))
	
	try:
		# Convert all pixels to closest C64 color index and count mostly used index
		# fixme: by accessing tiles it would be faster than get_pixel, but images that are
		# not multiple sizes of (64,64) (tile size) we can't access the outer pixels.
		# Reading the pixels seems to be super slow!
		index_use = [0] * 16
		pixels_yuv = []
		has_transparent_pixels = False
		tiles_x = layer.width // 8
		tiles_y = layer.height // 8
		has_alpha = False
		for ty in range(tiles_y * 8):
			for tx in range(tiles_x * 8):
				gimp.progress_update(float(ty*tiles_x*8 + tx) * 0.5 / float(tiles_x*tiles_y*64))
				#source_pos = (tx + ty * layer.width) * pixel_size
				#pixel = source_pixels[source_pos : source_pos + pixel_size]
				pixel = layer.get_pixel(tx, ty)
				if len(pixel) > 3:
					has_alpha = True
				if has_alpha and pixel[3] * color_scale_factor < 0.5:
					# transparent pixel
					pixels_yuv += [(-1.0, -1.0, -1.0)]
					has_transparent_pixels = True
				else:
					rgb = (pixel[0] * color_scale_factor, pixel[1] * color_scale_factor, pixel[2] * color_scale_factor)
					rgb = c64fylib.RemoveGammaCorrection(rgb)
					yuv = c64fylib.RGBToYUV(rgb)
					index = c64fylib.FindBestColorForYUV(yuv, uv_limit_grey)
					index_use[index] += 1
					pixels_yuv += [yuv]
		# If image has alpha and we have transparent pixels, use these as first fix color.
		# Replace them by least used color index
		most_used_index = 16
		if has_transparent_pixels:
			least_used_index = 16
			least_index_use = layer.width * layer.height
			for i in range(0, 16):
				if index_use[i] < least_index_use:
					least_index_use = index_use[i]
					least_used_index = i
			most_used_index = least_used_index
		else:
			most_index_use = 0
			for i in range(0, 16):
				if index_use[i] > most_index_use:
					most_index_use = index_use[i]
					most_used_index = i

		fixed_indices = [most_used_index]
		givenindices = []
		fix_index_0 = int(fix_index_0)
		fix_index_1 = int(fix_index_1)
		fix_index_2 = int(fix_index_2)
		if fix_index_0 >= 0 and fix_index_0 <= 15:
			givenindices += [fix_index_0]
		if fix_index_1 >= 0 and fix_index_1 <= 15:
			givenindices += [fix_index_1]
		if fix_index_2 >= 0 and fix_index_2 <= 15:
			givenindices += [fix_index_2]
		if len(givenindices) > 0:
			# with transparency, just add them
			fixed_indices += givenindices
		else:
			# replace detected indices
			fixed_indices = givenindices

		for ty in range(tiles_y):
			for tx in range(tiles_x):
				# Update the progress bar.
				gimp.progress_update(0.5 + float(ty*tiles_x + tx) * 0.5 / float(tiles_x*tiles_y))
				colorblock = []
				for yy in range(0, 8):
					for xx in range(0, 8):
						yuv = pixels_yuv[(ty*8+yy)*(tiles_x*8)+tx*8+xx]
						if has_transparent_pixels and yuv[0] < -0.5:
							yuv = c64fylib.colors_c64_yuv[most_used_index]
						colorblock += [yuv]
				color_indices = c64fylib.GenerateBestBlock(colorblock, fixed_indices, charmode, hiresmode, multicolorscaledown, enable_dithering, uv_limit_grey)[0]
				for yy in range(0, 8):
					for xx in range(0, 8):
						color_index = color_indices[yy*8+xx]
						pixel = (0, 0, 0, 0)
						if not has_transparent_pixels or color_index != most_used_index:
							yuv = c64fylib.colors_c64_yuv[color_index]
							rgb = c64fylib.YUVToRGB(yuv)
							rgb = c64fylib.AddGammaCorrection(rgb)
							r = int(rgb[0] / color_scale_factor)
							g = int(rgb[1] / color_scale_factor)
							b = int(rgb[2] / color_scale_factor)
							if has_alpha:
								pixel = (r, g, b, 255)
							else:
								pixel = (r, g, b)
						#dest_pos = (tx*8+xx + (ty*8+yy) * layer.width) * pixel_size
						#dest_pixels[dest_pos : dest_pos + pixel_size] = pixel2
						newLayer.set_pixel(tx*8+xx, ty*8+yy, pixel)

		# Copy array to pixel region
		#dest_region[0:layer.width, 0:layer.height] = dest_pixels.tostring() 

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
	[
		# Char mode doesn't make sense for plugin, nor sprite mode
		# Outputting data isn't needed then.
		(PF_SLIDER, "fix_index_0", "Fix color index 0", -1, (-1, 15, -1)),
		(PF_SLIDER, "fix_index_1", "Fix color index 1", -1, (-1, 15, -1)),
		(PF_SLIDER, "fix_index_2", "Fix color index 2", -1, (-1, 15, -1)),
		(PF_OPTION, "hiresmode", "HiRes mode:", 0, ["no", "yes"]),
		(PF_OPTION, "multicolorscaledown", "Scale down for multicolor:", 1, ["no", "yes"]),
		(PF_OPTION, "enable_dithering", "Enable dithering:", 1, ["no", "yes"]),
		(PF_OPTION, "enable_mixing", "Enable color mixing:", 0, ["no", "yes"])	# fixme: implement
		#(PF_FILE, "filepath", "Output Filepath", ""),
		#(PF_DIRNAME, "directory", "Output Directory", ""),
	],
	[],
	c64fy)

main()
