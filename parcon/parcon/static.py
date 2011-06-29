
"""
A static typing library for Python. That may sound at first as if this module
was designed to simply decorate methods specifying the type of objects that
must be passed to them, and it can definitely do that. However, it's quite a
bit more powerful than that. It has a collection of constructs that allow
constructing type patterns, objects that allow a form of pattern matching
against Python objects. For example, And(Type(list), All(Type(int))) is a type
pattern that matches all objects that are instances of list and whose values
are all ints. All(Type(int)) would match any iterable object, not just a list,
whose values are ints, while Or(Not(Iterable()), All(Type(int))) would
additionally match objects that are not iterable, and Type(int) would simply
match objects of type int.

A short notation can be used to represent some of the type constructs. These
must be passed to the compile function to convert them to type patterns for
actual use. Any Python type is a type pattern matching objects of that type.
A list containing one item, a type pattern (short or otherwise), is a type
pattern matching objects that are iterable and whose values are all of that
type and a tuple containing one or more items is a type pattern that matches
any object that matches at least one of its contained types. In that way,
Python types are converted to instances of Type, lists are converted to
instances of All, and tuples are converted to instances of Or.

Type patterns have two methods, matches and check_matches. Both take a single
argument, the value to match against. matches returns true if the specified
value matches the type pattern on which the matches function was called.
check_matches calls matches and throws a StaticTypeError if it returned false.

Each of the type pattern constructs clearly defines what fields it creates,
which allows for metatyping: creating type patterns that match type patterns
themselves. Such a thing is used in JPath's query optimizer, where the
optimizer uses metatyping to determine if the type pattern that an optimizer
will be called for makes any definitive assertions as to what type of compiler
production it operates on, which allows the compiler to significantly decrease
the time it takes to look up the set of optimizations to be applied to a
particular compiler production.
"""

class StaticTypeError(Exception):
    """
    An exception thrown when an object passed to check_matches does not match
    the specified static type.
    """
    pass


class TypeFormatError(Exception):
    """
    An exception thrown when a static type is malformed. This could happen if,
    for example, the number 5 was passed to the compile function; 5 is
    obviously not a valid static type, so a TypeFormatError would be raised.
    """
    pass


class InternalError(Exception):
    """
    An exception thrown when an internal problem occurs with the static type
    library. This usually indicates a bug in this library.
    """
    pass


class StaticType(object):
    """
    The class that all static types extend from. It has two useful methods:
    matches and check_matches.
    
    StaticType cannot itself be instantiated; you can only construct instances
    of subclasses of StaticType.
    """
    def matches(self, value):
        """
        Checks to see if the specified object matches this static type. If it
        does, True will be returned, and False will be returned if it doesn't.
        Subclasses of StaticType must override this to perform the actual
        matching; StaticType's implementation throws an InternalError.
        """
        raise InternalError("StaticType subclass " + str(type(self)) + 
                " doesn't implement the matches function")
    
    def check_matches(self, value):
        """
        Calls self.matches(value). If the reslt is false, a StaticTypeError is
        raised. If the result is true, this method simply returns.
        """
        if not self.matches(value):
            raise StaticTypeError("Value " + str(value) + " is not of type " + 
            str(self));
    
    def __str__(self):
        raise Exception(str(type(self)) + " does not provide __str__")
    
    def __repr__(self):
        return self.__str__()

class Type(StaticType):
    """
    A static type that checks to make sure values are instances of a
    particular Python type as per Python's bult-in isinstance function.
    
    The type is stored in a field named type.
    """
    def __init__(self, type):
        self.type = type
    
    def matches(self, value):
        return isinstance(value, self.type)
    
    def __str__(self):
        return "Type(" + str(self.type) + ")"


class Or(StaticType):
    """
    A static type that matches a value if any of its constructs match that
    particular value. The constructs are stored in a field named constructs.
    """
    def __init__(self, *constructs):
        self.constructs = [compile(c) for c in constructs]
    
    def matches(self, value):
        for c in self.constructs:
            if c.matches(value):
                return True
        return False
    
    def __str__(self):
        return "Or(" + ", ".join(str(c) for c in self.constructs) + ")"


class And(StaticType):
    """
    A static type that matches a value if all of its constructs match that
    particular value. The constructs are stored in a field named constructs.
    """
    def __init__(self, *constructs):
        self.constructs = [compile(c) for c in constructs]
    
    def matches(self, value):
        for c in self.constructs:
            if not c.matches(value):
                return False
        return True
    
    def __str__(self):
        return "And(" + ", ".join(str(c) for c in self.constructs) + ")"


class Not(StaticType):
    """
    A static type that matches a value if that particular value does not match
    the construct with which this Not instance was created. The construct is
    stored in a field named construct.
    """
    def __init__(self, construct):
        self.construct = compile(construct);
    
    def matches(self, value):
        return not self.construct.matches(value)
    
    def __str__(self):
        return "Not(" + str(self.construct) + ")"


