#
# (re)generate unicode property and type databases
#
# this script converts a unicode 3.0 database file to
# Modules/unicodedata_db.h and Objects/unicodetype_db.h
#
# history:
# 2000-09-24 fl   created (based on bits and pieces from unidb)
# 2000-09-25 fl   merged tim's splitbin fixes, separate decomposition table
# 2000-09-25 fl   added character type table
#
# written by Fredrik Lundh (fredrik@pythonware.com), September 2000
#

import sys

SCRIPT = sys.argv[0]
VERSION = "1.1"

UNICODE_DATA = "UnicodeData-Latest.txt"

CATEGORY_NAMES = [ "Cn", "Lu", "Ll", "Lt", "Mn", "Mc", "Me", "Nd",
    "Nl", "No", "Zs", "Zl", "Zp", "Cc", "Cf", "Cs", "Co", "Cn", "Lm",
    "Lo", "Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk",
    "So" ]

BIDIRECTIONAL_NAMES = [ "", "L", "LRE", "LRO", "R", "AL", "RLE", "RLO",
    "PDF", "EN", "ES", "ET", "AN", "CS", "NSM", "BN", "B", "S", "WS",
    "ON" ]

ALPHA_MASK = 0x01
DECIMAL_MASK = 0x02
DIGIT_MASK = 0x04
LOWER_MASK = 0x08
NUMERIC_MASK = 0x10
SPACE_MASK = 0x20
TITLE_MASK = 0x40
UPPER_MASK = 0x80

def maketables():

    unicode = UnicodeData(UNICODE_DATA)

    # extract unicode properties
    dummy = (0, 0, 0, 0)
    table = [dummy]
    cache = {0: dummy}
    index = [0] * len(unicode.chars)

    # 1) database properties
    for char in unicode.chars:
        record = unicode.table[char]
        if record:
            # extract database properties
            category = CATEGORY_NAMES.index(record[2])
            combining = int(record[3])
            bidirectional = BIDIRECTIONAL_NAMES.index(record[4])
            mirrored = record[9] == "Y"
            item = (
                category, combining, bidirectional, mirrored
                )
            # add entry to index and item tables
            i = cache.get(item)
            if i is None:
                cache[item] = i = len(table)
                table.append(item)
            index[char] = i

    # 2) decomposition data

    # FIXME: <fl> using the encoding stuff from unidb would save
    # another 50k or so, but I'll leave that for 2.1...

    decomp_data = [""]
    decomp_index = [0] * len(unicode.chars)

    for char in unicode.chars:
        record = unicode.table[char]
        if record:
            if record[5]:
                try:
                    i = decomp_data.index(record[5])
                except ValueError:
                    i = len(decomp_data)
                    decomp_data.append(record[5])
            else:
                i = 0
            decomp_index[char] = i

    FILE = "Modules/unicodedata_db.h"

    sys.stdout = open(FILE, "w")

    print "/* this file was generated by %s %s */" % (SCRIPT, VERSION)
    print
    print "/* a list of unique database records */"
    print "const _PyUnicode_DatabaseRecord _PyUnicode_Database_Records[] = {"
    for item in table:
        print "    {%d, %d, %d, %d}," % item
    print "};"
    print

    # FIXME: the following tables should be made static, and
    # the support code moved into unicodedatabase.c

    print "/* string literals */"
    print "const char *_PyUnicode_CategoryNames[] = {"
    for name in CATEGORY_NAMES:
        print "    \"%s\"," % name
    print "    NULL"
    print "};"

    print "const char *_PyUnicode_BidirectionalNames[] = {"
    for name in BIDIRECTIONAL_NAMES:
        print "    \"%s\"," % name
    print "    NULL"
    print "};"

    print "static const char *decomp_data[] = {"
    for name in decomp_data:
        print "    \"%s\"," % name
    print "    NULL"
    print "};"

    # split record index table
    index1, index2, shift = splitbins(index)

    print "/* index tables for the database records */"
    print "#define SHIFT", shift
    Array("index1", index1).dump(sys.stdout)
    Array("index2", index2).dump(sys.stdout)

    # split decomposition index table
    index1, index2, shift = splitbins(decomp_index)

    print "/* index tables for the decomposition data */"
    print "#define DECOMP_SHIFT", shift
    Array("decomp_index1", index1).dump(sys.stdout)
    Array("decomp_index2", index2).dump(sys.stdout)

    sys.stdout = sys.__stdout__

    #
    # 3) unicode type data

    # extract unicode types
    dummy = (0, 0, 0, 0)
    table = [dummy]
    cache = {0: dummy}
    index = [0] * len(unicode.chars)

    for char in unicode.chars:
        record = unicode.table[char]
        if record:
            # extract database properties
            category = record[2]
            bidirectional = record[4]
            flags = 0
            if category in ["Lm", "Lt", "Lu", "Ll", "Lo"]:
                flags |= ALPHA_MASK
            if category == "Ll":
                flags |= LOWER_MASK
            if category == "Zs" or bidirectional in ("WS", "B", "S"):
                flags |= SPACE_MASK
            if category in ["Lt", "Lu"]:
                flags |= TITLE_MASK
            if category == "Lu":
                flags |= UPPER_MASK
            # use delta predictor for upper/lower/title
            if record[12]:
                upper = (int(record[12], 16) - char) & 0xffff
            else:
                upper = 0
            if record[13]:
                lower = (int(record[13], 16) - char) & 0xffff
            else:
                lower = 0
            if record[14]:
                title = (int(record[14], 16) - char) & 0xffff
            else:
                title = 0
            item = (
                flags, upper, lower, title
                )
            # add entry to index and item tables
            i = cache.get(item)
            if i is None:
                cache[item] = i = len(table)
                table.append(item)
            index[char] = i

    FILE = "Objects/unicodetype_db.h"

    sys.stdout = open(FILE, "w")

    print "/* this file was generated by %s %s */" % (SCRIPT, VERSION)
    print
    print "/* a list of unique character type descriptors */"
    print "const _PyUnicode_TypeRecord _PyUnicode_TypeRecords[] = {"
    for item in table:
        print "    {%d, %d, %d, %d}," % item
    print "};"
    print

    # split decomposition index table
    index1, index2, shift = splitbins(index)

    print "/* type indexes */"
    print "#define SHIFT", shift
    Array("index1", index1).dump(sys.stdout)
    Array("index2", index2).dump(sys.stdout)

    sys.stdout = sys.__stdout__

