
class Options(object):
    def __init__(self, m, d={}, **defaults):
        self.values = {}
        self.values.update(defaults)
        self.values.update(d)
        self.values.update(m)
    
    def __getattr__(self, name):
        return self.values[name]
    
    __getitem__ = __getattr__
    
    def __iter__(self):
        for k, v in self.values:
            yield k, v