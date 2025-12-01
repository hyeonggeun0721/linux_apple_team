import tkinter as tk
import random
import time
import socket       # [추가] 통신용 라이브러리
import threading    # [추가] 비동기 수신용 라이브러리

# === 네트워크 관련 변수 ===
CLIENT_SOCKET = None
SERVER_IP = "10.125.234.111"
SERVER_PORT = 8080

# ================================
# Game 클래스: 게임 상태 관리
# ================================
class Game:
    def __init__(self, board_data_param, first_player_is_human=True):
        self.board = board_data_param   # 게임 보드 (숫자)
        self.rows = len(self.board)
        self.cols = len(self.board[0])
        # owner_board: 'none', 'human', 'ai'
        self.owner_board = [['none' for _ in range(self.cols)] for _ in range(self.rows)]
        self.player_scores = {"human": 0, "ai": 0}
        self.current_turn = "human" if first_player_is_human else "ai"
        self.consecutive_passes = 0
        self.game_over = False

    def isValid(self, r1, c1, r2, c2):
        sums = 0
        r1_has_val = False
        r2_has_val = False
        c1_has_val = False
        c2_has_val = False

        # 유효하지 않은 좌표 범위 검사
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

        if all_zero:
            return False

        # Rule 2: sum must be 10, and all four sides must have at least one non-zero value
        return sums == 10 and r1_has_val and r2_has_val and c1_has_val and c2_has_val

    def calculateMove(self): # AI의 움직임 계산 (가장 많은 칸을 점령하는 최적의 해)
        best_move = (-1, -1, -1, -1)
        max_cells_gained = -1

        for r1 in range(self.rows):
            for c1 in range(self.cols):
                for r2 in range(r1, self.rows):
                    for c2 in range(c1, self.cols):
                        if self.isValid(r1, c1, r2, c2):
                            current_cells_gained = 0
                            for r in range(r1, r2 + 1):
                                for c in range(c1, c2 + 1):
                                    if self.board[r][c] != 0:
                                        current_cells_gained += 1

                            if current_cells_gained > max_cells_gained:
                                max_cells_gained = current_cells_gained
                                best_move = (r1, c1, r2, c2)
                            elif current_cells_gained == max_cells_gained:
                                # 동점인 경우, 사전순으로 더 작은 것을 선택
                                if best_move == (-1,-1,-1,-1) or (r1, c1, r2, c2) < best_move:
                                    best_move = (r1, c1, r2, c2)
        return best_move

    def process_move(self, r1, c1, r2, c2, player_type):
        if self.game_over:
            return None # None을 반환하여 유효하지 않은 이동임을 알림

        if r1 == c1 == r2 == c2 == -1: # 패스
            self.consecutive_passes += 1
            return [] # 빈 리스트를 반환하여 애니메이션 대상 없음
        
        if not self.isValid(r1, c1, r2, c2):
            return None

        self.consecutive_passes = 0
        cells_to_animate = []

        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.board[r][c] != 0:
                    self.player_scores[player_type] += 1
                    self.board[r][c] = 0

        opponent_type = "ai" if player_type == "human" else "human"
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                current_owner = self.owner_board[r][c]
                if current_owner != 'none' and current_owner != player_type:
                    self.player_scores[current_owner] -= 1
                
                # 소유권이 바뀌는 셀만 애니메이션 대상에 추가
                if current_owner != player_type:
                    cells_to_animate.append((r, c))
                
                self.owner_board[r][c] = player_type
        
        return cells_to_animate # 애니메이션에 사용할 셀 리스트 반환

    def switch_turn(self):
        self.current_turn = "ai" if self.current_turn == "human" else "human"
        update_canvas_cursor()
        update_score_display()

    def check_game_over(self):
        if self.consecutive_passes >= 2:
            self.game_over = True
            update_canvas_cursor()
            update_score_display()
            display_game_over_message()
            return True
        return False

# ================================
# Tkinter GUI 설정 및 전역 변수
# ================================
NUM_ROWS = 10
NUM_COLS = 17
CELL_SIZE = 40
FONT_SIZE = 16
SCOREBOARD_WIDTH = 250
WINDOW_WIDTH = NUM_COLS * CELL_SIZE + (SCOREBOARD_WIDTH * 2) + 20
WINDOW_HEIGHT = NUM_ROWS * CELL_SIZE + 180

