
import parcon as p
from collections import namedtuple

'''
A BNF-to-Parcon converter. This module provides a method, convert, which
converts a BNF grammar passed as a string into a dictionary of Parcon parsers,
one for each nonterminal in the BNF grammar, whose value is a Parcon parser
that will parse text conforming to the specified nonterminal. For example, a
very simple numeric expression evaluator using only the bnf module (and not any
other Parcon modules) could look like this:

bnf = """
<expression> ::= <term> | <term> "+" <expression>
<term>       ::= <factor> | <factor> "*" <term>
<factor>     ::= <constant> | "(" <expression> ")"
<constant>   ::= <digit> | <digit> <constant>
<digit>      ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
"""
parsers = convert(bnf)
parser = parsers["expression"]
...continue this example...

Note that grammars must not be left-recursive; attempting to use a
left-recursive grammar will cause an infinite loop when attempting to parse text
that (ostensibly) conforms to the BNF grammar specified. If anyone wants to fix
this, feel free; see github.com/javawizard/parcon.
'''

Production = namedtuple("Production", ["name", "alternatives"])
Alternative = namedtuple("Alternative", ["values"])
Reference = namedtuple("Reference", ["name"])
String = namedtuple("String", ["value"])

whitespace = p.Regex(r"[ \t]+")

equals = p.Literal("::=")
ref = (p.Literal("<") + (+p.CharNotIn(">"))["".join](desc="Any char except >") + ">")(name="name")
production_start = ref + equals
string = p.Exact('"' + p.CharNotIn('"')[...](desc='Any char except "') + '"')["".join][String]
component = (ref & p.Not(p.Present(ref + equals)))[Reference] | string
alternative = (+component)[Alternative](name="alternative")
production = (production_start + p.InfixExpr(alternative[lambda a: [a]], [("|", lambda a, b: a+b)]))[lambda (n, a): Production(n, a)](name="production")
productions = (+production)(name="bnf")

def bnf_to_parcon(productions):
    result = {}
    for name, alternatives in productions:
        result[name] = p.Forward()
    for name, alternatives in productions:
        alternative_parsers = []
        for alternative in alternatives:
            component_parsers = []
            for component in alternative.values:
                if isinstance(component, String):
                    component_parsers.append(p.SignificantLiteral(component.value))
                elif isinstance(component, Reference):
                    component_parsers.append(result[component.name])
                else:
                    raise TypeError(type(component))
            alternative_parsers.append(reduce(p.Then, component_parsers))
        result[name] << p.First(alternative_parsers)[name](name=name)
    # Unwrap all of the forwards to make things somewhat more clear
    for name in result:
        result[name] = result[name].parser
    return result































