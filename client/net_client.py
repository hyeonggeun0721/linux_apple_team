# client/net_client.py

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

def send_pass_request():
    if constants.CLIENT_SOCKET:
        try:
            msg = "PASS\n"
            constants.CLIENT_SOCKET.send(msg.encode('utf-8'))
            print("[서버로 전송]: PASS")
        except: pass

def send_surrender_request():
    if constants.CLIENT_SOCKET:
        try:
            msg = "SURRENDER\n"
            constants.CLIENT_SOCKET.send(msg.encode('utf-8'))
            print("[서버로 전송]: SURRENDER") # 디버깅 로그
        except: pass

def connect_to_server(root_window):
    try:
        constants.CLIENT_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        constants.CLIENT_SOCKET.connect((constants.SERVER_IP, constants.SERVER_PORT))
        print(f"서버 연결됨")
        recv_thread = threading.Thread(target=lambda: receive_message(root_window), daemon=True)
        recv_thread.start()
    except Exception as e:
        messagebox.showerror("연결 실패", f"{e}")

def receive_message(root_window):
    buffer = ""
    while True:
        try:
            data = constants.CLIENT_SOCKET.recv(1024)
            if not data:
                print("서버 연결 끊김")
                break
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
                    print(f"게임 시작! {role}")
                    root_window.event_generate("<<GameStart>>")
                    root_window.after(100, lambda r=role: root_window.title(f"Net-Mushroom - {r}"))

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
                    
                    if game_model.current_game is None:
                        is_p1 = (constants.MY_PLAYER_ID == 0)
                        game_model.current_game = game_model.Game(new_board, first_player_is_human=is_p1)
                    else:
                        game_model.current_game.board = new_board
                        
                    root_window.after(0, draw_board)

                elif command == "VALID":
                    if len(parts) < 8: continue
                    who_moved = int(parts[1])
                    r1, c1, r2, c2 = map(int, parts[2:6])
                    s1 = int(parts[6])
                    s2 = int(parts[7])

                    is_my_move = (who_moved == constants.MY_PLAYER_ID)
                    player_type = "human" if is_my_move else "ai"
                    
                    if constants.MY_PLAYER_ID == 0:
                        game_model.current_game.player_scores['human'] = s1
                        game_model.current_game.player_scores['ai'] = s2
                    else:
                        game_model.current_game.player_scores['human'] = s2
                        game_model.current_game.player_scores['ai'] = s1

                    cells_to_animate = []
                    for r in range(r1, r2 + 1):
                        for c in range(c1, c2 + 1):
                            if game_model.current_game.board[r][c] != 0:
                                game_model.current_game.board[r][c] = 0
                            game_model.current_game.owner_board[r][c] = player_type 
                            cells_to_animate.append((r, c))
                    
                    root_window.after(0, lambda cells=cells_to_animate, p=player_type: _animate_cell_fill(cells, p))

                elif command == "TURN_CHANGE":
                    if len(parts) < 2: continue 
                    if game_model.current_game is None: continue

                    next_turn_id = int(parts[1])
                    if next_turn_id == constants.MY_PLAYER_ID:
                        game_model.current_game.current_turn = "human"
                        print(">>> 내 차례 <<<")
                    else:
                        game_model.current_game.current_turn = "ai"
                        print(">>> 상대 차례 <<<")
                    
                    root_window.after(0, update_canvas_cursor)
                    root_window.after(0, update_score_display)

                elif command == "GAME_OVER":
                    if len(parts) < 4: continue
                    winner_id = int(parts[1])
                    
                    msg = "승리! 🎉" if winner_id == constants.MY_PLAYER_ID else "패배... 😭"
                    if winner_id == constants.MY_PLAYER_ID:
                         detail = "상대가 항복했거나 점수가 더 높습니다."
                    else:
                         detail = "당신이 항복했거나 점수가 더 낮습니다."

                    root_window.after(0, lambda: messagebox.showinfo("게임 종료", f"{msg}\n{detail}"))
                    root_window.after(100, lambda: root_window.event_generate("<<ReturnToHome>>"))

                elif command == "INVALID":
                     root_window.after(0, lambda: messagebox.showerror("오류", "규칙 위반! 합이 10이 아닙니다."))

        except Exception as e:
            print(f"수신 오류: {e}")
            break