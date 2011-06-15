Parcon is a parser combinator library. It's designed to be easy to use, easy to learn, and to provide informative error messages.

**Pydoc documentation for Parcon** is available [here](parcon.html).

**Some example Parcon grammars** (along with explanations of what they do) are available [here](parcon-examples.html). 

# Introduction

*One important note here: for the rest of the documentation, we'll assume that you've run the following Python statement:*

	from parcon import *

*so that all of the parcon functions and classes are available in the local namespace.*

Parcon is a Python parser library that uses combinatorial parsing. There is no separate language for declaring grammars; every Parcon grammar is written simply as a series of Python expressions using a number of classes that Parcon provides to represent grammars.

Each of these classes is a parser by itself. Every parser class parses a portion of a string and, if it succeeds, returns some parser-specific object representing the result.

Each parser class is a subclass of Parser, and as such, each parser class provides some important methods:

* **parseString**: This is the method that you'll likely use most. You typically call it like parser.parseString("some text to parse"), and it either returns the result of the parser or throws an exception if the parser didn't match the input. There are two additional arguments to this method that will be discussed later.
* **parse**: You typically won't use this method yourself, but you'll need to know about it if you decide to implement your own parser for whatever reason. It's the method that actually knows how to parse text. Each parser provides an implementation of this method. It will be discussed in more detail later.

Methods for parsing input from files or sockets will be present in a future release of Parcon.

# Literal and SignificantLiteral: literal string parsers

Let's look at one of the most basic parsers that Parcon provides: Literal. This parser is constructed with a literal string. It matches only if the input is that string, and it returns None. A similar class, SignificantLiteral, returns the literal string itself instead of None.

So, our first example:

	expr = Literal("hello")

expr is now a parser that will parse any piece of text that is exactly "hello".

# First: tries multiple parsers until one succeeds

This isn't really much use to us yet, so let's look at another parser: First. This parser is constructed with any number of other parsers. It tries to match the first parser first. If it matches, it returns whatever that parser's result was. Otherwise, it tries the second parser, and so on. If none of the parsers match, First fails.

Using this, we can create a parser that matches either "hello" or "bye":

	expr = First(Literal("hello"), Literal("bye"))

If we call expr.parseString("hello") or expr.parseString("bye"), the result will be None. If we call expr.parseString with anything else, an exception will be thrown indicating the problem. If we change Literal to SignificantLiteral:

	expr = First(SignificantLiteral("hello"), SignificantLiteral("bye"))

then the result of expr.parseString("hello") will be "hello", and similar for "bye".

# Interlude: operator overloading

Up until now, actual Parcon classes have been used to create parsers. Every parser overloads some operators, though, which allow us to create parsers in a less verbose manner. These operators are available:

* **x + y** is the same as **Then(x, y)**.
* **x | y** is the same as **First(x, y)**.
* **-x** is the same as **Optional(x)**.
* **+x** is the same as **OneOrMore(x)**.
* **x - y** is the same as **Except(x, y)**.
* **x[min:max]** is the same as **Repeat(x, min, max)**.
* **x[function]** is the same as **Translate(x, function)**.
* **"x" op some_parser** or **some_parser op "x"** is the same as **Literal("x") op some_parser** or **some_parser op Literal("x")**, respectively.

You've only seen First thus far; the rest of these parsers will be discussed later. If the literal string is used on one side of an operator where a parser is used on the other side, the literal string will be wrapped with Literal automatically. Some other parsers (such as Keyword) will also automatically wrap literal string passed into them with instances of Literal.

# Then: one parser followed by another

Going back to our hello/bye example, let's say that we wanted to be able to parse "hello there" and "bye there", but we want the result of our parser to still be "hello" or "bye", so we can't just add " there" to the end of each SignificantLiteral. We can use Then to do this. Then attempts to match its first parser. If it succeeds, it matches its second parser where the first one stopped. If either parser fails, Then fails. If both parsers succeed, the result is a tuple containing the results, with two exceptions: first, if either of Then's parsers also produce a tuple, the resulting tuples are flattened together, and second, if either of Then's parsers produces None, the result is simply the result of the parser that did not, or None if both parsers did.

So let's try it out. We'll be using | to represent First and + to represent Then, as outlined in the previous section.

	expr = (SignificantLiteral("hello") | SignificantLiteral("bye")) + " there"

This parser will match "hello there" or "bye there", and will return "hello" or "bye", respectively. All other strings will result in an exception.

# Further reading

Each parser class in the Parcon library has a docstring specifying what it does and how to use it. That's probably the best place to start with all of the other parsers.





































