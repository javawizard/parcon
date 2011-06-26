This file contains a bunch of examples of things you can do with Parcon. More
examples are present in the [Parcon module documentation](parcon.html).

### Expression evaluator

    from parcon import rational, Forward, InfixExpr
    from decimal import Decimal
    import operator
    expr = Forward()
    number = rational[Decimal]
    term = number | "(" + expr + ")"
    term = InfixExpr(term, [("*", operator.mul), ("/", operator.truediv)])
    term = InfixExpr(term, [("+", operator.add), ("-", operator.sub)])
    expr << term
	
This implements a simple expression evaluator, and shows how Parcon allows the
evaluation logic to be specified as part of the parser. It uses Python's
decimal module for arbitrary-precision arithmetic. This expression parser can
then be used thus:

	print expr.parse_string("1+2") # prints 3
	print expr.parse_string("1+2+3") # prints 6
	print expr.parse_string("1+2+3+4") # prints 10
	print expr.parse_string("3*4") # prints 12
	print expr.parse_string("5+3*4") # prints 17
	print expr.parse_string("(5+3)*4") # prints 32
	print expr.parse_string("10/4") # prints 2.5
