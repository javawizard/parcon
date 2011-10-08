"""
parcon.py

Parcon is a parser library written by Alexander Boyd and James Stoker. It's
designed to be fast, easy to use, and to provide informative error messages.

(and it's designed to include new, awesome things, like syntax diagram
generators.)

Technically, it's a monadic parser combinator library, but you don't need to
know that unless you're doing really fancy things. (The bind and return
operations are provided by the Bind and Return parsers, respectively.) It's
also technically a parser combinator library, but again, you usually won't need
to know that.

Parcon grammars are written as Python statements that make use of various
classes provided with Parcon.

Parcon also supports generation of graphs and generation of syntax diagrams
(also known as railroad diagrams) from parsers. See the parcon.graph and
parcon.railroad modules, respectively, for information on how to generate these
graphs and diagrams.

To get started with Parcon, look at all of the subclasses of Parser, _GParser,
_RParser, and _GRParser, and specifically, their parse_string methods. And
perhaps take a look at this example:

>>> parser = "(" + ZeroOrMore(SignificantLiteral("a") | SignificantLiteral("b")) + ")"
>>> parser.parse_string("(abbaabaab)")
['a', 'b', 'b', 'a', 'a', 'b', 'a', 'a', 'b']
>>> parser.parse_string("(a)")
['a']
>>> parser.parse_string("")
Traceback (most recent call last):
ParseException: Parse failure: At position 0: expected one of "("
>>> parser.parse_string("(a")
Traceback (most recent call last):
ParseException: Parse failure: At position 2: expected one of "a", "b", ")"
>>> parser.parse_string("(ababacababa)")
Traceback (most recent call last):
ParseException: Parse failure: At position 6: expected one of "a", "b", ")"

The Parser class, and hence all of its subclasses, overload a few operators
that can be used to make writing parsers easier. Here's what each operator
ends up translating to:

x + y is the same as Then(x, y).
x | y is the same as First(x, y).
x - y is the same as Except(x, y).
x & y is the same as And(x, y).
-x is the same as Optional(x).
+x is the same as OneOrMore(x).
~x is the same as Discard(x).
x[min:max] is the same as Repeat(x, min, max).
x[some_int] is the same as Repeat(x, some_int, some_int).
x[some_string] is the same as Tag(some_string, x).
x[...] (three literal dots) is the same as ZeroOrMore(x).
x[function] is the same as Translate(x, function).
x(name="test") is the same as Name("test", x).
x(desc="test") or x(description="test") is the same as Desc("test", x)
"x" op some_parser or some_parser op "x" is the same as Literal("x") op 
       some_parser or some_parser op Literal("x"), respectively.

A simple expression evaluator written using Parcon:

>>> from parcon import number, Forward, InfixExpr
>>> import operator
>>> expr = Forward()
>>> term = number[float] | "(" + expr + ")"
>>> term = InfixExpr(term, [("*", operator.mul), ("/", operator.truediv)])
>>> term = InfixExpr(term, [("+", operator.add), ("-", operator.sub)])
>>> expr << term(name="expr")

Some example expressions that can now be evaluated using the above
simple expression evaluator:

>>> expr.parse_string("1+2")
3.0
>>> expr.parse_string("1+2+3")
6.0
>>> expr.parse_string("1+2+3+4")
10.0
>>> expr.parse_string("3*4")
12.0
>>> expr.parse_string("5+3*4")
17.0
>>> expr.parse_string("(5+3)*4")
32.0
>>> expr.parse_string("10/4")
2.5

A syntax diagram can also be generated for the expression parser with:

expr.draw_productions_to_png({}, "expr-syntax.png")

Another example use of Parcon, this one being a JSON parser (essentially
a reimplementation of Python's json.dumps, without all of the fancy
arguments that it supports, and currently without support for backslash
escapes in JSON string literals):

>>> from parcon import *
>>> import operator
>>> cat_dicts = lambda x, y: dict(x.items() + y.items())
>>> json = Forward()
>>> number = (+Digit() + -(SignificantLiteral(".") + +Digit()))[flatten]["".join][float]
>>> boolean = Literal("true")[lambda x: True] | Literal("false")[lambda x: False]
>>> string = ('"' + Exact(ZeroOrMore(AnyChar() - CharIn('\\"'))) +  '"')["".join]
>>> null = Literal("null")[lambda x: None]
>>> pair = (string + ":" + json[lambda x: (x,)])[lambda x: {x[0]: x[1]}]
>>> json_object = ("{" + Optional(InfixExpr(pair, [(",", cat_dicts)]), {}) + "}")
>>> json_list = ("[" + Optional(InfixExpr(json[lambda x: [x]], [(",", operator.add)]), []) + "]")
>>> json << (json_object | json_list | string | boolean | null | number)

Thereafter, json.parse_string(text) can be used as a replacement for
Python's json.loads.

An interesting fact: the set of all Parcon parsers form a monoid with the
binary operation being the Then parser (or the + operator, since it produces a
Then parser) and the identity element being Return(None).
"""

# Parcon is Copyright 2011 Alexander Boyd. Released under the
# terms of the GNU Lesser General Public License.

import itertools
from parcon import static
import re
import collections
from parcon.graph import Graphable as _Graphable
from parcon import railroad as _rr
from parcon.railroad import regex as _rr_regex

upper_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
lower_chars = "abcdefghijklmnopqrstuvwxyz"
alpha_chars = upper_chars + lower_chars
digit_chars = "0123456789"
alphanum_chars = alpha_chars + digit_chars
whitespace = " \t\r\n"

Pair = collections.namedtuple("Pair", ("key", "value"))


class ParseException(Exception):
    pass


class Expectation(object):
    """
    NOTE: Most users won't need to know about this class or any of its
    subclasses. They're usually only used internally by Parcon, but advanced
    users may wish to use them.
    
    An expectation. Instances of the various subclasses of this class are
    provided as part of a Result object to indicate what could have made a
    parser succeed if it failed, or consume more input if it succeeded.
    Expectations are used to format the error message when Parser.parse_string
    throws an exception because of a parse error.
    
    This class should not be instantiated directly; one of its various
    subclasses should be used instead.
    """
    def format(self):
        """
        Formats this expectation into a human-readable string. For example,
        EStringLiteral("hello").format() returns '"hello"', and
        EAnyCharIn("abc").format() returns 'any char in "abc"'.
        
        Subclasses must override this method; Expectation's implementation of
        the method raises NotImplementedError.
        """
        raise NotImplementedError
    
    def __str__(self):
        return "Expectation()"
    
    def __repr__(self):
        return self.__str__()


expectation_list_type = static.compile([static.Positional(int, Expectation)])


class EUnsatisfiable(Expectation):
    """
    An expectation indicating that there is no input that could have been
    present that would have made the parser in question succeed or consume more
    input. Invalid(), for example, returns EUnsatisfiable() since nothing will
    make an Invalid match, and EStringLiteral, when it succeeds, returns
    EUnsatisfiable() since there isn't any additional text that could be added
    that would make EStringLiteral consume more of the input.
    
    EUnsatisfiable is treated specially by format_failure; instances of it are
    removed if there are expectations of any other type in the list provided
    to format_failure. If there are not, the EUnsatisfiable with the greatest
    position (expectations are stored as tuples of (position, Expectation)) is
    used, and the message will look something like "At position n: expected
    EOF".
    """
    def format(self):
        return "EOF"
    
    def __str__(self):
        return "EUnsatisfiable()"


class EStringLiteral(Expectation):
    """
    An expectation indicating that some literal string was expected. When
    formatted, the string will be enclosed in double quotes. In the future, I
    may have the representation as returned from Python's repr function be used
    instead.
    """
    def __init__(self, text):
        self.text = text
    
    def format(self):
        return '"' + self.text + '"'
    
    def __str__(self):
        return "EStringLiteral(%s)" % repr(self.text)

