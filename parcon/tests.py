from __future__ import print_function

from parcon.testframework import *
import parcon
from parcon import pargen
from parcon import static

tests = []
classes_tested = set()

test = TestSuite()


@test(parcon.Return)
def case():
    x = parcon.Return("test")
    assert x.parse_string("") == "test"
    x = parcon.Return({1:2, "3":"4"})
    assert x.parse_string("") == {1:2, "3":"4"}
    x = parcon.Return(None)
    assert x.parse_string("") is None
    check_raises(Exception, x.parse_string, "test")


@test(parcon.Literal)
def case(): #@DuplicatedSignature
    x = parcon.Literal("hello")
    assert x.parse_string("hello") is None
    check_raises(Exception, x.parse_string, "bogus")


@test(parcon.SignificantLiteral)
def case(): #@DuplicatedSignature
    x = parcon.SignificantLiteral("hello")
    assert x.parse_string("hello") == "hello"
    check_raises(Exception, x.parse_string, "bogus")


@test(parcon.Translate)
def case(): #@DuplicatedSignature
    x = parcon.Translate(parcon.SignificantLiteral("5"), int)
    assert x.parse_string("5") == 5
    x = parcon.SignificantLiteral("5")[int]
    assert x.parse_string("5") == 5


@test(parcon.Exact)
def case(): #@DuplicatedSignature
    ws = parcon.Word(parcon.whitespace)
    x = parcon.Exact(parcon.alpha_word + ws + parcon.alpha_word)
    assert x.parse_string('foo \t\r\n bar') == ('foo', ' \t\r\n ', 'bar')
    x = parcon.Exact(ws + parcon.alpha_word)
    assert (
        x.parse_string(' \t\r\n bar', whitespace=parcon.Word(' ')) ==
        ('\t\r\n ', 'bar'))


@test(parcon.NonConsumingExact)
def case(): #@DuplicatedSignature
    ws = parcon.Word(parcon.whitespace)
    x = parcon.NonConsumingExact(ws + parcon.alpha_word)
    assert x.parse_string(' \t\r\n bar') == (' \t\r\n ', 'bar')


@test(parcon.Invalid)
def case(): #@DuplicatedSignature
    x = (parcon.Word(parcon.whitespace) + parcon.alpha_word)
    assert (
        x.parse_string(' \t bar', whitespace=parcon.Invalid()) ==
        (' \t ', 'bar'))

def run_tests():
    targets = set()
    targets |= set(subclasses_in_module(parcon.Parser, ("parcon",)))
    targets |= set(subclasses_in_module(pargen.Formatter, ("parcon.pargen",)))
    targets |= set(subclasses_in_module(static.StaticType, ("parcon.static",)))
    test.warn_missing_targets(targets)
    passed, failed = test.run_tests()
    print("-" * 75)
    print("%s tests passed" % passed)
    print("%s tests failed" % failed)
    print("-" * 75)
    print()
    if failed == 0:
        print("TESTING SUCCESSFUL")
    else:
        print("TESTING FAILED")


if __name__ == "__main__":
    run_tests()






































