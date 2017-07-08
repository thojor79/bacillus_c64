#!/usr/bin/python
# coding=utf8
import Image
import random
import sys
import colorsys
import math

# Farben des C64
colors = [
(0x00, 0x00, 0x00),
(0xFF, 0xFF, 0xFF),
(0x68, 0x37, 0x2B),
(0x70, 0xA4, 0xB2),
(0x6F, 0x3D, 0x86),
(0x58, 0x8D, 0x43),
(0x35, 0x28, 0x79),
(0xB8, 0xC7, 0x6F),
(0x6F, 0x4F, 0x25),
(0x43, 0x39, 0x00),
(0x9A, 0x67, 0x59),
(0x44, 0x44, 0x44),
(0x6C, 0x6C, 0x6C),
(0x9A, 0xD2, 0x84),
(0x6C, 0x5E, 0xB5),
(0x95, 0x95, 0x95) ]

# Grautöne und Farben als Indizes
cigrey = [0, 11, 12, 15, 1]
cicolors = [2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14]

# Farbskalierung
cf = 1.0 / 255.0

infinity = 1000000000.0

meansat = 0.0	# fixme: braucht man das noch? nein, eher nicht

# Farben umrechnen in RGB / HLS / YIQ Farbräume
colors_rgb = []
colors_hls = []
colors_yiq = []
for x in range(0, 16):
	r = colors[x][0] * cf
	g = colors[x][1] * cf
	b = colors[x][2] * cf
	colors_rgb += [(r, g, b)]
	colors_hls += [colorsys.rgb_to_hls(r, g, b)]
	colors_yiq += [colorsys.rgb_to_yiq(r, g, b)]
	# HLS-Farben anpassen
	if x in cicolors and colors_hls[x][1] > 0.5: # Test, zu helle Farben umplatzieren (gelb/hellgrün)
		colors_hls[x] = (colors_hls[x][0], 0.5, colors_hls[x][2])

#fixme: obsolet?
def MixColor(c1, c2, f):
	c = [0, 0, 0]
	for i in range(0, 3):
		c[i] = (c1[i] * (256 - f) + c2[i] * f) / 256
	return (c[0], c[1], c[2])

def NearestColorIndices_NEW(deltas):
	mind0 = infinity
	mind1 = infinity
	i0 = 0
	i1 = 0
	for i in range(0, len(deltas)):
		d = deltas[i]
		if d < mind0:
			i1 = i0
			mind1 = mind0
			i0 = i
			mind0 = d
		elif d < mind1:
			i1 = i
			mind1 = d
	f = mind0 / (mind0 + mind1)
	return (i0, i1, f)

def ComputeDeltasRGB(c):
	r = c[0] * cf
	g = c[1] * cf
	b = c[2] * cf
	deltas = []
	for i in colors_rgb:
		dr = r - i[0]
		dg = g - i[1]
		db = b - i[2]
		d = math.sqrt(dr*dr + dg*dg + db*db)
		deltas += [d]
	return deltas

def ComputeDeltasYIQ(c):
	yiq = colorsys.rgb_to_yiq(c[0] * cf, c[1] * cf, c[2] * cf)
	deltas = []
	for i in range(0, 16):
		a0 = yiq[0] - colors_yiq[i][0]
		a1 = yiq[1] - colors_yiq[i][1]
		a2 = yiq[2] - colors_yiq[i][2]
		# Y geht von 0...1, IQ aber von -1...1, daher a0 ggf. skalieren
		# theoretisch *2, aber damit wird es eher schlechter, mit 0.5 wird
		# es eher besser, also bei 1.0 lassen
		# a0 *= 2.0
		d = math.sqrt(a0*a0 + a1*a1 + a2*a2)
		if math.sqrt(yiq[1]*yiq[1] + yiq[2]*yiq[2]) < 0.01 and i not in cigrey:
			# Grauwerte nur auf Grau mappen
			d = infinity
		deltas += [d]
	return deltas

