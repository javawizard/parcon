"""
parcon.py

Parcon is a parser combinator library written by Alexander Boyd.

To get started, look at all of the subclasses of the Parser class, and
specifically, look at Parser's parse_string method. And perhaps try
running this:

parser = "(" + ZeroOrMore(SignificantLiteral("a") + SignificantLiteral("b")) + ")"
print parser.parse_string("(abbaabaab)")
print parser.parse_string("(a)")
print parser.parse_string("") # should raise an exception
print parser.parse_string("(a") # should raise an exception
print parser.parse_string("(ababacababa)") # should raise an exception

The Parser class, and hence all of its subclasses, overload a few operators
that can be used to make writing parsers easier. Here's what each operator
ends up translating to:

x + y is the same as Then(x, y).
x | y is the same as First(x, y).
-x is the same as Optional(x).
+x is the same as OneOrMore(x).
x - y is the same as Except(x, y).
x[min:max] is the same as Repeat(x, min, max).
x[...] (three literal dots) is the same as ZeroOrMore(x).
x[function] is the same as Translate(x, function).
"x" op some_parser or some_parser op "x" is the same as Literal("x") op 
       some_parser or some_parser op Literal("x"), respectively.

A simple expression evaluator written using Parcon:

from parcon import *
from decimal import Decimal
import operator
expr = Forward()
number = (+Digit() + -(SignificantLiteral(".") + +Digit()))[flatten]["".join][Decimal]
term = number | "(" + expr + ")"
term = InfixExpr(term, [("*", operator.mul), ("/", operator.truediv)])
term = InfixExpr(term, [("+", operator.add), ("-", operator.sub)])
expr << term

Some example expressions that can now be evaluated using the above
simple expression evaluator:

print expr.parse_string("1+2") # prints 3
print expr.parse_string("1+2+3") # prints 6
print expr.parse_string("1+2+3+4") # prints 10
print expr.parse_string("3*4") # prints 12
print expr.parse_string("5+3*4") # prints 17
print expr.parse_string("(5+3)*4") # prints 32
print expr.parse_string("10/4") # prints 2.5

Another example use of Parcon, this one being a JSON parser (essentially
a reimplementation of Python's json.dumps, without all of the fancy
arguments that it supports, and currently without support for backslash
escapes in JSON string literals):

from parcon import *
import operator
cat_dicts = lambda x, y: dict(x.items() + y.items())
json = Forward()
number = (+Digit() + -(SignificantLiteral(".") + +Digit()))[flatten]["".join][float]
boolean = Literal("true")[lambda x: True] | Literal("false")[lambda x: False]
string = ('"' + Exact(ZeroOrMore(AnyChar() - CharIn('\\"'))) +  '"')["".join]
null = Literal("null")[lambda x: None]
pair = (string + ":" + json[lambda x: (x,)])[lambda x: {x[0]: x[1]}]
json_object = ("{" + Optional(InfixExpr(pair, [(",", cat_dicts)]), {}) + "}")
json_list = ("[" + Optional(InfixExpr(json[lambda x: [x]], [(",", operator.add)]), []) + "]")
json << (json_object | json_list | string | boolean | null | number)

Thereafter, json.parse_string(text) can be used as a replacement for
Python's json.loads.
"""

# Parcon is Copyright 2011 Alexander Boyd. Released under the
# terms of the GNU Lesser General Public License.

import itertools

upper_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
lower_chars = "abcdefghijklmnopqrstuvwxyz"
alpha_chars = upper_chars + lower_chars
digit_chars = "0123456789"
alphanum_chars = alpha_chars + digit_chars
whitespace = " \t\r\n"

