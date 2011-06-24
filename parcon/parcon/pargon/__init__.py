"""
A set of functions and classes that make it easier to use Parcon and Pargen
together. Pargon is a portmanteau of Parcon and Pargen.
"""

import parcon
from parcon import pargen
from parcon import static

parser_type = static.compile(parcon.Parser)
formatter_type = static.compile(pargen.Formatter)


class ParserFormatter(parcon.Parser, pargen.Formatter):
    """
    A class that allows creating objects which are both parsers and formatters.
    Such a parser/formatter is created by passing in a Parser and a Formatter.
    The resulting instance of ParserFormatter, when used as a parser, acts like
    the parser passed to it, and when used as a formatter, acts like the
    formatter passed to it.
    
    This class should only be used when you want to create a parser/formatter
    that acts like a predetermined parser and a predetermined formatter. If you
    want to implement a custom parser/formatter yourself, you can just subclass
    both Parser and Formatter in your new class.
    
    When a ParserFormatter is used as an argument to an operator such as + or
    |, it behaves as a parser. If you need it to behave as a formatter, you'll
    probably want to wrap it in a pargen.Forward instance.
    """
    def __init__(self, parser, formatter):
        parser_type.check_matches(parser)
        formatter_type.check_matches(formatter)
        self.parser = parser
        self.formatter = formatter
    
    def parse(self, text, position, end, space):
        return self.parser.parse(text, position, end, space)
    
    def format(self, input):
        return self.formatter.format(input)


class Literal(ParserFormatter):
    """
    A parser/formatter that behaves like Parcon and Pargen's Literal classes.
    """
    def __init__(self, text):
        ParserFormatter.__init__(self, parcon.Literal(text), pargen.Literal(text))




