root = tk.Tk()
root.title("Apple Game Client") # 타이틀 변경
root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
root.resizable(False, False)
root.config(bg="white")

# 레이아웃 설정
root.grid_rowconfigure(0, weight=0, minsize=50)
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=0)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=0)
root.grid_columnconfigure(2, weight=1)

main_game_frame = tk.Frame(root, bg="white")
main_game_frame.grid(row=1, column=0, columnspan=3, pady=5)

# --- 점수판 (좌측: Human) ---
human_score_frame = tk.Frame(main_game_frame, bd=0, relief="flat", bg="white")
human_score_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
human_score_frame.grid_rowconfigure(0, weight=1)
human_score_frame.grid_rowconfigure(1, weight=1)
human_score_frame.grid_columnconfigure(0, weight=1)

# --- 게임 보드 (중앙) ---
human_info_bg_frame = tk.Frame(human_score_frame, bd=0, relief="flat")
human_info_bg_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
human_info_bg_frame.grid_rowconfigure(0, weight=1)
human_info_bg_frame.grid_rowconfigure(1, weight=1)
human_info_bg_frame.grid_columnconfigure(0, weight=1)

human_emoji_label = tk.Label(human_info_bg_frame, text="😊", font=("Arial", 45, "bold"))
human_emoji_label.grid(row=0, column=0, pady=(10,0))

human_name_label = tk.Label(human_info_bg_frame, text="플레이어", font=("Arial", 20, "normal"))
human_name_label.grid(row=1, column=0)

human_score_label = tk.Label(human_score_frame, text="0", font=("Arial", 45, "bold"), bg="white")
human_score_label.grid(row=1, column=0, pady=(0,10))

game_board_frame = tk.Frame(main_game_frame, bd=2, relief="sunken", bg="white")
game_board_frame.grid(row=0, column=1, padx=10, pady=5)

canvas = tk.Canvas(game_board_frame, width=NUM_COLS * CELL_SIZE, height=NUM_ROWS * CELL_SIZE, bg="white", highlightthickness=0)
canvas.pack(fill="both", expand=True)

ai_score_frame = tk.Frame(main_game_frame, bd=0, relief="flat", bg="white")
ai_score_frame.grid(row=0, column=2, padx=10, pady=5, sticky="nsew")
ai_score_frame.grid_rowconfigure(0, weight=1)
ai_score_frame.grid_rowconfigure(1, weight=1)
ai_score_frame.grid_columnconfigure(0, weight=1)
ai_info_bg_frame = tk.Frame(ai_score_frame, bd=0, relief="flat")
ai_info_bg_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
ai_info_bg_frame.grid_rowconfigure(0, weight=1)
ai_info_bg_frame.grid_rowconfigure(1, weight=1)
ai_info_bg_frame.grid_columnconfigure(0, weight=1)
ai_emoji_label = tk.Label(ai_info_bg_frame, text="🤖", font=("Arial", 45, "bold"))
ai_emoji_label.grid(row=0, column=0, pady=(10,0))
ai_name_label = tk.Label(ai_info_bg_frame, text="핑크빈", font=("Arial", 20, "normal"))
ai_name_label.grid(row=1, column=0)
ai_score_label = tk.Label(ai_score_frame, text="0", font=("Arial", 45, "bold"), bg="white")
ai_score_label.grid(row=1, column=0, pady=(0,10))


main_game_frame.grid_columnconfigure(0, weight=1, minsize=SCOREBOARD_WIDTH)
main_game_frame.grid_columnconfigure(1, weight=0)
main_game_frame.grid_columnconfigure(2, weight=1, minsize=SCOREBOARD_WIDTH)


button_frame = tk.Frame(root, bg="white")
button_frame.grid(row=2, column=0, columnspan=3, pady=(5,15))

reset_button = tk.Button(button_frame, text="다시 하기", command=lambda: initialize_game(True), width=15, height=2)
reset_button.pack(side=tk.LEFT, padx=10)

pass_button = tk.Button(button_frame, text="스킵", command=lambda: handle_pass(), width=15, height=2)
pass_button.pack(side=tk.LEFT, padx=10)

