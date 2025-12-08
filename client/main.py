# client/main.py

import tkinter as tk
from tkinter import messagebox
import threading
import socket

from . import constants
from . import game_model
from . import net_client
# [추가] chat_view에서 ChatPanel 가져오기
from .chat_view import ChatPanel
from .gui_view import setup_gui_elements, draw_board, update_canvas_cursor, \
                       draw_selection_rectangle, clear_selection_rectangle, get_cell_coords, update_score_display
from .login_view import LoginApp
from .home_view import HomeApp

def center_window(window, width, height):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

# =================================================================
# 1. 게임 화면 실행
# =================================================================
def start_game_session(event=None):
    global root, canvas
    
    for widget in root.winfo_children():
        widget.destroy()
        
    root.title(f"Net-Mushroom - P{constants.MY_PLAYER_ID + 1}")
    center_window(root, constants.WINDOW_WIDTH, constants.WINDOW_HEIGHT)
    root.resizable(False, False)
    root.config(bg="white")

    root.bind("<Motion>", track_mouse_cursor)

    # 1. 메인 컨테이너 (좌/우 분할)
    main_container = tk.Frame(root, bg="white")
    main_container.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------------------------------------------------
    # [좌측] 게임 영역 (보드 + 점수 + 버튼)
    # ---------------------------------------------------------
    left_container = tk.Frame(main_container, bg="white")
    left_container.pack(side=tk.LEFT, fill="both", expand=True)

    # A. 게임 보드와 점수판이 들어갈 상단 프레임
    board_score_frame = tk.Frame(left_container, bg="white")
    board_score_frame.pack(side=tk.TOP, pady=(0, 10))

    # P1 점수
    human_score_frame = tk.Frame(board_score_frame, bg="white", width=constants.SCOREBOARD_WIDTH)
    human_score_frame.pack(side=tk.LEFT, padx=5)
    
    human_bg = tk.Frame(human_score_frame, bg="white")
    human_bg.pack(fill="both")
    tk.Label(human_bg, text="😊", font=("Arial", 25), bg="white").pack()
    tk.Label(human_bg, text="나", font=("Arial", 12, "bold"), bg="white").pack()
    human_score_label = tk.Label(human_score_frame, text="0", font=("Arial", 25, "bold"), bg="white")
    human_score_label.pack(pady=5)

    # 게임 보드 (Canvas)
    canvas = tk.Canvas(board_score_frame, 
                       width=constants.NUM_COLS * constants.CELL_SIZE, 
                       height=constants.NUM_ROWS * constants.CELL_SIZE, 
                       bg="white", highlightthickness=2, highlightbackground="#eee")
    canvas.pack(side=tk.LEFT, padx=5)

    # P2 점수
    ai_score_frame = tk.Frame(board_score_frame, bg="white", width=constants.SCOREBOARD_WIDTH)
    ai_score_frame.pack(side=tk.LEFT, padx=5)
    
    ai_bg = tk.Frame(ai_score_frame, bg="white")
    ai_bg.pack(fill="both")
    tk.Label(ai_bg, text="🤖", font=("Arial", 25), bg="white").pack()
    tk.Label(ai_bg, text="상대", font=("Arial", 12, "bold"), bg="white").pack()
    ai_score_label = tk.Label(ai_score_frame, text="0", font=("Arial", 25, "bold"), bg="white")
    ai_score_label.pack(pady=5)

    # B. 버튼 영역
    button_frame = tk.Frame(left_container, bg="white")
    button_frame.pack(side=tk.TOP, pady=10)

    pass_button = tk.Button(button_frame, text="턴 넘기기 (PASS)", 
                         command=handle_pass_button, 
                         bg="#FFB74D", fg="white", font=("Arial", 12, "bold"), 
                         width=16, height=2, relief="flat")
    pass_button.pack(side=tk.LEFT, padx=20)

    giveup_btn = tk.Button(button_frame, text="항복 (GG)", 
                       command=confirm_surrender, 
                       bg="#E57373", fg="white", font=("Arial", 12, "bold"), 
                       width=12, height=2, relief="flat")
    giveup_btn.pack(side=tk.LEFT, padx=20)

    # ---------------------------------------------------------
    # [우측] 채팅 영역 (ChatPanel 사용)
    # ---------------------------------------------------------
    # 기존 tk.Text 생성 코드를 제거하고 ChatPanel 인스턴스 생성
    chat_panel = ChatPanel(main_container, width=constants.CHAT_WIDTH, height=constants.WINDOW_HEIGHT)
    chat_panel.pack(side=tk.RIGHT, fill="y", padx=(10, 0))

    # GUI 요소 연결 (ChatPanel 객체 전달)
    setup_gui_elements(root, canvas, 
                       (human_score_label, ai_score_label), 
                       (human_bg, ai_bg),
                       chat_panel) # <--- 수정됨

    # 이벤트 바인딩
    canvas.bind("<ButtonPress-1>", handle_canvas_press)
    canvas.bind("<B1-Motion>", handle_canvas_drag)
    canvas.bind("<ButtonRelease-1>", handle_canvas_release)
    
    # 초기화
    is_p1 = (constants.MY_PLAYER_ID == 0)
    game_model.current_game = game_model.Game(game_model.initialize_board_data(), first_player_is_human=is_p1)
    
    draw_board()
    update_canvas_cursor()
    update_score_display()

