"""
This module will have parsers for parsing binary protocols in it. Parcon can
already parse binary data; this module will provide some Parcon parsers
specifically oriented toward that purpose. Its most important feature will be
a set of parsers to parse integers and other data in network byte order, hence
this module's name (NBO = Network Byte Order). It will have parsers for parsing
other binary things too, though, such as length-specified strings or packets in
protocols that have a defined length.

This module will also contain formatters for all of the binary types that it
can parse. In fact, I'm considering having all of the parsers be subclasses of
parcon.pargon.ParserFormatter. The only difficulty is that it would make
assembling formatters difficult since ParserFormatters act like parsers when
used as arguments to operators. So this needs some thought.

(if you can't tell, the nbo module is still in planning :-) )
"""