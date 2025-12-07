# client/gui_view.py

import tkinter as tk
from . import constants
from . import game_model 

root = None
canvas = None
human_score_label = None
ai_score_label = None
human_info_bg_frame = None
ai_info_bg_frame = None
current_rect_id = None
animation_queue = []
animation_target_color = ""

def setup_gui_elements(root_ref, canvas_ref, score_labels, info_frames):
    global root, canvas, human_score_label, ai_score_label, human_info_bg_frame, ai_info_bg_frame
    root = root_ref
    canvas = canvas_ref
    human_score_label, ai_score_label = score_labels
    human_info_bg_frame, ai_info_bg_frame = info_frames

def get_cell_coords(event_x, event_y):
    r = event_y // constants.CELL_SIZE
    c = event_x // constants.CELL_SIZE
    return r, c

def draw_board():
    if not canvas or not game_model.current_game: return
    canvas.delete("all")
    game = game_model.current_game
    for r in range(game.rows):
        for c in range(game.cols):
            x1, y1 = c * constants.CELL_SIZE, r * constants.CELL_SIZE
            x2, y2 = x1 + constants.CELL_SIZE, y1 + constants.CELL_SIZE
            bg_color = "white"
            if game.owner_board[r][c] == 'human': bg_color = "lightblue"
            elif game.owner_board[r][c] == 'ai': bg_color = "lightcoral"
            canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill=bg_color)
            number = game.board[r][c]
            if number != 0:
                canvas.create_text(x1 + constants.CELL_SIZE/2, y1 + constants.CELL_SIZE/2,
                                   text=str(number), font=("Arial", constants.FONT_SIZE, "bold"), fill="black")
    update_score_display()

def update_score_display():
    if not game_model.current_game: return
    game = game_model.current_game
    human_score_label.config(text=f"{game.player_scores['human']}")
    ai_score_label.config(text=f"{game.player_scores['ai']}")
    if game.current_turn == "human":
        set_info_frame_colors(human_info_bg_frame, "lightblue")
        set_info_frame_colors(ai_info_bg_frame, "white")
    else:
        set_info_frame_colors(human_info_bg_frame, "white")
        set_info_frame_colors(ai_info_bg_frame, "lightpink")

def set_info_frame_colors(info_frame, color):
    info_frame.config(bg=color)
    for widget in info_frame.winfo_children():
        if isinstance(widget, tk.Label): widget.config(bg=color)

def draw_selection_rectangle(x1, y1, x2, y2, color="black"):
    global current_rect_id
    if current_rect_id: canvas.delete(current_rect_id)
    current_rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(7, 7))

def clear_selection_rectangle():
    global current_rect_id
    if current_rect_id:
        canvas.delete(current_rect_id)
        current_rect_id = None

def update_canvas_cursor():
    if not canvas or not game_model.current_game: return
    if game_model.current_game.current_turn == "human":
        canvas.config(cursor="cross")
    else:
        canvas.config(cursor="arrow")

def _animate_cell_fill(cells, player_type):
    global animation_queue, animation_target_color
    animation_queue = list(cells)
    animation_target_color = "lightblue" if player_type == "human" else "lightcoral"
    update_score_display()
    _animate_next_cell()

def _animate_next_cell():
    global animation_queue, animation_target_color
    if animation_queue:
        r, c = animation_queue.pop(0)
        x1, y1 = c * constants.CELL_SIZE, r * constants.CELL_SIZE
        x2, y2 = x1 + constants.CELL_SIZE, y1 + constants.CELL_SIZE
        final_owner_type = game_model.current_game.owner_board[r][c]
        fill_color = "lightblue" if final_owner_type == 'human' else "lightcoral"
        canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill=fill_color)
        root.after(50, _animate_next_cell)
    else:
        draw_board()
