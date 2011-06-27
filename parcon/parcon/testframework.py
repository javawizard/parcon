
from traceback import print_exc

class TestException(Exception):
    pass


def check_raises(*args, **kwargs):
    """
    check_raises(exception_type, function, ...)
    
    Calls function, passing in the rest of the positional arguments and keyword
    arguments. If the function does not raise an exception, check_raises raises
    an exception indicating that the specified function failed to do so. If the
    function raises an exception not of the specified exception_type (which can
    be a tuple of multiple types if desired), another exception is raised
    indicating the problem. Otherwise, check_raises returns None.
    """
    exception_type = args[0]
    function = args[1]
    try:
        function(*args, **kwargs)
        raise TestException(str(function) + " failed to raise " + str(exception_type))
    except Exception as e:
        if not isinstance(e, exception_type):
            raise TestException(str(function) + " was supposed to raise an " + 
                                "exception of type " + str(exception_type) +
                                " but raised " + str(e) + " instead")


def subclasses_in_module(c, modules=None, original=True):
    result = []
    if original:
        if modules is None or c.__module__ in modules:
            result.append(c)
    subclasses = c.__subclasses__()
    for subclass in subclasses:
        result += subclasses_in_module(subclass, modules)


class TestSuite(object):
    def __init__(self):
        self.tests = []
        self.targets = set()
    
    def __call__(self, target):
        def decorator(function):
            self.tests.append(function)
            self.targets.add(target)
            return function
        return decorator
    
    def warn_missing_targets(self, targets):
        if len(targets - self.targets) > 0:
            print "WARNING: missing tests for " + str(targets - self.targets)
    
    def run_tests(self):
        for test in self.tests:
            try:
                test()
                print "TEST PASSED:  " + str(test)
            except:
                print "TEST FAILED:  " + str(test)
                print "Exception for the above failure:"
                print_exc()