def ComputeDeltasHLS(c):
	hls = colorsys.rgb_to_hls(c[0] * cf, c[1] * cf, c[2] * cf)
	deltas = [infinity] * len(colors_hls)
	#  wenn Sättigung gering, wähle passenden Grauwert, sonst nächste und zweitnächste farbe in HL Ebene,
	# dort auch schwarz + weiß als Farben zulassen (Linien in Ebene quasi)
	if hls[2] < 0.25: # meansat:	# taugt auch nicht bei jedem Bild, fixme, gibt teilweise seltsam grau in hlsrgb, abs. evtl besser
		# Grauwert
		# fixme: gibt so keinen glatten Verlauf!
		for i in cigrey:
			# hier könnte man eher sagen, die (zweit)nächste Farbe je nach L-Wert
			deltas[i] = abs(colors_hls[i][1] - hls[1])
	else:
		for i in cicolors:
			dh = abs(colorshls2[i][0] - hls[0])
			if dh > 0.5:	# hue vergleich mit wrap!
				dh = 1.0 - dh
			dl = abs(colorshls2[i][1] - hls[1])
			deltas[i] = math.sqrt(dh*dh + dl*dl)
		bwf = 1.0 # 2 theoretisch besser, aber Abstandsrechnung dann evtl. anders
		# schwarz
		deltas[0] = hls[1] * bwf
		# weiß
		deltas[1] = (1.0 - hls[1]) * bwf
	return deltas

def CombineDeltas(deltas0, deltas1, f0, f1):
	deltas = []
	for i in range(0, len(deltas0)):
		deltas += [deltas0[i] * f0 + deltas1[i] * f1]
	return deltas







colorshls2 = []
for x in range(0, 16):
	print x, colorsys.rgb_to_hls(colors[x][0] * cf, colors[x][1] * cf, colors[x][2] * cf)
	colorshls2 += [colorsys.rgb_to_hls(colors[x][0] * cf, colors[x][1] * cf, colors[x][2] * cf)]
	if x in cicolors and colorshls2[x][1] > 0.5: # Test, zu helle Farben umplatzieren (gelb/hellgrün)
		print x,colorshls2[x][1]
		colorshls2[x] = (colorshls2[x][0], 0.5, colorshls2[x][2])

# H-Werte für rot,grün,blau,lila,türkis
# macht das Ergebnis aber nicht wirklich besser, eher schlechter, evtl noch besser platzieren bzw HLS-Werte tunen,
# scheint aber nicht viel zu bringen
if False:
	colorshls2[2] = (0.0/6, 0.33, colorshls2[2][2])	# rot
	colorshls2[3] = (3.0/6, 0.33, colorshls2[3][2])	# türkis
	colorshls2[4] = (5.0/6, 0.33, colorshls2[4][2])	# lila
	colorshls2[5] = (2.0/6, 0.33, colorshls2[5][2])	# grün
	colorshls2[6] = (4.0/6, 0.33, colorshls2[6][2])	# blau
	colorshls2[7] = (1.0/6, 0.45, colorshls2[7][2])	# gelb
	colorshls2[8] = (0.5/6, 0.33, colorshls2[8][2])	# orange
	colorshls2[9] = (0.5/6, 0.25, colorshls2[9][2])	# braun
	colorshls2[10] = (0.0/6, 0.6, colorshls2[10][2])	# hellrot
	colorshls2[13] = (2.0/6, 0.6, colorshls2[13][2])	# hellgrün
	colorshls2[14] = (4.0/6, 0.6, colorshls2[14][2])	# hellblau
	# eventuell einige Grauwerte als Farben in HL Ebene platzieren! fixme

if False:
	im = Image.open('hls.png')
	print len(im.getdata())
	p = []
	p2 = []
	p3 = []
	p4 = []
	p5 = []
	for y in range(0, 256):
		for x in range(0, 256):
			s = colorsys.hls_to_rgb(x / 255.0, y / 255.0, 1.0)
			p += [(int(s[0] * 255), int(s[1] * 255), int(s[2] * 255))]
			s = colorsys.hls_to_rgb(x / 255.0, 0.5, y / 255.0)
			p2 += [(int(s[0] * 255), int(s[1] * 255), int(s[2] * 255))]
			s = colorsys.hls_to_rgb(0.0, x / 255.0, y / 255.0)
			p3 += [(int(s[0] * 255), int(s[1] * 255), int(s[2] * 255))]
			s = colorsys.yiq_to_rgb(0.0, x / 255.0 * 2 - 1, y / 255.0 * 2 - 1)
			p4 += [(int(s[0] * 255), int(s[1] * 255), int(s[2] * 255))]
			s = colorsys.yiq_to_rgb(x / 255.0, 0.0, 0.0)
			p5 += [(int(s[0] * 255), int(s[1] * 255), int(s[2] * 255))]
	im.putdata(p)
	im.save('hlsrgb.png')
	im.putdata(p2)
	im.save('hlsrgb_HS.png')
	im.putdata(p3)
	im.save('hlsrgb_LS.png')
	im.putdata(p4)
	im.save('yiq.png')
	im.putdata(p5)
	im.save('yiq2.png')
	p = [(0,0,0)] * 65536
	for i in range(0, 16):
		x = int(colorshls2[i][0] * 255)
		y = int(colorshls2[i][1] * 255)
		p[y*256+x] = colors[i] # (255,255,255)
	im.putdata(p)
	im.save('hlsrgb2.png')