class ERegex(Expectation):
    """
    An expectation indicating that some regular expression was expected.
    """
    def __init__(self, pattern_text):
        self.pattern_text = pattern_text
    
    def format(self):
        return 'regex "' + self.pattern_text + '"'
    
    def __str__(self):
        return "ERegex(%s)" % repr(self.pattern_text)


class EAnyCharIn(Expectation):
    """
    An expectation indicating that any character in a particular sequence of
    characters (a list of one-character strings, or a string containing the
    expected characters) was expected.
    """
    def __init__(self, chars):
        self.chars = chars
    
    def format(self):
        return 'any char in "' + "".join(self.chars) + '"'
    
    def __str__(self):
        return "EAnyCharIn(%s)" % repr(self.chars)


class EAnyCharNotIn(Expectation):
    """
    An expectation indicating that any character not in a particular sequence of
    characters (a list of one-character strings, or a string containing the
    expected characters) was expected.
    """
    def __init__(self, chars):
        self.chars = chars
    
    def format(self):
        return 'any char not in "' + "".join(self.chars) + '"'
    
    def __str__(self):
        return "EAnyCharNotIn(%s)" % repr(self.chars)


class EAnyChar(Expectation):
    """
    An expectation indicating that any character was expected.
    """
    def format(self):
        return "any char"
    
    def __str__(self):
        return "EAnyChar()"


class ECustomExpectation(Expectation):
    """
    An expectation indicating that some custom value was expected. This is used
    when instances of the Expected parser fail. Users implementing their own
    subclass of Parser that don't want to write a corresponding subclass of
    Expectation but that find that none of the current subclasses of
    Expectation fit their needs might also want to use ECustomExpectation.
    """
    def __init__(self, message):
        self.message = message
    
    def format(self):
        return self.message
    
    def __str__(self):
        return "ECustomExpectation(%s)" % repr(self.message)


class Result(object):
    """
    A result from a parser. Parcon users usually won't have any use for
    instances of this class since it's primarily used internally by Parcon, but
    if you're implementing your own Parser subclass, then you'll likely find
    this class useful since you'll be returning instances of it.
    
    You typically don't create instances of Result directly; instead, you
    usually call either match() or failure(), which return result objects
    indicating success or failure, respectively.
    
    Three fields are made available on a Result object:
    
        expected: A list of expectations in the same format as provided to the
        failure() function
        
        end: The position at which the parser finished parsing, if this result
        indicates success. The value is undefined in the case of a failure.
        
        value: The value that the parser produced, if this result indicates
        success. The value is undefined in the case of a failure.
    
    You can test whether or not a result indicates success by using it as a
    boolean. For example:
    
    >>> successful_result = match(0, "some random value", [])
    >>> failed_result = failure([(0, EUnsatisfiable())])
    >>> if successful_result:
    ...     print "Yes"
    ... else:
    ...     print "No"
    ...
    Yes
    >>> if failed_result:
    ...     print "Yes"
    ... else:
    ...     print "No"
    ...
    No
    """
    def __init__(self, end, value, expected):
        self.end = end
        self.value = value
        if not isinstance(expected, list):
            expected = [expected]
        # This was causing performance to significantly degrade, so it's gone
        # for now. I might add some sort of switch to selectively enable it
        # at some point.
        # expectation_list_type.check_matches(expected)
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
    piece of text was expected and an instance of one of the subclasses of
    Expectation describing what was expected.
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


def filter_expectations(expected):
    """
    Extracts the expectations from the specified expectation list, which should
    be of the same format as that passed to failure(), that have the maximum
    position within the list. A tuple (position, expectations) will then be
    returned, where position is the maximum position and expectations is the
    list of expectations at that position.
    
    If the specified list is empty, (0, []) will be returned.
    
    All instances of EUnsatisfiable will be filtered from the expectation list,
    unless it consists only of EUnsatisfiable instances. In that case, only a
    single EUnsatisfiable will be present in the returned expectation list,
    even if there were more than one at the maximum position.
    """
    expectation_list_type.check_matches(expected)
    # First make sure we actually have some expectations to deal with
    if len(expected) == 0:
        return 0, []
    # Now we check to see if this is a list of entirely EUnsatisfiables
    if static.compile([static.Positional(int, EUnsatisfiable)]).matches(expected):
        # This is a bunch of EUnsatisfiables, so we simply take the one at the
        # last position and return a singleton list based off of it.
        position, e = max(expected, key=lambda (position, _): position)
        expected = [e]
    else:
        # This contains things besides EUnsatisfiables, so we filter out all of
        # the unsatisfiables, then get all the other ones at the resulting
        # maximum position.
        expected = [e for e in expected if not isinstance(e[1], EUnsatisfiable)]
        position = max(expected, key=lambda (position, _): position)[0]
        expected = [e for p, e in expected if p == position]
    # Now we remove duplicates. I used to pass these into set() until I
    # discovered that because Expectation objects don't compare based on their
    # actual value, the resulting order was based on the memory position at
    # which the expectation resided, which tended to mess up doctests that used
    # the position of expectations in an "At position n: expected x, y, z"
    # message. So I'm not doing that anymore :-)
    used_expectations = set()
    result = []
    for e in expected:
        # Create a tuple of the expectation's type and its format
        e_tuple = type(e), e.format()
        # Then check to see if that resulting combination has already been used
        if e_tuple not in used_expectations:
            # ...and add it if it hasn't been.
            result.append(e)
            used_expectations.add(e_tuple)
    return position, result


def stringify_expectations(expectations):
    """
    Converts the specified list of Expectation objects into a list of strings.
    This essentially just returns [e.format() for e in expectations].
    """
    return [e.format() for e in expectations]


def format_expectations(position, expectations):
    """
    Formats a position and a list of strings into a failure message that
    typically looks like this:
    
    At position n: expected one of x, y, z
    
    Position is the position to use for n. Expectations is the list of strings
    to use for x, y, and z.
    """
    return "At position %s: expected one of %s" % (position, ", ".join(expectations))


def format_failure(expected):
    """
    Formats a list of expectations into a failure message that typically looks
    something like this:
    
    At position n: expected one of x, y, z
    
    Expectations are provided in the same format as passed to the failure()
    function.
    
    This function used to contain all of the formatting logic, but the logic
    has since been split into the functions filter_expectations,
    stringify_expectations, and format_expectations. This function now
    functions as a convenience wrapper around those three functions.
    """
    position, expectations = filter_expectations(expected)
    expectations = stringify_expectations(expectations)
    return format_expectations(position, expectations)


def parse_space(text, position, end, space):
    """
    Repeatedly applies the specified whitespace parser to the specified text
    starting at the specified position until it no longer matches. The result
    of all of these parses will be discarded, and the location at which the
    whitespace parser failed will be returned.
    """
    # Basically just parse space, then loop while we actually parsed some
    # space, and parse more and more space, and so on. Of course, we'll want to
    # pass Invalid() as the whitespace parser to avoid indefinite recursion
    # because we try to remove the whitespace from before the whitespace parser
    # and so on.
    raise Exception("parse_space is now defunct. Something just called it, "
            "however, so that something needs to be fixed.")


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