# === [추가] 네트워크 버튼 ===
connect_btn = tk.Button(button_frame, text="서버 연결", command=lambda: connect_to_server(), bg="yellow")
connect_btn.pack(side=tk.LEFT, padx=10)

test_msg_btn = tk.Button(button_frame, text="인사 보내기", command=lambda: send_test_message(), bg="lightgreen")
test_msg_btn.pack(side=tk.LEFT, padx=10)


current_game = None
start_x, start_y = -1, -1
current_rect_id = None
thinking_text_id = None
game_over_text_id = None
animation_queue = [] # 애니메이션 대기열
animation_target_color = ""

# ================================
# GUI 업데이트 함수
# ================================
def get_cell_coords(event_x, event_y):
    r = event_y // CELL_SIZE
    c = event_x // CELL_SIZE
    return r, c

def draw_board():
    canvas.delete("all")
    if not current_game: return
    for r in range(current_game.rows):
        for c in range(current_game.cols):
            x1, y1 = c * CELL_SIZE, r * CELL_SIZE
            x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
            bg_color = "white"
            if current_game.owner_board[r][c] == 'human':
                bg_color = "lightblue"
            elif current_game.owner_board[r][c] == 'ai':
                bg_color = "lightcoral"
            canvas.create_rectangle(x1 + 1, y1 + 1, x2, y2, outline="gray", width=1, fill=bg_color)
            number = current_game.board[r][c]
            if number != 0:
                canvas.create_text(x1 + CELL_SIZE / 2, y1 + CELL_SIZE / 2,
                                   text=str(number), font=("Arial", FONT_SIZE, "bold"), fill="black")
    update_score_display()

def update_score_display():
    human_score = current_game.player_scores['human'] if current_game else 0
    ai_score = current_game.player_scores['ai'] if current_game else 0
    human_emoji_label.config(text="😊")
    human_name_label.config(text="플레이어")
    human_score_label.config(text=f"{human_score}")
    ai_emoji_label.config(text="🤖")
    ai_name_label.config(text="핑크빈")
    ai_score_label.config(text=f"{ai_score}")
    if current_game and not current_game.game_over:
        if current_game.current_turn == "human":
            set_info_frame_colors(human_info_bg_frame, "lightblue")
            set_info_frame_colors(ai_info_bg_frame, "white")
        elif current_game.current_turn == "ai":
            set_info_frame_colors(human_info_bg_frame, "white")
            set_info_frame_colors(ai_info_bg_frame, "lightpink")
    else:
        set_info_frame_colors(human_info_bg_frame, "white")
        set_info_frame_colors(ai_info_bg_frame, "white")

def set_info_frame_colors(info_frame, color):
    info_frame.config(bg=color)
    for widget in info_frame.winfo_children():
        if isinstance(widget, tk.Label):
            widget.config(bg=color)

def draw_selection_rectangle(x1, y1, x2, y2, color="black"):
    global current_rect_id
    if current_rect_id:
        canvas.delete(current_rect_id)
    current_rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, dash=(7, 7))

def clear_selection_rectangle():
    global current_rect_id
    if current_rect_id:
        canvas.delete(current_rect_id)
        current_rect_id = None
        
def display_thinking_message():
    global thinking_text_id
    if thinking_text_id:
        canvas.delete(thinking_text_id)
    x_center = NUM_COLS * CELL_SIZE / 2
    y_center = NUM_ROWS * CELL_SIZE / 2
    thinking_text_id = canvas.create_text(x_center, y_center, text="핑크빈 생각중...", font=("Arial", 24, "bold"), fill="black")

def hide_thinking_message():
    global thinking_text_id
    if thinking_text_id:
        canvas.delete(thinking_text_id)
        thinking_text_id = None

def display_game_over_message():
    global game_over_text_id
    if game_over_text_id:
        canvas.delete(game_over_text_id)
    human_score = current_game.player_scores['human']
    ai_score = current_game.player_scores['ai']
    winner = "플레이어" if human_score > ai_score else \
             "핑크빈" if ai_score > human_score else "무승부"
    message = f"게임 종료! 승자: {winner}\n(플레이어: {human_score}, 핑크빈: {ai_score})"
    x_center = NUM_COLS * CELL_SIZE / 2
    y_center = NUM_ROWS * CELL_SIZE / 2
    game_over_text_id = canvas.create_text(x_center, y_center, text=message, font=("Arial", 24, "bold"), fill="red", justify=tk.CENTER)