colorshls = []
for x in range(0, 16):
	colorshls += [(colorsys.rgb_to_hls(colors[x][0] * cf, colors[x][1] * cf, colors[x][2] * cf), (x,x))]
	for y in range(x+1, 16):
		c = MixColor(colors[x], colors[y], 128)
		colorshls += [(colorsys.rgb_to_hls(c[0] * cf, c[1] * cf, c[2] * cf), (x, y))]

def Show(im):
	if len(sys.argv) == 2:
		im2 = im.resize((320*2, 200*2), Image.NEAREST)
		im2.show()

def CompareHls(hls1, c2):
	# RGB Vergleich, war gar nicht so schlecht!
	c1 = colorsys.hls_to_rgb(hls1[0], hls1[1], hls1[2])
	d = 0
	for i in range(0, 3):
		x1 = c1[i] * 255
		x2 = c2[i]
		x = 0
		if x1 > x2:
			x = x1 - x2
		else:
			x = x2 - x1
		#d += x * x
		d += x
	return d

def CompareHls2(i, c):
	hls1 = colorshls2[i]
	hls2 = c
	dh = abs(hls1[0] - hls2[0])
	# hue vergleich mit wrap!
	if dh > 0.5:
		dh = 1.0 - dh
	dl = abs(hls1[1] - hls2[1])
	ds = abs(hls1[2] - hls2[2])
	# irgendwie muß L noch stärker beachtet werden...
	if hls2[2] > meansat:
		if hls1[2] < 0.2:
			return 2.0 + dh * 2 + dl
		else:
			return dh * 2 + dl
	else:
		if hls1[2] < 0.2:
			return dl * 2
		else:
			return 2 + dl * 2

def NearestColor2(c):
	hls = colorsys.rgb_to_hls(c[0] * cf, c[1] * cf, c[2] * cf)
	mind0 = 100000000
	mind1 = 100000000
	i0 = 0
	i1 = 0
	mind = 100000000
	mindi = 0
	#  wenn Sättigung gering, wähle passenden Grauwert, sonst nächste und zweitnächste farbe in HL Ebene,
	# dort auch schwarz + weiß als Farben zulassen (Linien in Ebene quasi)
	if hls[2] < 0.25: # meansat:	# taugt auch nicht bei jedem Bild, fixme, gibt teilweise seltsam grau in hlsrgb, abs. evtl besser
		# Grauwert
		# fixme: gibt so keinen glatten Verlauf!
		for i in cigrey:
			# hier könnte man eher sagen, die (zweit)nächste Farbe je nach L-Wert
			d = abs(colorshls2[i][1] - hls[1])
			if d < mind0:
				i1 = i0
				mind1 = mind0
				i0 = i
				mind0 = d
			elif d < mind1:
				i1 = i
				mind1 = d
	else:
		for i in cicolors:
			dh = abs(colorshls2[i][0] - hls[0])
			if dh > 0.5:	# hue vergleich mit wrap!
				dh = 1.0 - dh
			dl = abs(colorshls2[i][1] - hls[1])
			d = math.sqrt(dh*dh + dl*dl)
			if d < mind0:
				i1 = i0
				mind1 = mind0
				i0 = i
				mind0 = d
			elif d < mind1:
				i1 = i
				mind1 = d
		bwf = 1.0 # 2 theoretisch besser, aber Abstandsrechnung dann evtl. anders
		# schwarz
		d = hls[1] * bwf
		if d < mind0:
			i1 = i0
			mind1 = mind0
			i0 = 0
			mind0 = d
		elif d < mind1:
			i1 = 0
			mind1 = d
		# weiß
		d = (1.0 - hls[1]) * bwf
		if d < mind0:
			i1 = i0
			mind1 = mind0
			i0 = 1
			mind0 = d
		elif d < mind1:
			i1 = 1
			mind1 = d
	# Faktor berechnen
	f = mind0 / (mind0 + mind1)
	return (i0, i1, f)