class Result(object):
    """
    A result from a parser. Parcon users usually won't have any use for
    instances of this class since it's primarily used internally by Parcon, but
    if you're implementing your own Parser subclass, then you'll likely find
    this class useful since you'll be returning instances of it.
    """
    def __init__(self, end, value, expected):
        self.end = end
        self.value = value
        if not isinstance(expected, list):
            expected = [expected]
        self.expected = expected
    
    def __nonzero__(self):
        return self.end is not None
    
    def __str__(self):
        if self:
            return "<Result: %s ending at %s>" % (self.value, self.end)
        else:
            return "<Result: Failure: %s>" % str(self.expected)
    
    __repr__ = __str__


def failure(expected):
    """
    Returns a Result representing a failure of a parser to match. expected is
    a list of expectations that would have had to be satisfied in the text
    passed to the parser calling this method in order for it to potentially
    succeed. Expectations are 2-tuples of the position at which some particular
    piece of text was expected and a string describing the text, such as
    'any char' or '"literal-text"'.
    """
    return Result(None, None, expected)


def match(end, value, expected):
    """
    Returns a Result representing a parser successfully matching. end is the
    position in the string just after where the parser finished, or rather,
    where the next parser after this one would be expected to start parsing.
    value is the value that this parser resulted in, which is typically
    specific to the parser calling this function. expected is a list of
    expectations that would have allowed this parser to match more input than
    it did; this parameter takes the same format as its corresponding parameter
    to the failure function.
    """
    return Result(end, value, expected)


def format_failure(expected):
    """
    Formats a list of expectations into a failure message of the form:
    
    At position n: expected one of x, y, z
    """
    if len(expected) == 0:
        return "(No expectations present, so an error message can't be constructed)"
    max_position = max(expected, key=lambda (position, expectation): position)[0]
    expectations = filter(lambda (position, expectation): position == max_position, expected)
    expectations = [expectation for (position, expectation) in expectations]
    return "At position %s: expected one of %s" % (max_position, ", ".join(expectations))


def parse_space(text, position, space):
    """
    Repeatedly applies the specified whitespace parser to the specified text
    starting at the specified position until it no longer matches. The result
    of all of these parses will be discarded, and the location at which the
    whitespace parser failed will be returned.
    """
    result = space.parse(text, position, Invalid())
    while result:
        position = result.end
        result = space.parse(text, position, Invalid())
    return position


def promote(value):
    """
    Converts a value of some type to an appropriate parser. Right now, this
    returns the value as is if it's an instance of Parser, or Literal(value) if
    the value is a string.
    """
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
    elif function == Ellipsis:
        return ZeroOrMore(parser)
    else:
        return Translate(parser, function)


class Parser(object):
    """
    A parser. This class cannot itself be instantiated; you can only use one of
    its subclasses. Most classes in this module are Parser subclasses.
    
    The method you'll typically use on Parser objects is parse_string.
    """
    def parse(self, text, position, space):
        raise Exception("Parse not implemented for " + str(type(self)))
    
    def parse_string(self, string, all=True, whitespace=None):
        """
        Parses a string using this parser and returns the result, or throws an
        exception if the parser does not match. If all is True (the default),
        an exception will be thrown if this parser does not match all of the
        input. Otherwise, if the parser only matches a portion of the input
        starting at the beginning, just that portion will be returned.
        
        whitespace is the whitespace parser to use; this parser will be applied
        (and its results discarded) between matching every other parser while
        attempting to parse the specified string. A typical grammar might have
        this parser represent whitespace and comments. An instance of Exact can
        be used to suppress whitespace parsing for a portion of the grammar,
        which you would most likely use in, for example, string literals. The
        default value for this parameter is Whitespace().
        """
        if whitespace is None:
            whitespace = Whitespace()
        result = self.parse(string, 0, whitespace)
        if result and (result.end == len(string) or not all):
            # Result matched, and either the entire string was parsed or we're
            # not trying to parse the entire string.
            return result.value
        else:
            raise Exception("Parse failure: " + format_failure(result.expected))
        return result.value
            
    
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
    
    def __str__(self):
        return self.__repr__()


