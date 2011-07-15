
"""
A module that provides graphing support to Parcon and its associated libraries.
You most likely won't use this module directly; instead, you just call the
graph method on a Parcon parser (or other sort of object) that extends
Graphable as well (and all parsers included with Parcon do, or they will at
some point in the future, as will Pargen formatters and Static types).
"""

import subprocess
import json

def escape_string(string):
    return json.dumps(str(string))[1:-1]

class Graphable(object):
    """
    A class that classes knowing how to graph themselves should subclass. The
    idea is that all parsers in parcon and, in the future, formatters from
    pargen and types from static, will extend this class.
    
    This class is intended to be used as a mixin; calling Graphable.__init__ is
    not necessary. The only requirement is that a subclass override do_graph.
    """
    def graph(self):
        """
        Graphs this Graphable object by calling its do_graph and the do_graph
        functions defined by all of the things that this Graphable depends on.
        The result will be a Graph object.
        
        Each node in the resulting Graph will be named after its respective
        object's identity, a.k.a. the value returned by the built-in id
        function.
        
        The quickest way to use this would be to do something like this:
        
        something.graph().draw("example.png")
        
        For the draw method to work, however, you must have the dot program
        (which is part of Graphviz) installed.
        """
        graph = Graph()
        visited = set()
        new_list = [self]
        while new_list:
            old_list = new_list
            new_list = []
            for graphable in old_list:
                if not isinstance(graphable, Graphable):
                    raise Exception("A non-graphable object was found  in the "
                                    "graph. The object was of type " +
                                    str(type(graphable)) + ", and it appears "
                                    " to be " + str(graphable) + ".")
                if id(graphable) in visited:
                    continue
                visited.add(id(graphable))
                new_list += graphable.do_graph(graph)
        return graph
    
    def do_graph(self, graph):
        """
        Adds nodes (typically one, but more are allowed) representing this
        Graphable to the specified graph, which should be an instance of Graph,
        and adds all relevant edges linking to other nodes (even if they
        haven't actually been created in the graph yet).
        
        The return value should then be a list of all other Graphable instances
        to which this one linked and which thus need to have their do_graph
        methods called to add them into the graph.
        
        Each node's id should be the result of id(object), where object is the
        corresponding Graphable. Thus this graphable should add itself to the
        graph as a node named id(self), and it should link to any other
        Graphables by using id(some_graphable) as the edge target.
        
        Unless you're writing a subclass of Graphable, you probably won't
        actually need to use this method; instead, you'll most likely use the
        graph method. Subclasses must override this method; it will raise a
        NotImplementedError if they don't.
        """
        raise NotImplementedError(str(type(self)))
    

class Graph(object):
    """
    A graph. Instances of this class represent a graph of nodes and edges, with
    nodes and edges both being able to have attributes.
    
    This class is, by default, set up to create directed graphs. You can
    create undirected ones by setting a graph's separator field to "--" and
    that same graph's graph_type field to "graph".
    
    I wrote my own class instead of using pygraphviz because the underlying
    library that pygraphviz uses doesn't preserve node ordering when writing
    output, which results in ordering="out" not working correctly; Parcon
    depends on ordering="out" to lay out parsers correctly, hence this class
    provided as a replacement.
    
    This class is also pure-Python, whereas pygraphviz is not.
    """
    def __init__(self):
        self.nodes = {} # map of node names to maps of node attributes
        self.edges = [] # list of edges as (from_name, to_name, attribute_map)
        self.top_node = None
        self.separator = "->"
        self.graph_type = "digraph"
    
    def add_node(self, name, **attributes):
        """
        Adds a node to this graph. Name is the name of the node. Attributes are
        the attributes that should be added, from the set of allowed Graphviz
        node attributes.
        """
        node_map = self.nodes.get(name)
        if node_map is None:
            node_map = {}
            self.nodes[name] = node_map
        node_map.update(attributes)
        if self.top_node is None:
            self.top_node = name
    
    def add_edge(self, source, target, **attributes):
        """
        Adds an edge to this graph. Unlike Pygraphviz, adding an edge does not
        create any nodes it depends on; however, an edge can be added before
        its corresponding nodes have been added, so long as they are then added
        before a function such as to_dot_file() is called.
        
        source is the name of the source node. target is the name of the target
        node. attributes are attributes for this edge.
        """
        self.edges.append((source, target, attributes))
    
    def __str__(self):
        return self.to_dot_file()
    
    def to_dot_file(self):
        """
        Formats this graph into a .dot-style file, and returns the would-be
        file contents.
        """
        format_attributes = lambda attributes: ", ".join(k + '="' + escape_string(v) + '"' for k, v in attributes.items())
        result = []
        result.append(self.graph_type + " g {")
        for node, attributes in self.nodes.items():
            result.append("    " + str(node) + " [" + format_attributes(attributes) + "];")
        for source, target, attributes in self.edges:
            result.append("    " + str(source) + " " + self.separator + " " + str(target) + " [" + format_attributes(attributes) + "];")
        if self.top_node is not None:
            result.append('    {rank="min"; ' + str(self.top_node) + "}")
        result.append("}")
        result.append("")
        return "\n".join(result)
    
    def draw(self, file, format="png", program="dot"):
        """
        Draws this graph into a file.
        
        file is the name of the file to write to (not a file object). format is
        the format to use; this defaults to "png". program is the program to
        use; this defaults to "dot", and as a result, the dot program must be
        installed to call this with its default arguments.
        """
        p = subprocess.Popen([program, "-T", format, "-o", file], stdin=subprocess.PIPE)
        with p.stdin as stdin:
            stdin.write(self.to_dot_file())
        p.wait()




































