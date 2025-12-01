# net_client.py
import socket
import threading
import tkinter as tk
from tkinter import messagebox
from . import constants
from . import game_model 
from .gui_view import draw_board, update_canvas_cursor, update_score_display, _animate_cell_fill

def send_move_request(fr1, fc1, fr2, fc2):
    if constants.CLIENT_SOCKET:
        if game_model.current_game.current_turn != "human":
            messagebox.showerror("턴 오류", "현재 당신의 차례가 아닙니다!")
            return
        msg = f"MOVE {fr1} {fc1} {fr2} {fc2}\n"
        try:
            constants.CLIENT_SOCKET.send(msg.encode('utf-8'))
            print(f"[서버로 전송]: {msg.strip()}")
        except Exception as e:
            messagebox.showerror("통신 오류", f"전송 실패: {e}")

def connect_to_server(root_window):
    global CLIENT_SOCKET
    try:
        constants.CLIENT_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        constants.CLIENT_SOCKET.connect((constants.SERVER_IP, constants.SERVER_PORT))
        print(f"서버 연결됨!")
        recv_thread = threading.Thread(target=lambda: receive_message(root_window), daemon=True)
        recv_thread.start()
    except Exception as e:
        messagebox.showerror("연결 실패", f"서버 연결 실패: {e}")

def receive_message(root_window):
    buffer = ""
    while True:
        try:
            data = constants.CLIENT_SOCKET.recv(1024)
            if not data: break
            buffer += data.decode('utf-8')
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                if not msg.strip(): continue 
                parts = msg.split()
                if len(parts) < 1: continue 
                command = parts[0]

                if command == "START":
                    if len(parts) < 2: continue
                    constants.MY_PLAYER_ID = int(parts[1])
                    role = "선공 (Player 1)" if constants.MY_PLAYER_ID == 0 else "후공 (Player 2)"
                    root_window.title(f"Net-Mushroom Client - Player {constants.MY_PLAYER_ID + 1}")
                    print(f"게임 시작! 당신은 {role} 입니다.")

                elif command == "BOARD":
                    if len(parts) < 2: continue
                    numbers = list(map(int, parts[1:]))
                    new_board = []
                    idx = 0
                    for r in range(constants.NUM_ROWS):
                        row = []
                        for c in range(constants.NUM_COLS):
                            row.append(numbers[idx])
                            idx += 1
                        new_board.append(row)
                    if game_model.current_game:
                        game_model.current_game.board = new_board
                        draw_board()

                elif command == "VALID":
                    if len(parts) < 7: continue
                    who_moved = int(parts[1])
                    r1, c1, r2, c2 = map(int, parts[2:6])
                    new_score = int(parts[6])
                    
                    is_my_move = (who_moved == constants.MY_PLAYER_ID)
                    player_type = "human" if is_my_move else "ai"
                    
                    if is_my_move: game_model.current_game.player_scores['human'] = new_score
                    else: game_model.current_game.player_scores['ai'] = new_score

                    cells_to_animate = []
                    for r in range(r1, r2 + 1):
                        for c in range(c1, c2 + 1):
                            if game_model.current_game.board[r][c] != 0:
                                game_model.current_game.board[r][c] = 0
                                game_model.current_game.owner_board[r][c] = player_type 
                                cells_to_animate.append((r, c))
                    _animate_cell_fill(cells_to_animate, player_type)

                elif command == "TURN_CHANGE":
                    if len(parts) < 2: continue 
                    next_turn_id = int(parts[1])
                    if next_turn_id == constants.MY_PLAYER_ID:
                        game_model.current_game.current_turn = "human"
                    else:
                        game_model.current_game.current_turn = "ai"
                    update_canvas_cursor()
                    update_score_display()
                
                elif command == "INVALID":
                     messagebox.showerror("오류", "합이 10이 아니거나 규칙을 위반했습니다. 다시 시도하세요.")
        except Exception as e:
            break