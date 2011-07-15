
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
        position = parcon.parse_space(text, position, end, space)
        if position + self.length > end:
            return parcon.failure([(position, "struct.unpack format " + repr(self.format))])
        result =  struct.unpack(self.format, text[position:position+self.length])
        if len(result) == 1:
            return result[0]
        return list(result)
    
    def __repr__(self):
        return "PyStruct(%s)" % repr(self.format)


integer = PyStruct(">i")(expected="four bytes (signed integer)")
u_integer = PyStruct(">I")(expected="four bytes (signed integer)")
short = PyStruct(">h")(expected="two bytes (signed short)")
u_short = PyStruct(">H")(expected="two bytes (signed short)")
byte = PyStruct(">b")(expected="one byte (signed byte)")
u_byte = PyStruct(">B")(expected="one byte (signed byte)")


































