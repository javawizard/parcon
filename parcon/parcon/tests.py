
from parcon.testframework import *
import parcon
from parcon import pargen
from parcon import static

tests = []
classes_tested = set()

test = TestSuite()

def run_tests():
    targets = set()
    targets |= set(subclasses_in_module(parcon.Parser, ("parcon",)))
    targets |= set(subclasses_in_module(pargen.Formatter, ("parcon.pargen",)))
    targets |= set(subclasses_in_module(static.StaticType, ("parcon.static",)))
    test.warn_missing_targets(targets)
    passed, failed = test.run_tests()
    print "-------------------------------------------------------"
    print "%s TESTS PASSED"
    print "%s TESTS FAILED"







































