"""
Pargen is a formatter combinator library. It's much the opposite of parcon:
while parcon parses text into objects, pargen formats objects into text.
I'll get more documentation up on here soon, but for now, here's a JSON
formatter (essentially a simplified reimplementation of Python's json.dumps):

>>> from parcon.pargen import *
>>> from decimal import Decimal
>>> json = Forward()
>>> number = Type(float, int, long, Decimal) & String()
>>> boolean = Type(bool) & ((Is(True) & "true") | (Is(False) & "false"))
>>> null = Is(None) & "null"
>>> string = Type(basestring) & '"' + String() + '"'
>>> json_list = Type(list, tuple) & ("[" + ForEach(json, ", ") + "]")
>>> json_map =Type(dict) &  ("{" + ForEach(Head(json) + ": " + Tail(json), ", ") + "}")
>>> json << (boolean | number | null | string | json_list | json_map)

You can then do things like:

>>> json.format([True,1,{"2":3,"4":None},5,None,False,"hello"]).text
'[true, 1, {"2": 3, "4": null}, 5, null, false, "hello"]'

You'll probably want to take a look at the Formatter class. It's the "main"
class for pargen, analogous to parcon.Parser. It contains some module
documentation that can probably help to get you started.
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
    """
    A formatter result. Instances of this class are returned from
    Formatter.format.
    
    Two fields are present: text and remainder. If this result represents
    failure of a formatter, text will be None and remainder will be unspecified.
    If this result represents success, text will be the text produced by the
    formatter, and remainder will be the portion of the input object that the
    parser did not consume.
    
    Result objects have a boolean truth value corresponding to whether or not
    they succeeded. For example, this could be used to print whether some
    particular result succeeded:
    
    if some_result:
        print "Result succeeded"
    else:
        print "Result failed"
    """
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
    """
    Method called by formatters to create a new Result object indicating
    failure. Formatters typically fail when their input was not in the format
    that they expected it to be, or for other reasons. Head, for example, fails
    if the provided value is not a sequence, or if the sequence provided is
    empty.
    """
    return Result(None, None)


def match(text, remainder):
    """
    Method called by formatters to create a new Result object indicating
    success. text is the text that the formatter produced; this can be the
    empty string, but it must be a string of some sort. remainder is the
    portion of the input value that the formatter did not consume; parser such
    as Then, for example, pass the remainder of their first parser as the value
    to their second parser.
    """
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
    The main class of this module, analogous to parcon.Parser, but for
    formatters.
    
    Like parcon.Parser, instances of Formatter should not be directly
    constructed; instances of its various subclasses should be created and used
    instead.
    
    The main method that you'll want to look at is format.
    """
    def format(self, input):
        """
        Formats a specified input object into a piece of text. Subclasses of
        Formatter should override this and provide an actual implementation.
        
        The return value of this method is a Result object created by calling
        either the match function or the failure function. The former function
        is used to indicate success; the latter is used to indicate that the
        formatter failed for some reason, such as the input not being of an
        appropriate type.
        """
        raise Exception("format not implemented for " + str(type(self)))
    
    __add__ = op_add
    __and__ = op_and
    __or__ = op_or
    __radd__ = reversed(op_add)
    __rand__ = reversed(op_and)
    __ror__ = reversed(op_or)


class Literal(Formatter):
    """
    A formatter that outputs a specified piece of literal text. It doesn't
    consume any of the input.
    """
    def __init__(self, text):
        self.text = text
    
    def format(self, input):
        return match(self.text, input)


class ForEach(Formatter):
    """
    A formatter that expects a sequence or dict as input. If the input is a
    dict, its items() method will be called, and the resulting list used as the
    input sequence. For each item in the input sequence, ForEach calls the
    specified formatter, passing in that item. The results of all of these
    formatters are then concatenated into a single string, separated by the
    specified delimiter string (which defaults to the empty string). This
    string is then returned. ForEach consumes all of the input so that the
    remainder is the empty list.
    """
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
    """
    A formatter that formats whatever data it's provided as input using
    Python's str() function. This is typically the formatter that you'll use
    to format numbers and other things like that. The remainder is always None.
    """
    def format(self, input):
        return match(str(input), None)


class Repr(Formatter):
    """
    Same to String(), but this formatter uses repr() instead of str() to do the
    actual formatting.
    """
    def format(self, input):
        return match(repr(input), None)


class _ListExtremity(Formatter):
    """
    An abstract formatter that makes dealing with items at either end of a
    sequence easier to work with. You shouldn't use this formatter; instead,
    use one of its four subclasses, Head, Tail, Front, and Back.
    """
    def __init__(self, formatter):
        self.formatter = formatter
    
    def format(self, input):
        if not sequence_type.matches(input):
            return failure()
        elif len(input) < 1:
            return failure()
        else:
            value = self._value_function(input)
            remainder = self._remainder_function(input)
        result = self.formatter.format(value)
        if not result:
            return failure()
        return match(result.text, remainder)