class Invalid(Parser):
    """
    A parser that never matches any input and always fails.
    """
    def parse(self, text, position, space):
        return failure((position, "EOF"))
    
    def __repr__(self):
        return "Invalid()"


class Literal(Parser):
    """
    A parser that matches the specified literal piece of text. It succeeds
    only if that piece of text is found, and it returns None when it succeeds.
    If you need the return value to be the literal piece of text, you should
    probably use SignificantLiteral instead.
    """
    def __init__(self, text):
        self.text = text
    
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if text[position:position + len(self.text)] == self.text:
            return match(position + len(self.text), None, [(position + len(self.text), "EOF")])
        else:
            return failure((position, '"' + self.text + '"'))
    
    def __repr__(self):
        return "Literal(%s)" % repr(self.text)


class SignificantLiteral(Literal):
    """
    A parser that matches the specified literal piece of text. Is succeeds
    only if that piece of text is found. Unlike Literal, however,
    SignificantLiteral returns the literal string passed into it instead of
    None.
    """
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if text[position:position + len(self.text)] == self.text:
            return match(position + len(self.text), self.text, [(position + len(self.text), "EOF")])
        else:
            return failure((position, '"' + self.text + '"'))
    
    def __repr__(self):
        return "SignificantLiteral(%s)" % repr(self.text)


class AnyCase(Parser):
    """
    A case-insensitive version of Literal. Behaves exactly the same as Literal
    does, but without regard to the case of the input.
    """
    def __init__(self, text):
        self.text = text.lower()
    
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if text[position:position + len(self.text)].lower() == self.text:
            return match(position + len(self.text), None, [(position + len(self.text), "EOF")])
        else:
            return failure((position, '"' + self.text + '"'))
    
    def __repr__(self):
        return "AnyCase(%s)" % repr(self.text)


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
            return match(position + 1, text[position], [(position + 1, "EOF")])
        else:
            return failure([(position, 'any char in "' + self.chars + '"')])
    
    def __repr__(self):
        return "CharIn(" + repr(self.chars) + ")"


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
    
    def __repr__(self):
        return "Whitespace()"


class AnyChar(Parser):
    """
    A parser that matches any single character. It returns the character that
    it matched.
    """
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if text[position:position + 1]: # At least one char left
            return match(position + 1, text[position], [(position + 1, "EOF")])
        else:
            return failure([(position, "any char")])
    
    def __repr__(self):
        return "AnyChar()"


class Except(Parser):
    """
    A parser that matches and returns whatever the specified parser matches
    and returns, as long as the specified avoidParser does not also match at
    the same location. For example, Except(AnyChar(), Literal("*/")) would
    match any character as long as that character was not a * followed
    immediately by a / character. This would most likely be useful in, for
    example, a parser designed to parse C-style comments.
    """
    def __init__(self, parser, avoidParser):
        self.parser = parser
        self.avoidParser = avoidParser
    
    def parse(self, text, position, space):
        # May want to parse space to make sure the two parsers are in sync
        result = self.parser.parse(text, position, space)
        if not result:
            return failure(result.expected)
        avoidResult = self.avoidParser.parse(text, position, space)
        if avoidResult:
            return failure([(position, "(TBD: Except)")])
        return result
    
    def __repr__(self):
        return "Except(%s, %s)" % (repr(self.parser), repr(self.avoidParser))


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
        return match(position, result, parserResult.expected)
    
    def __repr__(self):
        return "ZeroOrMore(%s)" % repr(self.parser)