def NearestColorIndices2(c):
	hls = colorsys.rgb_to_hls(c[0] * cf, c[1] * cf, c[2] * cf)
	mind0 = 100000000
	mind1 = 100000000
	i0 = 16
	i1 = 16
	for i in range(0, 16):
		d = CompareHls2(i, hls)
		if d < mind0:
			i1 = i0
			mind1 = mind0
			i0 = i
			mind0 = d
		elif d < mind1:
			i1 = i
			mind1 = d
	return (i0, i1)

def CompareHls_(hls1, c2):
	hls2 = colorsys.rgb_to_hls(c2[0] * cf, c2[1] * cf, c2[2] * cf)
	dh = abs(hls1[0] - hls2[0])
	# hue vergleich mit wrap!
	if dh > 0.5:
		dh = 1.0 - dh
	# hier fehlt spezialabfragen, zB wenn Saturation < limit, dann wähle nur unsaturierte Farben oder so
	# wenn c2 Sättigung kleiner als Mittelwert der Sättigung, dann suche passendes Grau als Zielfarbe,
	# sonst passendes H wichtig, erst dann L. Bei Grau nur L.
	# bei c64-Vergleichsfarben ähnlich handhaben.
	# Der Mixvergleich ist eigentlich schlecht, besser nächstpassende Farbe finden
	# und passend dazu alle anderen 15 mit Mixfaktoren ]0...0,5] ausprobieren
	# das dann für Farbmischung nehmen
	# Abstandsberechnung dann eben 1+DL oder DL je nachdm ob Sättigung stimmt oder L+S*2 oder so...
	dl = abs(hls1[1] - hls2[1])
	ds = abs(hls1[2] - hls2[2])
	return dh * 2 + dl * 4 + ds * 1

def Compare(c1, c2):
	hls1 = colorsys.rgb_to_hls(c1[0] * cf, c1[1] * cf, c1[2] * cf)
	hls2 = colorsys.rgb_to_hls(c2[0] * cf, c2[1] * cf, c2[2] * cf)
	dh = abs(hls1[0] - hls2[0])
	# hue vergleich mit wrap!
	if dh > 0.5:
		dh = 1.0 - dh
	dl = abs(hls1[1] - hls2[1])
	ds = abs(hls1[2] - hls2[2])
	return dh * 2 + dl * 4 + ds

	d = 0
	for i in range(0, 3):
		x1 = c1[i]
		x2 = c2[i]
		x = 0
		if x1 > x2:
			x = x1 - x2
		else:
			x = x2 - x1
		#d += x * x
		d += x
	return d

def NearestColorIndicesHls(p):
	mind = 1000000000
	for c in colorshls:
		d = CompareHls(c[0], p)
		if d < mind:
			mind = d
			i0 = c[1][0]
			i1 = c[1][1]
	return (i0, i1)

def NearestColorIndices(p):
	# Alle 16x16 Kombinationen in Mixfaktoren [0...1[ testen,
	# Mixfaktor in festen Schritten (1/8)
	mind = 1000000000
	i0 = 0
	i1 = 0
	for j in range(0, 16):
		d = Compare(colors[j], p)
		if d < mind:
			mind = d
			i0 = j
			i1 = j
	for k in range(1, 3):
		kk = k * 256 / 4
		for i in range(0, 16):
			for j in range(0, 16):
				if i != j:
					c = MixColor(colors[i], colors[j], kk)
					d = Compare(c, p)
					if d < mind:
						mind = d
						i0 = i
						i1 = j
	return (i0, i1)

	mind0 = 100000000
	mind1 = 100000000
	i0 = 16
	i1 = 16
	for i in range(0, 16):
		d = Compare(colors[i], p)
		if d < mind0:
			i1 = i0
			mind1 = mind0
			i0 = i
			mind0 = d
		elif d < mind1:
			i1 = i
			mind1 = d
	return (i0, i1)

