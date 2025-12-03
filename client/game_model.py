# client/game_model.py

import random

current_game = None
start_x, start_y = -1, -1

class Game:
    def __init__(self, board_data_param, first_player_is_human=True):
        self.board = board_data_param
        self.rows = len(self.board)
        self.cols = len(self.board[0])
        self.owner_board = [['none' for _ in range(self.cols)] for _ in range(self.rows)]
        self.player_scores = {"human": 0, "ai": 0}
        self.current_turn = "human" if first_player_is_human else "ai"
        self.consecutive_passes = 0
        self.game_over = False

    def isValid(self, r1, c1, r2, c2):
        sums = 0
        r1_has_val, r2_has_val, c1_has_val, c2_has_val = False, False, False, False
        
        if not (0 <= r1 <= r2 < self.rows and 0 <= c1 <= c2 < self.cols):
            return False
            
        all_zero = True
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.board[r][c] != 0:
                    all_zero = False
                    sums += self.board[r][c]
                    if r == r1: r1_has_val = True
                    if r == r2: r2_has_val = True
                    if c == c1: c1_has_val = True
                    if c == c2: c2_has_val = True
        
        if all_zero: return False
        return sums == 10 and r1_has_val and r2_has_val and c1_has_val and c2_has_val

def initialize_board_data():
    new_board = []
    for r in range(10): 
        row = []
        for c in range(17): 
            row.append(random.randint(1, 9))
        new_board.append(row)
    return new_board