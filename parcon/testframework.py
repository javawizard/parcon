
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
        function(*args[2:], **kwargs)
        raise TestException(str(function) + " failed to raise " + str(exception_type))
    except Exception as e:
        if not isinstance(e, exception_type):
            print_exc()
            raise TestException(str(function) + " was supposed to raise an " + 
                                "exception of type " + str(exception_type) +
                                " but raised " + str(type(e)) + " instead")


def subclasses_in_module(c, modules=None, original=True):
    result = []
    if original:
        if modules is None or c.__module__ in modules:
            result.append(c)
    subclasses = c.__subclasses__()
    for subclass in subclasses:
        result += subclasses_in_module(subclass, modules)
    return result


class TestSuite(object):
    def __init__(self):
        self.tests = []
        self.targets = set()
    
    def __call__(self, target):
        def decorator(function):
            self.tests.append(function)
            self.targets.add(target)
            function.testing_target = target
            return function
        return decorator
    
    def warn_missing_targets(self, targets):
        if len(targets - self.targets) > 0:
            print "WARNING: missing tests for " + str(list(targets - self.targets))
            print "-" * 75
    
    def run_tests(self):
        passed = 0
        failed = 0
        for test in self.tests:
            target = getattr(test, "testing_target", None)
            target_desc = str(target) if target is not None else "(no target)"
            if target is not None and getattr(target, "__module__", None) is not None:
                target_desc += " in module " + target.__module__
            try:
                test()
                print "TEST PASSED: " + test.__name__ + " testing " + target_desc
                passed += 1
            except:
                print "TEST FAILED: " + test.__name__ + " testing " + target_desc
                print "Exception for the above failure:"
                print_exc()
                failed += 1
        return passed, failed




