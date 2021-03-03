import constants as C

class Grid(object):
    def __init__(self, size):
        self.width, self.height = size
        self.width = int(self.width)
        self.height = int(self.height)
        self.grid = [None for _ in range(self.width*self.height)]

    def set(self, x, y, tile):
        self.grid[y*self.width + x] = tile

    def get(self, x, y):
        return self.grid[y*self.width + x]

    def subsume(self, offset_x, offset_y, grid):
        for x in range(grid.width):
            for y in range(grid.height):
                tile = grid.get(x, y)
                self.set(offset_x + x, offset_y + y, tile)

class Exit(object):
    def __init__(self, direction, pos):
        self.direction = direction
        self.pos = pos
        self.edge = None

    def __repr__(self):
        return 'Exit Direction: %s, Pos: %s, Edge: %s' % (self.direction, self.pos, self.edge)

class Room(Grid):
    def __init__(self, image, name):
        self.image = image
        self.name = name
        Grid.__init__(self, image.size)
        self.c_width = self.width//C.CHUNK_SIZE
        self.c_height = self.height//C.CHUNK_SIZE
        self.exits = {'up': set(),
                      'left': set(),
                      'right': set(),
                      'down': set()}
        self.is_subchunk = False
        self.subchunks = []  # Only non-empty if self.is_subchunk == True

        for x in range(self.width):
            for y in range(self.height):
                color = image.getpixel((x, y))
                # Wall
                if color[:3] == (0, 0, 0):
                    self.set(x, y, 'Wall')
                elif color[:3] == (200, 0, 0):
                    self.set(x, y, 'Exit')
                    if x == 0:
                        self.exits['left'].add(Exit('left', y//C.CHUNK_SIZE))
                    elif x == self.width - 1:
                        self.exits['right'].add(Exit('right', y//C.CHUNK_SIZE))
                    elif y == 0:
                        self.exits['up'].add(Exit('up', x//C.CHUNK_SIZE))
                    elif y == self.height - 1:
                        self.exits['down'].add(Exit('down', x//C.CHUNK_SIZE))
                elif color[:3] == (200, 200, 200):
                    self.set(x, y, 'Void')
                else:
                    self.set(x, y, 'Empty')

    def confirm_match(self, offset_x, offset_y, true_pos_x, true_pos_y, direction):
        my_exits = self.exits[direction]
        if direction == 'left':
            if offset_x == true_pos_x:
                for exit in my_exits:
                    if exit.pos == true_pos_y - offset_y:
                        return exit
        elif direction == 'right':
            if offset_x + self.c_width == true_pos_x:
                for exit in my_exits:
                    if exit.pos == true_pos_y - offset_y:
                        return exit
        elif direction == 'up':
            if offset_y == true_pos_y:
                for exit in my_exits:
                    if exit.pos == true_pos_x - offset_x:
                        return exit
        elif direction == 'down':
            if offset_y + self.c_height == true_pos_y:
                for exit in my_exits:
                    if exit.pos == true_pos_x - offset_x:
                        return exit
        return False

    def get_exit(self, direction, pos):
        if pos < 0:
            if direction in ('left', 'right'):
                return [e for e in self.exits[direction] if e.pos == (self.c_height + pos)]
            else:
                return [e for e in self.exits[direction] if e.pos == (self.c_width + pos)]
        return [e for e in self.exits[direction] if e.pos == pos][0]

    def get_unchunked_exits(self, direction):
        return [exit for exit in self.exits[direction] if not exit.edge]

    def get_num_exits(self):
        return len(self.exits['up']) + len(self.exits['left']) + len(self.exits['right']) + len(self.exits['down'])

    def get_other_exit(self, exit):
        # Assumes that room has exactly two exits
        for direc in C.DIRECTIONS:
            for e in self.exits[direc]:
                if e is not exit:
                    return e, direc 
        print('Error! Could not find other exit!')
        return None

    def reset_all_exits(self):
        for direction, exit_set in self.exits.items():
            for exit in exit_set:
                exit.edge = None

    def mark_all_exits(self):
        assert self.is_subchunk
        for direction, exit_set in self.exits.items():
            for exit in exit_set:
                exit.edge = True

    def __repr__(self):
        return self.name

    def copy(self):
        return Room(self.image, self.name)
