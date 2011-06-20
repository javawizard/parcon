"""
Pargen is a formatter combinator library. It's much the opposite of parcon:
while parcon parses text into objects, pargen formats objects into text.
I'll get more documentation up on here soon, but for now, here's a JSON
formatter (essentially a simplified reimplementation of Python's json.dumps):

from parcon.pargen import *
from decimal import Decimal
json = Forward()
number = Type(float, int, long, Decimal) & String()
boolean = Type(bool) & ((Is(True) & "true") | (Is(False) & "false"))
null = Is(None) & "null"
string = Type(basestring) & '"' + String() + '"'
json_list = Type(list, tuple) & ("[" + ForEach(json, ", ") + "]")
json_map =Type(dict) &  ("{" + ForEach(Head(json) + ": " + Tail(json), ", ") + "}")
json << (boolean | number | null | string | json_list | json_map)

You can then do things like:

>>> print json.format([True,1,{"2":3,"4":None},5,None,False,"hello"]).text
[true, 1, {"2": 3, "4": null}, 5, null, false, "hello"]
"""

"""
TODO: write something that can convert a number into its textual representation,
so like the opposite of the number parser example, and then write something that
can format a list of items into, say, "first", "first or second", "first, second, or third", etc, meaning
that it converts a list of items into an english language phrase describing that set properly. Also add
things for extracting keys from maps.
"""

from parcon import static

sequence_type = static.Sequence()
sequence_or_dict_type = static.Or(static.Sequence(), static.Type(dict))

class Result(object):
    def __init__(self, text, remainder):
        self.text = text
        self.remainder = remainder
    
    def __nonzero__(self):
        return self.text is not None
    
    def __str__(self):
        if self:
            return "<Result: %s with remainder %s>" % (repr(self.text), self.remainder)
        else:
            return "<Result: Failure>"
    
    __repr__ = __str__


def failure():
    return Result(None, None)


def match(text, remainder):
    return Result(text, remainder)


def promote(value):
    if isinstance(value, Formatter):
        return value
    if isinstance(value, basestring):
        return Literal(value)
    return value

def reversed(function):
    def new_function(x, y):
        return function(y, x)
    return new_function


def op_add(first, second):
    return Then(promote(first), promote(second))


def op_and(first, second):
    return And(promote(first), promote(second))


def op_or(first, second):
    return First(promote(first), promote(second))


class Formatter(object):
    """
    The main class of this module, analogous to 
    """
    def format(self, input):
        raise Exception("format not implemented for " + str(type(self)))
    
    __add__ = op_add
    __and__ = op_and
    __or__ = op_or
    __radd__ = reversed(op_add)
    __rand__ = reversed(op_and)
    __ror__ = reversed(op_or)


class Literal(Formatter):
    def __init__(self, text):
        self.text = text
    
    def format(self, input):
        return match(self.text, input)


class ForEach(Formatter):
    def __init__(self, formatter, delimiter=""):
        self.formatter = formatter
        self.delimiter = delimiter
    
    def format(self, input):
        if not sequence_or_dict_type.matches(input):
            return failure()
        results = []
        if isinstance(input, dict):
            items = input.items()
        else:
            items = input
        for item in items:
            result = self.formatter.format(item)
            if not result:
                # TODO: what should ForEach do when its formatter fails on a
                # particular item? At this point I'm just having it fail out,
                # but this needs to be thought out to see if that's really the
                # best behavior.
                return failure()
            results.append(result.text)
        return match(self.delimiter.join(results), []) # TODO: should this result in an
        # empty list, or should it result in None instead?


class String(Formatter):
    def format(self, input):
        return match(str(input), None)


class Repr(Formatter):
    def format(self, input):
        return match(repr(input), None)


class Head(Formatter):
    def __init__(self, formatter):
        self.formatter = formatter
    
    def format(self, input):
        if not sequence_type.matches(input):
            return failure()
        if len(input) < 1:
            return failure()
        first = input[0]
        rest = input[1:]
        result = self.formatter.format(first)
        if not result:
            return failure()
        return match(result.text, rest)


class Tail(Formatter):
    def __init__(self, formatter):
        self.formatter = formatter
    
    def format(self, input):
        if not sequence_type.matches(input):
            return failure()
        if len(input) < 1:
            return failure()
        last = input[-1]
        rest = input[:-1]
        result = self.formatter.format(last)
        if not result:
            return failure()
        return match(result.text, rest)


class Type(Formatter):
    def __init__(self, *static_types):
        self.static_type = static.Or(static_types)
    
    def format(self, input):
        if not self.static_type.matches(input):
            return failure()
        return match("", input)


class And(Formatter):
    def __init__(self, first, second):
        self.first = first
        self.second = second
    
    def format(self, input):
        first_result = self.first.format(input)
        if not first_result:
            return failure()
        return self.second.format(input)


class Then(Formatter):
    def __init__(self, first, second):
        self.first = first
        self.second = second
    
    def format(self, input):
        first_result = self.first.format(input)
        if not first_result:
            return failure()
        second_result = self.second.format(first_result.remainder)
        if not second_result:
            return failure()
        return match(first_result.text + second_result.text, second_result.remainder)


class First(Formatter):
    def __init__(self, *formatters):
        self.formatters = formatters
    
    def format(self, input):
        for formatter in self.formatters:
            result = formatter.format(input)
            if result:
                return match(result.text, result.remainder)
        return failure()


class Forward(Formatter):
    def __init__(self):
        self.formatter = None
    
    def format(self, input):
        if self.formatter is None:
            raise Exception("Forward has not yet had a formatter set into it")
        return self.formatter.format(input)
    
    def set(self, formatter):
        self.formatter = formatter
    
    __lshift__ = set


class Is(Formatter):
    def __init__(self, value):
        self.value = value
    
    def format(self, input):
        if input == self.value:
            return match("", input)
        return failure()







































