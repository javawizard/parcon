
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

This module also requires Pango and PyGTK (for the Pango bindings). A similar
Google search should turn up information on how to install these.

If you're on Ubuntu, all of the above dependencies can be installed via
apt-get; I'll get a list of the specific packages to install up here soon.
"""

from __future__ import division
from parcon import railroad as rr
from parcon import options
from math import radians
try:
    import cairo
    import pango
    import pangocairo
except ImportError:
    print ("ERROR: parcon.railroad.raildraw requires Cairo, PyCairo, Pango,"
           "and PyGTK (for the Pango bindings). Please install any of those "
           "that you may be missing. An ImportError is about to be raised as "
           "a result of one of those not being present.")
    raise


# We have two dicts, one that maps railroad classes (Then, Or, Token, etc.) to
# functions that return (width, height, line_position) and one that maps
# railroad classes to functions that draw them.

size_functions = {}
draw_functions = {}

plain_font = pango.FontDescription("sans 16")
bold_font = pango.FontDescription("sans bold 16")
default_line_size = 2

def create_options(map):
    return options.Options(map,
        raildraw_production_font=bold_font,
        raildraw_text_font=bold_font,
        raildraw_anycase_font=plain_font,
        raildraw_description_font=plain_font,
        raildraw_arrow_width=12,
        raildraw_arrow_height=9,
        raildraw_size_of_arrow=size_of_arrow,
        raildraw_draw_arrow=draw_arrow,
        raildraw_token_padding=3,
        raildraw_token_margin=0,
        raildraw_then_before_arrow=5,
        raildraw_then_after_arrow=0
    )

def f(map, key):
    """
    A function decorator that results in the specified function being added
    to the specified map under the specified key.
    """
    def decorator(function):
        map[key] = function
        return function
    return decorator


def size_of(image, construct, options):
    return size_functions[type(construct)](image, construct, options)


def draw(image, x, y, construct, options, forward):
    return draw_functions[type(construct)](image, x, y, construct, options, forward)


def get_font_for_token(options, token):
    if token.type == rr.PRODUCTION:
        return options.raildraw_production_font
    if token.type == rr.TEXT:
        return options.raildraw_text_font
    if token.type == rr.ANYCASE:
        return options.raildraw_anycase_font
    if token.type == rr.DESCRIPTION:
        return options.raildraw_description_font
    raise ValueError


def draw_arrow(image, x, y, options, forward):
    """
    Draws an arrow at the specified position.
    """
    width, height = size_of_arrow(options)
    line_pos = height / 2
    if forward:
        image.move_to(x, y)
        image.line_to(x + width, y + line_pos)
        image.line_to(x, y + height)
        image.line_to(x + (width / 5), y + line_pos)
    else:
        image.move_to(x + width, y)
        image.line_to(x, y + line_pos)
        image.line_to(x + width, y + height)
        image.line_to(x + (width - (width / 5)), y + line_pos)
    image.close_path()
    image.fill()


def draw_line(image, x1, y1, x2, y2):
    if x1 == y1 and x2 == y2: # Empty line
        return
    image.move_to(x1, y1)
    image.line_to(x2, y2)
    image.stroke()


def size_of_arrow(options):
    """
    Returns the size of an arrow, in the same format as all of the other size
    functions, namely (width, height, line_position).
    """
    width = options.raildraw_arrow_width
    height = options.raildraw_arrow_height
    return width, height


@f(size_functions, rr.Nothing)
def size_of_Nothing(image, construct, options):
    width, height = options.raildraw_size_of_arrow(options)
    return width, height, height / 2


@f(draw_functions, rr.Nothing)
def draw_Nothing(image, x, y, construct, options, forward):
    return options.raildraw_draw_arrow(image, x, y, options, forward)


@f(size_functions, rr.Token)
def size_of_Token(image, construct, options):
    pango_context = pangocairo.CairoContext(image)
    layout = pango_context.create_layout()
    layout.set_text(construct.text)
    layout.set_font_description(get_font_for_token(options, construct))
    text_width, text_height = layout.get_pixel_size()
    padding = options.raildraw_token_padding
    margin = options.raildraw_token_margin
    height = text_height + (padding * 2) + (margin * 2)
    width = text_width + (padding * 2) + (margin * 2)
    if construct.type in (rr.TEXT, rr.ANYCASE):
        # TEXT and ANYCASE are drawn with half-circles on either end, so we
        # need to account for the size of these circles. What we add here is
        # the diameter of these circles, which accounts for a half circle at
        # either end.
        width += text_height + (padding * 2)
    return (width, height, height / 2)


@f(draw_functions, rr.Token)
def draw_Token(image, x, y, construct, options, forward):
    margin = options.raildraw_token_margin
    padding = options.raildraw_token_padding
    pango_context = pangocairo.CairoContext(image)
    layout = pango_context.create_layout()
    layout.set_text(construct.text)
    layout.set_font_description(get_font_for_token(options, construct))
    text_width, text_height = layout.get_pixel_size()
    if construct.type in (rr.TEXT, rr.ANYCASE):
        diameter = padding + text_height + padding
        radius = diameter / 2
        image.move_to(x + margin + radius + padding, y + margin + padding)
        pango_context.show_layout(layout)
        image.move_to(x + margin + radius, y + margin)
        image.line_to(x + margin + radius + padding + text_width + padding, y + margin)
        image.arc(x + margin + radius + padding + text_width + padding, y + margin + radius, radius, radians(270), radians(90))
        image.line_to(x + margin + radius, y + margin + padding + text_height + padding)
        image.arc(x + margin + radius, y + margin + radius, radius, radians(90), radians(270))
        image.close_path() # Shouldn't have any effect since we're already at
        # the start, but just in case
        image.stroke()
        width = margin + radius + padding + text_width + padding + radius + margin
    else:
        image.move_to(x + margin + padding, y + margin + padding)
        pango_context.show_layout(layout)
        image.move_to(x + margin, y + margin)
        image.line_to(x + margin + padding + text_width + padding, y + margin)
        image.line_to(x + margin + padding + text_width + padding, y + margin + padding + text_height + padding)
        image.line_to(x + margin, y + margin + padding + text_height + padding)
        image.close_path()
        image.stroke()
        width = margin + padding + text_width + padding + margin
    image.move_to(x, y + margin + padding + (text_height / 2))
    image.line_to(x + margin, y + margin + padding + (text_height / 2))
    image.stroke()
    image.move_to(x + width, y + margin + padding + (text_height / 2))
    image.line_to(x + width - margin, y + margin + padding + (text_height / 2))
    image.stroke()


@f(size_functions, rr.Then)
def size_of_Then(image, construct, options):
    constructs = construct.constructs
    sizes = [size_of(image, c, options) for c in constructs]
    before_heights = [l for w, h, l in sizes]
    after_heights = [h - l for w, h, l in sizes]
    max_before = max(before_heights)
    max_after = max(after_heights)
    arrow_line_size = (options.raildraw_then_before_arrow + 
                       options.raildraw_size_of_arrow(options)[0] + 
                       options.raildraw_then_after_arrow)
    return sum([w for w, h, l in sizes]) + (len(sizes) - 1) * arrow_line_size, max_before + max_after, max_before


@f(draw_functions, rr.Then)
def draw_Then(image, x, y, construct, options, forward):
    constructs = construct.constructs
    arrow_before = options.raildraw_then_before_arrow
    arrow_after = options.raildraw_then_after_arrow
    if not forward:
        constructs = reversed(constructs)
        arrow_before, arrow_after = arrow_after, arrow_before
    arrow_width, arrow_height = options.raildraw_size_of_arrow(options)
    width, height, line_position = size_of_Then(image, construct, options)
    current_x = x
    for index, c in enumerate(constructs):
        c_width, c_height, c_line_position = size_of(image, c, options)
        draw(image, current_x, y + (line_position - c_line_position), c, options, forward)
        current_x += c_width
        if index != (len(constructs) - 1):
            draw_line(image, current_x, y + line_position, current_x + arrow_before, y + line_position)
            current_x += arrow_before
            options.raildraw_draw_arrow(image, current_x, y + line_position - (arrow_height/2), options, forward)
            current_x += arrow_width
            draw_line(image, current_x, y + line_position, current_x + arrow_after, y + line_position)
            current_x += arrow_after


del f


def draw_to_png(diagram, options, filename):
    """
    Draws the specified railroad diagram, which should be an instance of
    parcon.railroad.Component or one of its subclasses, into the PNG file at
    the specified file name.
    
    You can either manually create instances of any of
    parcon.railroad.Component's subclasses to pass to this method, or you can
    convert a Parcon parser to a Component by calling its create_railroad
    method.
    
    options is a dictionary of options to use. For now, just use the empty
    dict; I'll get around to documenting the options that you can use here at
    some point.
    """
    width, height, line_position = size_of(diagram)
    image = cairo.ImageSurface(cairo.FORMAT_ARGB32, width + 3, height + 3)
    context = cairo.Context(image)
    draw(context, 1, 1, diagram, options, True)






