class OneOrMore(Parser):
    """
    Same as ZeroOrMore, but requires that the specified parser match at least
    once. If it does not, this parser will fail.
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
            return failure(parserResult.expected)
        return match(position, result, parserResult.expected)
    
    def __repr__(self):
        return "OneOrMore(%s)" % repr(self.parser)


class Then(Parser):
    """
    A parser that matches the first specified parser followed by the second.
    If neither of them matches, or if only one of them matches, this parser
    fails. If both of them match, the result is as follows, assuming A and B
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
            return failure(firstResult.expected)
        position = firstResult.end
        secondResult = self.second.parse(text, position, space)
        if not secondResult:
            return failure(firstResult.expected + secondResult.expected)
        position = secondResult.end
        a, b = firstResult.value, secondResult.value
        if a is None:
            return match(position, b, secondResult.expected)
        elif b is None:
            return match(position, a, secondResult.expected)
        if isinstance(a, tuple) and isinstance(b, tuple):
            return match(position, a + b, secondResult.expected)
        elif isinstance(a, tuple):
            return match(position, a + (b,), secondResult.expected)
        elif isinstance(b, tuple):
            return match(position, (a,) + b, secondResult.expected)
        else:
            return match(position, (a, b), secondResult.expected)
    
    def __repr__(self):
        return "Then(%s, %s)" % (repr(self.first), repr(self.second))


class Discard(Parser):
    """
    A parser that matches if the parser it's constructed with matches. It
    consumes the same amount of input that the specified parser does, but this
    parser always returns None as the result. Since instances of Then treat
    None values specially, you'll likely use this parser in conjunction with
    Then in some grammars.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, space):
        result = self.parser.parse(text, position, space)
        if result:
            return match(result.end, None, result.expected)
        else:
            return failure(result.expected)
    
    def __repr__(self):
        return "Discard(" + repr(self.parser) + ")"


class First(Parser):
    """
    A parser that tries all of its specified parsers in order. As soon as one
    matches, its result is returned. If none of them match, this parser fails.
    """
    def __init__(self, *parsers):
        self.parsers = parsers
    
    def parse(self, text, position, space):
        expectedForErrors = []
        for parser in self.parsers:
            result = parser.parse(text, position, space)
            if result:
                return result
            else:
                expectedForErrors += result.expected
        return failure(expectedForErrors)
    
    def __repr__(self):
        return "First(%s)" % ", ".join(repr(parser) for parser in self.parsers)


class Longest(Parser):
    """
    A parser that tries all of its specified parsers. The longest one that
    succeeds is chosen, and its result is returned. If none of the parsers
    succeed, Longest fails.
    """
    def __init__(self, *parsers):
        self.parsers = parsers
    
    def parse(self, text, position, space):
        expectedForErrors = []
        successful = []
        for parser in self.parsers:
            result = parser.parse(text, position, space)
            if result:
                successful.append(result)
            else:
                expectedForErrors += result.expected
        if len(successful) == 0:
            return failure(expectedForErrors)
        return max(successful, key=lambda result: result.end)
    
    def __repr__(self):
        return "Longest(%s)" % ", ".join(repr(parser) for parser in self.parsers)


class Translate(Parser):
    """
    A parser that passes the result of the parser it's created with, if said
    parser matches successfully, through a function, and the function's return
    value is then used as the result. The function is not called if the
    specified parser fails.
    
    For example, the following parser would use the flatten function provided
    by parcon to flatten any lists and tuples produced by the parser
    example_parser:
    
    Translate(example_parser, flatten)
    
    The following parser would likewise expect another_parser to produce a list
    of strings and concatenate them together into a single result string:
    
    Translate(another_parser, "".join)
    """
    def __init__(self, parser, function):
        self.parser = parser
        self.function = function
    
    def parse(self, text, position, space):
        result = self.parser.parse(text, position, space)
        if not result:
            return failure(result.expected)
        return match(result.end, self.function(result.value), result.expected)
    
    def __repr__(self):
        return "Translate(%s, %s)" % (repr(self.parser), repr(self.function))


class Exact(Parser):
    """
    A parser that returns whatever the specified parser returns, but Invalid()
    will be passed as the whitespace parser to the specified parser when its
    parse method is called. This allows for sections of the grammar to take
    whitespace significantly, which is useful in, for example, string literals.
    For example, the following parser, intended to parse string literals,
    demonstrates the problem:
    
    stringLiteral = '"' + ZeroOrMore(AnyChar() - '"') + '"'
    result = stringLiteral.parse_string('"Hello, great big round world"')
    
    After running that, result would have the value "Hello,greatbigroundworld".
    This is because the whitespace parser (which defaults to Whitespace())
    consumed all of the space in the string literal. This can, however, be
    rewritten using Exact to mitigate this problem:

    stringLiteral = '"' + Exact(ZeroOrMore(AnyChar() - '"')) + '"'
    result = stringLiteral.parse_string('"Hello, great big round world"')
    
    This parser produces the correct result, 'Hello, great big round world'.
    """
    def __init__(self, parser, space_parser=Invalid()):
        self.parser = parser
        self.space_parser = space_parser
    
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        return self.parser.parse(text, position, self.space_parser)
    
    def __repr__(self):
        return "Exact(" + repr(self.parser) + ")"


class Optional(Parser):
    """
    A parser that returns whatever its underlying parser returns, except that
    if the specified parser fails, this parser succeeds and returns the default
    result specified to it (which, itself, defaults to None).
    """
    def __init__(self, parser, default=None):
        self.parser = parser
        self.default = default
    
    def parse(self, text, position, space):
        result = self.parser.parse(text, position, space)
        if result:
            return result
        else:
            return match(position, self.default, result.expected)
    
    def __repr__(self):
        return "Optional(%s, %s)" % (repr(self.parser), repr(self.default))

class Repeat(Parser):
    """
    A parser that matches its underlying parser a certain number of times. If
    the underlying parser did not match at least min times, this parser fails.
    This parser stops parsing after max times, even if the underlying parser
    would still match. The results of all of the parses are returned as a list.
    
    If max is None, no maximum limit will be enforced. The same goes for min.
    
    Repeat(parser, 0, None) is the same as ZeroOrMore(parser), and
    Repeat(parser, 1, None) is the same as OneOrMore(parser).
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
            return failure(parse_result.expected)
        return match(position, result, parse_result.expected)
    
    def __repr__(self):
        return "Repeat(%s, %s, %s)" % (repr(self.parser), repr(self.min), repr(self.max))


