
"""
This module provides various classes for specifying what a particular syntax
diagram (a.k.a. railroad diagram) should look like.

The actual drawing of diagrams created with classes in this module is left up
to other modules included with Parcon in order to allow railroad diagrams that
look different to be created. The main one of these is the submodule raildraw,
which is a from-scratch railroad diagram drawing engine that can take a
railroad diagram as specified by classes in this module and convert it to a PNG
image.

Here's a really simple example that uses raildraw to draw a syntax diagram:

from parcon import First
from parcon.railroad import create_railroad
from parcon.railroad.raildraw import draw_to_png
# Create a parser to draw
some_parser = "Hello, " + First("world", "all you people")
# Then draw a diagram of it.
draw_to_png(create_railroad(some_parser, {}), "test.png")
"""

from itertools import chain

PRODUCTION = 1
TEXT = 2
ANYCASE = 3
DESCRIPTION = 4

class Component(object):
    def copy(self):
        raise NotImplementedError
    
    def optimize(self):
        pass


class Nothing(Component):
    def copy(self):
        return Nothing()


class Then(Component):
    def __init__(self, *constructs):
        self.constructs = list(constructs)
    
    def copy(self):
        return Then(*[c.copy() for c in self.constructs])
    
    def optimize(self):
        modified = True
        while modified:
            modified = False
            old_constructs = self.constructs
            new_constructs = list(chain(*[c.constructs if isinstance(c, Then) else [c] for c in old_constructs]))
            if old_constructs != new_constructs:
                modified = True
            self.constructs = new_constructs
        for construct in self.constructs:
            construct.optimize()


class Or(Component):
    def __init__(self, *constructs):
        self.constructs = list(constructs)
    
    def copy(self):
        return Or(*[c.copy() for c in self.constructs])
    
    def optimize(self):
        modified = True
        while modified:
            modified = False
            old_constructs = self.constructs
            new_constructs = list(chain(*[c.constructs if isinstance(c, Or) else [c] for c in old_constructs]))
            if old_constructs != new_constructs:
                modified = True
            self.constructs = new_constructs
        for construct in self.constructs:
            construct.optimize()


class Token(Component):
    def __init__(self, type, text):
        assert type >= 1 and type <= 4
        self.type = type
        self.text = text
    
    def copy(self):
        return Token(self.type, self.text)


class Loop(Component):
    def __init__(self, component, delimiter):
        self.component = component
        self.delimiter = delimiter
    
    def copy(self):
        return Loop(self.component.copy(), self.delimiter.copy())
    
    def optimize(self):
        if isinstance(self.component, Loop):
            self.component, self.delimiter = self.component.component, Or(self.component.delimiter, self.delimiter)
            self.optimize()
            return
        self.component.optimize()
        self.delimiter.optimize()


class Bullet(Component):
    def copy(self):
        return Bullet()


class Railroadable(object):
    def create_railroad(self, options):
        raise NotImplementedError
    
    def draw_railroad_to_png(self, options, filename):
        """
        Draws a syntax diagram for this object to the specified .png image file
        using the specified options. For now, just pass {} (i.e. an empty
        dictionary) as options; I'll document what this actually does at a
        later date.
        """
        # raildraw /has/ to be imported here, not at the top of the module,
        # because it depends on us and circular dependency issues will arise
        # if the import is done at the top of this module
        from parcon.railroad import raildraw as _raildraw
        diagram = Then(Bullet(), self.create_railroad(options), Bullet())
        _raildraw.draw_to_png(diagram, options, filename)
        del _raildraw


def create_railroad(value, options):
    if not isinstance(value, Railroadable):
        raise Exception("Trying to create a railroad diagram for an object of "
                        "class " + str(type(value)) + " but that type is not a "
                        "subclass of Railroadable, so this is not allowed.")
    return value.create_railroad(options)







































