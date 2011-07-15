
"""
This module provides classes that make it easier to parse data from network
sockets or files.
"""

class LazyString(object):
    def __init__(self, more_function):
        self.more = more_function
        self.buffer = ""
    
    def __len__(self):
        return 2**30
    
    def __getitem__(self, item):
        if isinstance(item, slice):
            limit = item.stop
        else:
            limit = item + 1
        self.get_more(limit)
        return self.buffer[item]
    
    def get_more(self, limit):
        while len(self.buffer) < limit:
            self.buffer += self.more(limit - len(self.buffer)) 
