"""
A set of functions and classes that make it easier to use Parcon and Pargen
together. Pargon is a portmanteau of Parcon and Pargen.
"""

import parcon
from parcon import pargen


class ParserFormatter(parcon.Parser, pargen.Formatter):
    """
    A class that allows creating objects which are both parsers and formatters.
    Such a parser/formatter is created by passing in a Parser and a Formatter.
    The resulting instance of ParserFormatter, when used as a parser, acts like
    the parser passed to it, and when used as a formatter, acts like the
    formatter passed to it.
    
    This class should only be used 
    """