from utilities import opposite
import constants as C

N_ID = 0

class Edge(object):
    def __init__(self, direction, fro, to):
        self.direction = direction
        self.fro = fro
        self.to = to

    def __repr__(self):
        return '%s: %s %s' % (self.direction, self.fro, self.to)

class Node(object):
    NUM_UNCHUNKS = 1

    def __init__(self, fake=False):
        self.adj = {}  # Node, Edge dictionary
        self.edges = {'up': set(),  # Set of edges
                      'left': set(),
                      'right': set(),
                      'down': set()}
        global N_ID
        self.nid = N_ID
        N_ID += 1
        self.chunk = None  # What chunk (room) is assigned to this node
        # === For backtracking ===
        self.bad_chunks = set()  # set of rooms
        self.parent = None  # From which node did we access this node
        self.children = set()  # What nodes follow this node in the graph
        self.num_times_unchunked = 0

    def get_edge(self, node):
        return self.adj[node]

    def get_adj_nodes(self):
        return self.adj.keys()

    def add_adj(self, direction, node):
        edge_to = Edge(direction, self, node)
        self.adj[node] = edge_to
        self.edges[direction].add(edge_to)

    def add_adj_both(self, direction, node):
        self.add_adj(direction, node)
        node.add_adj(opposite(direction), self)

    def remove_adj(self, node):
        edge_between = self.adj[node]
        del self.adj[node]
        self.edges[edge_between.direction].remove(edge_between)

    def remove_adj_both(self, node):
        self.remove_adj(node)
        node.remove_adj(self)

    def get_unchunked_directions(self):
        unchunked_directions = set()
        for node, edge in self.adj.items():
            if not node.chunk:
                unchunked_directions.add(edge.direction)
        return unchunked_directions

    def get_direction_to_node(self, node):
        return self.adj[node].direction

    def check_rooms(self, legal_chunks):
        num_exits = len(self.get_adj_nodes())
        legal_chunks = [room for room in legal_chunks if room.get_num_exits() == num_exits]
        if C.DEBUG and not legal_chunks:
            print('*** Error! No room with %d exits' % num_exits)
            return legal_chunks
        legal_chunks = [room for room in legal_chunks if all(len(room.exits[direc]) == len(self.edges[direc]) for direc in ('up', 'down', 'left', 'right'))]
        if C.DEBUG and not legal_chunks:
            print('*** Error! No room with exits in right directions!')
            return legal_chunks
        legal_chunks = [room for room in legal_chunks if room.name not in self.bad_chunks]
        if C.DEBUG and not legal_chunks:
            print("*** Warning! Only room that's legal has been tried before!")
            return legal_chunks
        return legal_chunks

    def set_chunk(self, chunk):
        if C.DEBUG:
            print('Chunking: %s' % self)
        self.chunk = chunk

    def unchunk(self, chunk_grid, child=False):
        if C.DEBUG: 
            if child:
                print('Child Unchunking: %s' % self)
            else:
                print('Unchunking: %s' % self)
        if self.chunk:
            chunk_grid.unset(self.chunk)
            if self.chunk.is_subchunk:
                for chunk in self.chunk.subchunks:
                    chunk_grid.unset(chunk)
            else:
                self.bad_chunks.add(self.chunk.name)  # make sure we don't choose that one again
            # Also unchunk adjacent peoples exits to me
            for adj_node in self.adj:
                if C.DEBUG:
                    print('Adj: %s' % adj_node)
                if adj_node.chunk:
                    for direction, exit_set in adj_node.chunk.exits.items():
                        for exit in exit_set:
                            if C.DEBUG: print('has Exit: %s' % exit)
                            if exit.edge and exit.edge.to == self:
                                exit.edge = None
        for child_chunk in self.children:
            child_chunk.unchunk(chunk_grid, child=True)
        self.chunk = None
        if child:
            self.num_times_unchunked = 0
            self.bad_chunks = set()
            return self
        elif self.parent and self.num_times_unchunked >= self.NUM_UNCHUNKS:
            print('Backtracking!')
            self.num_times_unchunked = 0  # reset
            self.bad_chunks = set()
            return self.parent.unchunk(chunk_grid)
        else:
            self.num_times_unchunked += 1
            return self

    # def child_unchunk(self, chunk_grid):
    #     if C.DEBUG: print('Child Unchunking: %s' % self)
    #     if self.chunk:
    #         chunk_grid.unset(self.chunk)
    #         self.num_times_unchunked += 1
    #         self.bad_chunks = set()
    #     self.chunk = None
    #     for child in self.children:
    #         child.child_unchunk(chunk_grid)

    def __repr__(self):
        return '%s' % self.nid