class Keyword(Parser):
    """
    A parser that matches the specified parser as long as it is followed
    immediately by the specified terminator parser, or by whitespace
    (according to the current whitespace parser) if a terminator parser is not
    specified.
    """
    def __init__(self, parser, terminator=None):
        self.parser = promote(parser)
        self.terminator = promote(terminator) if terminator is not None else None
    
    def parse(self, text, position, space):
        if self.terminator:
            terminator = self.terminator
        else:
            terminator = space
        result = self.parser.parse(text, position, space)
        if not result:
            return failure(result.expected)
        terminatorResult = terminator.parse(text, result.end, space)
        if not terminatorResult:
            return failure(terminatorResult.expected)
        return result
    
    def __repr__(self):
        return "Keyword(%s, %s)" % (repr(self.parser), repr(self.terminator))


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
    
    def __repr__(self):
        return "Forward()"


class InfixExpr(Parser):
    """
    A parser that's created with a component parser and a series of operator
    parsers, which can be literal strings (and will be translated to Literal
    instances), and two-argument functions for each of these operator parsers.
    It parses expressions of the form "component" or "component op component"
    or "component op component op component" etc. For each op it encounters in
    the result it parses, it calls the two-arg function supplied with that
    operator, passing in the value of the parser on its left and the value of
    the parser on its right. It then stores the result, and moves onto the next
    operator, this time using the aforementioned result as the left-hand value
    for the next operator.
    
    This reduction of values proceeds from left to right, which makes InfixExpr
    implement a left-associative infix grammar. In the future, there will be a
    way to specify that certain operators should be right-associative instead.
    
    If only a single component is present, InfixExpr will match that and return
    whatever the component resulted in. If not even a single component is
    present, InfixExpr will fail to match.
    """
    def __init__(self, component_parser, operators):
        """
        Creates an InfixExpr. component_parser is the parser that will parse
        the individual components of the expression. operators is a list of
        2-tuples; each tuple represents an operator, with the first item in the
        tuple being a parser that parses the operator itself (or a literal
        string, such as "+", "-", etc, which will be wrapped with a Literal
        instance) and the second item being a two-arg function that will be
        used to reduce components on either side of the operator to get a
        result.
        """
        self.component = component_parser
        if len(operators) == 0:
            raise Exception("InfixExpr must be created with at least one operator")
        self.operators = [(promote(op), function) for op, function in operators]
    
    def parse(self, text, position, space):
        # Parse the first component
        component_result = self.component.parse(text, position, space)
        if not component_result:
            return failure(component_result.expected)
        # Set up initial values from the first component
        value = component_result.value
        position = component_result.end
        # Now try to parse the rest of the "op component" pairs
        while True:
            found_op = False
            ops_expected = []
            # Add the expectations for the last component
            ops_expected += component_result.expected
            # Try each operator's op parser in sequence
            for op_parser, op_function in self.operators:
                op_result = op_parser.parse(text, position, space)
                if op_result:
                    # This operator matched, so we break out of our loop
                    found_op = True
                    break
                else:
                    # This operator didn't match, so we add its failure
                    # expectations to the list and move on to the next operator
                    ops_expected += op_result.expected
            if not found_op: # No more operators, so we return the current value
                return match(position, value, ops_expected)
            # We have an operator. Now we set the new position and try to parse
            # a component following it.
            component_result = self.component.parse(text, op_result.end, space)
            if not component_result:
                # Component didn't match, so we return the current value, along
                # with the component's expectation and the expectations of the
                # operator that matched
                return match(position, value, component_result.expected + op_result.expected)
            # Component did match, so we set the position to the end of where
            # the component matched to, get the component's value, and reduce
            # it with the current value using the op function
            position = component_result.end
            value = op_function(value, component_result.value)
            # and then we start the whole thing over again, trying to parse
            # another operator.
    
    def __repr__(self):
        return "InfixExpr(%s, %s)" % (repr(self.component), repr(self.operators))


