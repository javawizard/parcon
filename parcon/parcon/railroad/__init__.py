
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
# Create a parser to draw
some_parser = "Hello, " + First("world", "all you people")
# Then draw a diagram of it.
some_parser.draw_railroad_to_png({}, "test.png")
"""

from itertools import chain
from parcon import ordered_dict

PRODUCTION = 1
TEXT = 2
ANYCASE = 3
DESCRIPTION = 4

class Component(object):
    def copy(self):
        raise NotImplementedError
    
    def optimize(self):
        pass
    
    def __repr__(self):
        return self.__str__()


class Nothing(Component):
    def copy(self):
        return Nothing()
    
    def __str__(self):
        return "Nothing()"


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
            new_constructs = list(chain(*[c.constructs if isinstance(c, Then) else [c] for c in old_constructs if not isinstance(c, Nothing)]))
            if old_constructs != new_constructs:
                modified = True
            self.constructs = new_constructs
        for construct in self.constructs:
            construct.optimize()
    
    def __str__(self):
        return "Then(%s)" % ", ".join([repr(c) for c in self.constructs])


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
    
    def __str__(self):
        return "Or(%s)" % ", ".join([repr(c) for c in self.constructs])


class Token(Component):
    def __init__(self, type, text):
        assert type >= 1 and type <= 4
        self.type = type
        self.text = text
    
    def copy(self):
        return Token(self.type, self.text)
    
    def __str__(self):
        return "Token(%s, %s)" % (repr(self.type), repr(self.text))


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
    
    def __str__(self):
        return "Loop(%s, %s)" % (repr(self.component), repr(self.delimiter))


class Bullet(Component):
    def copy(self):
        return Bullet()
    
    def __str__(self):
        return "Bullet()"


class Railroadable(object):
    """
    A class representing an object that can be drawn as a railroad diagram.
    Most Parcon parsers subclass this class in addition to parcon.Parser.
    """
    railroad_children = []
    railroad_production_name = None
    railroad_production_delegate = None
    
    def create_railroad(self, options):
        raise NotImplementedError
    
    def get_productions(self):
        map = ordered_dict.OrderedDict()
        visited = set()
        self._list_productions(map, visited)
        # TODO: in the future, check that each possible result for a given
        # production generates a railroad that means syntactically the same
        # thing. For now, we're just going to use the first one in the list.
        return ordered_dict.OrderedDict([(k, v[0]) for k, v in map.items()])
    
    def _list_productions(self, map, visited):
        if self in visited: # Already visited this object
            return
        visited.add(self)
        if self.railroad_production_name is not None:
            the_list = map.get(self.name, None)
            if not the_list:
                the_list = []
                map[self.name] = the_list
            if self.railroad_production_delegate not in the_list:
                the_list.append(self.railroad_production_delegate)
        for r in self.railroad_children:
            ensure_railroadable(r)
            r._list_productions(map, visited)
    
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
    
    def draw_productions_to_png(self, options, filename, tail=[]):
        productions = self.get_productions()
        if len(productions) == 0:
            raise Exception("No named productions to generate")
        # Sort the specified tail productions to the end
        for name in tail:
            if name in productions:
                value = productions[name]
                del productions[name]
                productions[name] = value
        from parcon.railroad import raildraw as _raildraw
        _raildraw.draw_to_png(ordered_dict.OrderedDict([(k,
            Then(Bullet(), v.create_railroad(options), Bullet()))
            for k, v in productions.items()]), options, filename)
        del _raildraw


def ensure_railroadable(value):
    if not isinstance(value, Railroadable):
        raise Exception("Trying to create a railroad diagram for an object of "
                        "class " + str(type(value)) + " but that type is not a "
                        "subclass of Railroadable, so this is not allowed.")


def create_railroad(value, options):
    ensure_railroadable(value)
    return value.create_railroad(options)







































