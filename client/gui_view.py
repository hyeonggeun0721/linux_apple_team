# client/gui_view.py

import tkinter as tk
import sys
from . import constants
from . import game_model 

# 전역 UI 요소 참조 변수
root = None
canvas = None
human_score_label = None
ai_score_label = None
human_info_bg_frame = None
ai_info_bg_frame = None
current_rect_id = None
animation_queue = []
animation_target_color = ""
chat_panel = None

def setup_gui_elements(root_ref, canvas_ref, score_labels, info_frames, chat_panel_ref):
    """메인 모듈의 UI 위젯들을 이 모듈의 전역 변수로 연결"""
    global root, canvas, human_score_label, ai_score_label, human_info_bg_frame, ai_info_bg_frame, chat_panel
    root = root_ref
    canvas = canvas_ref
    human_score_label, ai_score_label = score_labels
    human_info_bg_frame, ai_info_bg_frame = info_frames
    chat_panel = chat_panel_ref

def append_chat_message(sender, message):
    """채팅 패널에 메시지 추가"""
    if chat_panel:
        chat_panel.add_message(sender, message)

def get_cell_coords(event_x, event_y):
    """마우스 좌표를 그리드 좌표(행, 열)로 변환"""
    r = event_y // constants.CELL_SIZE
    c = event_x // constants.CELL_SIZE
    return r, c

def draw_board():
    """현재 게임 상태를 기반으로 보드 전체 다시 그리기"""
    if not canvas or not game_model.current_game: return
    canvas.delete("all")

    game = game_model.current_game
    
    # OS별 이모티콘 폰트 설정
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

            # 1. 배경 박스 그리기
            canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill="white")

            # 2. 소유자(사과) 그리기
            if owner == 'human':
                canvas.create_text(center_x, center_y, text="🍎", font=emoji_font, anchor="center")
            elif owner == 'ai':
                canvas.create_text(center_x, center_y, text="🍏", font=emoji_font, anchor="center")
            
            # 3. 숫자 그리기
            if number != 0:
                canvas.create_text(center_x, center_y,
                                   text=str(number), 
                                   font=number_font, 
                                   fill="black")
    
    update_score_display()

def update_score_display():
    """점수판 업데이트 및 현재 턴 강조"""
    if not game_model.current_game: return
    game = game_model.current_game
    human_score_label.config(text=f"{game.player_scores['human']}")
    ai_score_label.config(text=f"{game.player_scores['ai']}")
    
    # 턴에 따라 배경색 변경
    if game.current_turn == "human":
        set_info_frame_colors(human_info_bg_frame, "lightblue")
        set_info_frame_colors(ai_info_bg_frame, "white")
    else:
        set_info_frame_colors(human_info_bg_frame, "white")
        set_info_frame_colors(ai_info_bg_frame, "lightpink")

def set_info_frame_colors(info_frame, color):
    """프레임과 내부 라벨들의 배경색 일괄 변경"""
    info_frame.config(bg=color)
    for widget in info_frame.winfo_children():
        if isinstance(widget, tk.Label): widget.config(bg=color)

def draw_selection_rectangle(x1, y1, x2, y2, color="black"):
    """드래그 중인 선택 영역 표시"""
    global current_rect_id
    if current_rect_id: canvas.delete(current_rect_id)
    current_rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(7, 7))

def clear_selection_rectangle():
    """선택 영역 제거"""
    global current_rect_id
    if current_rect_id:
        canvas.delete(current_rect_id)
        current_rect_id = None

def update_canvas_cursor():
    """내 턴일 때 커서 모양 변경"""
    if not canvas or not game_model.current_game: return
    if game_model.current_game.current_turn == "human":
        canvas.config(cursor="cross")
    else:
        canvas.config(cursor="arrow")

def _animate_cell_fill(cells, player_type):
    """사과 획득 애니메이션 시작"""
    global animation_queue, animation_target_emoji
    
    animation_queue = list(cells)
    
    if player_type == "human":
        animation_target_emoji = "🍎"
    else:
        animation_target_emoji = "🍏"
        
    update_score_display()
    _animate_next_cell()

def _animate_next_cell():
    """순차적으로 셀 애니메이션 수행"""
    global animation_queue, animation_target_emoji
    
    if animation_queue:
        r, c = animation_queue.pop(0)
        x1, y1 = c * constants.CELL_SIZE, r * constants.CELL_SIZE
        x2, y2 = x1 + constants.CELL_SIZE, y1 + constants.CELL_SIZE
        center_x = x1 + constants.CELL_SIZE / 2
        center_y = y1 + constants.CELL_SIZE / 2
        
        emoji_size = int(constants.CELL_SIZE * 0.75)
        font_family = "Apple Color Emoji" if 'darwin' in sys.platform else "Segoe UI Emoji"
        
        # 숫자 배경을 지우고 사과 이모티콘 생성
        canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill="white")
        canvas.create_text(center_x, center_y, 
                           text=animation_target_emoji, 
                           font=(font_family, emoji_size),
                           anchor="center")
        
        root.after(50, _animate_next_cell)
    else:
        draw_board()