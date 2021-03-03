def opposite(direction):
    if direction == 'up':
        return 'down'
    elif direction == 'left':
        return 'right'
    elif direction == 'right':
        return 'left'
    elif direction == 'down':
        return 'up'

def calculate_distance(position1, position2):
    return (abs(position1[0] - position2[0]) + abs(position1[1] - position2[1]))
