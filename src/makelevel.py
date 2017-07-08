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

random.seed()

# Bild laden
if len(sys.argv) < 2:
	print 'Usage: ', sys.argv[0], ' [Options] INPUTFILENAME'
	sys.exit(1)
inputfilename = sys.argv[len(sys.argv) - 1]

im = Image.open(inputfilename)
img_w = im.size[0]
img_h = im.size[1]

# Konfiguration der Tiles
background_size = (2,2)
background_tiles = [(0,1,2,3)]
floor_size = (2,1)
floor_tiles = [(8,9), (10,11), (12,13)]
floor_hole_tiles = [(14,15)]
obstacleA_size = (2,2)
obstacleA_tiles = [(16,17,18,19)]
obstacleB_size = (2,1)
obstacleB_tiles = [(20,21), (22,23)]
island_size = (2,1)
island_tiles = [(24,25), (26,27)]
background_anim_size = (1,1)
background_anim_tiles = [[4]]
bonus_size = (1,1)
bonus_tiles = [[5],[6],[7]]
leveldata = [0] * (img_w * img_h)
print 'Generating',img_w,'*',img_h,'tiles.'

def is_first(x, y, sz):
	return (x / sz[0]) * sz[0] == x and (y / sz[1]) * sz[1] == y

def put_ld(x, y, sz, d):
	for yy in range(0, sz[1]):
		for xx in range(0, sz[0]):
			leveldata[(y+yy)*img_w+(x+xx)] = d[yy*sz[0]+xx]

px = im.getdata()
nr = 0

# fill in background data everywhere
for y in range(0, img_h):
	for x in range(0, img_w):
		if is_first(x, y, background_size):
			random.seed(x+y)
			nr = int(random.random() * len(background_tiles))
			put_ld(x, y, background_size, background_tiles[nr])

# Lese Pixeldaten aus Bild und generiere passende Tile-Daten
actor_nr = 1
for y in range(0, img_h):
	for x in range(0, img_w):
		rgb = px[y * img_w + x]
		mrgb = max(rgb[0], rgb[1], rgb[2])
		random.seed(x+y)
		# background is black, skip it
		if mrgb < 16:
			continue
		# if all colors are the same we have actors
		elif rgb[0] == rgb[1] and rgb[1] == rgb[2]:
			# position dependant randomness ?
			# at most 16 types...
			actor_type = rgb[0] / 16 - 1 # from level map
			if actor_type > 0:
				actor_type = actor_nr
				actor_nr += 1
				if actor_nr > 15:
					actor_nr = 1
				#actor_type = (x * 3 + y * 7) & 15 # by position
				#if actor_type == 0:
				#	actor_type = 1
			leveldata[y*img_w+x] = leveldata[y*img_w+x] - background_tiles[0][0] + 128 + actor_type * 8
		# floor is red, orange gaps
		elif rgb[0] == mrgb:
			if rgb[1] == rgb[0]:
				nr = int(random.random() * len(bonus_tiles))
				put_ld(x, y, bonus_size, bonus_tiles[nr])
				# yellow are boni
			elif is_first(x, y, floor_size):
				if rgb[1] >= 128:
					nr = int(random.random() * len(floor_hole_tiles))
					put_ld(x, y, floor_size, floor_hole_tiles[nr])
				else:
					nr = int(random.random() * len(floor_tiles))
					put_ld(x, y, floor_size, floor_tiles[nr])
		# obstacles are green
		elif rgb[1] == mrgb:
			if rgb[2] == mrgb:
				# background animation tiles are cyan
				if is_first(x, y, background_anim_size):
					nr = int(random.random() * len(background_anim_tiles))
					put_ld(x, y, background_anim_size, background_anim_tiles[nr])
			else:
				if rgb[1] >= 128:
					if is_first(x, y, obstacleA_size):
						nr = int(random.random() * len(obstacleA_tiles))
						put_ld(x, y, obstacleA_size, obstacleA_tiles[nr])
				else:
					if is_first(x, y, obstacleB_size):
						nr = int(random.random() * len(obstacleB_tiles))
						put_ld(x, y, obstacleB_size, obstacleB_tiles[nr])
		# islands are blue
		elif rgb[2] == mrgb:
			if is_first(x, y, island_size):
				nr = int(random.random() * len(island_tiles))
				put_ld(x, y, island_size, island_tiles[nr])

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

# Generate .a data file
dfl = '' # 'leveldata\n'
dfl += dumpbytes(leveldata)
dfl += '\n'
f = open(inputfilename + '_lvldata.a','wt')
f.writelines(dfl)

