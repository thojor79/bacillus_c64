#!/usr/bin/python
# coding=utf8
import Image
import random
import sys
import colorsys
import math

# Farben des C64
colors1 = [ # Farben von einer Analyse-Website
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

colors2 = [ # Farben von vice
(0x00, 0x00, 0x00),
(0xFF, 0xFF, 0xFE),
(0x92, 0x4a, 0x40),
(0x84, 0xc5, 0xcc),
(0x93, 0x51, 0xb6),
(0x72, 0xb1, 0x4b),
(0x48, 0x3a, 0xaa),
(0xd5, 0xde, 0x7c),
(0x99, 0x69, 0x2D),
(0x67, 0x52, 0x00),
(0xc1, 0x81, 0x78),
(0x60, 0x60, 0x60),
(0x8a, 0x8a, 0x8a),
(0xb3, 0xec, 0x91),
(0x86, 0x7a, 0xde),
(0xb3, 0xb3, 0xb3) ]

colors = colors2

# Grautöne und Farben als Indizes
cigrey = [0, 11, 12, 15, 1]
cicolors = [2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14]

# Farbskalierung
cf = 1.0 / 255.0

infinity = 1000000000.0

# Bilder umwandeln funktioniert, aber:
# Wir brauchen auch eine Teilfunktionalität, die Charsetdaten generiert.
# Also gebe Bild rein, das Vielfache Breite/Höhe von 8 hat (Breite eher 4 wegen Multicolor).
# und gebe an, wieviele Characters generiert werden sollen und ab welcher Nummer.
# Dann werden drei Hauptfarben bestimmt, hier gerne erstmal Bildweites Ausgleichen der
# Helligkeit und Sättigung, das auch als Option.
# Pro 8x8 Teil des Bildes bestimme einen idealen Character. Als vierte Farbe nur 0-7 möglich.
# Idealerweise bestimme auch eine Farbe von 0-7 als Alternative für hohe Auflösung,
# falls das ähnlicher ist zum Tile. Also bei beiden Fällen Fehler testen und entsprechend etwas
# generieren. Wenn man statt einer drei Farben pro Tile freigibt, kann man denselben Code für
# Multicolor-Bilder verwenden!
# Hat man dann alle Characters generiert und es sind mehr als man nutzen darf, dann zähle, wie
# oft einer benutzt wird, je seltener desto verzichtbarer. Ersetze dann seltene durch häufigere,
# jeweils mit Farbvergleich, also Fehlerfunktion, solange bis es paßt.
#
# Also umbauen:
# Bild einlesen in HiRes-Auflösung (bei Bildern runterskalieren, Aspect-Ratio behalten?)
# Dann Sättigung/Helligkeit strecken (Sättigung aber mit Limit, damit aus Grau nicht Farbe wird).
# Dann eine oder drei Hauptfarben bestimmen.
# Dann pro 8x8 Block umwandeln, bei Char mit HiRes-Option (geht nicht bei Bitmap)
# Bei Char noch Reduktion.
# Dann Daten ausgeben: Char/Color/Bitmap oder Charset/Color/Char
# Versuche auch Interlace-Mix-Farben zu benutzen, bei halber vertikaler Auflösung.
# Es gibt 7 bzw. 14 Mixfarben, aber nur wenige taugen.
# Zusammen mit acme könnte man gleich auch fertiges PRG erzeugen, das auf x64 gestartet wird.
# Entsprechendes Programm mal entwickeln.
# Generell brauchen wir eine Fehlerfunktion, die c64-Kachel (8x8 bzw. 4x8) mit Bildkachel vergleicht.

meansat = 0.0	# fixme: braucht man das noch? nein, eher nicht, war für HLS gedacht, dort geht absoluter Wert aber besser

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

# Nur fuer Tests gebraucht
def MixColor(c1, c2, f):
	c = [0, 0, 0]
	for i in range(0, 3):
		c[i] = (c1[i] * (256 - f) + c2[i] * f) / 256
	return (c[0], c[1], c[2])

def NearestColorIndices(deltas):
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
			dh = abs(colors_hls[i][0] - hls[0])
			if dh > 0.5:	# hue vergleich mit wrap!
				dh = 1.0 - dh
			dl = abs(colors_hls[i][1] - hls[1])
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
		d = infinity
		if deltas0[i] > infinity * 0.5:
			if deltas1[i] < infinity * 0.5:
				d = deltas1[i] * (f0 + f1)
		elif deltas1[i] > infinity * 0.5:
			d = deltas0[i] * (f0 + f1)
		else:
			d = deltas0[i] * f0 + deltas1[i] * f1
		deltas += [d]
	return deltas

def ScaleMixFactor(f, sf):
	ff = f*sf - (sf-1)*0.5
	if ff < 0.0:
		ff = 0.0
	if ff > 1.0:
		ff = 1.0
	return int(ff * 255)

def Show(im):
	if len(sys.argv) == 2:
		im2 = im.resize((320*2, 200*2), Image.NEAREST)
		im2.show()

def GenColor(c1, c2, f):
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
	cnt = [0] * 16
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
			yiq1 = colors_yiq[tile[i]]
			mind = infinity
			c = tc[0]
			for j in range(0, 4):
				yiq0 = colors_yiq[tc[j]]
				a0 = yiq0[0] - yiq1[0]
				a1 = yiq0[1] - yiq1[1]
				a2 = yiq0[2] - yiq1[2]
				# hier keine Y-Skalierung und auch kein Mapping auf Grauwerte
				d = math.sqrt(a0*a0 + a1*a1 + a2*a2)
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
			



#
# HLS-Tests
#
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



# Bild laden
if len(sys.argv) < 2:
	print 'Usage: ', sys.argv[0], ' FILENAME [NUM_CHARS_TO_USE [START_CHAR_CODE]]'
	print 'First argument is a picture. Without any further arguments it is converted'
	print 'to a C64 multicolor bitmap.'
	print 'With further arguments character set part is generated and char codes'
	print 'as well. The image size must be multiple of 8 or some parts will be cut.'
	sys.exit(1)
im = Image.open(sys.argv[1])
charmode = False
firstchar = 0
numchars = 0
if len(sys.argv) > 2:
	charmode = True
	numchars = int(sys.argv[2])
	if len(sys.argv) > 3:
		firstchar = int(sys.argv[3])
	if firstchar < 0 or numchars < 1 or firstchar > 255 or firstchar + numchars > 256:
		print 'Error in char data input arguments!'
		sys.exit(1)
	print 'Using character mode with characters', firstchar, 'to', firstchar+numchars-1, '.'

# skalieren/zuschneiden
if charmode:
	img_w = im.size[0]
	img_h = im.size[1]
	print img_w, img_h
	img_w = (img_w / 8) * 8
	img_h = (img_h / 8) * 8
	print img_w, img_h
	im = im.crop((0, 0, img_w, img_h))
else:
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
# hier fehlt PAL emulation, gewisse farben kann man zu neuen mischen

# fixme: Gebe Bild mal als einzelne H/L/S-Werte aus, L/S als Grauwerte und H mit L=0.5,S=1.0

# macht man einfach Ähnlichkeit als 3D-Abstand im YIQ (=YUV?) Raum, siehts schon eher aus wie c64yourself,
# aber nicht ganz. Vermutlich benutzt c64yourself einfach einen anderen Farbraum (Lab vielleicht?)
# in HLS kann man keinen 3D Abstand benutzen - leider.
# mit YIQ ist fast genauso wie in c64yourself, oft viel besser als HLS... ggf Y stärker gewichten???
# orange ist etwas unterrepräsentiert, leider. muß man ggf. durch passende YIQ Werte stärken
# oder was eben wenig IQ hat (also eher grau), dann auch nur Grauwerte als Vergleich nehmen.
# evtl YIQ Werte der c64-Farben justieren für bessere Ergebnisse
# ACHTUNG das mittlere grau wird irgendwie gar nicht so verwendet/abgedeckt

# evtl Kombilösung aus HLS und YIQ wählen, distanz-Wert als Kombination aus beiden oder so...

# Skript mal aufräumen, unbenutzte Teile raus, alten Stand aufheben.

# Funktion, die zu jeder Farbe den Abstand berechnet, je eine Version für RGB,HLS,YIQ.

# Aufrufende Funktion vergleicht dann die Abstände und ermittelt Faktor, kann dann auch mischen zwischen
# YIQ und HLS.

# Modus zB per Kommandozeile, YIQ, HLS, RGB als Distanzen unterstützen

# YIQ ist nicht gleich YUV, I wichtiger als Q, evtl da auch variieren,
# oder eben echtes YUV.
# Formel von wikipedia. http://en.wikipedia.org/wiki/YUV#Converting_between_Y.27UV_and_RGB

# Idee für Farbreduktion: alle Tiles 4x8 mit <= 3 verschiedenen Farben sind für
# Hintergrundfarbe irrelevant. Nur Tiles mit >= 4 Farben für Berechnung der
# Hintergrundfarbe ranziehen!

# Idee: Analyse der Farben, des Bildes: ist es eher blass, gewichte die Sättigung anders, so
# daß mehr passende Farben gewählt werden, also die Abbildung von Pixeln zu Farbe nicht
# immer gleich ist über einfache RGB/YUV-Umrechnung, sondern mehr symbolisch.
# Blasses Blau zu starkem Blau, wenn es nur blasses Blau im Bild gibt zB.
# Verzerrt, aber macht es ggf. besser darstellbar

# fixme codiere 10k binary daten als .byte datei für acme!

# fixme eine eher symbolische codierung wäre auch gut, also ist eingabe rosa, nehme auch eher rosa,
# grau paßt zwar evtl besser von helligkeit, aber nicht von farbe her!
# das wäre dann eher HLS codiert mit Verstärkung auf Hue, aber nur wenn Saturation hoch genug
# Idee wäre auch CharCode Generator, also 256 Zeichen generieren mit 3 festen Farben und
# das auch für breitere Bilder (Scrollende Bildschirme)
# Am besten noch mit Anzahl der Zeichen angebbar, die es werden sollen.
# Berechne pro Block wie das Zeichen aussehen sollte, gibt N Zeichen, sortiere dann gleiche
# aus und rechne für alle NxN Kombinationen die Ähnlichkeiten aus, solange die ähnlichsten
# jeweils ersetzen bis Gesamtanzahl <= Soll. Unterschiede aber auch mit Anzahl verrechnen,
# damit nur einzeln vorkommende sehr unähnliche nicht unnötig Chars kriegen.
# equalizer auch nicht verkehrt, dunkles bild einfach aufhellen, um farbraum besser zu nutzen!
# eher auch die Farben in Eingabe mehr zu clustern auf wenige typische ähnliche und dann
# ein direkteres mapping auf die 16 verfügbaren, ggf mit den zusätzlichen 14 durch interlace mix.
# wenn in eingabe drei grautöne, dann werden das auch die drei vom c64, auch wenn helligkeit nicht
# so paßt usw...
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

for i in px:
	d1 = ComputeDeltasRGB(i) # RGB ist auch gar nicht so schlecht, mal 50:50 mit YIQ testen
	d2 = ComputeDeltasYIQ(i) # Nur YIQ ist schon ziemlich gut, aber Mischung evtl leicht besser
	#d3 = ComputeDeltasHLS(i) # HLS nur geringer Anteil, sonst schlecht, zB 0,05 zu 1 YIQ.
	#d = CombineDeltas(d2, d3, 1.0, 0.05)	#  fixme: ideale Kombination testen
	#d = d1
	d = CombineDeltas(d1, d2, 0.5, 0.5)
	si = NearestColorIndices(d)
	f = ScaleMixFactor(si[2], 16.0)	# 8 bei HLS, 16-32 bei YIQ
	px3 += [colors[si[0]]]	# fast schon am besten, nur leichter Mix fehlt eben
	px4 += [colors[si[1]]]
	px5 += [MixColor(colors[si[0]], colors[si[1]], int(si[2] * 255))]
	# Fortschrittsanzeige
	c = GenColor(si[0], si[1], f)
	px6 += [colors[c]]
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
im.putdata(px6)
Show(im)


# Bild erzeugen
im.putdata(px2)

# Ausgeben
Show(im)

im.resize((320, 200), Image.NEAREST).save(sys.argv[1] + '_c64.png')