class Bind(Parser):
    """
    A parser that functions similar to Then, but that allows the second parser
    to be determined from the value that the first parser produced. It's
    constructed as Bind(parser, function). parser is the first parser to run.
    function is a function that accepts one argument, the value that the first
    parser produced. It will be called whenever the first parser succeeds; the
    value that the first parser produced will be passed in, and the function
    should return a second parser. This parser will then be applied immediately
    after where the first parser finished parsing from (similar to how Then
    starts its second parser parsing after where its first parser finished).
    Bind then returns the value that the second parser produced.
    
    Those of you familiar with functional programming will notice that this
    parser implements a monadic bind, hence its name.
    """
    def __init__(self, parser, function):
        self.parser = parser
        self.function = function
    
    def parse(self, text, position, whitespace):
        first_result = self.parser.parse(text, position, whitespace)
        if not first_result:
            return failure(first_result.expected)
        second_parser = self.function(first_result.value)
        second_result = second_parser.parse(text, first_result.end, whitespace)
        if not second_result:
            return failure(second_result.expected + first_result.expected)
        return match(second_result.end, second_result.value, second_result.expected)


class Return(Parser):
    """
    A parser that always succeeds, consumes no input, and always returns a
    value specified when the Return instance is constructed.
    
    Those of you familiar with functional programming will notice that this
    parser implements a monadic return, hence its name.
    """
    def __init__(self, value):
        self.value = value
    
    def parse(self, text, position, whitespace):
        return match(position, self.value, [(position, "EOF")])


