"""
parcon.py

Parser combinator library written by Alexander Boyd.

Copyright 2011 Alexander Boyd. Released under the terms of the GNU Lesser
General Public License. 

2011.05.31

(I wrote the initial version of this thing in three hours, which goes to show
the power and simplicity of combinatorial parsing.)
"""

import itertools

upper_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
lower_chars = "abcdefghijklmnopqrstuvwxyz"
digit_chars = "0123456789"
whitespace = " \t\r\n"

class Result(object):
    def __init__(self, end, value, reason):
        self.end = end
        self.value = value
        if not isinstance(reason, (FailureReason, type(None))):
            raise TypeError("Not a FailureReason or None: " + str(type(reason)))
        self._reason = reason
    
    def __nonzero__(self):
        return self.end is not None
    
    @property
    def reason(self):
        if not self._reason:
            raise Exception("Can't get the reason of a result that succeeded")
        return self._reason
    
    def __str__(self):
        if self:
            return "<Result: %s ending at %s>" % (self.value, self.end)
        else:
            return "<Result: Failure: %s>" % str(self.reason)
    
    __repr__ = __str__


class FailureReason(object):
    def __init__(self, position, expected):
        self.position = position
        self.expected = flatten(expected)
    
    def __repr__(self):
        return "FailureReason(%s, %s)" % (self.position, self.expected)
    
    def __str__(self):
        return "At position %s: expected one of %s" % (self.position, ", ".join(self.expected))


def failure(*args):
    """
    failure(failure_reason) -> create a failure result from a FailureReason
    failure(position, expected) -> create a new FailureReason and a
    result wrapping it
    """
    if len(args) == 1:
        return Result(None, None, args[0])
    position, expected = args
    return Result(None, None, FailureReason(position, expected))


def match(end, value):
    return Result(end, value, None)


def parse_space(text, position, space):
    result = space.parse(text, position, Invalid())
    while result:
        position = result.end
        result = space.parse(text, position, Invalid())
    return position


def promote(value):
    if isinstance(value, Parser):
        return value
    if isinstance(value, basestring):
        return Literal(value)
    return value


def op_add(first, second):
    first = promote(first)
    second = promote(second)
    if isinstance(first, Parser) and isinstance(second, Parser):
        return Then(first, second)
    return NotImplemented

def op_sub(first, second):
    first = promote(first)
    second = promote(second)
    if isinstance(first, Parser) and isinstance(second, Parser):
        return Except(first, second)
    return NotImplemented

def op_or(first, second):
    first = promote(first)
    second = promote(second)
    if isinstance(first, Parser) and isinstance(second, Parser):
        return First(first, second)
    return NotImplemented

def op_pos(parser):
    return OneOrMore(parser)

def op_neg(parser):
    return Optional(parser)

def op_getitem(parser, function):
    if isinstance(function, slice):
        return Repeat(parser, function.start, function.stop)
    else:
        return Translate(parser, function)


class Parser(object):
    def parse(self, text, position, space):
        raise Exception("Parse not implemented for " + str(type(self)))
    
    def __add__(self, other):
        return op_add(self, other)
    
    def __radd__(self, other):
        return op_add(other, self)
    
    def __sub__(self, other):
        return op_sub(self, other)
    
    def __rsub__(self, other):
        return op_sub(other, self)
    
    def __or__(self, other):
        return op_or(self, other)
    
    def __ror__(self, other):
        return op_or(other, self)
    
    def __getitem__(self, function):
        return op_getitem(self, function)
    
    def __pos__(self):
        return op_pos(self)
    
    def __neg__(self):
        return op_neg(self)


class Invalid(Parser):
    """
    A parser that never matches any input and always fails.
    """
    def parse(self, text, position, space):
        return failure(position, "EOF")


class Literal(Parser):
    """
    A parser that matches the specified literal piece of text. It succeeds
    only if that piece of text is found, and it returns None when it succeeds.
    """
    def __init__(self, text):
        self.text = text
    
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if text[position:position + len(self.text)] == self.text:
            return match(position + len(self.text), None)
        else:
            return failure(position, '"' + self.text + '"')


class SignificantLiteral(Literal):
    """
    A parser that matches the specified literal piece of text. Is succeeds
    only if that piece of text is found. Unlike Literal, however,
    SignificantLiteral returns the literal string passed into it instead of
    None.
    """
    def parse(self, text, position, space):
        result = Literal.parse(self, text, position, space)
        if result:
            return match(result.end, self.text)
        else:
            return failure(position, '"' + self.text + '"')