# These are the various operators provided on every parser. The documentation
# for each one is provided as part of the Parcon module documentation.

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
        return First(*
                     (list(first.parsers) if isinstance(first, First) else [first])
                     + 
                     (list(second.parsers) if isinstance(second, First) else [second])
                     )
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
    elif isinstance(function, (int, long)):
        return Repeat(parser, function, function)
    elif isinstance(function, basestring):
        return Tag(function, parser)
    elif callable(function):
        return Translate(parser, function)
    raise Exception("Object passed to some_parser[value] must be a slice, "
                    "an ellipsis, an int or long, or a callable object "
                    "(such as a function or a class, or an object with "
                    "a __call__ method)")

def op_invert(parser):
    return Discard(parser)

def op_and(first, second):
    first = promote(first)
    second = promote(second)
    if isinstance(first, Parser) and isinstance(second, Parser):
        return And(first, second)
    return NotImplemented

def op_call(parser, *args, **kwargs):
    if kwargs.get("name") is not None:
        return Name(kwargs["name"], parser)
    if kwargs.get("desc") is not None:
        return Description(kwargs["desc"], parser)
    if kwargs.get("description") is not None:
        return Description(kwargs["description"], parser)
    if kwargs.get("expected") is not None:
        return Expected(parser, kwargs["expected"])
    raise NotImplementedError


class Parser(object):
    """
    A parser. This class cannot itself be instantiated; you can only use one of
    its subclasses. Most classes in this module are Parser subclasses.
    
    The method you'll typically use on Parser objects is parse_string.
    """
    def parse(self, text, position, end, space):
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
        result = self.parse(string, 0, len(string), whitespace)
        if result:
            if not all: # We got a result back and we're not trying to match
                # everything, so regardless of what the result was, we should
                # return it.
                return result.value
            # Result matched and we're trying to match everything, so we ask
            # the whitespace parser to consume everything at the end, then
            # check to see if the end position is equal to the string length,
            # and if it is, we return the value.
            if whitespace.consume(string, result.end, len(string)) == len(string):
                return result.value
        raise ParseException("Parse failure: " + format_failure(result.expected))
    
    def consume(self, text, position, end):
        result = self.parse(text, position, end, Invalid())
        while result:
            position = result.end
            result = self.parse(text, position, end, Invalid())
        return position
        
    # All of the operators available to parsers
    
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
    
    def __invert__(self):
        return op_invert(self)
    
    def __and__(self, other):
        return op_and(self, other)
    
    def __rand__(self, other):
        return op_and(other, self)
    
    def __call__(self, *args, **kwargs):
        return op_call(self, *args, **kwargs)
    
    def __str__(self):
        return self.__repr__()


class _GParser(Parser, _Graphable):
    pass

class _RParser(Parser, _rr.Railroadable):
    pass


class _GRParser(Parser, _Graphable, _rr.Railroadable):
    pass


class Invalid(_GParser):
    """
    A parser that never matches any input and always fails.
    """
    def parse(self, text, position, end, space):
        # This MUST NOT attempt to parse out any whitespace before failing, for
        # two reasons: 1, it's pointless anyway, and 2, it will cause
        # infinite recursion in parse_whitespace, which is called by nearly
        # every parser. (If you want to see why, add a call to parse_whitespace
        # to this method, then try parsing any string with something like
        # Literal("a"), and you'll see what happens.)
        return failure((position, EUnsatisfiable()))
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Invalid")
        return []
    
    def __repr__(self):
        return "Invalid()"


class Literal(_GRParser):
    """
    A parser that matches the specified literal piece of text. It succeeds
    only if that piece of text is found, and it returns None when it succeeds.
    If you need the return value to be the literal piece of text, you should
    probably use SignificantLiteral instead.
    """
    def __init__(self, text):
        self.text = text
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        expected_end = position + len(self.text)
        if expected_end <= end and text[position:expected_end] == self.text:
            return match(expected_end, None, [(expected_end, EUnsatisfiable())])
        else:
            return failure((position, EStringLiteral(self.text)))
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='Literal:\n%s' % repr(self.text))
        return []
    
    def create_railroad(self, options):
        return _rr.Token(_rr.TEXT, self.text)
    
    def __repr__(self):
        return "Literal(%s)" % repr(self.text)


class SignificantLiteral(Literal):
    """
    A parser that matches the specified literal piece of text. Is succeeds
    only if that piece of text is found. Unlike Literal, however,
    SignificantLiteral returns the literal string passed into it instead of
    None.
    """
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        expected_end = position + len(self.text)
        if expected_end <= end and text[position:expected_end] == self.text:
            return match(expected_end, self.text, [(expected_end, EUnsatisfiable())])
        else:
            return failure((position, EStringLiteral(self.text)))
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='SignificantLiteral:\n%s' % repr(self.text))
        return []
    
    def __repr__(self):
        return "SignificantLiteral(%s)" % repr(self.text)


class AnyCase(_GRParser):
    """
    A case-insensitive version of Literal. Behaves exactly the same as Literal
    does, but without regard to the case of the input.
    
    If enough people request a version that returns the matched text instead of
    None (send me an email if you're one of these people; my email is at the
    top of this file, in the module docstring), I'll provide such a parser. For
    now, though, you can use a Regex parser to accomplish the same thing.
    """
    def __init__(self, text):
        self.text = text.lower()
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        expected_end = position + len(self.text)
        if expected_end <= end and text[position:expected_end].lower() == self.text:
            return match(expected_end, None, [(expected_end, EUnsatisfiable())])
        else:
            return failure((position, EStringLiteral(self.text)))
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='AnyCase:\n%s' % repr(self.text))
        return []
    
    def create_railroad(self, options):
        return _rr.Token(_rr.ANYCASE, self.text)
    
    def __repr__(self):
        return "AnyCase(%s)" % repr(self.text)


class CharIn(_GRParser):
    """
    A parser that matches a single character as long as it is in the specified
    sequence (which can be a string or a list of one-character strings). It
    returns the character matched.
    """
    def __init__(self, chars):
        self.chars = chars
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        expected_end = position + 1
        if position < end and text[position:expected_end] in self.chars:
            return match(expected_end, text[position], [(expected_end, EUnsatisfiable())])
        else:
            return failure([(position, EAnyCharIn(self.chars))])
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='CharIn:\n%s' % repr(self.chars))
        return []
    
    def create_railroad(self, options):
        return _rr.Or(*[_rr.Token(_rr.TEXT, c) for c in self.chars])
    
    def __repr__(self):
        return "CharIn(" + repr(self.chars) + ")"


class CharNotIn(_GParser):
    """
    A parser that matches a single character as long as it is not in the
    specified sequence. This is much the opposite of CharIn.
    """
    def __init__(self, chars):
        self.chars = chars
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        expected_end = position + 1
        if position < end and text[position:expected_end] not in self.chars:
            return match(expected_end, text[position], [(expected_end, EUnsatisfiable())])
        else:
            return failure([(position, EAnyCharNotIn(self.chars))])
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='CharNotIn:\n%s' % repr(self.chars))
        return []
    
    def __repr__(self):
        return "CharNotIn(" + repr(self.chars) + ")"


class Digit(CharIn):
    """
    Same as CharIn(digit_chars).
    """
    def __init__(self):
        CharIn.__init__(self, digit_chars)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='Digit')
        return []


class Upper(CharIn):
    """
    Same as CharIn(upper_chars).
    """
    def __init__(self):
        CharIn.__init__(self, upper_chars)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='Upper')
        return []


class Lower(CharIn):
    """
    Same as CharIn(lower_chars).
    """
    def __init__(self):
        CharIn.__init__(self, lower_chars)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='Lower')
        return []


class Alpha(CharIn):
    """
    Same as CharIn(upper_chars + lower_chars).
    """
    def __init__(self):
        CharIn.__init__(self, upper_chars + lower_chars)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='Alpha')
        return []