class Chars(Parser):
    """
    A parser that parses a specific number of characters and returns them as
    a string. Chars(5), for example, would parse exactly five characters in a
    row, and return a string of length 5. This would be essentially identical
    to AnyChar()[5:5]["".join], except for two things: 1, the whitespace parser
    is not applied in between each character parsed by Chars (although it is
    applied just before the first character), and 2, Chars is much more
    efficient than the aforementioned expression using AnyChar.
    
    This can be used in combination with Bind to create a parser that parses
    a binary protocol where a fixed number of bytes are present that specify
    the length of the rest of a particular packet, followed by the rest of the
    packet itself. For example, imagine a protocol where packets look like this:
    
    length b1 b2 b3 ... blength
    
    a.k.a. a byte indicating the length of the data carried in that packet,
    followed by the actual data of the packet. Such a packet could be parsed
    into a string containing the data of a single packet with this:
    
    Bind(AnyChar(), lambda x: Chars(ord(x)))
    """


class Word(Parser):
    """
    A parser that parses a word consisting of a certain set of allowed
    characters. A minimum and maximum word length can also be specified, as can
    a set of characters of which the first character in the word must be a
    member.
    
    If min is unspecified, it defaults to 1. Max defaults to None, which places
    no upper limit on the number of characters that can be in this word.
    
    Word parses as many characters as it can that are in the specified
    character set until it's parsed the specified maximum number of characters,
    or it hits a character not in the specified character set. If, at that
    point, the number of characters parsed is less than min, this parser fails.
    Otherwise, it succeeds and produces a string containing all the characters.
    
    min can be zero, which will allow this parser to succeed even if there are
    no characters available or if the first character is not in init_chars.
    The empty string will be returned in such a case.
    """
    def __init__(self, chars, init_chars=None, min=1, max=None):
        self.chars = chars
        if init_chars:
            self.init_chars = init_chars
        else:
            self.init_chars = chars
        self.min = min
        self.max = max
    
    def parse(self, text, position, space):
        position = parse_space(text, position, space)
        if not text[position:position + 1] or text[position:position + 1] not in self.init_chars: # Initial char
            # not present or not one of the ones we expected
            if min == 0:
                return match(position, "", [(position, 'any char in "%s"' % self.init_chars)])
            else:
                return failure([(position, 'one of "%s"' % self.init_chars)])
        # Found initial char. Store it, then start parsing the rest of the chars
        char_list = [text[position]]
        position += 1
        parsed_so_far = 1
        while text[position:position + 1] and text[position:position + 1] in self.chars and (self.max is None or parsed_so_far < self.max):
            char_list.append(text[position])
            position += 1
            parsed_so_far += 1
        if len(char_list) < self.min:
            return failure([(position, 'any char in "%s"' % self.chars)])
        return match(position, "".join(char_list), [(position, 'any char in "%s"' % self.chars)])


class Present(Parser):
    """
    A lookahead parser; it matches as long as the parser it's constructed with
    matches at the specified position, but it doesn't actually consume any
    input, and its result is None.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, space):
        result = self.parser.parse(text, position, space)
        if result:
            return match(position, None, [(position, "EOF")])
        else:
            return failure(result.expected)


alpha_word = Word(alpha_chars)
alphanum_word = Word(alphanum_chars)
# Need to decide on a better name for this
# alpha_alphanum_word = Word(alphanum_chars, init_chars=alpha_chars)


def flatten(value):
    """
    A function that recursively flattens the specified value. Tuples and lists
    are flattened into the items that they contain. The result is a list.
    
    If a single non-list, non-tuple value is passed in, the result is a list
    containing just that item. If, however, that value is None, the result is
    the empty list.
    
    This function is intended to be used as the function passed to Translate
    where the parser passed to Translate could produce multiple nested lists of
    tuples and lists, and a single, flat, list is desired.
    """
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        return [value]
    result = []
    for item in value:
        item = flatten(item)
        result += list(item)
    return result
 








































