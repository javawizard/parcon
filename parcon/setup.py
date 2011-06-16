from distutils.core import setup

setup(
    name="parcon",
    version="0.1.9",
    author="Alexander Boyd",
    author_email="alex@opengroove.org",
    url="http://www.opengroove.org/parcon/",
    description="A parser combinator library (and soon-to-be formatter combinator library as well) that's easy to use and that provides informative error messages.",
    long_description=
"""
Parcon is a parser combinator library. It can be used for parsing both normal
text and binary data. It's designed to be easy to use and to provide informative
error messages.

All of the classes, and most of the functions, in Parcon are comprehensively
documented. The best place to look for help is in Parcon's module documentation.

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

    print expr.parseString("1+2") # prints 3
    print expr.parseString("1+2+3") # prints 6
    print expr.parseString("1+2+3+4") # prints 10
    print expr.parseString("3*4") # prints 12
    print expr.parseString("5+3*4") # prints 17
    print expr.parseString("(5+3)*4") # prints 32
    print expr.parseString("10/4") # prints 2.5
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