# --------------------------------------------------------------------
# the following support code is taken from the unidb utilities
# Copyright (c) 1999-2000 by Secret Labs AB

# load a unicode-data file from disk

import string, sys

class UnicodeData:

    def __init__(self, filename):
        file = open(filename)
        table = [None] * 65536
        while 1:
            s = file.readline()
            if not s:
                break
            s = string.split(string.strip(s), ";")
            char = string.atoi(s[0], 16)
            table[char] = s

        # public attributes
        self.filename = filename
        self.table = table
        self.chars = range(65536) # unicode

    def uselatin1(self):
        # restrict character range to ISO Latin 1
        self.chars = range(256)

# stuff to deal with arrays of unsigned integers

class Array:

    def __init__(self, name, data):
        self.name = name
        self.data = data

    def dump(self, file):
        # write data to file, as a C array
        size = getsize(self.data)
        # print >>sys.stderr, self.name+":", size*len(self.data), "bytes"
        file.write("static ")
        if size == 1:
            file.write("unsigned char")
        elif size == 2:
            file.write("unsigned short")
        else:
            file.write("unsigned int")
        file.write(" " + self.name + "[] = {\n")
        if self.data:
            s = "    "
            for item in self.data:
                i = str(item) + ", "
                if len(s) + len(i) > 78:
                    file.write(s + "\n")
                    s = "    " + i
                else:
                    s = s + i
            if string.strip(s):
                file.write(s + "\n")
        file.write("};\n\n")

def getsize(data):
    # return smallest possible integer size for the given array
    maxdata = max(data)
    if maxdata < 256:
        return 1
    elif maxdata < 65536:
        return 2
    else:
        return 4

def splitbins(t, trace=0):
    """t, trace=0 -> (t1, t2, shift).  Split a table to save space.

    t is a sequence of ints.  This function can be useful to save space if
    many of the ints are the same.  t1 and t2 are lists of ints, and shift
    is an int, chosen to minimize the combined size of t1 and t2 (in C
    code), and where for each i in range(len(t)),
        t[i] == t2[(t1[i >> shift] << shift) + (i & mask)]
    where mask is a bitmask isolating the last "shift" bits.

    If optional arg trace is true (default false), progress info is
    printed to sys.stderr.
    """

    import sys
    if trace:
        def dump(t1, t2, shift, bytes):
            print >>sys.stderr, "%d+%d bins at shift %d; %d bytes" % (
                len(t1), len(t2), shift, bytes)
        print >>sys.stderr, "Size of original table:", len(t)*getsize(t), \
                            "bytes"
    n = len(t)-1    # last valid index
    maxshift = 0    # the most we can shift n and still have something left
    if n > 0:
        while n >> 1:
            n >>= 1
            maxshift += 1
    del n
    bytes = sys.maxint  # smallest total size so far
    t = tuple(t)    # so slices can be dict keys
    for shift in range(maxshift + 1):
        t1 = []
        t2 = []
        size = 2**shift
        bincache = {}
        for i in range(0, len(t), size):
            bin = t[i:i+size]
            index = bincache.get(bin)
            if index is None:
                index = len(t2)
                bincache[bin] = index
                t2.extend(bin)
            t1.append(index >> shift)
        # determine memory size
        b = len(t1)*getsize(t1) + len(t2)*getsize(t2)
        if trace:
            dump(t1, t2, shift, b)
        if b < bytes:
            best = t1, t2, shift
            bytes = b
    t1, t2, shift = best
    if trace:
        print >>sys.stderr, "Best:",
        dump(t1, t2, shift, bytes)
    if __debug__:
        # exhaustively verify that the decomposition is correct
        mask = ~((~0) << shift) # i.e., low-bit mask of shift bits
        for i in xrange(len(t)):
            assert t[i] == t2[(t1[i >> shift] << shift) + (i & mask)]
    return best

if __name__ == "__main__":
    maketables()