def update_canvas_cursor():
    if current_game and not current_game.game_over and current_game.current_turn == "human":
        canvas.config(cursor="cross")
    else:
        canvas.config(cursor="arrow")

def _animate_cell_fill(cells, player_type):
    global animation_queue, animation_target_color
    animation_queue = list(cells)
    animation_target_color = "lightblue" if player_type == "human" else "lightcoral"
    update_score_display()  # 애니메이션 시작 전에 점수판 업데이트
    _animate_next_cell()

def _animate_next_cell():
    global animation_queue, animation_target_color
    if animation_queue:
        r, c = animation_queue.pop(0)
        x1, y1 = c * CELL_SIZE, r * CELL_SIZE
        x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
        
        # 기존 셀 내용(숫자)을 지우고 다시 그리는 방식이 아닌,
        # 기존 숫자가 보존되도록 셀의 배경만 업데이트
        canvas.create_rectangle(x1 + 1, y1 + 1, x2, y2, outline="gray", width=1, fill=animation_target_color)
        number = current_game.board[r][c]
        if number != 0:
            canvas.create_text(x1 + CELL_SIZE / 2, y1 + CELL_SIZE / 2,
                               text=str(number), font=("Arial", FONT_SIZE, "bold"), fill="black")
        
        root.after(50, _animate_next_cell)
    else:
        check_and_switch_turn()

def handle_successful_move(cells_to_animate, player_type):
    if cells_to_animate is None:
        return
    elif not cells_to_animate:
        check_and_switch_turn()
    else:
        _animate_cell_fill(cells_to_animate, player_type)

# ================================
# [추가] 네트워크 함수
# ================================
def connect_to_server():
    global CLIENT_SOCKET
    try:
        CLIENT_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CLIENT_SOCKET.connect((SERVER_IP, SERVER_PORT))
        print(f"서버({SERVER_IP}:{SERVER_PORT})에 연결되었습니다!")
        
        # 서버로부터 메시지를 받는 '귀'를 별도의 스레드(일꾼)로 실행
        recv_thread = threading.Thread(target=receive_message, daemon=True)
        recv_thread.start()
        
    except Exception as e:
        print(f"서버 연결 실패: {e}")

def receive_message():
    global CLIENT_SOCKET, current_game
    while True:
        try:
            data = CLIENT_SOCKET.recv(4096) # 보드 데이터가 크니까 버퍼를 좀 늘려주세요
            if not data: break
            
            msg = data.decode('utf-8')
            # print(f"[서버 수신]: {msg}") # 디버깅용 (너무 길면 주석 처리)
            
            parts = msg.split()
            command = parts[0]

            # ★ [추가] 서버가 보드판 데이터를 보내줬을 때 (동기화)
            if command == "BOARD":
                # "BOARD 5 3 2 ..." -> 숫자 리스트로 변환
                numbers = list(map(int, parts[1:]))
                
                # 1차원 리스트를 2차원 보드로 변환
                new_board = []
                idx = 0
                for r in range(NUM_ROWS):
                    row = []
                    for c in range(NUM_COLS):
                        row.append(numbers[idx])
                        idx += 1
                    new_board.append(row)
                
                # 내 게임판 업데이트 및 다시 그리기
                if current_game:
                    current_game.board = new_board
                    draw_board()
                    print("서버와 보드 동기화 완료!")

            elif command == "VALID":
                # ... (기존 VALID 처리 코드 그대로 유지) ...
                r1, c1, r2, c2 = map(int, parts[1:5])
                new_score = int(parts[5])

                cells_to_animate = []
                for r in range(r1, r2 + 1):
                    for c in range(c1, c2 + 1):
                        if current_game.board[r][c] != 0:
                            current_game.board[r][c] = 0
                            cells_to_animate.append((r, c))
                
                current_game.player_scores['human'] = new_score
                _animate_cell_fill(cells_to_animate, "human")

            # ... (나머지 코드는 그대로) ...

        except Exception as e:
            print(f"수신 오류: {e}")
            break

