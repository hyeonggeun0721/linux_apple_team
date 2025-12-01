# main.py
import tkinter as tk
from . import constants
from . import game_model
from . import net_client
from .gui_view import setup_gui_elements, draw_board, update_canvas_cursor, \
                       draw_selection_rectangle, clear_selection_rectangle, get_cell_coords 

root = tk.Tk()
root.title("Net-Mushroom Client")
root.geometry(f"{constants.WINDOW_WIDTH}x{constants.WINDOW_HEIGHT}")
root.resizable(False, False)
root.config(bg="white")

main_game_frame = tk.Frame(root, bg="white")
main_game_frame.pack(pady=5)

human_score_frame = tk.Frame(main_game_frame, bg="white")
human_score_frame.pack(side=tk.LEFT, padx=10)
human_info_bg_frame = tk.Frame(human_score_frame)
human_info_bg_frame.pack()
human_emoji_label = tk.Label(human_info_bg_frame, text="😊", font=("Arial", 45))
human_emoji_label.pack()
human_score_label = tk.Label(human_score_frame, text="0", font=("Arial", 45), bg="white")
human_score_label.pack()

canvas = tk.Canvas(main_game_frame, width=constants.NUM_COLS * constants.CELL_SIZE, height=constants.NUM_ROWS * constants.CELL_SIZE, bg="white", highlightthickness=0)
canvas.pack(side=tk.LEFT, padx=10)

ai_score_frame = tk.Frame(main_game_frame, bg="white")
ai_score_frame.pack(side=tk.LEFT, padx=10)
ai_info_bg_frame = tk.Frame(ai_score_frame)
ai_info_bg_frame.pack()
ai_emoji_label = tk.Label(ai_info_bg_frame, text="🤖", font=("Arial", 45))
ai_emoji_label.pack()
ai_score_label = tk.Label(ai_score_frame, text="0", font=("Arial", 45), bg="white")
ai_score_label.pack()

button_frame = tk.Frame(root, bg="white")
button_frame.pack(pady=10)

setup_gui_elements(root, canvas, (human_score_label, ai_score_label), (human_info_bg_frame, ai_info_bg_frame))

def handle_canvas_release(event):
    r1, c1 = get_cell_coords(game_model.start_x, game_model.start_y)
    r2, c2 = get_cell_coords(event.x, event.y)
    net_client.send_move_request(min(r1,r2), min(c1,c2), max(r1,r2), max(c1,c2))
    clear_selection_rectangle()
    game_model.start_x, game_model.start_y = -1, -1

def handle_canvas_press(event):
    if not game_model.current_game or game_model.current_game.current_turn != "human": return
    game_model.start_x, game_model.start_y = event.x, event.y
    clear_selection_rectangle()

def handle_canvas_drag(event):
    if not game_model.current_game or game_model.start_x == -1: return
    end_x = max(0, min(event.x, constants.NUM_COLS * constants.CELL_SIZE - 1))
    end_y = max(0, min(event.y, constants.NUM_ROWS * constants.CELL_SIZE - 1))
    r1, c1 = get_cell_coords(game_model.start_x, game_model.start_y)
    r2, c2 = get_cell_coords(end_x, end_y)
    color = "light green" if game_model.current_game.isValid(min(r1,r2), min(c1,c2), max(r1,r2), max(c1,c2)) else "red"
    draw_selection_rectangle(game_model.start_x, game_model.start_y, end_x, end_y, color)

connect_btn = tk.Button(button_frame, text="서버 연결", command=lambda: net_client.connect_to_server(root), bg="yellow", width=12)
connect_btn.pack()

if __name__ == "__main__":
    game_model.current_game = game_model.Game(game_model.initialize_board_data())
    canvas.bind("<ButtonPress-1>", handle_canvas_press)
    canvas.bind("<B1-Motion>", handle_canvas_drag)
    canvas.bind("<ButtonRelease-1>", handle_canvas_release)
    draw_board()
    update_canvas_cursor()
    root.mainloop()