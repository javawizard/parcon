#!/usr/bin/env python

from distutils.core import setup

setup(
    name="parcon",
    version="0.1.18",
    author="Alexander Boyd",
    author_email="alex@opengroove.org",
    url="http://www.opengroove.org/parcon/",
    description="A parser/formatter library that's easy to use and that provides informative error messages.",
    long_description=
"""
Parcon is a parser combinator library. It can be used for parsing both normal
text and binary data. It's designed to be easy to use and to provide informative
error messages.

Pargen, which is provided as a submodule of Parcon, is a formatter combinator
library. It's much the opposite of Parcon: while Parcon is used to parse text
into various objects, Pargen is used to format objects into text. As an
example, if you wanted to reimplement Python's json module, you would use
Parcon to implement json.loads and Pargen to implement json.dumps.

Static, which is also provided as a submodule of Parcon, is a static typing
library and Python object pattern library. It lets you build patterns that
match Python objects based on their type, their attributes, certain properties
such as whether or not the object is a sequence, the types that make up the
object's values if the object is a sequence, and so on.

All of the classes, and most of the functions, in Parcon are comprehensively
documented. The best place to look for help is in Parcon's module documentation.
Pargen's classes and functions and Static's classes and functions are also 
documented, though not quite as well as Parcon's are at present.

Here's an example of a simple expression evaluator written using Parcon::

    from parcon import *
    from decimal import Decimal
    import operator
    expr = Forward()
    number = (+Digit() + -(SignificantLiteral(".") + +Digit()))[flatten]["".join][Decimal]
    term = number | "(" + expr + ")"
    term = InfixExpr(term, [("*", operator.mul), ("/", operator.truediv)])
    term = InfixExpr(term, [("+", operator.add), ("-", operator.sub)])
    expr << term

This expression evaluator can be used thus::

    print expr.parse_string("1+2") # prints 3
    print expr.parse_string("1+2+3") # prints 6
    print expr.parse_string("1+2+3+4") # prints 10
    print expr.parse_string("3*4") # prints 12
    print expr.parse_string("5+3*4") # prints 17
    print expr.parse_string("(5+3)*4") # prints 32
    print expr.parse_string("10/4") # prints 2.5

More examples can be found on `Parcon's blog <http://blog.parcon.opengroove.org>`_,
and more information in general can be found at `Parcon's website <http://parcon.opengroove.org>`_.

Parcon is currently much more comprehensively documented than Pargen and Static
are. Improved documentation for Pargen and Static will come soon.
""",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing"
    ],
    packages=["parcon"]
)