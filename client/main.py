import tkinter as tk
import socket
import threading
from . import constants
from . import game_model
from . import net_client
from .gui_view import setup_gui_elements, draw_board, update_canvas_cursor, \
                       draw_selection_rectangle, clear_selection_rectangle, get_cell_coords
from .login_view import LoginApp
from .home_view import HomeApp # [추가]

# [중요] 홈 화면 복귀 함수
def return_to_home(event=None):
    # 현재 소켓과 ID 정보를 유지한 채 홈 화면 재실행
    start_home_screen(constants.CLIENT_SOCKET, f"User{constants.MY_PLAYER_ID}") # ID는 임시
    
# =================================================================
# 1. 게임 화면 실행 (매칭 성공 시)
# =================================================================
# 중앙 배치 함수
def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

def start_game_session(event=None):
    """홈 화면을 지우고 게임 화면(보드)을 띄웁니다."""
    global root, canvas
    
    # 1. 기존 화면(홈/로그인) 위젯 제거
    for widget in root.winfo_children():
        widget.destroy()
        
    # 2. 게임 화면 설정
    root.title(f"Net-Mushroom - 게임 중 ({constants.MY_PLAYER_ID})")
    # [수정] 게임 화면 크기에 맞춰 중앙 배치
    center_window(root, constants.WINDOW_WIDTH, constants.WINDOW_HEIGHT)
    root.resizable(False, False)
    root.config(bg="white")

    # 3. UI 구성 (기존 게임 UI 코드 복원)
    main_game_frame = tk.Frame(root, bg="white")
    main_game_frame.pack(pady=5)

    human_score_frame = tk.Frame(main_game_frame, bd=0, relief="flat", bg="white")
    human_score_frame.pack(side=tk.LEFT, padx=10)
    human_info_bg_frame = tk.Frame(human_score_frame, bd=0, relief="flat")
    human_info_bg_frame.pack(fill="both", expand=True)
    human_emoji_label = tk.Label(human_info_bg_frame, text="😊", font=("Arial", 45, "bold"))
    human_emoji_label.pack(pady=(10,0))
    human_name_label = tk.Label(human_info_bg_frame, text="플레이어", font=("Arial", 20, "normal"))
    human_name_label.pack()
    human_score_label = tk.Label(human_score_frame, text="0", font=("Arial", 45, "bold"), bg="white")
    human_score_label.pack(pady=(0,10))

    canvas = tk.Canvas(main_game_frame, width=constants.NUM_COLS * constants.CELL_SIZE, height=constants.NUM_ROWS * constants.CELL_SIZE, bg="white", highlightthickness=0)
    canvas.pack(side=tk.LEFT, padx=10)

    ai_score_frame = tk.Frame(main_game_frame, bd=0, relief="flat", bg="white")
    ai_score_frame.pack(side=tk.LEFT, padx=10)
    ai_info_bg_frame = tk.Frame(ai_score_frame, bd=0, relief="flat")
    ai_info_bg_frame.pack(fill="both", expand=True)
    ai_emoji_label = tk.Label(ai_info_bg_frame, text="🤖", font=("Arial", 45, "bold"))
    ai_emoji_label.pack(pady=(10,0))
    ai_name_label = tk.Label(ai_info_bg_frame, text="상대방", font=("Arial", 20, "normal"))
    ai_name_label.pack()
    ai_score_label = tk.Label(ai_score_frame, text="0", font=("Arial", 45, "bold"), bg="white")
    ai_score_label.pack(pady=(0,10))

    setup_gui_elements(root, canvas, 
                       (human_score_label, ai_score_label), 
                       (human_info_bg_frame, ai_info_bg_frame))

    # [수정] 버튼 프레임에 스킵/항복 버튼 추가
    button_frame = tk.Frame(root, bg="white")
    button_frame.pack(pady=10)

    # 스킵 버튼
    pass_btn = tk.Button(button_frame, text="턴 넘기기 (Skip)", 
                         command=lambda: net_client.send_pass_request(),
                         bg="#FFC107", width=15, height=2)
    pass_btn.pack(side=tk.LEFT, padx=5)

    # 항복 버튼 (팝업 포함)
    def confirm_surrender():
        if tk.messagebox.askyesno("항복", "정말 항복하고 나가시겠습니까?\n(패배로 기록됩니다)"):
            net_client.send_surrender_request()

    giveup_btn = tk.Button(button_frame, text="항복 (나가기)", 
                           command=confirm_surrender,
                           bg="#F44336", fg="white", width=15, height=2)
    giveup_btn.pack(side=tk.LEFT, padx=5)

    # 이벤트 바인딩
    canvas.bind("<ButtonPress-1>", handle_canvas_press)
    canvas.bind("<B1-Motion>", handle_canvas_drag)
    canvas.bind("<ButtonRelease-1>", handle_canvas_release)
    
    # 게임 데이터 초기화 및 수신 대기
    # (주의: 이미 net_client.receive_message 스레드가 돌고 있으므로 여기서 또 켤 필요는 없음
    #  단, login_view에서 만든 임시 스레드는 종료되었을 수 있으니 확인 필요)
    #  -> 여기서는 net_client가 소켓을 계속 물고 있다고 가정
    
    game_model.current_game = game_model.Game(game_model.initialize_board_data())
    # 서버로부터 START, BOARD 메시지가 오면 화면이 갱신됨

# =================================================================
# 2. 홈 화면 실행 (로그인 성공 시 호출)
# =================================================================
def start_home_screen(socket_obj, user_id, user_data=None):
    """로그인 창 닫고 홈 화면 띄우기"""
    if user_data is None: user_data = {}

    # 1. 위젯 정리
    for widget in root.winfo_children():
        widget.destroy()

    # 2. 소켓 전역 저장
    constants.CLIENT_SOCKET = socket_obj
    
    # 3. [중요] 서버 메시지 수신 스레드 시작 (여기서부터 net_client가 통신 담당)
    recv_thread = threading.Thread(target=lambda: net_client.receive_message(root), daemon=True)
    recv_thread.start()

    # 4. 홈 화면 생성
    home = HomeApp(root, user_id, user_data)
    
    # 5. 게임 시작 이벤트 바인딩 (HomeApp에서 <<GameStart>> 발생 시 실행)
    root.bind("<<GameStart>>", start_game_session)

    # [추가] 게임 종료 이벤트 바인딩 (net_client에서 발생시킴)
    root.bind("<<ReturnToHome>>", lambda e: start_home_screen(constants.CLIENT_SOCKET, user_id, user_data))

# =================================================================
# 3. 컨트롤러 (이벤트 핸들러)
# =================================================================
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
# 4. 메인 실행
# =================================================================
if __name__ == "__main__":
    root = tk.Tk()
    # 로그인 앱 실행 (성공 시 start_home_screen 호출)
    app = LoginApp(root, on_login_success=start_home_screen)
    root.mainloop()