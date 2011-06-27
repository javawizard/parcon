
from parcon.testframework import *
import parcon
from parcon import pargen
from parcon import static

tests = []
classes_tested = set()

def test(test_class):
    def wrapper(function):
        tests.append(function)
        classes_tested |= set([test_class])
        return function
    return wrapper

def run_tests():
    pass







