def send_test_message():
    """테스트용: 서버에 인사말 보내기"""
    if CLIENT_SOCKET:
        msg = "Hello Server! I am Python Client."
        try:
            CLIENT_SOCKET.send(msg.encode('utf-8'))
            print(f"[전송함]: {msg}")
        except Exception as e:
            print(f"전송 실패: {e}")
    else:
        print("서버에 연결되어 있지 않습니다.")

# ================================
# 이벤트 핸들러
# ================================
def on_canvas_press(event):
    global start_x, start_y
    if current_game is None or current_game.game_over or current_game.current_turn != "human":
        return
    start_x, start_y = event.x, event.y
    clear_selection_rectangle()

def on_canvas_drag(event):
    if current_game is None or current_game.game_over or current_game.current_turn != "human" or start_x == -1:
        return
    end_x_clamped = max(0, min(event.x, NUM_COLS * CELL_SIZE - 1))
    end_y_clamped = max(0, min(event.y, NUM_ROWS * CELL_SIZE - 1))
    r1, c1 = get_cell_coords(start_x, start_y)
    r2, c2 = get_cell_coords(end_x_clamped, end_y_clamped)
    r1, r2 = min(r1, r2), max(r1, r2)
    c1, c2 = min(c1, c2), max(c1, c2)
    color = "red"
    if current_game.isValid(r1, c1, r2, c2):
        color = "light green"
    draw_selection_rectangle(start_x, start_y, end_x_clamped, end_y_clamped, color=color)

def on_canvas_release(event):
    global start_x, start_y
    if current_game is None or current_game.game_over or current_game.current_turn != "human" or start_x == -1:
        start_x, start_y = -1, -1
        return
    end_x, end_y = event.x, event.y
    clear_selection_rectangle()
    r1_idx, c1_idx = get_cell_coords(start_x, start_y)
    r2_idx, c2_idx = get_cell_coords(end_x, end_y)
    final_r1 = min(r1_idx, r2_idx)
    final_c1 = min(c1_idx, c2_idx)
    final_r2 = max(r1_idx, r2_idx)
    final_c2 = max(c1_idx, c2_idx)
    if not (0 <= r1_idx < NUM_ROWS and 0 <= c1_idx < NUM_COLS):
        start_x, start_y = -1, -1
        return
    cells_to_animate = current_game.process_move(final_r1, final_c1, final_r2, final_c2, "human")
    start_x, start_y = -1, -1
    handle_successful_move(cells_to_animate, "human")

def handle_pass():
    if current_game is None or current_game.game_over or current_game.current_turn != "human":
        return
    cells_to_animate = current_game.process_move(-1, -1, -1, -1, "human")
    handle_successful_move(cells_to_animate, "human")

def ai_turn_handler():
    if current_game is None or current_game.game_over or current_game.current_turn != "ai":
        return
    display_thinking_message()
    root.update_idletasks()
    root.after(500, _ai_calculate_and_move)

def _ai_calculate_and_move():
    ai_move = current_game.calculateMove()
    r1, c1, r2, c2 = ai_move
    hide_thinking_message()
    cells_to_animate = current_game.process_move(r1, c1, r2, c2, "ai")
    handle_successful_move(cells_to_animate, "ai")

def check_and_switch_turn():
    if current_game.check_game_over():
        draw_board()
    else:
        current_game.switch_turn()
        if current_game.current_turn == "ai":
            root.after(500, ai_turn_handler)

def initialize_game(first_player_is_human=True):
    global current_game, game_over_text_id
    if game_over_text_id:
        canvas.delete(game_over_text_id)
        game_over_text_id = None
    new_board = []
    for r in range(NUM_ROWS):
        row = []
        for c in range(NUM_COLS):
            row.append(random.randint(1, 9))
        new_board.append(row)
    current_game = Game(new_board, first_player_is_human)
    draw_board()
    update_canvas_cursor()

if __name__ == "__main__":
    canvas.bind("<ButtonPress-1>", on_canvas_press)
    canvas.bind("<B1-Motion>", on_canvas_drag)
    canvas.bind("<ButtonRelease-1>", on_canvas_release)
    canvas.bind("<Enter>", lambda event: update_canvas_cursor())
    canvas.bind("<Leave>", lambda event: canvas.config(cursor="arrow"))
    root.bind("p", lambda event: handle_pass())
    
    # 게임 바로 시작
    initialize_game()
    
    root.mainloop()