# =================================================================
# 2. 버튼 및 이벤트 핸들러
# =================================================================

def track_mouse_cursor(event):
    if not root or not canvas: return
    x, y = root.winfo_pointerxy()
    widget_under_mouse = root.winfo_containing(x, y)
    
    if widget_under_mouse == canvas:
        if game_model.current_game and game_model.current_game.current_turn == "human":
            if canvas['cursor'] != "cross": canvas.config(cursor="cross")
        else:
            if canvas['cursor'] != "arrow": canvas.config(cursor="arrow")
    else:
        if canvas['cursor'] != "arrow": canvas.config(cursor="arrow")
        if game_model.start_x != -1:
            game_model.start_x = -1; game_model.start_y = -1
            clear_selection_rectangle()

def handle_pass_button():
    if game_model.current_game and game_model.current_game.current_turn == "human":
        net_client.send_pass_request()
    else:
        tk.messagebox.showwarning("경고", "지금은 당신의 차례가 아닙니다!")

def confirm_surrender():
    if not constants.CLIENT_SOCKET:
        tk.messagebox.showerror("오류", "서버와 연결되지 않았습니다.")
        return
    if tk.messagebox.askyesno("항복 확인", "정말 항복하시겠습니까?\n이 게임에서 패배하게 됩니다."):
        net_client.send_surrender_request()

def handle_canvas_release(event):
    r1, c1 = get_cell_coords(game_model.start_x, game_model.start_y)
    r2, c2 = get_cell_coords(event.x, event.y)
    fr1, fr2 = min(r1, r2), max(r1, r2)
    fc1, fc2 = min(c1, c2), max(c1, c2)
    net_client.send_move_request(fr1, fc1, fr2, fc2)
    clear_selection_rectangle()
    game_model.start_x, game_model.start_y = -1, -1

def handle_canvas_press(event):
    if not game_model.current_game or game_model.current_game.game_over: return
    if game_model.current_game.current_turn != "human": return
    game_model.start_x, game_model.start_y = event.x, event.y
    clear_selection_rectangle()

def handle_canvas_drag(event):
    if not game_model.current_game or game_model.current_game.game_over or game_model.start_x == -1: return
    end_x = max(0, min(event.x, constants.NUM_COLS * constants.CELL_SIZE - 1))
    end_y = max(0, min(event.y, constants.NUM_ROWS * constants.CELL_SIZE - 1))
    r1, c1 = get_cell_coords(game_model.start_x, game_model.start_y)
    r2, c2 = get_cell_coords(end_x, end_y)
    color = "red"
    if game_model.current_game.isValid(min(r1,r2), min(c1,c2), max(r1,r2), max(c1,c2)):
        color = "#4CAF50"
    draw_selection_rectangle(game_model.start_x, game_model.start_y, end_x, end_y, color)

# =================================================================
# 3. 메인 실행
# =================================================================
def start_home_screen(socket_obj, user_id, user_data=None):
    if user_data is None: user_data = {}
    for widget in root.winfo_children(): widget.destroy()

    constants.CLIENT_SOCKET = socket_obj
    if not getattr(constants, 'RECV_THREAD_STARTED', False):
        constants.RECV_THREAD_STARTED = True
        recv_thread = threading.Thread(target=lambda: net_client.receive_message(root), daemon=True)
        recv_thread.start()

    home = HomeApp(root, user_id, user_data)
    center_window(root, 900, 600)
    root.unbind("<Motion>")
    root.bind("<<GameStart>>", start_game_session)
    root.bind("<<ReturnToHome>>", lambda e: start_home_screen(constants.CLIENT_SOCKET, user_id, user_data))

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginApp(root, on_login_success=start_home_screen)
    root.mainloop()