def NearestColorIndicesYIQ(c):
	yiq = colorsys.rgb_to_yiq(c[0] * cf, c[1] * cf, c[2] * cf)
	mind0 = 100000000
	mind1 = 100000000
	i0 = 16
	i1 = 16
	for i in range(0, 16):
		yiq2 = colorsys.rgb_to_yiq(colors[i][0] * cf, colors[i][1] * cf, colors[i][2] * cf)
		a0 = yiq[0] - yiq2[0]
		# a0 *= 2.0 # * 2, weil von 0...1, IQ aber -1...1, fixme test - wird aber eher schlechter, mit 0.5 wirds eher besser
		a1 = yiq[1] - yiq2[1]
		a2 = yiq[2] - yiq2[2]
		d = math.sqrt(a0*a0+a1*a1+a2*a2)
		if math.sqrt(yiq[1]*yiq[1] + yiq[2]*yiq[2]) < 0.01 and i not in cigrey:	# fixme Test: Grauwerte nur auf Grau mappen
			d = 10000000
		if d < mind0:
			i1 = i0
			mind1 = mind0
			i0 = i
			mind0 = d
		elif d < mind1:
			i1 = i
			mind1 = d
	# Faktor berechnen
	f = mind0 / (mind0 + mind1)
	return (i0, i1, f)

def FindMixFactor(col, c1, c2):
	mind = Compare(col, c1)
	mixf = 0
	for i in range(1, 16):
		f = i * 256 / 16
		c = MixColor(c1, c2, f)
		d = Compare(col, c)
		if d < mind:
			mind = d
			mixf = f
	return mixf
		
	f = 128
	df = 64
	ca = c1
	cb = c2
	while df > 0:
		c = MixColor(c1, c2, f)
		d0 = Compare(col, c)
		d1 = Compare(col, cb)
		if d0 < d1:
			cb = c
			f -= df
			df /= 2
		else:
			ca = c
			f += df
			df /= 2
	return f

def GenColor(c1, c2, f, br):
#	limit = 85
#	if f < limit:
#		return c1
#	elif f >= 256 - limit:
#		return c2
#	elif br == 0:
#		return c1
#	else:
#		return c2
	# Random ist besser als gleichmäßiges Raster
	limit = 0 # 32
	if f < limit:
		return c1
	elif f > 255 - limit:
		return c2
	else:
		r = random.randint(limit, 255 - limit)
		if f <= r:
			return c1
		else:
			return c2
	

def EncodeTile(tile, bgcol):
	# Zaehle die Haeufigkeit aller Farben und nehme die drei hoechsten
	# ausser der Hintergrundfarbe
	cnt = []
	for i in range(0, 16):
		cnt += [0]
	for i in tile:
		cnt[i] += 1
	#print cnt
	tc = []
	for j in range(0, 4):
		maxcnt = 0
		mi = 0
		for i in range(0, 16):
			if cnt[i] > maxcnt:
				maxcnt = cnt[i]
				mi = i
		tc += [mi]
		cnt[mi] = 0
	#print tc
	# Wenn Hintergrundfarbe nicht bei 4 haeufigsten ist, ersetze
	# vierthaeufigste durch Hintergrundfarbe
	if bgcol not in tc:
		tc[3] = bgcol
	# Jetzt alle Farben der Kachel ersetzen durch andere
	for i in range(0, len(tile)):
		if tile[i] not in tc:
			mind = 1000000
			c = tc[0]
			for j in range(0, 4):
				d = Compare(colors[tc[j]], colors[tile[i]])
				if d < mind:
					mind = d
					c = tc[j]
			#print 'repl', tile[i], c
			tile[i] = c
	return tile

def VICIIEncode(idx):
	# Finde haeufigste Farbe im Bild
	cnt = []
	for i in range(0, 16):
		cnt += [0]
	for i in idx:
		cnt[i] += 1
	maxcnt = 0
	bgcol = 0
	for i in range(0, 16):
		if cnt[i] > maxcnt:
			bgcol = i
			maxcnt = cnt[i]
	print 'Background color=', bgcol
	# Fuer jede 4x8 Kachel max. 4 Farben
	for y in range(0, 200/8):
		ly = (y*8) * 160
		for x in range(0, 160/4):
			lx = x*4
			tile = []
			for yy in range(0, 8):
				lly = ly + lx + yy * 160
				for xx in range(0, 4):
					tile += [idx[lly + xx]]
			EncodeTile(tile, bgcol)
			u = 0
			for yy in range(0, 8):
				lly = ly + lx + yy * 160
				for xx in range(0, 4):
					idx[lly + xx] = tile[u]
					u += 1
			

