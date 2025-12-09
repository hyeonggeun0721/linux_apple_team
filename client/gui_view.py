# client/gui_view.py

import tkinter as tk
import sys
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

# [수정] Text 위젯 대신 ChatPanel 객체를 저장
chat_panel = None

def setup_gui_elements(root_ref, canvas_ref, score_labels, info_frames, chat_panel_ref):
    global root, canvas, human_score_label, ai_score_label, human_info_bg_frame, ai_info_bg_frame, chat_panel
    root = root_ref
    canvas = canvas_ref
    human_score_label, ai_score_label = score_labels
    human_info_bg_frame, ai_info_bg_frame = info_frames
    
    # [수정] 전달받은 ChatPanel 객체 저장
    chat_panel = chat_panel_ref

def append_chat_message(sender, message):
    """ChatPanel의 add_message 메서드 호출"""
    if chat_panel:
        chat_panel.add_message(sender, message)

# --- 이하 기존 게임 렌더링 함수들 (유지) ---

def get_cell_coords(event_x, event_y):
    r = event_y // constants.CELL_SIZE
    c = event_x // constants.CELL_SIZE
    return r, c

def draw_board():
    if not canvas or not game_model.current_game: return
    canvas.delete("all") # 캔버스 초기화

    game = game_model.current_game
    
    # 폰트 크기 설정
    emoji_size = int(constants.CELL_SIZE * 0.75) # 사과 크기
    number_font = ("Arial", int(constants.FONT_SIZE * 1.3), "bold") # 숫자 폰트

    for r in range(game.rows):
        for c in range(game.cols):
            x1, y1 = c * constants.CELL_SIZE, r * constants.CELL_SIZE
            x2, y2 = x1 + constants.CELL_SIZE, y1 + constants.CELL_SIZE
            
            center_x = x1 + constants.CELL_SIZE / 2
            center_y = y1 + constants.CELL_SIZE / 2
            
            owner = game.owner_board[r][c]
            number = game.board[r][c]

            # [1단계] 격자(테두리) 그리기 - ★무조건 실행★
            # 주인이 있든 없든 일단 하얀 네모와 회색 테두리를 그립니다.
            canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill="white")

            # [2단계] 사과 그리기 (주인이 있을 때만)
            if owner is not None:
                apple_emoji = "🍏" if owner == 'human' else "🍎"
                
                # 맥(Darwin)인지 윈도우인지에 따라 폰트 선택
                font_family = "Apple Color Emoji" if 'darwin' in sys.platform else "Segoe UI Emoji"
                
                canvas.create_text(center_x, center_y, 
                                   text=apple_emoji, 
                                   font=(font_family, emoji_size),
                                   anchor="center")

            # [3단계] 숫자 그리기
            if number != 0:
                # 사과 위에서도 잘 보이도록 약간의 그림자 효과(선택사항)나 색상 조정
                text_color = "black"
                # 만약 사과 색이 진해서 숫자가 안 보이면 흰색으로 변경
                # text_color = "white" if owner is not None else "black"

                canvas.create_text(center_x, center_y,
                                   text=str(number), 
                                   font=number_font, 
                                   fill=text_color)
    
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