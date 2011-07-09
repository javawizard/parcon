
"""
This module provides support for drawing railroad diagrams created by
parcon.railroad (which usually creates them from Parcon parsers) into image
files or other locations.

It's possible to use this module and parcon.railroad as standalone modules to
create syntax diagrams for things unrelated to Parcon. I'll write up
documentation on how to use this module separate from Parcon at some point.

A simple example of how to use this module is present in the module
documentation of parcon.railroad.

This module requires Cairo and PyCairo in order to function. These must be
installed separately from Parcon; both Cairo and PyCairo are available for
Windows, Linux, and Mac. A Google search should turn up information on where to
download and install both. (If it doesn't, go to pypi.python.org/pypi/parcon
and send an email to the email address you find there.)
"""

try:
    import cairo
except ImportError:
    try:
        f = __file__
    except AttributeError:
        f = "(unknown)"
    print ("ERROR: parcon.railroad.raildraw requires Cairo and PyCairo, but "
           "these libraries don't seem to be installed. An ImportError is "
           "about to be raised as a result. See the module documentation for "
           "raildraw (you can examine the source if you can't actually import "
           "the module; it's at %s) for information on how to install Cairo "
           "and PyCairo." % f)
    raise


def draw_to_png(diagram, filename):
    """
    Draws the specified railroad diagram, which should be an instance of
    parcon.railroad.Component or one of its subclasses, into the PNG file at
    the specified file name.
    """
    raise NotImplementedError
