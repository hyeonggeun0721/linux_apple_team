# client/main.py
#시발 고친거임 22
import tkinter as tk
from tkinter import messagebox
import threading
import socket

from . import constants
from . import game_model
from . import net_client
from .gui_view import setup_gui_elements, draw_board, update_canvas_cursor, \
                       draw_selection_rectangle, clear_selection_rectangle, get_cell_coords, update_score_display
from .login_view import LoginApp
from .home_view import HomeApp

# UI 중앙 배치 함수
def center_window(window, width, height):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

# =================================================================
# 1. 게임 화면 실행 (매칭 성공 시)
# =================================================================
def start_game_session(event=None):
    """로비를 닫고 게임 화면을 띄웁니다."""
    global root, canvas
    
    for widget in root.winfo_children():
        widget.destroy()
        
    root.title(f"Net-Mushroom - 게임 중 (Player {constants.MY_PLAYER_ID + 1})")
    center_window(root, constants.WINDOW_WIDTH, constants.WINDOW_HEIGHT)
    root.resizable(False, False)
    root.config(bg="white")

    # --- UI 구성 ---
    main_game_frame = tk.Frame(root, bg="white")
    main_game_frame.pack(pady=5)

    # Player 1 (Human) Score
    human_score_frame = tk.Frame(main_game_frame, bd=0, relief="flat", bg="white")
    human_score_frame.pack(side=tk.LEFT, padx=10)
    human_info_bg_frame = tk.Frame(human_score_frame, bd=0, relief="flat")
    human_info_bg_frame.pack(fill="both", expand=True)
    tk.Label(human_info_bg_frame, text="😊", font=("Arial", 45, "bold")).pack(pady=(10,0))
    tk.Label(human_info_bg_frame, text="플레이어", font=("Arial", 20, "normal")).pack()
    human_score_label = tk.Label(human_score_frame, text="0", font=("Arial", 45, "bold"), bg="white")
    human_score_label.pack(pady=(0,10))

    # Board Canvas
    canvas = tk.Canvas(main_game_frame, width=constants.NUM_COLS * constants.CELL_SIZE, height=constants.NUM_ROWS * constants.CELL_SIZE, bg="white", highlightthickness=0)
    canvas.pack(side=tk.LEFT, padx=10)

    # Player 2 (AI) Score
    ai_score_frame = tk.Frame(main_game_frame, bd=0, relief="flat", bg="white")
    ai_score_frame.pack(side=tk.LEFT, padx=10)
    ai_info_bg_frame = tk.Frame(ai_score_frame, bd=0, relief="flat")
    ai_info_bg_frame.pack(fill="both", expand=True)
    tk.Label(ai_info_bg_frame, text="🤖", font=("Arial", 45, "bold")).pack(pady=(10,0))
    tk.Label(ai_info_bg_frame, text="상대방", font=("Arial", 20, "normal")).pack()
    ai_score_label = tk.Label(ai_score_frame, text="0", font=("Arial", 45, "bold"), bg="white")
    ai_score_label.pack(pady=(0,10))

    # 뷰 모듈 연결
    setup_gui_elements(root, canvas, 
                       (human_score_label, ai_score_label), 
                       (human_info_bg_frame, ai_info_bg_frame))

    # 버튼 생성
    button_frame = tk.Frame(root, bg="white")
    button_frame.pack(pady=10)

    pass_button = tk.Button(button_frame, text="턴 넘기기 (Skip)", 
                         command=handle_pass_button, 
                         bg="#FFC107", width=15, height=2)
    pass_button.pack(side=tk.LEFT, padx=5)

    giveup_btn = tk.Button(button_frame, text="항복 (나가기)", 
                       command=confirm_surrender, 
                       bg="#F44336", fg="white", width=15, height=2)
    giveup_btn.pack(side=tk.LEFT, padx=5)

    # ★ [핵심 수정] 이벤트 바인딩 (Enter, Leave 추가)
    canvas.bind("<ButtonPress-1>", handle_canvas_press)
    canvas.bind("<B1-Motion>", handle_canvas_drag)
    canvas.bind("<ButtonRelease-1>", handle_canvas_release)
    canvas.bind("<Enter>", handle_canvas_enter)  # 마우스 들어올 때
    canvas.bind("<Leave>", handle_canvas_leave)  # 마우스 나갈 때
    
    # 게임 객체 초기화
    game_model.current_game = game_model.Game(game_model.initialize_board_data())

def start_home_screen(socket_obj, user_id, user_data=None):
    """홈 화면(로비) 띄우기"""
    if user_data is None: user_data = {}
    for widget in root.winfo_children():
        widget.destroy()

    constants.CLIENT_SOCKET = socket_obj
    
    if not getattr(constants, 'RECV_THREAD_STARTED', False):
        constants.RECV_THREAD_STARTED = True
        recv_thread = threading.Thread(target=lambda: net_client.receive_message(root), daemon=True)
        recv_thread.start()

    home = HomeApp(root, user_id, user_data)
    center_window(root, 900, 600)
    
    root.bind("<<GameStart>>", start_game_session)
    root.bind("<<ReturnToHome>>", lambda e: start_home_screen(constants.CLIENT_SOCKET, user_id, user_data))

# =================================================================
# 2. 이벤트 핸들러 (CONTROLLER)
# =================================================================

# ★ [추가] 마우스가 캔버스에 들어올 때
def handle_canvas_enter(event):
    update_canvas_cursor() # 내 턴이면 십자가, 아니면 화살표로 설정

# ★ [추가] 마우스가 캔버스 밖으로 나갈 때 (버튼 누르러 갈 때)
def handle_canvas_leave(event):
    if canvas:
        canvas.config(cursor="arrow") # 무조건 화살표로 변경
    
    # 드래그 중이었다면 취소 (이게 없으면 버튼 클릭이 드래그로 인식될 수 있음)
    if game_model.start_x != -1:
        game_model.start_x = -1
        game_model.start_y = -1
        clear_selection_rectangle()

def handle_pass_button():
    if game_model.current_game and game_model.current_game.current_turn == "human":
        net_client.send_pass_request()
    else:
        tk.messagebox.showerror("턴 오류", "현재 당신의 차례가 아닙니다.")

def confirm_surrender():
    if not constants.CLIENT_SOCKET:
        tk.messagebox.showerror("오류", "서버와 연결된 상태가 아닙니다.")
        return
    if tk.messagebox.askyesno("항복", "정말 항복하고 나가시겠습니까?\n(패배로 기록됩니다)"):
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
        color = "light green"
    draw_selection_rectangle(game_model.start_x, game_model.start_y, end_x, end_y, color)

# =================================================================
# 3. 메인 실행
# =================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = LoginApp(root, on_login_success=start_home_screen)
    root.mainloop()