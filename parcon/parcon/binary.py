
"""
A module that provides parsers to allow Parcon to parse binary data. Some of
the main parsers it provides are:

integer: parses four bytes in big-endian order and returns an int.
short: parses two bytes in big-endian order and returns an int.
byte: parses one byte and returns an int.
u_integer, u_short, u_byte: same as integer, short, and byte, respectively,
except that they treat the value as unsigned.

This module also provides a class, PyStruct, which is created with a format
specification (in the same format as that passed to Python's
struct.pack/unpack). It parses any data that matches the specification, and
returns the resulting values.
"""

import parcon
import struct

class PyStruct(parcon.Parser):
    """
    A parser that takes a particular format specification as expected by
    Python's struct module's operations. It parses any input that
    struct.unpack can successfully understand and returns the result as a list
    if more than one item was returned; otherwise it returns the single result
    that unpack produced.
    
    Note that the format specifier cannot contain "p" (a.k.a. a pascal string
    format) at present. I'll add support for this later.
    """
    def __init__(self, format):
        self.format = format
        self.length = struct.calcsize(format)
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        if position + self.length > end:
            return parcon.failure([(position, parcon.ECustomExpectation("struct.unpack format " + repr(self.format)))])
        result =  struct.unpack(self.format, text[position:position+self.length])
        if len(result) == 1:
            result = result[0]
        else:
            result = list(result)
        return parcon.match(position + self.length, result, (position + self.length, parcon.EUnsatisfiable()))
    
    def __repr__(self):
        return "PyStruct(%s)" % repr(self.format)


integer = PyStruct(">i")(expected="four bytes (signed integer)")
u_integer = PyStruct(">I")(expected="four bytes (unsigned integer)")
short = PyStruct(">h")(expected="two bytes (signed short)")
u_short = PyStruct(">H")(expected="two bytes (unsigned short)")
byte = PyStruct(">b")(expected="one byte (signed byte)")
u_byte = PyStruct(">B")(expected="one byte (unsigned byte)")


