# Bild laden
if len(sys.argv) < 2:
	print 'Usage: ', sys.argv[0], ' FILENAME'
	sys.exit(1)
im = Image.open(sys.argv[1])

# skalieren
im = im.resize((160, 200), Image.BICUBIC)
Show(im)

# Es fehlt noch ein Farb-Stretching, hellste Farbe wird weiss/dunkelste schwarz,
# also Kontrastspreizung, fixme

# irgendwie Farben besser clustern, also zB das RGB Bild auf 256 Farben reduzieren, ggf. mit
# Dithern und dann für die 256 den besten Mix finden, was am nächsten dran ist oder so...

# mit RGB waren Ergebnisse schonmal besser! fixme, aber nur teilweise

# c64fy yourself hat weniger Mischmuster, eher direktes Farbmapping,
# aber zum Mischen teilweise noch viel weitergehendere Muster...
# das Farbmapping da ist aber recht gut... geht sehr auf Hue wohl

# Farbvergleichsfunktion besser mit HSV oder YUV machen als RGB, fixme - LAB wird noch empfohlen, mit HSL kaum besser als RGB...

# Encodierung könnte freie Farben besser nutzen fuer mischen ersetzter Farben oder
# fuer dreifach-Mischung einer Zielfarbe (RGB)

# Farbtest: hellgrün wird irgendwie gar nicht verwendet?! Gelb auch schlecht dargestellt.
# beide haben viel L, daher werden sie evtl. nicht so gewählt? mit Begrenzung auf 0.5 etwas besser, fixme

# c64 yourself ist teilweise detailreicher und besser

# die c64 Farbkoordinaten in der HL-Ebene optimieren, zB für blau dieselbe Koordinate
# wie RGB 0,0,1 o.ä. und hellblau mit gleichem H wie blau, aber L=0,5 oder 0,6.
# Dadurch besseres Farbmatching.
# blau/Grün/rot wie RGB Werte 0,0,1 0,1,0 1,0,0 bzw mit 0.8 oder so.
# Farben in H Richtung äquidistant. Gelb/orange/braun gut platzieren,
# Türkis/lila wie rot/blau/grün vom L-Wert her, aber H mittig.
# bringt aber nicht viel.

# Testweise mal HS oder LS Ebene ausgeben für bessere Farbeinschätzung. Getan, ist so ok.

# Farbmischung zwar gute Idee an echtem C64 aber auf TFT/PC sieht es nicht so gut aus,
# vor allem wenn Farben sehr unterschiedlich, wie gelb und hellrot.

# fixme: Gebe Bild mal als einzelne H/L/S-Werte aus, L/S als Grauwerte und H mit L=0.5,S=1.0

# macht man einfach Ähnlichkeit als 3D-Abstand im YIQ (=YUV?) Raum, siehts schon eher aus wie c64yourself,
# aber nicht ganz. Vermutlich benutzt c64yourself einfach einen anderen Farbraum (Lab vielleicht?)
# in HLS kann man keinen 3D Abstand benutzen - leider.
# mit YIQ ist fast genauso wie in c64yourself, oft viel besser als HLS... ggf Y stärker gewichten???
# orange ist etwas unterrepräsentiert, leider. muß man ggf. durch passende YIQ Werte stärken
# oder was eben wenig IQ hat (also eher grau), dann auch nur Grauwerte als Vergleich nehmen.
# evtl YIQ Werte der c64-Farben justieren für bessere Ergebnisse

# evtl Kombilösung aus HLS und YIQ wählen, distanz-Wert als Kombination aus beiden oder so...

# Skript mal aufräumen, unbenutzte Teile raus, alten Stand aufheben.

# Funktion, die zu jeder Farbe den Abstand berechnet, je eine Version für RGB,HLS,YIQ.

# Aufrufende Funktion vergleicht dann die Abstände und ermittelt Faktor, kann dann auch mischen zwischen
# YIQ und HLS.

# Modus zB per Kommandozeile, YIQ, HLS, RGB als Distanzen unterstützen

# YIQ ist nicht gleich YUV, I wichtiger als Q, evtl da auch variieren,
# oder eben echtes YUV.
# Formel von wikipedia. http://en.wikipedia.org/wiki/YUV#Converting_between_Y.27UV_and_RGB

random.seed()

# Farbmischung finden
px = im.getdata()