class Alphanum(CharIn):
    """
    Same as CharIn(upper_chars + lower_chars + digit_chars).
    """
    def __init__(self):
        CharIn.__init__(self, upper_chars + lower_chars + digit_chars)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='Alphanum')
        return []


class Whitespace(CharIn):
    """
    Same as CharIn(whitespace).
    """
    def __init__(self):
        CharIn.__init__(self, whitespace)
        # Speed optimization
        regex = re.compile(r"[ \t\r\n]*")
        self.consume = lambda t, p, e: regex.match(t, p, e).end()
    
    def __repr__(self):
        return "Whitespace()"
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='Whitespace')
        return []


class AnyChar(_GRParser):
    """
    A parser that matches any single character. It returns the character that
    it matched.
    """
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        if position < end: # At least one char left
            return match(position + 1, text[position], [(position + 1, EUnsatisfiable())])
        else:
            return failure([(position, EAnyChar())])
    
    def do_graph(self, graph):
        graph.add_node(id(self), label='AnyChar')
        return []
    
    def create_railroad(self, options):
        return _rr.Token(_rr.DESCRIPTION, "any char")
    
    def __repr__(self):
        return "AnyChar()"


class Except(_GRParser):
    """
    A parser that matches and returns whatever the specified parser matches
    and returns, as long as the specified avoid_parser does not also match at
    the same location. For example, Except(AnyChar(), Literal("*/")) would
    match any character as long as that character was not a * followed
    immediately by a / character. This would most likely be useful in, for
    example, a parser designed to parse C-style comments.
    
    When this parser is converted to a railroad diagram, it simply replaces
    itself with the underlying parser it wraps. The resulting railroad diagram
    does not, therefore, mention the avoid parser, so you should be careful
    that this is really what you want to do.
    """
    def __init__(self, parser, avoid_parser):
        self.parser = parser
        self.avoid_parser = avoid_parser
        self.railroad_children = [parser]
    
    def parse(self, text, position, end, space):
        # May want to parse space to make sure the two parsers are in sync
        result = self.parser.parse(text, position, end, space)
        if not result:
            return failure(result.expected)
        avoid_result = self.avoid_parser.parse(text, position, end, space)
        if avoid_result:
            return failure([(position, EStringLiteral("(TBD: except)"))])
        return result
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Except")
        graph.add_edge(id(self), id(self.parser), label="match")
        graph.add_edge(id(self), id(self.avoid_parser), label="avoid")
        return [self.parser, self.avoid_parser]
    
    def create_railroad(self, options):
        return _rr.create_railroad(self.parser, options)
    
    def __repr__(self):
        return "Except(%s, %s)" % (repr(self.parser), repr(self.avoid_parser))


class ZeroOrMore(_GRParser):
    """
    A parser that matches the specified parser as many times as it can. The
    results are collected into a list, which is then returned. Since
    ZeroOrMore succeeds even if zero matches were made (the empty list will
    be returned in such a case), this parser always succeeds.
    """
    def __init__(self, parser):
        self.parser = parser
        self.railroad_children = [parser]
    
    def parse(self, text, position, end, space):
        result = []
        parserResult = self.parser.parse(text, position, end, space)
        while parserResult:
            result.append(parserResult.value)
            position = parserResult.end
            parserResult = self.parser.parse(text, position, end, space)
        return match(position, result, parserResult.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="ZeroOrMore")
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.Loop(_rr.Nothing(), _rr.create_railroad(self.parser, options))
    
    def __repr__(self):
        return "ZeroOrMore(%s)" % repr(self.parser)


class OneOrMore(_GRParser):
    """
    Same as ZeroOrMore, but requires that the specified parser match at least
    once. If it does not, this parser will fail.
    """
    def __init__(self, parser):
        self.parser = parser
        self.railroad_children = [parser]
    
    def parse(self, text, position, end, space):
        result = []
        parserResult = self.parser.parse(text, position, end, space)
        while parserResult:
            result.append(parserResult.value)
            position = parserResult.end
            parserResult = self.parser.parse(text, position, end, space)
        if len(result) == 0:
            return failure(parserResult.expected)
        return match(position, result, parserResult.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="OneOrMore")
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.Loop(_rr.create_railroad(self.parser, options), _rr.Nothing())
    
    def __repr__(self):
        return "OneOrMore(%s)" % repr(self.parser)