class Head(_ListExtremity):
    """
    A formatter meant to be used on lists. It's constructed with another
    formatter. When it's called, it expects some sort of sequence; it fails if
    the value provided to it is not a sequence, or if it's an empty sequence.
    If there's at least one item, this formatter calls its underlying formatter
    with the first item in the sequence. It returns whatever this formatter
    returns, with the remainder being all of the list items except for the
    first. In this way, repeated invocations of Head remove items from the
    front of the list, so, for example, the formatter:
    
    >>> first_three = Head(String()) + Head(String()) + Head(String())
    >>> first_three.format("12345").text
    '123'
    """
    _value_function = lambda self, x: x[0]
    _remainder_function = lambda self, x: x[1:]


class Tail(_ListExtremity):
    """
    Same as Head, but this operates on and removes the last item in the list
    instead of the first item.
    """
    _value_function = lambda self, x: x[-1]
    _remainder_function = lambda self, x: x[:-1]


class Front(_ListExtremity):
    """
    Same as Head, but the remainder of this parser is exactly the value passed
    to it, I.E. it doesn't consume any input. Thus the formatter:
    
    >>> first_three_times = Front(String()) + Front(String()) + Front(String())
    >>> first_three_times.format("12345").text
    '111'
    """
    _value_function = lambda self, x: x[0]
    _remainder_function = lambda self, x: x


class Back(_ListExtremity):
    """
    Same as Front, but this operates on the last item in the list instead of
    the first item.
    """
    _value_function = lambda self, x: x[-1]
    _remainder_function = lambda self, x: x


class Type(Formatter):
    """
    A formatter that produces the empty string and consumes no input. However,
    it only succeeds if the value passed to it matches at least one of the
    specified static types. Each of those types can be a Python class or a
    static type as defined by parcon.static.
    """
    def __init__(self, *static_types):
        self.static_type = static.Or(static_types)
    
    def format(self, input):
        if not self.static_type.matches(input):
            return failure()
        return match("", input)


class And(Formatter):
    """
    A formatter that acts like its second formatter, except that its first
    formatter must succeed in order for the second formatter to be considered.
    What the first formatter consumes will be ignored; the second formatter
    will be provided with the exact value that was passed into the And instance.
    
    This could be used with Type, for example, to make a certain formatter only
    succeed if its input is of a specific type; for example:
    
    >>> int_formatter = Type(int, long) & String()
    
    would be a formatter that formats ints and longs as per the String
    formatter but that fails if any other type is passed to it.
    """
    def __init__(self, first, second):
        self.first = first
        self.second = second
    
    def format(self, input):
        first_result = self.first.format(input)
        if not first_result:
            return failure()
        return self.second.format(input)


class Then(Formatter):
    """
    A formatter that applies two formatters one after the other, concatenating
    their results and returning them. The remainder of the first formatter will
    be passed to the second formatter as its value, and the remainder of Then
    will be the remainder of the second formatter.
    
    If either formatter fails, Then also fails.
    """
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
    """
    A formatter that attempts to apply all of its formatters in sequence to the
    value provided to First; First then acts exactly like the first of its
    formatters to succeed. Each formatter is passed a fresh copy of the value
    provided to First, without regard to what the formatter applied before it
    may have consumed.
    
    If none of the formatters match, First fails.
    """
    def __init__(self, *formatters):
        self.formatters = formatters
    
    def format(self, input):
        for formatter in self.formatters:
            result = formatter.format(input)
            if result:
                return match(result.text, result.remainder)
        return failure()


class Forward(Formatter):
    """
    A forward-declared formatter. This allows for mutually-recursive
    formatters; the actual underlying formatter that a particular Forward
    delegates to can be set later on after the Forward is created.
    
    A formatter can be set into this Forward by doing:
    
    some_forward_formatter << formatter_to_delegate_to
    
    or:
    
    some_forward_formatter.set(formatter_to_delegate_to)
    
    It's important to remember that << is not the lowest precedence of all
    operators; you'll probably want to wrap the right-hand side in parentheses
    in order to avoid precedence issues that might otherwise occur.
    """
    def __init__(self, formatter=None):
        self.formatter = formatter
    
    def format(self, input):
        if self.formatter is None:
            raise Exception("Forward has not yet had a formatter set into it")
        return self.formatter.format(input)
    
    def set(self, formatter):
        self.formatter = formatter
    
    __lshift__ = set


class Is(Formatter):
    """
    A formatter that consumes no input and returns the empty string. However,
    it only succeeds if its input is equal, as per the == operator, to a value
    provided to the Is instance when it's constructed.
    """
    def __init__(self, value):
        self.value = value
    
    def format(self, input):
        if input == self.value:
            return match("", input)
        return failure()


class IsExactly(Formatter):
    """
    Same as Is, but IsExactly uses Python's is operator instead of Python's ==
    operator to perform the equality check. This should be used for True,
    False, None, and other such values.
    """
    def __init__(self, value):
        self.value = value
    
    def format(self, input):
        if input is self.value:
            return match("", input)
        return failure()







