class CharIn(Parser):
    """
    A parser that matches a single character as long as it is in the specified
    sequence (which can be a string or a list of one-character strings). It
    returns the character matched.
    """
    def __init__(self, chars):
        self.chars = chars
    
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if text[position:position + 1] and text[position:position + 1] in self.chars:
            return match(position + 1, text[position])
        else:
            return failure(position, 'any char in "' + self.chars + '"')


class Digit(CharIn):
    """
    Same as CharIn(digit_chars).
    """
    def __init__(self):
        CharIn.__init__(self, digit_chars)


class Upper(CharIn):
    """
    Same as CharIn(upper_chars).
    """
    def __init__(self):
        CharIn.__init__(self, upper_chars)


class Lower(CharIn):
    """
    Same as CharIn(lower_chars).
    """
    def __init__(self):
        CharIn.__init__(self, lower_chars)


class Alpha(CharIn):
    """
    Same as CharIn(upper_chars + lower_chars).
    """
    def __init__(self):
        CharIn.__init__(self, upper_chars + lower_chars)


class Alphanum(CharIn):
    """
    Same as CharIn(upper_chars + lower_chars + digit_chars).
    """
    def __init__(self):
        CharIn.__init__(self, upper_chars + lower_chars + digit_chars)


class Whitespace(CharIn):
    """
    Same as CharIn(whitespace).
    """
    def __init__(self):
        CharIn.__init__(self, whitespace)


class AnyChar(Parser):
    """
    A parser that matches any single character. It returns the character that
    it matched.
    """
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if text[position:position + 1]: # At least one char left
            return match(position + 1, text[position])
        else:
            return failure(position, "any char")


class Except(Parser):
    """
    A parser that matches and returns whatever the specified parser matches
    and returns, as long as the specified avoidParser does not also match at
    the same location. For example, Except(AnyChar(), Literal("*/")) would
    match any character as long as that character was not a * followed
    immediately by a / character. 
    """
    def __init__(self, parser, avoidParser):
        self.parser = parser
        self.avoidParser = avoidParser
    
    def parse(self, text, position, space):
        # May want to parse space to make sure the two parsers are in sync
        result = self.parser.parse(text, position, space)
        if not result:
            return failure(result.reason)
        avoidResult = self.avoidParser.parse(text, position, space)
        if avoidResult:
            return failure(position, "(TBD: Except)")
        return result


class ZeroOrMore(Parser):
    """
    A parser that matches the specified parser as many times as it can. The
    results are collected into a list, which is then returned. Since
    ZeroOrMore succeeds even if zero matches were made (the empty list will
    be returned in such a case), this parser always succeeds.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, space):
        result = []
        parserResult = self.parser.parse(text, position, space)
        while parserResult:
            result.append(parserResult.value)
            position = parserResult.end
            parserResult = self.parser.parse(text, position, space)
        return match(position, result)


class OneOrMore(Parser):
    """
    Same as ZeroOrMore, but requires that the specified parser match at least
    once.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, space):
        result = []
        parserResult = self.parser.parse(text, position, space)
        while parserResult:
            result.append(parserResult.value)
            position = parserResult.end
            parserResult = self.parser.parse(text, position, space)
        if len(result) == 0:
            return failure(parserResult.reason)
        return match(position, result)


class Then(Parser):
    """
    A parser that matches the first specified parser followed by the second.
    If neither of them matches, or if only one of them matches, this parser
    fails. If both of them match, the result is as followes, assming A and B
    are the results of the first and the second parser, respectively:
    
    If A is None, the result is B.
    If B is None, the result is A.
    If A and B are tuples, the result is A + B.
    If A is a tuple but B is not, the result is A + (B,).
    If B is a tuple but A is not, the result is (A,) + B.
    Otherwise, the result is (A, B).
    """
    def __init__(self, first, second):
        self.first = first
        self.second = second
    
    def parse(self, text, position, space):
        firstResult = self.first.parse(text, position, space)
        if not firstResult:
            return failure(firstResult.reason)
        position = firstResult.end
        secondResult = self.second.parse(text, position, space)
        if not secondResult:
            return failure(secondResult.reason)
        position = secondResult.end
        a, b = firstResult.value, secondResult.value
        if a is None:
            return match(position, b)
        elif b is None:
            return match(position, a)
        if isinstance(a, tuple) and isinstance(b, tuple):
            return match(position, a + b)
        elif isinstance(a, tuple):
            return match(position, a + (b,))
        elif isinstance(b, tuple):
            return match(position, (a,) + b)
        else:
            return match(position, (a, b))