class Then(_GRParser):
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
    
    Named tuples (instances of classes created with collections.namedtuple) are
    not treated as tuples in the above decision process. In fact, any subclass
    of tuple is treated as if it were a completely separate object and not a
    tuple at all.
    """
    def __init__(self, first, second):
        self.first = promote(first)
        self.second = promote(second)
        self.railroad_children = [self.first, self.second]
    
    def parse(self, text, position, end, space):
        firstResult = self.first.parse(text, position, end, space)
        if not firstResult:
            return failure(firstResult.expected)
        position = firstResult.end
        secondResult = self.second.parse(text, position, end, space)
        if not secondResult:
            return failure(firstResult.expected + secondResult.expected)
        position = secondResult.end
        expectations = firstResult.expected + secondResult.expected
        a, b = firstResult.value, secondResult.value
        if a is None:
            return match(position, b, expectations)
        elif b is None:
            return match(position, a, expectations)
        if type(a) == tuple and type(b) == tuple:
            return match(position, a + b, expectations)
        elif type(a) == tuple:
            return match(position, a + (b,), expectations)
        elif type(b) == tuple:
            return match(position, (a,) + b, expectations)
        else:
            return match(position, (a, b), expectations)
    
    
    def do_graph(self, graph):
        # Define a function for recursively expanding nested Thens into a list
        expand = lambda x: [x] if not isinstance(x, Then) else expand(x.first) + expand(x.second)
        graph.add_node(id(self), label="Then", ordering="out")
        child_parsers = expand(self)
        for index, parser in enumerate(child_parsers):
            graph.add_edge(id(self), id(parser), label=str(index + 1))
        return child_parsers
    
    def create_railroad(self, options):
        return _rr.Then(_rr.create_railroad(self.first, options), _rr.create_railroad(self.second, options))
    
    def __repr__(self):
        return "Then(%s, %s)" % (repr(self.first), repr(self.second))


class Discard(_GRParser):
    """
    A parser that matches if the parser it's constructed with matches. It
    consumes the same amount of input that the specified parser does, but this
    parser always returns None as the result. Since instances of Then treat
    None values specially, you'll likely use this parser in conjunction with
    Then in some grammars.
    """
    def __init__(self, parser):
        self.parser = parser
        self.railroad_children = [parser]
    
    def parse(self, text, position, end, space):
        result = self.parser.parse(text, position, end, space)
        if result:
            return match(result.end, None, result.expected)
        else:
            return failure(result.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Discard")
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.create_railroad(self.parser, options)
    
    def __repr__(self):
        return "Discard(" + repr(self.parser) + ")"


class First(_GRParser):
    """
    A parser that tries all of its specified parsers in order. As soon as one
    matches, its result is returned. If none of them match, this parser fails.
    
    The parsers can be specified either as arguments (i.e. First(parser1,
    parser2, parser3) or as a single list or tuple (i.e. First([parser1,
    parser2, parser3]).
    """
    def __init__(self, *parsers):
        if len(parsers) == 1 and isinstance(parsers[0], (list, tuple)):
            # Allow passing in a single list of parsers instead of each parser
            # as an argument
            parsers = parsers[0]
        self.parsers = [promote(p) for p in parsers]
        self.railroad_children = self.parsers
    
    def parse(self, text, position, end, space):
        expectedForErrors = []
        for parser in self.parsers:
            result = parser.parse(text, position, end, space)
            if result:
                return match(result.end, result.value, result.expected + expectedForErrors)
            else:
                expectedForErrors += result.expected
        return failure(expectedForErrors)
    
    def do_graph(self, graph):
        for index, parser in enumerate(self.parsers):
            graph.add_edge(id(self), id(parser), label=str(index + 1))
        graph.add_node(id(self), label="First", ordering="out")
        return self.parsers
    
    def create_railroad(self, options):
        return _rr.Or(*[_rr.create_railroad(v, options) for v in self.parsers])
    
    def __repr__(self):
        return "First(%s)" % ", ".join(repr(parser) for parser in self.parsers)


class Longest(_GRParser):
    """
    A parser that tries all of its specified parsers. The longest one that
    succeeds is chosen, and its result is returned. If none of the parsers
    succeed, Longest fails.
    
    The parsers can be specified either as arguments (i.e. First(parser1,
    parser2, parser3) or as a single list or tuple (i.e. First([parser1,
    parser2, parser3]).
    
    Longest is typically more expensive than First since it has to try each
    parser to see which one consumes the most input whereas First stops trying
    parsers once one succeeds. Because of this, it's usually better to use
    First if the parsers to check can be reordered so that those consuming the
    most input are at the beginning of the list.
    """
    def __init__(self, *parsers):
        if len(parsers) == 1 and isinstance(parsers[0], (list, tuple)):
            # Allow passing in a single list of parsers instead of each parser
            # as an argument
            parsers = parsers[0]
        self.parsers = [promote(p) for p in parsers]
        self.railroad_children = self.parsers
    
    def parse(self, text, position, end, space):
        expectedForErrors = []
        successful = []
        for parser in self.parsers:
            result = parser.parse(text, position, end, space)
            if result:
                successful.append(result)
            else:
                expectedForErrors += result.expected
        if len(successful) == 0:
            return failure(expectedForErrors)
        return max(successful, key=lambda result: result.end)
    
    def do_graph(self, graph):
        for index, parser in enumerate(self.parsers):
            graph.add_edge(id(self), id(parser), label=str(index + 1))
        graph.add_node(id(self), label="Longest", ordering="out")
        return self.parsers
    
    def create_railroad(self, options):
        return _rr.Or(*[_rr.create_railroad(v, options) for v in self.parsers])
    
    def __repr__(self):
        return "Longest(%s)" % ", ".join(repr(parser) for parser in self.parsers)


class Translate(_GRParser):
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
        self.railroad_children = [self.parser]
    
    def parse(self, text, position, end, space):
        result = self.parser.parse(text, position, end, space)
        if not result:
            return failure(result.expected)
        return match(result.end, self.function(result.value), result.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Translate")
        graph.add_node(id(self.function), label=repr(self.function), shape="rect")
        graph.add_edge(id(self), id(self.parser), label="parser")
        graph.add_edge(id(self), id(self.function), label="function")
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.create_railroad(self.parser, options)
    
    def __repr__(self):
        return "Translate(%s, %s)" % (repr(self.parser), repr(self.function))


class Exact(_GRParser):
    """
    A parser that returns whatever the specified parser returns, but Invalid()
    will be passed as the whitespace parser to the specified parser when its
    parse method is called. This allows for sections of the grammar to take
    whitespace significantly, which is useful in, for example, string literals.
    For example, the following parser, intended to parse string literals,
    demonstrates the problem:
    
    >>> stringLiteral = '"' + ZeroOrMore(AnyChar() - '"')["".join] + '"'
    >>> stringLiteral.parse_string('"Hello, great big round world"')
    'Hello,greatbigroundworld'
    
    This is because the whitespace parser (which defaults to Whitespace())
    consumed all of the space in the string literal. This can, however, be
    rewritten using Exact to mitigate this problem:

    >>> stringLiteral = Exact('"' + ZeroOrMore(AnyChar() - '"')["".join] + '"')
    >>> stringLiteral.parse_string('"Hello, great big round world"')
    'Hello, great big round world'
    
    This parser produces the correct result, 'Hello, great big round world'.
    """
    def __init__(self, parser, space_parser=Invalid()):
        self.parser = parser
        self.space_parser = space_parser
        self.railroad_children = [self.parser]
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        return self.parser.parse(text, position, end, self.space_parser)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Exact")
        graph.add_edge(id(self), id(self.parser), label="parser")
        if not isinstance(self.space_parser, Invalid):
            graph.add_edge(id(self), id(self.space_parser), label="space")
    
    def create_railroad(self, options):
        return _rr.create_railroad(self.parser, options)
    
    def __repr__(self):
        return "Exact(" + repr(self.parser) + ")"


class Optional(_GRParser):
    """
    A parser that returns whatever its underlying parser returns, except that
    if the specified parser fails, this parser succeeds and returns the default
    result specified to it (which, itself, defaults to None).
    """
    def __init__(self, parser, default=None):
        self.parser = parser
        self.default = default
        self.railroad_children = [self.parser]
    
    def parse(self, text, position, end, space):
        result = self.parser.parse(text, position, end, space)
        if result:
            return result
        else:
            return match(position, self.default, result.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Optional, defaulting to:\n%s" % repr(self.default))
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.Or(_rr.create_railroad(self.parser, options), _rr.Nothing())
    
    def __repr__(self):
        return "Optional(%s, %s)" % (repr(self.parser), repr(self.default))

class Repeat(_GParser):
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
    
    def parse(self, text, position, end, space):
        if self.max == 0: # This does actually happen some times;
            # specifically, it came up in a parser that James Stoker was
            # writing to parse CIDRs in BGP packets
            return match(position, [], (position, EUnsatisfiable()))
        if self.min == 1 and self.max == 1: # Optimization to short-circuit
            # into the underlying parser if we're parsing exactly one of it
            return self.parser.parse(text, position, end, space)
        result = []
        parse_result = None
        for i in (xrange(self.max) if self.max is not None else itertools.count(0)):
            parse_result = self.parser.parse(text, position, end, space)
            if not parse_result:
                break
            position = parse_result.end
            result.append(parse_result.value)
        if self.min and len(result) < self.min:
            return failure(parse_result.expected)
        return match(position, result, parse_result.expected)
    
    def do_graph(self, graph):
        if self.min is None and self.max is None:
            label = "zero or more times"
        elif self.min is None:
            label = "not more than %s" % self.max
        elif self.max is None:
            label = "at least %s" % self.min
        else:
            label = "at least %s\nbut not more than %s" % (self.min, self.max)
        graph.add_node(id(self), label="Repeat\n" + label)
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def __repr__(self):
        return "Repeat(%s, %s, %s)" % (repr(self.parser), repr(self.min), repr(self.max))


class Keyword(_GRParser):
    """
    A parser that matches the specified parser as long as it is followed
    immediately by the specified terminator parser, or by whitespace
    (according to the current whitespace parser) if a terminator parser is not
    specified.
    
    If exact_terminator is True, the terminator is matched with Invalid() as
    its whitespace parser. This prevents the whitespace parser from consuming
    input that the terminator might have been expecting to see to indicate
    proper termination of the keyword. If exact_terminator is False, the same
    whitespace parser passed to Keyword will be passed into the terminator.
    
    If or_end is True, the terminator will be replaced with
    (terminator | End()) just before attempting to parse it, which would allow
    the keyword to be present at the end of the input without causing a parse
    failure due to the keyword not being followed immediately by the
    terminator.
    """
    def __init__(self, parser, terminator=None, exact_terminator=True, or_end=True):
        self.parser = promote(parser)
        self.terminator = promote(terminator) if terminator is not None else None
        self.exact_terminator = exact_terminator
        self.or_end = or_end
        self.railroad_children = [self.parser]
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        if self.terminator:
            terminator = self.terminator
        else:
            terminator = space
        result = self.parser.parse(text, position, end, space)
        if not result:
            return failure(result.expected)
        if self.exact_terminator:
            t_space = Invalid()
        else:
            t_space = space
        if self.or_end:
            terminator = terminator | End()
        terminator_result = terminator.parse(text, result.end, end, t_space)
        if not terminator_result:
            return failure(terminator_result.expected)
        return result
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Keyword")
        graph.add_node(id(self), id(self.parser), label="parser")
        if self.terminator is not None:
            graph.add_node(id(self), id(self.terminator), label="terminator")
        return [self.parser] + [self.terminator] if self.terminator is not None else []
    
    def create_railroad(self, options):
        return _rr.create_railroad(self.parser, options)
    
    def __repr__(self):
        return "Keyword(%s, %s)" % (repr(self.parser), repr(self.terminator))


class Forward(_GRParser):
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
    Forward instance.
    
    You can also specify the parser when you create the Forward instance. This
    is usually somewhat pointless, but it can be useful if you're simply trying
    to create a mutable parser (the parser can be set into a Forward multiple
    times, with the effect of changing the underlying parser each time).
    """
    def __init__(self, parser=None):
        self.parser = parser
    
    @property
    def railroad_children(self):
        return [self.parser]
    
    def parse(self, text, position, end, space):
        if not self.parser:
            raise Exception("Forward.parse was called before the specified "
                            "Forward instance's set function or << operator "
                            "was used to specify a parser.")
        return self.parser.parse(text, position, end, space)
    
    def set(self, parser):
        """
        Sets the parser that this Forward should use. After you call this
        method, this Forward acts just like it were really the specified parser.
        
        This method can be called multiple times; each time it's called, it
        changes the parser in use by this Forward instance.
        """
        parser = promote(parser)
        self.parser = parser
    
    __lshift__ = set
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Forward")
        graph.add_edge(id(self), id(self.parser), constraint="false")
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.create_railroad(self.parser, options)
    
    def __repr__(self):
        return "Forward()"


class InfixExpr(_GRParser):
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
    
    def parse(self, text, position, end, space):
        # Parse the first component
        component_result = self.component.parse(text, position, end, space)
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
                op_result = op_parser.parse(text, position, end, space)
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
            component_result = self.component.parse(text, op_result.end, end, space)
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
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="InfixExpr")
        graph.add_edge(id(self), id(self.component), label="component")
        for parser, function in self.operators:
            graph.add_edge(id(self), id(parser), label="op")
        return [self.component] + [p for p, f in self.operators]
    
    def create_railroad(self, options):
        op_railroads = [_rr.create_railroad(v, options) for (v, function) in self.operators]
        return _rr.Loop(_rr.create_railroad(self.component, options), _rr.Or(*op_railroads))
    
    @property
    def railroad_children(self):
        return [self.component] + [op for (op, function) in self.operators]
    
    def __repr__(self):
        return "InfixExpr(%s, %s)" % (repr(self.component), repr(self.operators))


class Bind(_GParser):
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
    
    def parse(self, text, position, end, whitespace):
        first_result = self.parser.parse(text, position, end, whitespace)
        if not first_result:
            return failure(first_result.expected)
        second_parser = self.function(first_result.value)
        second_result = second_parser.parse(text, first_result.end, end, whitespace)
        if not second_result:
            return failure(second_result.expected + first_result.expected)
        return match(second_result.end, second_result.value, second_result.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Bind using function:\n%s" % repr(self.function))
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def __repr__(self):
        return "Bind(%s, %s)" % (repr(self.parser), repr(self.function))


class Return(_GRParser):
    """
    A parser that always succeeds, consumes no input, and always returns a
    value specified when the Return instance is constructed.
    
    Those of you familiar with functional programming will notice that this
    parser implements a monadic return, hence its name.
    """
    def __init__(self, value):
        self.value = value
    
    def parse(self, text, position, end, whitespace):
        return match(position, self.value, [(position, EUnsatisfiable())])
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Return:\n%s" % repr(self.value))
        return []
    
    def create_railroad(self, options):
        return _rr.Nothing()
    
    def __repr__(self):
        return "Return(%s)" % repr(self.value)


class Chars(_GParser):
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
    def __init__(self, number):
        self.number = number
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        if position + self.number > end:
            return failure([(end, EAnyChar())])
        result = text[position:position + self.number]
        end_position = position + self.number
        return match(end_position, result, [(end_position, EUnsatisfiable())])
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Chars: %s chars" % self.number)
        return []


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
        if init_chars is None:
            init_chars = chars
        if min < 1:
            raise Exception("min must be greater than zero")
        self.pattern = re.compile("[%s][%s]{,%s}" % (
                re.escape(init_chars),
                re.escape(chars),
                "" if max is None else max - 1
                ))
        self.chars = chars
        self.init_chars = init_chars
        self.min = min
        self.max = max
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        result = self.pattern.match(text, position, end)
        # We'll always have a result here, we just need to check and make sure
        # it consumed the required number of characters
        if not result:
            return failure((position, EAnyCharIn(self.init_chars)))
        total_consumed = result.end() - position
        new_position = result.end()
        if total_consumed < self.min:
            return failure((result.end(), EAnyCharIn(self.chars)))
        if total_consumed < self.max:
            expected = (new_position, EAnyCharIn(self.chars))
        else:
            expected = (new_position, EUnsatisfiable())
        return match(new_position, result.group(0),
                expected)
    
    def __repr__(self):
        return "Word(%s, %s, %s, %s)" % (repr(self.chars), repr(self.init_chars),
                                         repr(self.min), repr(self.max))


class Present(_GParser):
    """
    A lookahead parser; it matches as long as the parser it's constructed with
    matches at the specified position, but it doesn't actually consume any
    input, and its result is None. If you need access to the result, you'll
    probably want to use Preserve instead.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, end, space):
        result = self.parser.parse(text, position, end, space)
        if result:
            return match(position, None, [(position, EUnsatisfiable())])
        else:
            return failure(result.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Present")
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def __repr__(self):
        return "Present(%s)" % repr(self.parser)


class Preserve(_GParser):
    """
    A lookahead parser; it matches as long as the parser it's constructed with
    matches at the specified position, but it doesn't actually consume any
    input. Unlike Present, however, Preserve returns whatever its underlying
    parser returned, even though it doesn't consume any input.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, end, space):
        result = self.parser.parse(text, position, end, space)
        if result:
            return match(position, result.value, [(position, EUnsatisfiable())])
        else:
            return failure(result.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Preserve")
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def __repr__(self):
        return "Present(%s)" % repr(self.parser)


class And(_GParser):
    """
    A parser that matches whatever its specified parser matches as long as its
    specified check_parser also matches at the same location. This could be
    considered the opposite of Except: And matches when the second parser it's
    passed also matches, while Except matches when the second parser it's
    passed does not match. Wrapping the second parser with Not can make And
    behave as Except and vice versa, although using whichever one makes more
    sense will likely lead to more informative error messages when parsing
    fails.
    """
    def __init__(self, parser, check_parser):
        self.parser = parser
        self.check_parser = check_parser
    
    def parse(self, text, position, end, space):
        # May want to parse space to make sure the two parsers are in sync
        result = self.parser.parse(text, position, end, space)
        if not result:
            return failure(result.expected)
        check_result = self.check_parser.parse(text, position, end, space)
        if not check_result:
            return failure(check_result.expected)
        return result
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="And")
        graph.add_edge(id(self), id(self.check_parser), label="check")
        graph.add_edge(id(self), id(self.parser), label="result")
        return [self.parser, self.check_parser]
    
    def __repr__(self):
        return "And(%s, %s)" % (repr(self.parser), repr(self.check_parser))


class Not(_GParser):
    """
    A parser that matches only if the parser it's created with does not. If the
    aforementioned parser fails, then Not succeeds, consuming no input and 
    returning None. If the aforementioned parser succeeds, then Not fails.
    """
    def __init__(self, parser):
        self.parser = parser
    
    def parse(self, text, position, end, space):
        result = self.parser.parse(text, position, end, space)
        if result:
            return failure([(position, EStringLiteral("(TBD: Not)"))])
        else:
            return match(position, None, [(position, EUnsatisfiable())])
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Not")
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def __repr__(self):
        return "Not(%s)" % repr(self.parser)


class Regex(_RParser):
    """
    A parser that matches the specified regular expression. Its result depends
    on the groups_only parameter passed to the constructor: if groups_only is
    None (the default), the result is the string that the regex matches. If
    groups_only is True, a list of the values that the groups in the regex
    matched is true; for example, Regex("(..)(.)(....)", groups_only=True)
    would parse the string "abcdefg" into ["ab", "c", "defg"]. If groups_only
    is False, the string that the regex matched is provided as the first item
    in the list, and the groups are provided as the rest of the items in the
    list; the above example with groups_only=False would parse the string
    "abcdefg" into ["abcdefg", "ab", "c", "defg"].
    
    >>> Regex("(..)(.)(....)", groups_only=True).parse_string("abcdefg")
    ['ab', 'c', 'defg']
    
    If you can avoid using Regex without requiring exorbitant amounts of
    additional code, it's generally best to, since error messages given by
    combinations of Parcon parsers are generally more informative than an
    error message providing a regex. If you really need to use Regex but you
    still want informative error messages, you could wrap your Regex instance
    in an instance of Expected.
    
    The specified regex can be either a string representing the regular
    expression or a pattern compiled with Python's re.compile. If you want to
    specify flags to the regex, you'll need to compile it with re.compile, then
    pass the result into Regex.
    
    Unlike the behavior of normal Python regex groups, groups that did not
    participate in a match are represented in the returned list (if
    groups_only is not None) by the empty string instead of None. If enough
    people want the ability for None to be used instead (and my email address
    is in the docstring for this module, at the top, so send me an email if
    you're one of the people that want this), I'll add a parameter that can be
    passed to Regex to switch this back to the usual behavior of using None.
    """
    def __init__(self, regex, groups_only=None):
        self.regex = re.compile(regex)
        self.groups_only = groups_only
    
    def parse(self, text, position, end, space):
        position = space.consume(text, position, end)
        regex_match = self.regex.match(text, position, end)
        if not regex_match:
            return failure([(position, ERegex(self.regex.pattern))])
        position = regex_match.end()
        if self.groups_only is None:
            result = regex_match.group()
        elif self.groups_only is True:
            result = list(regex_match.groups(""))
        else:
            result = [regex_match.group()] + list(regex_match.groups(""))
        return match(position, result, [(position, EUnsatisfiable())])
    
    def create_railroad(self, options):
        expanded = _rr_regex.convert_regex(self.regex.pattern)
        if expanded is None:
            return _rr.Token(_rr.DESCRIPTION, "regex: " + self.regex.pattern)
        else:
            return expanded
    
    def __repr__(self):
        return "Regex(%s, %s)" % (repr(self.regex.pattern), repr(self.groups_only))


class Expected(Parser):
    """
    A parser that allows customization of the error message provided when the
    parser it's created with fails. For example, let's say that you had a
    parser that would parse numbers with decimals, such as 1.5:
    
    >>> decimal = +Digit() + "." + +Digit()
    
    Now let's say that in your grammar, you included "true" and "false" as
    things that could be in the same location as a decimal number:
    
    >>> something = decimal | "true" | "false"
    
    If you call something.parse_string("bogus"), the resulting error message
    will be:
    
    >>> something.parse_string("bogus")
    Traceback (most recent call last):
    ParseException: Parse failure: At position 0: expected one of any char in "0123456789", "true", "false"
    
    which isn't very pretty or informative. If, instead, you did this:
    
    >>> decimal = +Digit() + "." + +Digit()
    >>> decimal = Expected(decimal, "decimal number")
    >>> something = decimal | "true" | "false"
    
    Then the error message would instead be something like:
    
    >>> something.parse_string("bogus")
    Traceback (most recent call last):
    ParseException: Parse failure: At position 0: expected one of decimal number, "true", "false"
    
    which is more informative as to what's missing.
    
    If the parameter remove_whitespace is True when constructing an instance
    of Expected, whitespace will be removed before calling the underlying
    parser's parse method. This will usually make error messages more accurate
    about the position at which this whole Expected instance was expected.
    If it's False, whitespace will not be removed, and it will be up to the
    underlying parser to remove it; as a result, error messages will indicate
    the position /before/ the removed whitespace as where the error occurred,
    which is usually not what you want.
    """
    def __init__(self, parser, expected_message, remove_whitespace=True):
        self.parser = parser
        self.expected_message = expected_message
        self.remove_whitespace = remove_whitespace
    
    def parse(self, text, position, end, space):
        if self.remove_whitespace:
            position = space.consume(text, position, end)
        result = self.parser.parse(text, position, end, space)
        if not result:
            return failure([(position, ECustomExpectation(self.expected_message))])
        return result
    
    def __repr__(self):
        return "Expected(%s, %s, %s)" % (repr(self.parser),
                repr(self.expected_message), repr(self.remove_whitespace))


class Limit(Parser):
    """
    A parser that imposes a limit on how much input its underlying parser can
    consume. All parsers, when asked to parse text, are passed the position
    that they can parse to before they have to stop; normally this is the length
    of the string being passed in. Limit, however, allows this to be set to a
    smaller value.
    
    When you construct a Limit instance, you pass in a parser that it will
    call and the number of characters that the specified parser can consume.
    If there aren't that many characters left in the input string, no limit is
    placed on what the specified parser can consume.
    
    You can also pass a parser instead of a number as the limit for how many
    characters can be parsed. If you do that, Limit will apply that parser
    first, then take its result (which should be an int or a long) and use
    that as the limit when applying the main parser.
    
    The behavior of the latter paragraph allows you to write parsers that
    parse length-specified values. For example, if you're parsing some sort of
    string from a piece of binary data where the string is stored as four
    bytes representing the length of the string followed by the bytes of the
    string itself, you could do that with
    Limit(parcon.binary.integer, ZeroOrMore(AnyChar()))[concat].
    """
    def __init__(self, length, parser):
        self.length = length
        self.parser = parser
    
    def parse(self, text, position, end, space):
        if isinstance(self.length, Parser):
            result = self.length.parse(text, position, end, space)
            if not result:
                return failure(result.expected)
            position = result.end
            limit = position + result.value
        else:
            limit = position + self.length
        if limit > end:
            limit = end
        return self.parser.parse(text, position, limit, space)
    
    def __repr__(self):
        return "Limit(%s, %s)" % (repr(self.length), repr(self.parser))


class Tag(_GParser):
    """
    A parser that "tags", so to speak, the value returned from its underlying
    parser. Specifically, you construct a Tag instance by specifying a tag and
    a parser, and the specified parser's return value will be wrapped in a
    Pair(tag, return_value). For example,
    
    >>> Tag("test", AnyChar()).parse_string("a")
    Pair(key='test', value='a')
    
    The reason why this is useful is that named tuples are treated as objects
    by Parcon things like Then and the flatten function, so they will be passed
    around as objects, but they are treated as tuples by Python's dict
    function. This allows you to use various parsers that assemble values
    passed through Tag, and then add [flatten][dict] onto the end of that whole
    parser group; the result of that parser will be a dictionary containing all
    of the tagged values, with the tags as keys. For example, a parser that
    parses numbers such as "123.45" into a dict of the form {"integer": "123",
    "decimal": "45"} could be written as:
    
    >>> decimal_parser = (Tag("integer", (+Digit())[concat]) + Tag("decimal", \
                             Optional("." + (+Digit())[concat], "")))[dict]
    
    Of course, using the short notation parser["tag"] in place of Tag("tag",
    parser), we can reduce that further to:
    
    >>> decimal_parser = ((+Digit())[concat]["integer"] + Optional("." + \
                             (+Digit())[concat], "")["decimal"])[dict]
    
    Note that the short notation of parser[tag] only works if tag is a string
    (or a unicode instance; anything that subclasses from basestring works).
    No other datatypes will work; if you want to use those, you'll need to use
    Tag itself instead of the short notation.
    
    If you want to preserve all values with a particular tag instead of just
    one of them, you may want to use parser[list_dict] instead of parser[dict].
    See the documentation for list_dict for more on what it does.
    """
    def __init__(self, tag, parser):
        self.tag = tag
        self.parser = parser
    
    def parse(self, text, position, end, space):
        result = self.parser.parse(text, position, end, space)
        if result:
            return match(result.end, Pair(self.tag, result.value), result.expected)
        else:
            return failure(result.expected)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Tag:\n%s" % repr(self.tag))
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def __repr__(self):
        return "Tag(%s, %s)" % (repr(self.tag), repr(self.parser))


class End(_GParser):
    """
    A parser that matches only at the end of input. It parses whitespace before
    checking to see if it's at the end, so it will still match even if there is
    some whitespace at the end of the input. (If you don't want it to consume
    any whitespace, you can use Exact(End()).)
    
    This parser's result is always None. End(True) will consume any whitespace
    that it matches while searching for the end, which can improve performance
    under certain circumstances by avoiding having to parse out whitespace a
    second time. End(False) will still skip over whitespace while searching
    for the end, but it won't consume it, which may be desirable if the
    whitespace in question is significant to the grammar. End() is the same as
    End(True).
    
    Note that this parser succeeds at the end of the /logical/ input given to
    it; specifically, if you've restricted the region to parse with Length, End
    matches at the end of the limit set by Limit, not at the end of the actual
    input. A more technical way to put it would be to say that if, after
    removing whitespace, the resulting position is equal to the end parameter
    passed to the parse function, then this parser matches. Otherwise, it fails.
    """
    def __init__(self, consume=True):
        """
        Creates a new End parser. consume is described in the class docstring.
        """
        self.consume = consume
    
    def parse(self, text, position, end, space):
        new_position = space.consume(text, position, end)
        if new_position == end:
            if self.consume:
                result_pos = new_position
            else:
                result_pos = position
            return match(result_pos, None, [(result_pos, EUnsatisfiable())])
        else:
            # Should we use new_position here? I need to experiment around
            # more with error messages and see.
            return failure([(position, EUnsatisfiable())])
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="End")
        return []
    
    def __repr__(self):
        return "End()"


class Name(_GRParser):
    def __init__(self, name, parser):
        self.name = name
        self.parser = parser
        self.railroad_production_name = name
        self.railroad_production_delegate = parser
        self.railroad_children = [parser]
    
    def parse(self, text, position, end, space):
        return self.parser.parse(text, position, end, space)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Name:\n" + repr(self.name))
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.Token(_rr.PRODUCTION, self.name)
    
    def __repr__(self):
        return "Name(%s, %s)" % (repr(self.name), repr(self.parser))


class Description(_GRParser):
    def __init__(self, description, parser):
        self.description = description
        self.parser = parser
        # This should /not/ have any railroad children to prevent a Description
        # object from being descended into when constructing railroad diagrams
    
    def parse(self, text, position, end, space):
        return self.parser.parse(text, position, end, space)
    
    def do_graph(self, graph):
        graph.add_node(id(self), label="Description:\n" + repr(self.description))
        graph.add_edge(id(self), id(self.parser))
        return [self.parser]
    
    def create_railroad(self, options):
        return _rr.Token(_rr.DESCRIPTION, self.description)
    
    def __repr__(self):
        return "Description(%s, %s)" % (repr(self.description), repr(self.parser))


Desc = Description


def separated(item_parser, separator_parser):
    """
    Creates and returns a parser that will parse one or more items parsed by
    item_parser, separated by separator_parser. The result of the parser is a
    list of the items produced by item_parser.
    
    Both item_parser and separator_parser will be automatically promote()d, so
    a string such as ",", for example, could be used as separator_parser
    without having to wrap it in a Literal first.
    """
    item_parser, separator_parser = promote(item_parser), promote(separator_parser)
    # The translating of item_parser's result to be placed in a tuple is to
    # prevent the + concatenating it with the ()[...] from filtering it out if
    # the item_parser results in None. Ideally, there should be some way to
    # create a Then while telling it not to filter out None instances. 
    return (item_parser[lambda a: (a,)] + (~separator_parser + item_parser)[...])[lambda (a, rest): [a] + rest]


delimited = separated


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
    
    Named tuples (instances of classes created with collections.namedtuple) are
    treated as normal object, not tuples, so they will not be flattened.
    """
    if value is None:
        return []
    if not (isinstance(value, list) or type(value) is tuple): # Checking for
        # type(value) is tuple instead of isinstance(value, tuple) so that
        # named tuples are treated as normal objects and are not expanded
        return [value]
    result = []
    for item in value:
        item = flatten(item)
        result += list(item)
    return result


def concat(value, delimiter=""):
    """
    Walks through value, which should be a list or a tuple potentially
    containing other lists/tuples, and extracts all strings from it (and
    recursively from any other lists/tuples that it contains). These strings
    are then concatenated using the specified delimiter.
    
    Right now, this delegates to flatten to flatten out the specified value. It
    then iterates over all of the items in the resulting list and concatenates
    all of them that are strings.
    """
    return delimiter.join([s for s in flatten(value) if isinstance(s, basestring)])


def list_dict(list_of_pairs):
    """
    Similar to dict(list_of_pairs), but the values in the returned dict are
    lists containing one item for each pair with the specified key. In other
    words, this can be used to convert a list of 2-tuples into a dict where the
    same key might be present twice (or more) in the specified list; the value
    list in the resulting dict will have two (or more) items in it.
    
    This is intended to be used as parser[list_dict] in place of parser[dict]
    when all of the items with a particular tag need to be preserved; this is
    Parcon's equivalent to Pyparsing's setResultsName(..., listAllMatches=True)
    behavior.
    
    For example:
    
    >>> # The last tuple wins:
    >>> dict([(1,"one"),(2,"two"),(1,"first")])
    {1: 'first', 2: 'two'}
    >>> # All results included in lists:
    >>> list_dict([(1,"one"),(2,"two"),(1,"first")])
    {1: ['one', 'first'], 2: ['two']}
    """
    result = {}
    for k, v in list_of_pairs:
        container = result.get(k, None)
        if container is None:
            container = []
            result[k] = container
        container.append(v)
    return result


alpha_word = Word(alpha_chars)(name="alpha word")
alphanum_word = Word(alphanum_chars)(name="alphanum word")
id_word = Word(alphanum_chars, init_chars=alpha_chars)(name="id word")
title_word = Word(alphanum_chars, init_chars=upper_chars)(name="title word")

digit = Digit()(name="digit")
integer = Exact(+digit)["".join](name="integer")
number = Exact(-CharIn("+-") + +digit + -(SignificantLiteral(".") + +digit)
            )[flatten]["".join](name="number")
rational = number






































