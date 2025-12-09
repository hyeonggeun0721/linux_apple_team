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

# ChatPanel 객체를 저장할 변수
chat_panel = None

def setup_gui_elements(root_ref, canvas_ref, score_labels, info_frames, chat_panel_ref):
    global root, canvas, human_score_label, ai_score_label, human_info_bg_frame, ai_info_bg_frame, chat_panel
    root = root_ref
    canvas = canvas_ref
    human_score_label, ai_score_label = score_labels
    human_info_bg_frame, ai_info_bg_frame = info_frames
    chat_panel = chat_panel_ref

def append_chat_message(sender, message):
    if chat_panel:
        chat_panel.add_message(sender, message)

def get_cell_coords(event_x, event_y):
    r = event_y // constants.CELL_SIZE
    c = event_x // constants.CELL_SIZE
    return r, c

def draw_board():
    """
    보드 그리기 수정판
    - 빈 땅: 흰색 배경 + 숫자
    - 내 땅: 청사과(🍏) + 숫자
    - 남 땅: 빨간사과(🍎) + 숫자
    """
    if not canvas or not game_model.current_game: return
    canvas.delete("all")

    game = game_model.current_game
    
    emoji_size = int(constants.CELL_SIZE * 0.75)
    emoji_font = ("Apple Color Emoji", emoji_size) if 'darwin' in sys.platform else ("Segoe UI Emoji", emoji_size)
    number_font = ("Arial", int(constants.FONT_SIZE * 1.3), "bold")

    for r in range(game.rows):
        for c in range(game.cols):
            x1, y1 = c * constants.CELL_SIZE, r * constants.CELL_SIZE
            x2, y2 = x1 + constants.CELL_SIZE, y1 + constants.CELL_SIZE
            
            center_x = x1 + constants.CELL_SIZE / 2
            center_y = y1 + constants.CELL_SIZE / 2
            
            owner = game.owner_board[r][c]
            number = game.board[r][c]

            # [1단계] 기본 배경 (흰색 박스) - 무조건 그림
            canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill="white")

            # [2단계] 사과 그리기 (조건 강화)
            # owner가 0이나 None일 때는 건너뛰도록 명시적으로 체크합니다.
            if owner == 'human':
                canvas.create_text(center_x, center_y, text="🍎", font=emoji_font, anchor="center")
            elif owner == 'ai':
                canvas.create_text(center_x, center_y, text="🍏", font=emoji_font, anchor="center")
            
            # [3단계] 숫자 그리기
            if number != 0:
                canvas.create_text(center_x, center_y,
                                   text=str(number), 
                                   font=number_font, 
                                   fill="black")
    
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
    """애니메이션 시작 함수"""
    global animation_queue, animation_target_emoji
    
    animation_queue = list(cells)
    
    # 플레이어에 따라 사과 종류 결정
    if player_type == "human":
        animation_target_emoji = "🍎"
    else:
        animation_target_emoji = "🍏"
        
    update_score_display()
    _animate_next_cell()

def _animate_next_cell():
    """한 칸씩 순서대로 사과를 그리는 함수"""
    global animation_queue, animation_target_emoji
    
    if animation_queue:
        r, c = animation_queue.pop(0)
        x1, y1 = c * constants.CELL_SIZE, r * constants.CELL_SIZE
        x2, y2 = x1 + constants.CELL_SIZE, y1 + constants.CELL_SIZE
        
        center_x = x1 + constants.CELL_SIZE / 2
        center_y = y1 + constants.CELL_SIZE / 2
        
        # 폰트 크기 설정 (draw_board와 동일하게)
        emoji_size = int(constants.CELL_SIZE * 0.75)
        font_family = "Apple Color Emoji" if 'darwin' in sys.platform else "Segoe UI Emoji"
        
        # 1. 먼저 흰색 박스를 그려서 기존의 '숫자'를 지웁니다.
        canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill="white")
        
        # 2. 그 위에 사과 이모티콘을 그립니다.
        canvas.create_text(center_x, center_y, 
                           text=animation_target_emoji, 
                           font=(font_family, emoji_size),
                           anchor="center")
        
        # 3. 다음 칸 애니메이션 예약 (속도 조절: 50ms -> 필요하면 숫자 조정)
        root.after(50, _animate_next_cell)
    else:
        # 애니메이션이 다 끝나면 최종적으로 보드를 다시 그려서 상태 확정
        draw_board()