class All(StaticType):
    """
    A static type that matches a value if that particular value is iterable
    and all of its values match the component type with which this All
    instance was created. The type is stored in a field named component_type.
    """
    def __init__(self, component_type):
        self.component_type = compile(component_type)
    
    def matches(self, value):
        try:
            iterator = iter(value)
        except TypeError: # Not an iterable type
            return False
        for item in iterator:
            if not self.component_type.matches(item):
                return False
        return True
    
    def __str__(self):
        return "All(" + str(self.component_type) + ")"


class Any(StaticType):
    """
    A static type that matches a value if that particular value is iterable
    and any of its values match the component type with which this All
    instance was created. The type is stored in a field named component_type.
    """
    def __init__(self, component_type):
        self.component_type = compile(component_type)
    
    def matches(self, value):
        try:
            iterator = iter(value)
        except TypeError: # Not an iterable type
            return False
        for item in iterator:
            if self.component_type.matches(item):
                return True
        return False
    
    def __str__(self):
        return "Any(" + str(self.component_type) + ")"


class Field(StaticType):
    """
    A static type that matches a value if that particular value has all of the
    fields named when constructing this Field instance and they are all match
    the type specified when constructing this Field instance. The field type
    is stored in a field named field_type and the field names are stored in a
    field named field_names. 
    """
    def __init__(self, field_type, *field_names):
        self.field_type = compile(field_type)
        self.field_names = list(field_names)
    
    def matches(self, value):
        for name in self.field_names:
            try:
                field_value = getattr(value, name)
                if not self.field_type.matches(field_value):
                    return False
            except AttributeError: # No such attribute, so return false
                return False
        return True
    
    def __str__(self):
        return "Field(" + ", ".join([str(self.field_type)] + list(self.field_names)) + ")"


class Iterable(StaticType):
    """
    A static type that matches a value if the value is iterable. A value is
    iterable if calling the Python function iter(value) does not raise a
    TypeError.
    """
    def __init__(self):
        pass
    
    def matches(self, value):
        try:
            iter(value)
            return True
        except TypeError:
            return False
    
    def __str__(self):
        return "Iterable()"


class Sequence(StaticType):
    """
    A static type that matches a value if the value is a sequence. A value is
    defined to be a sequence if calling len(value) does not raise a TypeError.
    """
    def matches(self, value):
        try:
            len(value)
            return True
        except TypeError:
            return False
    
    def __str__(self):
        return "Sequence()"


class Positional(StaticType):
    """
    A static type that matches a value if the value is a sequence, it has
    exactly the same number of value as were passed to the Positional instance
    when it was created, and each item matches the corresponding static type
    passed to the Positional instance when it was created. For example,
    Positional(int, str, bool) would match a sequence of length 3 containing
    an integer, a string, and a boolean, at each respective position in the
    sequence.
    """
    def __init__(self, *types):
        self.types = [compile(type) for type in types]
    
    def matches(self, value):
        if len(self.types) != len(value):
            return False
        for t, v in zip(self.types, value):
            if not t.matches(v):
                return False
        return True
    
    def __str__(self):
        return "Positional(%s)" % ", ".join(str(t) for t in self.types)


class Is(StaticType):
    """
    A static type that matches a value if the value is equal, as determined by
    the == operator, to a specified value.
    """
    def __init__(self, value):
        self.value = value
    
    def matches(self, value):
        return self.value == value


class Everything(StaticType):
    """
    A static type that matches all values.
    """
    def __init__(self):
        pass
    
    def matches(self, value):
        return True
    
    def __str__(self):
        return "Everything()"


def compile(short_type):
    """
    Compiles the specified static type. This involves converting Python classes
    to instances of Type, tuples to instances of Or, and lists to instances of
    All. Instances of one of StaticType's subclasses are returned as-is, so
    this function doesn't need to be called on them.
    
    This function is essentially analogous to Parcon and Pargen's promote
    functions.
    """
    if isinstance(short_type, StaticType): # Already compiled
        return short_type;
    if isinstance(short_type, list):
        if len(short_type) != 1:
            raise TypeFormatError("Lists in types must be of length 1, but "
                    + str(short_type) + " has length " + str(len(short_type)))
        component_type = short_type[0]
        return All(component_type)
    if isinstance(short_type, tuple):
        return Or(*short_type)
    if not isinstance(short_type, type):
        raise TypeFormatError("Type " + str(short_type) + " is not an "
                "instance of StaticType (or one of its subclasses) or a "
                "Python class or a list or a tuple.")
    return Type(short_type)


def matches(value, type):
    """
    Short for compile(type).matches(value).
    """
    return compile(type).matches(value)


def check_matches(value, type):
    """
    Short for compile(type).check_matches(value).
    """
    compile(type).check_matches(value)