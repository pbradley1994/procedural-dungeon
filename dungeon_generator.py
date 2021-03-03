import random, sys
import glob, os
from PIL import Image

# === my imports ===
from utilities import opposite, calculate_distance
import constants as C

# Seed setting needs to be done before import for some reason...
# Or else random seed does not take effect
if C.SEED is not None:
    print('Seed: %d' % C.SEED)
    random.seed(C.SEED)

from graph_objects import Node
from chunk_objects import Room, Grid

class Dungeon():
    def __init__(self, prefab_rooms):
        self.nodes = set()  # all nodes in the dungeon
        self.entrance_node = None

        self.prefab_rooms = prefab_rooms

        self.chunk_grid = ChunkGrid(self, prefab_rooms)
        self.main_grid = None
        self.img_output_count = 0
        self.num_subnodes = 0

        self.start()

    def add_node(self):
        new_node = Node()
        self.nodes.add(new_node)
        return new_node

    def start(self):
        # Step 2
        node_dict = self.build_node_graph('NodeMap.png')
        if C.DEBUG: 
            self.write_node_graph(node_dict)
        # Step 3
        output = self.build_chunk_grid()
        if not output:
            print('ERROR: Building chunk grid failed!')
            return
        # Step 4
        self.build_main_grid()

    # === BUILDING NODE GRAPH ================================================
    def build_node_graph(self, fp):
        def find_first_node(im):
            width, height = im.size
            # Find first black node
            for x in range(width):
                for y in range(height):
                    color = im.getpixel((x, y))
                    if color[:3] == (0, 0, 0):
                        self.entrance_node = self.add_node()
                        current_pos = x, y
                        return current_pos

        im = Image.open(fp)
        current_pos = find_first_node(im)
        
        frontier = [current_pos]
        node_dict = {current_pos: self.entrance_node}
        explored = set([current_pos])
        while frontier:
            c_pos = frontier.pop()
            for direc, pos in self.get_adj_nodes(im, c_pos):
                if pos not in explored:
                    explored.add(pos)
                    new_node = self.add_node()
                    node_dict[c_pos].add_adj(direc, new_node)
                    node_dict[pos] = new_node
                    frontier.append(pos)
                else:
                    node_dict[c_pos].add_adj(direc, node_dict[pos])
        return node_dict

    def get_adj_nodes(self, im, pos):
        adj_nodes = []
        true_pos = pos
        for direc in ('up', 'left', 'right', 'down'):
            pos = true_pos
            dx, dy = 0, 0
            if direc == 'up':
                dy = -2
            elif direc == 'left':
                dx = -2
            elif direc == 'right':
                dx = 2
            elif direc == 'down':
                dy = 2
            pos = pos[0] + dx, pos[1] + dy
            if pos[0] < 0 or pos[1] < 0 or pos[0] >= im.size[0] or pos[1] >= im.size[1]:
                continue
            color = im.getpixel(pos)
            if color[:3] == (0, 0, 0):
                adj_nodes.append((direc, pos))
        return adj_nodes

    # === BUILDING CHUNK GRID ================================================
    def build_chunk_grid(self):
        frontier = [self.entrance_node]
        # Whether a node is chunked is essentially our explored set
        while(frontier):
            print('== Round: %s -- %s %s' % (self.img_output_count, frontier, frontier[-1].adj.keys()))
            if C.IM_DEBUG:
                self.build_main_grid()
                self.draw()
            current_node = frontier.pop()
            if current_node.chunk:
                continue
            # Keep trying until we've chosen a chunk for the node and placed it
            success = self.chunk_grid.choose_room(current_node, self.prefab_rooms)
            if success:
                for node in current_node.get_adj_nodes():
                    if not node.chunk:
                        frontier.append(node)
                        node.parent = current_node
                        current_node.children.add(node)
            # Need to backtrack
            elif current_node.parent:
                f_node = current_node.parent.unchunk(self.chunk_grid)
                frontier.append(f_node)
            else:  # Total failure
                print('=== Total Failure! ===')
                return False
        return True

    # === BUILDING FINAL ROOMS ===============================================
    def build_main_grid(self):
        # Find the topleft of the chunk_grid
        min_x, min_y, max_x, max_y = 100, 100, -100, -100
        for chunk_pos, room in self.chunk_grid.chunks.items():
            x, y = chunk_pos
            if x < min_x:
                min_x = x
            if x + room.c_width > max_x:
                max_x = x + room.c_width
            if y < min_y:
                min_y = y
            if y + room.c_height > max_y:
                max_y = y + room.c_height
        width = max_x - min_x
        height = max_y - min_y
        self.main_grid = Grid((width * C.CHUNK_SIZE, height * C.CHUNK_SIZE))
        for chunk_pos, room in self.chunk_grid.chunks.items():
            offset_x = (chunk_pos[0] - min_x) * C.CHUNK_SIZE
            offset_y = (chunk_pos[1] - min_y) * C.CHUNK_SIZE
            self.main_grid.subsume(offset_x, offset_y, room)

    def write_node_graph(self, node_dict):
        min_x = min([k[0] for k in node_dict])
        min_y = min([k[1] for k in node_dict])
        new_grid = Grid((100, 100))
        for pos, node in node_dict.items():
            new_grid.set(pos[0] - min_x, pos[1] - min_y, node.nid)
        with open('node_grid_output.txt', 'w') as fp:
            for y in range(new_grid.height):
                for x in range(new_grid.width):
                    tile = new_grid.get(x, y)
                    if tile:
                        fp.write('%02d' % tile)
                    else:
                        fp.write('  ')
                fp.write('\n')

    def write(self):
        if not self.main_grid:
            print('Error! Main Grid has not been initialized yet!')
            return False
        with open('grid_output.txt', 'w') as fp:
            for y in range(self.main_grid.height):
                for x in range(self.main_grid.width):
                    tile = self.main_grid.get(x, y)
                    if tile == 'Wall':
                        fp.write('*')
                    else:
                        fp.write(' ')
                fp.write('\n')

    def draw(self, final=False):
        if not self.main_grid:
            print('Error! Main Grid has not been initialized yet!')
            return False
        if self.main_grid.width <= 0 or self.main_grid.height <= 0:
            return False
        im = Image.new('RGB', (self.main_grid.width, self.main_grid.height))
        for x in range(self.main_grid.width):
            for y in range(self.main_grid.height):
                tile = self.main_grid.get(x, y)
                if tile == 'Wall':
                    im.putpixel((x, y), (0, 0, 0))
                elif tile == 'Exit':
                    im.putpixel((x, y), (200, 0, 0))
                elif tile == 'Empty':
                    im.putpixel((x, y), (248, 248, 248))
                else:
                    im.putpixel((x, y), (200, 200, 200))
        # Resize to show user output
        if final:
            print('Saving final!')
            im = im.resize((im.width * 5, im.height * 5), Image.NEAREST)
            im.save('grid_output_final.png')
        elif self.img_output_count < C.LIMIT:
            im = im.resize((im.width * 5, im.height * 5), Image.NEAREST)
            im.save('Images/grid_output%04d.png' % self.img_output_count)
            self.img_output_count += 1
        else:
            sys.exit()
        im.close()

