# client/net_client.py

import socket
import threading
import tkinter as tk
from tkinter import messagebox
from . import constants
from . import game_model 
# gui_view에서 필요한 함수들을 가져옵니다.
from .gui_view import draw_board, update_canvas_cursor, update_score_display, _animate_cell_fill

def send_move_request(fr1, fc1, fr2, fc2):
    """서버로 MOVE 요청을 보냅니다."""
    if constants.CLIENT_SOCKET:
        # 클라이언트 측에서 턴이 아닐 경우 전송 자체를 막습니다.
        if game_model.current_game.current_turn != "human":
            messagebox.showerror("턴 오류", "현재 당신의 차례가 아닙니다!")
            return

        msg = f"MOVE {fr1} {fc1} {fr2} {fc2}\n"
        try:
            constants.CLIENT_SOCKET.send(msg.encode('utf-8'))
            print(f"[서버로 전송]: {msg.strip()}")
        except Exception as e:
            messagebox.showerror("통신 오류", f"전송 실패: 서버 연결 확인 필요 ({e})")

def connect_to_server(root_window):
    """서버와 연결하고 수신 스레드를 시작합니다."""
    try:
        constants.CLIENT_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        constants.CLIENT_SOCKET.connect((constants.SERVER_IP, constants.SERVER_PORT))
        print(f"서버({constants.SERVER_IP}:{constants.SERVER_PORT})에 연결되었습니다!")
        
        # daemon=True로 설정하여 메인 프로그램 종료 시 스레드도 함께 종료되게 함
        recv_thread = threading.Thread(target=lambda: receive_message(root_window), daemon=True)
        recv_thread.start()
        
    except Exception as e:
        messagebox.showerror("연결 실패", f"서버 연결 실패: {e}")

def receive_message(root_window):
    """서버로부터 메시지를 수신하고 처리하는 함수 (백그라운드 실행)"""
    buffer = ""

    while True:
        try:
            data = constants.CLIENT_SOCKET.recv(1024)
            if not data:
                print("서버와 연결이 끊어졌습니다.")
                break
            
            buffer += data.decode('utf-8')
            
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                if not msg.strip(): continue 
                
                parts = msg.split()
                if len(parts) < 1: continue 
                command = parts[0]

                # --- 1. START: 내 ID 할당 ---
                if command == "START":
                    if len(parts) < 2: continue
                    constants.MY_PLAYER_ID = int(parts[1])
                    role = "선공 (Player 1)" if constants.MY_PLAYER_ID == 0 else "후공 (Player 2)"
                    
                    # [GUI] 타이틀 변경 (메인 스레드 요청)
                    root_window.after(0, lambda r=role: root_window.title(f"Net-Mushroom Client - {r}"))
                    print(f"게임 시작! 당신은 {role} 입니다.")

                # --- 2. BOARD: 보드 동기화 ---
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
                        # [GUI] 보드 그리기 (메인 스레드 요청)
                        root_window.after(0, draw_board)
                        print("서버와 보드 동기화 완료!")

                # --- 3. VALID: 정답 처리 (핵심 수정) ---
                # --- 3. VALID: 정답 처리 ---
                elif command == "VALID":
                    # [수정] 인자가 늘어남 (score1, score2)
                    # VALID <pid> <r1> <c1> <r2> <c2> <score1> <score2>
                    if len(parts) < 8: continue # 길이 체크 수정 (8개여야 함)
                    
                    who_moved = int(parts[1])
                    r1, c1, r2, c2 = map(int, parts[2:6])
                    
                    # [수정] 두 명의 점수를 모두 받음
                    server_score_p1 = int(parts[6])
                    server_score_p2 = int(parts[7])

                    is_my_move = (who_moved == constants.MY_PLAYER_ID)
                    player_type = "human" if is_my_move else "ai"
                    
                    # [수정] 점수판 업데이트 (내 ID에 맞춰서 할당)
                    if constants.MY_PLAYER_ID == 0: # 내가 Player 1이면
                        game_model.current_game.player_scores['human'] = server_score_p1
                        game_model.current_game.player_scores['ai'] = server_score_p2
                    else: # 내가 Player 2면
                        game_model.current_game.player_scores['human'] = server_score_p2
                        game_model.current_game.player_scores['ai'] = server_score_p1

                    cells_to_animate = []
                    for r in range(r1, r2 + 1):
                        for c in range(c1, c2 + 1):
                            if game_model.current_game.board[r][c] != 0:
                                game_model.current_game.board[r][c] = 0          
                            
                            # 소유권 덮어쓰기 (뺏기)
                            game_model.current_game.owner_board[r][c] = player_type 
                            cells_to_animate.append((r, c))
                    
                    gui_view._animate_cell_fill(cells_to_animate, player_type)

                # --- 4. TURN_CHANGE: 턴 변경 ---
                elif command == "TURN_CHANGE":
                    if len(parts) < 2: continue 
                    next_turn_id = int(parts[1])
                    
                    if next_turn_id == constants.MY_PLAYER_ID:
                        game_model.current_game.current_turn = "human"
                        print(">>> 당신의 차례입니다! <<<")
                    else:
                        game_model.current_game.current_turn = "ai"
                        print(">>> 상대방의 차례입니다. <<<")
                    
                    # [GUI] 커서 및 점수판 업데이트 (메인 스레드 요청)
                    root_window.after(0, update_canvas_cursor)
                    root_window.after(0, update_score_display)
                
                # --- 5. INVALID ---
                elif command == "INVALID":
                     # [GUI] 에러 메시지 (메인 스레드 요청)
                     root_window.after(0, lambda: messagebox.showerror("오류", "합이 10이 아니거나 규칙을 위반했습니다. 다시 시도하세요."))


        except Exception as e:
            print(f"수신 오류: {e}") 
            break