# Kontrast/Farbe spreizen - bzw Sättigung erhöhen - nein, unnötig?
pxhls = []
minl = 1.0
maxl = 0.0
mins = 1.0
maxs = 0.0
meanl = 0.0
means = 0.0
for i in px:
	hls = colorsys.rgb_to_hls(i[0] * cf, i[1] * cf, i[2] * cf)
	if hls[1] < minl:
		minl = hls[1]
	if hls[1] > maxl:
		maxl = hls[1]
	if hls[2] < mins:
		mins = hls[2]
	if hls[2] > maxs:
		maxs = hls[2]
	meanl += hls[1]
	means += hls[2]
meanl /= (160*200)
means /= (160*200)
print minl, meanl, maxl, mins, means, maxs
meansat = means

cidx = []
zl = 0
px3 = []
px4 = []
px5 = []
px6 = []
px7 = []
px8 = []
px9 = []
for i in px:
	#s = NearestColorIndices(i)
	#s = NearestColorIndicesHls(i)
	hls = colorsys.rgb_to_hls(i[0] * cf, i[1] * cf, i[2] * cf)
	c0 = colorsys.hls_to_rgb(hls[0], 0.5, 1.0)
	px6 += [(int(c0[0] * 255), int(c0[1] * 255), int(c0[2] * 255))]
	px7 += [(int(hls[1] * 255), int(hls[1] * 255), int(hls[1] * 255))]
	px8 += [(int(hls[2] * 255), int(hls[2] * 255), int(hls[2] * 255))]
	k = (hls[1]+hls[2])*0.5
	if k > 1.0:
		k = 1.0
	px9 += [(int(k * 255), int(k * 255), int(k * 255))]
	#s = NearestColorIndices2(i)
	##s2 = NearestColor2(i) # teste zu der Farbe alle anderen 15 in diversen Mischfaktoren auf ähnlichkeit.
#	sy = NearestColorIndicesYIQ(i)
	d1 = ComputeDeltasRGB(i)
	d2 = ComputeDeltasYIQ(i)
	#d3 = ComputeDeltasHLS(i)
	d = CombineDeltas(d1, d2, 1.0, 1.0)	# fixme klappt irgendwie nicht! sollte 0.1 sein - stärkerer Wert größerer Faktor...
	#d = d1
	sy = NearestColorIndices_NEW(d)
	s2 = sy # fixme yiq test
	#f = FindMixFactor(i, colors[s[0]], colors[s[1]])
	s = (s2[0], s2[1])
	ff = s2[2]
	sf = 16.0 # 8 bei HLS, 16-32 bei YIQ, fixme: das an NearestColorIndices_NEW übergeben? oder besser separate Funktion
	ff = ff*sf - (sf-1)*0.5
	if ff < 0.0:
		ff = 0.0
	if ff > 1.0:
		ff = 1.0
	f = int(ff * 255)#ff
	# berechne 8*f-3.5 mit clamp bei 0,1
	px3 += [colors[s2[0]]]	# fast schon am besten, nur leichter Mix fehlt eben
	px4 += [colors[s2[1]]]
	#px3 += [colors[sy[0]]]
	#px4 += [colors[sy[1]]]
	px5 += [MixColor(colors[s2[0]], colors[s2[1]], int(s2[2] * 255))]
	# px3 += [MixColor(colors[s[0]], colors[s[1]], f)]
	# wenn f < 32 oder > 224 dann Farbe direkt, sonst Random-Verteilung nach f
	x = zl % 160
	y = zl / 160
	r = (x + y) % 2
	c = GenColor(s[0], s[1], f, r)
	cidx += [c]
	zl += 1
	if zl % 1280 == 0:
		print 'Zeile', zl / 160

# VIC-II Codierung (4x8 Pixel nur 4 Farben, Hintergrundfarbe finden)
VICIIEncode(cidx)

px2 = []
for i in cidx:
	px2 += [colors[i]]

im.putdata(px3)
Show(im)
im.putdata(px4)
Show(im)
im.putdata(px5)
Show(im)
if True:
	im.putdata(px6)
	Show(im)
	im.putdata(px7)
	Show(im)
	im.putdata(px8)
	Show(im)
	im.putdata(px9)
	Show(im)


# Bild erzeugen
im.putdata(px2)

# Ausgeben
Show(im)

im.resize((320, 200), Image.NEAREST).save(sys.argv[1] + '_c64.png')