class Discard(Parser):
    """
    A parser that matches if the parser it's constructed with matches. It
    consumes the same amount of input that the specified parser does, but this
    parser always returns None as the result.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, space):
        result = self.parser.parse(text, position, space)
        if result:
            return match(result.end, None)
        else:
            return failure(result.reason)


class First(Parser):
    """
    A parser that tries all of its specified parsers in order. As soon as one
    matches, its result is returned. If none of them match, this parser fails.
    """
    def __init__(self, *parsers):
        self.parsers = parsers
    
    def parse(self, text, position, space):
        errorReasons = []
        for parser in self.parsers:
            result = parser.parse(text, position, space)
            if result:
                return result
            else:
                errorReasons.append(result.reason)
        return failure(position, flatten([reason.expected for reason in errorReasons]))


class Translate(Parser):
    """
    A parser that passes the result of the parser it's created with, if said
    parser matches successfully, through a function, and the function's return
    value is then used as the result. The function is not called if the
    specified parser fails.
    """
    def __init__(self, parser, function):
        self.parser = parser
        self.function = function
    
    def parse(self, text, position, space):
        result = self.parser.parse(text, position, space)
        if not result:
            return failure(result.reason)
        return match(result.end, self.function(result.value))


class Exact(Parser):
    """
    A parser that returns whatever the specified parser returns, but Invalid()
    will be passed as the whitespace parser to the specified parser when its
    parse method is called. This allows for sections of the grammar to take
    whitespace significantly, which is useful in, for example, string literals.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        return self.parser.parse(text, position, Invalid())


class Optional(Parser):
    """
    A parser that returns whatever its underlying parser returns, except that
    if the specified parser fails, this parser succeeds and returns None.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, space):
        result = self.parser.parse(text, position, space)
        if result:
            return result
        else:
            return match(position, None)

class Repeat(Parser):
    """
    A parser that matches its underlying parser a certain number of times. If
    the underlying parser did not match at least min times, this parser fails.
    This parser stops parsing after max times, even if the underlying parser
    would still match. The results of all of the parses are returned as a list.
    """
    def __init__(self, parser, min, max):
        self.parser = parser
        self.min = min
        self.max = max
    
    def parse(self, text, position, space):
        result = []
        parse_result = None
        for i in (xrange(self.max) if self.max is not None else itertools.count(0)):
            parse_result = self.parser.parse(text, position, space)
            if not parse_result:
                break
            position = parse_result.end
            result.append(parse_result.value)
        if self.min and len(result) < self.min:
            if parse_result:
                return failure(parse_result.reason)
            else:
                return failure(position, "(TBD: Repeat)")
        return match(position, result)


class Keyword(Parser):
    """
    A parser that matches the specified parser as long as it is followed
    immediately by the specified terminator parser, or by whitespace
    (according to the current whitespace parser) if a terminator parser is not
    specified.
    """
    def __init__(self, parser, terminator=None):
        self.parser = parser
        self.terminator = promote(terminator)
    
    def parse(self, text, position, space):
        if self.terminator:
            terminator = self.terminator
        else:
            terminator = space
        result = self.parser.parse(text, position, space)
        if not result:
            return failure(result.reason)
        terminatorResult = terminator.parse(text, result.end, space)
        if not terminatorResult:
            return failure(terminatorResult.reason)
        return result


class Forward(Parser):
    """
    A parser that allows forward-definition. In other words, you can create a
    Forward and use it in a parser grammar, and then set the parser that it
    actually represents later on. This is useful for defining grammars that
    need to include themselves (for example, parentheses in a numerical
    expression contain yet another numberical expression, which is an example
    of where this would be used).
    
    You create a forward with something like this:
    
    forward = Forward()
    
    You can then use it in your grammar as you would a normal parser. When
    you're ready to set the parser that the Forward should actually represent,
    you can do it either with:
    
    forward << parser
    
    or with:
    
    forward.set(parser)
    
    Both of them cause the forward to act as if it was really just the
    specified parser.
    
    The parser must be set before parse is called on anything using the
    Forward instance for the first time. This normally shouldn't be a problem.
    """
    def __init__(self):
        self.parser = None
    def parse(self, text, position, space):
        if not self.parser:
            raise Exception("Forward.parse was called before the specified "
                            "Forward instance's set function or << operator "
                            "was used to specify a parser.")
        return self.parser.parse(text, position, space)
    
    def set(self, parser):
        """
        Sets the parser that this Forward should use. After you call this
        method, this Forward acts just like it were really the specified parser.
        """
        parser = promote(parser)
        self.parser = parser
    
    __lshift__ = set


def flatten(value):
    """
    A function that recursively flattens the specified value. Tuples and lists
    are flattened into the items that they contain. The result is a list.
    
    If a single non-list, non-tuple value is passed in, the result is a list
    containing just that item.
    """
    if not isinstance(value, (list, tuple)):
        return [value]
    result = []
    for item in value:
        item = flatten(item)
        result += list(item)
    return result
        








































