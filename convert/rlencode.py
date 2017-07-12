#!/usr/bin/python3
# coding=utf8

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
	# print(encoded)
	result = []
	temp = []
	for e in encoded:
		if e[0] >= 3:
			# at least three elements, use repeat code
			if len(temp) > 0:
				result += [len(temp)-1]
				result += temp
				temp = []
			result += [e[0] + 128 - 3, e[1]]
		else:
			temp += [e[1]] * e[0]
			if len(temp) > 128:
				result += [127]	# max single count (128-1)
				result += temp[:128]
				temp = temp[128:]
	if len(temp) > 0:
		result += [len(temp)-1]
		result += temp
	result += [255]

	#print result
	print('RLE encoded',len(bytes),'bytes to',len(result),'bytes (',len(result)*100/len(bytes),'%), saving',len(bytes)-len(result),'bytes.')
	return result