class ChunkGrid():
    def __init__(self, dungeon, prefab_rooms):
        self.chunks = {}
        self.chunk_positions = {}
        self.dungeon = dungeon
        self.prefab_rooms = prefab_rooms

    def find_new_position(self, direction, offset, adj_chunk, adj_exit, chosen_chunk, chosen_exit):
        if direction == 'right':
            x_pos = offset[0] + adj_chunk.c_width
            y_pos = offset[1] + adj_exit.pos - chosen_exit.pos
        elif direction == 'left':
            x_pos = offset[0] - chosen_chunk.c_width
            y_pos = offset[1] + adj_exit.pos - chosen_exit.pos
        elif direction == 'up':
            x_pos = offset[0] + adj_exit.pos - chosen_exit.pos
            y_pos = offset[1] - chosen_chunk.c_height
        elif direction == 'down':
            x_pos = offset[0] + adj_exit.pos - chosen_exit.pos
            y_pos = offset[1] + adj_chunk.c_height
        return x_pos, y_pos

    def choose_room(self, node, legal_chunks):
        true_legal_chunks = legal_chunks
        legal_chunks = node.check_rooms(legal_chunks)  # Returns all chunks that fit node's parameters (num exits, direction of exits, anything else we want)
        # print('Legal Chunks at start:')
        # print(legal_chunks)
        if not legal_chunks:
            print('Warning! No legal chunks!')
            return False
        chunked_adjs = [n for n in node.get_adj_nodes() if n.chunk]
        if chunked_adjs:
            for adj in chunked_adjs:
                unchunked_directions = adj.get_unchunked_directions()
                legal_chunks = [room for room in legal_chunks if any(room.exits[opposite(e)] for e in unchunked_directions)]
                if not legal_chunks:
                    return False
            if len(chunked_adjs) == 1:
                return self.find_one_exit(node, chunked_adjs[0], legal_chunks)
            elif len(chunked_adjs) == 2:
                return self.tie_loop(node, chunked_adjs, true_legal_chunks)  # Uses true legal chunks since need access to every chunk type
            else:
                return self.find_three_or_more(node, chunked_adjs, legal_chunks)
        else: # Entrance chunk
            one_direction = list(node.get_unchunked_directions())[0]
            legal_chunks = [chunk for chunk in legal_chunks if chunk.exits[one_direction]]
            chunk = random.choice(legal_chunks)
            chosen_chunk = chunk.copy()
            self.set(0, 0, chosen_chunk)
            node.set_chunk(chosen_chunk)
            return True
        return False

    def find_one_exit(self, node, adj_node, legal_chunks):
        if C.DEBUG:
            print('Finding one exit!')
        direction = adj_node.get_direction_to_node(node)
        adj_chunk = adj_node.chunk
        if C.DEBUG:
            print('Adj Node: %s, Direction: %s' % (adj_node, direction))
            print('Adj Chunk Exits: %s' % [s for s in adj_chunk.exits.values() if s])
        adj_exit = random.choice(tuple(adj_chunk.get_unchunked_exits(direction)))

        random.shuffle(legal_chunks)
        for chunk in legal_chunks:
            exit = random.choice(tuple(chunk.exits[opposite(direction)]))
            x_pos, y_pos = self.find_new_position(direction, self.chunk_positions[adj_chunk], adj_chunk, adj_exit, chunk, exit)
            if self.collides(x_pos, y_pos, chunk):
                continue
            chosen_chunk = chunk.copy()
            self.set(x_pos, y_pos, chosen_chunk)
            node.set_chunk(chosen_chunk)
            chosen_exit = chosen_chunk.get_exit(exit.direction, exit.pos)
            chosen_exit.edge = node.get_edge(adj_node)
            adj_exit.edge = adj_node.get_edge(node)
            return True
        return False

    def tie_loop(self, node, chunked_adjs, legal_chunks):
        def choose_chunk(chunk, real_pos, other_exit):
            chunks.append(chunk.copy())
            exits.append(other_exit)
            positions.append(real_pos)
            bad_rooms.append(set())

        def calc_new_pos(chunk, cur_chunk, cur_exit, cur_pos):
            first_exit = random.choice(chunk.get_unchunked_exits(opposite(cur_exit.direction)))
            x_pos, y_pos = self.find_new_position(cur_exit.direction, cur_pos, cur_chunk, cur_exit, chunk, first_exit)
            if self.collides(x_pos, y_pos, chunk):
                return None
            other_exit, other_direction = chunk.get_other_exit(first_exit)
            other_exit_pos = self.get_xy_pos(chunk, other_direction, other_exit)
            # real_pos, new_pos, other_exit
            return chunk, (x_pos, y_pos), (x_pos + other_exit_pos[0], y_pos + other_exit_pos[1]), other_exit 

        if C.DEBUG:
            print('Tying Loop!')
        # Only get nodes with two exits, since we're just tying off the loop
        legal_chunks = [chunk for chunk in legal_chunks if chunk.get_num_exits() == 2]
        # Initial set-up
        a, b = chunked_adjs
        a_dir = a.get_direction_to_node(node)
        b_dir = b.get_direction_to_node(node)

        a_exit = a.chunk.get_unchunked_exits(a_dir)
        assert len(a_exit) == 1
        a_exit = a_exit[0]

        b_exit = b.chunk.get_unchunked_exits(b_dir)
        assert len(b_exit) == 1, "Node to tie to has more than one unchunked exit %s" % b_dir
        b_exit = b_exit[0]

        # a_pos = self.chunk_positions[a.chunk]
        b_pos = self.chunk_positions[b.chunk]
        # a_exit_pos = self.get_xy_pos(a.chunk, a_dir, a_exit)
        b_exit_pos = self.get_xy_pos(b.chunk, b_dir, b_exit)
        # init_pos = a_pos[0] + a_exit_pos[0], a_pos[1] + a_exit_pos[1]
        final_pos = b_pos[0] + b_exit_pos[0], b_pos[1] + b_exit_pos[1]

        chunks = [a.chunk]
        exits = [a_exit]
        positions = [self.chunk_positions[a.chunk]]
        bad_rooms = [set()]

        # Keep searching for 
        loop_tied = False
        while chunks and not loop_tied:
            cur_chunk = chunks[-1]
            cur_exit = exits[-1]
            choose_from = [chunk for chunk in legal_chunks if chunk.get_unchunked_exits(opposite(cur_exit.direction)) and chunk.name not in bad_rooms[-1]]
            random.shuffle(choose_from)

            exit_pos = self.get_xy_pos(cur_chunk, cur_exit.direction, cur_exit)
            cur_pos = positions[-1]
            offset_x, offset_y = cur_pos[0] + exit_pos[0], cur_pos[1] + exit_pos[1]
            distance_to_end = calculate_distance((offset_x, offset_y), final_pos)
            if C.DEBUG:
                print('Offset: %s %s' % (offset_x, offset_y))
                print('Distance to end: %s' % distance_to_end)

            # Get important position data for all chunks that fit in bounds
            pos_data = []
            for chunk in choose_from:
                output = calc_new_pos(chunk, cur_chunk, cur_exit, cur_pos)
                if output:
                    pos_data.append(output)

            # Check if any chunk ties the loop
            for chunk, real_pos, new_pos, other_exit in pos_data:
                if new_pos == final_pos and other_exit.direction == opposite(b_dir):
                    if C.DEBUG:
                        print('New Pos: %s, Final Pos: %s, Other Exit: %s, b_dir: %s' % (new_pos, final_pos, other_exit, b_dir))
                    choose_chunk(chunk, real_pos, other_exit)
                    loop_tied = True
                    break
            else:  # If we didn't break
                # Since that failed, check if any chunk moves us closer to goal
                for chunk, real_pos, new_pos, other_exit in pos_data:
                    if C.DEBUG:
                        print('New Pos: %s, Final Pos: %s' % (new_pos, final_pos))
                    if calculate_distance(new_pos, final_pos) < distance_to_end:
                        choose_chunk(chunk, real_pos, other_exit)
                        break
                else:  # Could not find any legal chunks -- need to backtrack
                    bad_chunk = chunks.pop()
                    if len(chunks) <= 0:
                        return False  # Tying the loop did not work
                    exits.pop()
                    positions.pop()
                    bad_rooms.pop()
                    bad_rooms[-1].add(bad_chunk.name)

        # ================== #
        # Done on completion #
        print('Tied Loop Complete!')
        for idx in range(1, len(chunks)):  # Skip first chunk since it is already chunked room
            x_pos, y_pos = positions[idx]
            chosen_chunk = chunks[idx]
            chosen_chunk.is_subchunk = True
            self.set(x_pos, y_pos, chosen_chunk)
            # chosen_chunk.mark_all_exits()
        a_exit.edge = a.get_edge(node)  # To mark as connected
        b_exit.edge = b.get_edge(node)
        final_chunk = chunks[-1]
        node.set_chunk(final_chunk)
        # Mark important exits
        # final_chunk.get_unchunked_exits(opposite(a_dir))[0].edge = node.get_edge(a)
        # final_chunk.get_unchunked_exits(opposite(b_dir))[0].edge = node.get_edge(b)
        final_chunk.subchunks = chunks[1:-1]  # so that we still have a reference to them
        return True

    def find_three_or_more(self, node, chunked_adj_nodes, legal_chunks):
        if C.DEBUG:
            print('Finding Three or More!')
        # See if there is one chunk that fits all the requirements
        # Get the true exit positions and directions
        adj_exits = []
        for adj in chunked_adj_nodes:
            direction = adj.get_direction_to_node(node)
            if C.DEBUG:
                print(adj, direction)
                print(adj.chunk.exits)
            exits = adj.chunk.get_unchunked_exits(direction)
            assert exits, "Adjacent chunk has no unchunked exits! That is impossible! (since we haven't been chunked yet and are adjacent)"
            exit = random.choice(exits)
            adj_exits.append((direction, adj, exit))
        # print('Adjacent Exits')
        # print(adj_exits)
        # Now we have all true exit positions
        # We have to iterate through the legal chunks, finding any that can fit to the constraints
        random.shuffle(legal_chunks)  # Shuffle so that we can just pick the first one we find
        # print(legal_chunks)
        for chunk in legal_chunks:
            # Choose one of them to be first
            for first_idx, _ in enumerate(adj_exits):
                exit_match = {}
                fdir, fadj, fexit = adj_exits[first_idx]
                # Find offset
                adj_pos = self.chunk_positions[fadj.chunk]
                exit_pos = self.get_xy_pos(fadj.chunk, fdir, fexit)
                offset_x, offset_y = adj_pos[0] + exit_pos[0], adj_pos[1] + exit_pos[1]
                odir = opposite(fdir)
                # choose the chunk's exit to match
                chunk_exit = random.choice(tuple(chunk.exits[odir]))
                exit_match[fadj] = fexit, chunk_exit
                if odir == 'left' or odir == 'right':
                    offset_y -= chunk_exit.pos
                else:
                    offset_x -= chunk_exit.pos
                if self.collides(offset_x, offset_y, chunk):
                    continue

                # Now see if the rest fit
                for i, values in enumerate(adj_exits):
                    if first_idx == i:
                        continue
                    direc, adj, exit = values
                    xy_pos = self.get_xy_pos(adj.chunk, direc, exit)
                    chunk_pos = self.chunk_positions[adj.chunk]
                    true_pos_x, true_pos_y = chunk_pos[0] + xy_pos[0], chunk_pos[1] + xy_pos[1]
                    chunk_exit = chunk.confirm_match(offset_x, offset_y, true_pos_x, true_pos_y, opposite(direc))
                    if chunk_exit:
                        exit_match[adj] = exit, chunk_exit
                    else:
                        break
                else:
                    # Wow! Found them all!
                    chosen_chunk = chunk.copy()
                    self.set(offset_x, offset_y, chosen_chunk)
                    node.set_chunk(chosen_chunk)
                    for adj_node, values in exit_match.items():
                        adj_exit, exit = values
                        chosen_exit = chosen_chunk.get_exit(exit.direction, exit.pos)
                        chosen_exit.edge = node.get_edge(adj_node)
                        adj_exit.edge = adj_node.get_edge(node)
                    return True

        else:
            if C.DEBUG:
                print("*** Error! find_three_or_more didn't find any matching chunks!")
            return False

    def get_xy_pos(self, chunk, direction, exit):
        if direction == 'up':
            return (exit.pos, 0)
        elif direction == 'down':
            return (exit.pos, chunk.c_height)
        elif direction == 'left':
            return (0, exit.pos)
        elif direction == 'right':
            return (chunk.c_width, exit.pos)

    def set(self, x, y, chunk):
        self.chunks[(x, y)] = chunk
        self.chunk_positions[chunk] = (x, y)

    def unset(self, chunk):
        pos = self.chunk_positions[chunk]
        del self.chunks[pos]
        del self.chunk_positions[chunk]

    def collides(self, x1, y1, chunk):
        """
        # Checks for collision in chunk space
        # Currently very fast, but it does iterate through every single placed chunk
        # May want to try a subgrid (one-layer octree) if this ends up being too slow
        """ 
        width1, height1 = chunk.c_width, chunk.c_height
        for pos, chunk in self.chunks.items():
            x2, y2 = pos
            width2, height2 = chunk.c_width, chunk.c_height
            if x1 < x2 + width2 and x1 + width1 > x2 and y1 < y2 + height2 and y1 + height1 > y2:
                return True
        return False

if __name__ == '__main__':
    for im in glob.glob('Images/*.png'):
        os.remove(im)
    images = glob.glob('Rooms/*.png')
    rooms = [Room(Image.open(im), im) for im in images]
    # Also flip the rooms horizontally, since left-right direction doesn't matter, and so we own't have to make mirrored rooms
    rooms += [Room(Image.open(im).transpose(Image.FLIP_LEFT_RIGHT), im) for im in images]
    # Create dungeon
    new_dungeon = Dungeon(rooms)
    new_dungeon.draw(True)
