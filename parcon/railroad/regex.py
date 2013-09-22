
"""
This module knows how to convert some regular expressions into railroad
objects.
"""

from parcon import railroad as rr
import parcon as p

regex_parser = None

def _convert_repetition(construct, flag):
    if flag is None:
        return construct
    if flag == "*":
        return rr.Or(rr.Loop(construct, rr.Nothing()), rr.Nothing())
    if flag == "+":
        return rr.Loop(construct, rr.Nothing())
    if flag == "?":
        return rr.Or(construct, rr.Nothing())
    raise ValueError


def _translate_backslash(char):
    if char == "\\n":
        return "\n"
    if char == "\\r":
        return "\r"
    if char == "\\t":
        return "\t"
    return char


def init_parser():
    global regex_parser
    global component
    global alt_component
    global char
    global char_class
    global char_class_range
    global char_class_char
    global alternative
    expr = p.Forward()
    char_class_char = (p.AnyChar() - p.CharIn("^]"))[lambda x: rr.Token(rr.TEXT, x)]
    char_class_range = ((p.AnyChar() - p.CharIn("^-]")) + "-" + (p.AnyChar() - "-]"))[
        lambda (a, b): rr.Or(*[rr.Token(rr.TEXT, chr(c)) for c in range(ord(a), ord(b)+1)])]
    char_class = ("[" + +(char_class_range | char_class_char) + "]")[
        lambda x: rr.Or(*x) if len(x) != 1 else x[0]]
    char = (p.AnyChar() - p.CharIn("[]().|\\"))
    backslash = ("\\" + p.AnyChar())[_translate_backslash]
    chars = (+(backslash | char))[p.concat][lambda x: rr.Token(rr.TEXT, x)]
    matching_group = "(" + expr + ")"
    non_matching_group = "(?:" + expr + ")"
    component = char_class | chars | non_matching_group | matching_group
    alt_component = (component + p.Optional(p.CharIn("*+?"), (None,)))[
        lambda (t, m): _convert_repetition(t, m)]
    alt_component = alt_component[...][lambda x: x[0] if len(x) == 1 else rr.Then(*x)]
    alternative = p.InfixExpr(alt_component, [("|", rr.Or)])
    expr << alternative
    regex_parser = expr


def convert_regex(regex):
    """
    Converts a regex, specified as a string, to an instance of one of the
    subclasses of parcon.railroad.Component. If the specified regex contains
    constructs that this module does not understand, None will be returned.
    """
    if regex_parser is None:
        init_parser()
    try:
        return regex_parser.parse_string(regex, whitespace=p.Invalid())
    except p.ParseException:
        return None




































