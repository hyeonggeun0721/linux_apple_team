# client/net_client.py

import socket
import threading
import tkinter as tk
from tkinter import messagebox
from . import constants
from . import game_model 
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
        
        # 수신 스레드 시작
        recv_thread = threading.Thread(target=lambda: receive_message(root_window), daemon=True)
        recv_thread.start()
        
    except Exception as e:
        messagebox.showerror("연결 실패", f"서버 연결 실패: {e}")

# 스킵 요청
def send_pass_request():
    if constants.CLIENT_SOCKET:
        if game_model.current_game.current_turn != "human":
            messagebox.showerror("알림", "당신의 차례가 아닙니다.")
            return
        try:
            constants.CLIENT_SOCKET.send("PASS\n".encode('utf-8'))
        except: pass

# 항복 요청
def send_surrender_request():
    if constants.CLIENT_SOCKET:
        try:
            constants.CLIENT_SOCKET.send("SURRENDER\n".encode('utf-8'))
        except: pass

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

                # --- 1. START: 내 ID 할당 및 게임 화면 전환 ---
                if command == "START":
                    if len(parts) < 2: continue
                    constants.MY_PLAYER_ID = int(parts[1])
                    role = "선공 (Player 1)" if constants.MY_PLAYER_ID == 0 else "후공 (Player 2)"
                    
                    print(f"게임 시작! 당신은 {role} 입니다.")
                    
                    # ★ [핵심 수정] 게임 시작 이벤트를 발생시켜 main.py가 화면을 전환하게 함
                    # 이 이벤트가 처리되어야 gui_view의 score_label 등이 생성됨
                    root_window.event_generate("<<GameStart>>")
                    
                    # 타이틀 변경 (화면 전환 후 적용되도록 약간 딜레이)
                    root_window.after(100, lambda r=role: root_window.title(f"Net-Mushroom Client - Player {constants.MY_PLAYER_ID + 1} ({r})"))

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
                    
                    # 게임 객체가 없으면 생성 (혹시 GameStart 이벤트보다 먼저 도착했을 경우 대비)
                    if game_model.current_game is None:
                        is_p1 = (constants.MY_PLAYER_ID == 0)
                        game_model.current_game = game_model.Game(new_board, first_player_is_human=is_p1)
                    else:
                        game_model.current_game.board = new_board
                        
                    root_window.after(0, draw_board)
                    print("서버와 보드 동기화 완료!")

                # --- 3. VALID: 정답 처리 ---
                elif command == "VALID":
                    if len(parts) < 8: continue
                    
                    who_moved = int(parts[1])
                    r1, c1, r2, c2 = map(int, parts[2:6])
                    server_score_p1 = int(parts[6])
                    server_score_p2 = int(parts[7])

                    is_my_move = (who_moved == constants.MY_PLAYER_ID)
                    player_type = "human" if is_my_move else "ai"
                    
                    # 점수 업데이트
                    if constants.MY_PLAYER_ID == 0: 
                        game_model.current_game.player_scores['human'] = server_score_p1
                        game_model.current_game.player_scores['ai'] = server_score_p2
                    else: 
                        game_model.current_game.player_scores['human'] = server_score_p2
                        game_model.current_game.player_scores['ai'] = server_score_p1

                    cells_to_animate = []
                    for r in range(r1, r2 + 1):
                        for c in range(c1, c2 + 1):
                            if game_model.current_game.board[r][c] != 0:
                                game_model.current_game.board[r][c] = 0
                            
                            game_model.current_game.owner_board[r][c] = player_type 
                            cells_to_animate.append((r, c))
                    
                    root_window.after(0, lambda cells=cells_to_animate, p=player_type: _animate_cell_fill(cells, p))

                # --- 4. TURN_CHANGE: 턴 변경 ---
                elif command == "TURN_CHANGE":
                    if len(parts) < 2: continue 
                    
                    # 게임 객체가 아직 생성되지 않았으면 무시 (타이밍 이슈 방지)
                    if game_model.current_game is None: continue

                    next_turn_id = int(parts[1])
                    
                    if next_turn_id == constants.MY_PLAYER_ID:
                        game_model.current_game.current_turn = "human"
                        print(">>> 당신의 차례입니다! <<<")
                    else:
                        game_model.current_game.current_turn = "ai"
                        print(">>> 상대방의 차례입니다. <<<")
                    
                    root_window.after(0, update_canvas_cursor)
                    root_window.after(0, update_score_display)
                
                # [추가] 게임 오버 처리
                elif command == "GAME_OVER":
                    if len(parts) < 4: continue
                    winner_id = int(parts[1])
                    # s1 = int(parts[2])
                    # s2 = int(parts[3])
                    
                    result_msg = "승리!" if winner_id == constants.MY_PLAYER_ID else "패배..."
                    if winner_id == constants.MY_PLAYER_ID:
                         msg = "상대방이 항복했습니다. 당신의 승리입니다! 🎉"
                    else:
                         msg = "당신이 항복했습니다. (패배) 😭"

                    # 결과 알림창 띄우기 (메인 스레드)
                    root_window.after(0, lambda m=msg: messagebox.showinfo("게임 종료", m))
                    
                    # ★ 홈 화면으로 복귀 이벤트 발생
                    root_window.after(100, lambda: root_window.event_generate("<<ReturnToHome>>"))
                    
                # --- 5. INVALID ---
                elif command == "INVALID":
                     root_window.after(0, lambda: messagebox.showerror("오류", "합이 10이 아니거나 규칙을 위반했습니다. 다시 시도하세요."))

        except Exception as e:
            print(f"수신 오류: {e}")
            break