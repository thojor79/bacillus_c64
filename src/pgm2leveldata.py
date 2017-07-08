#!/usr/bin/python
f = open('leveldata.pgm')
ln = f.readlines()[4:]
count = 0
out = '!byte '
for i in ln:
    n = int(i[:-1]) / 16
    out += str(n) + ','
    count += 1
    if count == 16:
        count = 0
        out = out[:-1] + '\n!byte '
print out
