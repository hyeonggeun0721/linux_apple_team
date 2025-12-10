# client/net_client.py

import socket
import threading
import tkinter as tk
from tkinter import messagebox
from . import constants
from . import game_model 
from .record_view import RecordDialog
from .gui_view import draw_board, update_canvas_cursor, update_score_display, _animate_cell_fill, clear_selection_rectangle, append_chat_message

# --- 서버로 패킷 전송 함수들 ---

def send_move_request(fr1, fc1, fr2, fc2):
    if constants.CLIENT_SOCKET:
        if game_model.current_game.current_turn != "human": return
        msg = f"MOVE {fr1} {fc1} {fr2} {fc2}\n"
        try: constants.CLIENT_SOCKET.send(msg.encode('utf-8'))
        except: pass

def send_pass_request():
    if constants.CLIENT_SOCKET:
        try: constants.CLIENT_SOCKET.send("PASS\n".encode('utf-8'))
        except: pass

def send_surrender_request():
    if constants.CLIENT_SOCKET:
        try: constants.CLIENT_SOCKET.send("SURRENDER\n".encode('utf-8'))
        except: pass

def send_cancel_queue_request():
    if constants.CLIENT_SOCKET:
        try: constants.CLIENT_SOCKET.send("CANCEL_QUEUE\n".encode('utf-8'))
        except: pass

def send_chat_request(message):
    if constants.CLIENT_SOCKET:
        try:
            packet = f"CHAT {message}\n"
            constants.CLIENT_SOCKET.send(packet.encode('utf-8'))
        except: pass

def send_history_request():
    if constants.CLIENT_SOCKET:
        try: constants.CLIENT_SOCKET.send("REQ_HISTORY\n".encode('utf-8'))
        except: pass

def send_refresh_request():
    if constants.CLIENT_SOCKET:
        try: constants.CLIENT_SOCKET.send("REQ_REFRESH\n".encode('utf-8'))
        except: pass

# --- 네트워크 연결 및 수신 ---

def connect_to_server(root_window):
    """서버 소켓 연결 및 수신 스레드 시작"""
    try:
        constants.CLIENT_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        constants.CLIENT_SOCKET.connect((constants.SERVER_IP, constants.SERVER_PORT))
        print(f"서버 연결 성공")
        recv_thread = threading.Thread(target=lambda: receive_message(root_window), daemon=True)
        recv_thread.start()
    except Exception as e:
        messagebox.showerror("연결 실패", f"서버 접속 불가\n{e}")

def receive_message(root_window):
    """서버 메시지 수신 및 분기 처리"""
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

                # 1. 게임 시작 메시지
                if command == "START":
                    constants.MY_PLAYER_ID = int(parts[1])
                    role = "Player 1" if constants.MY_PLAYER_ID == 0 else "Player 2"
                    root_window.event_generate("<<GameStart>>")
                    root_window.after(100, lambda: messagebox.showinfo("게임 시작", f"당신은 {role} 입니다."))

                # 2. 보드 데이터 수신
                elif command == "BOARD":
                    numbers = list(map(int, parts[1:]))
                    new_board = []
                    idx = 0
                    for r in range(constants.NUM_ROWS):
                        row = []
                        for c in range(constants.NUM_COLS):
                            row.append(numbers[idx]); idx += 1
                        new_board.append(row)
                    
                    if game_model.current_game is None:
                        is_p1 = (constants.MY_PLAYER_ID == 0)
                        game_model.current_game = game_model.Game(new_board, first_player_is_human=is_p1)
                    else:
                        game_model.current_game.board = new_board
                    root_window.after(0, draw_board)

                # 3. 유효한 이동 (성공)
                elif command == "VALID":
                    who_moved = int(parts[1])
                    r1, c1, r2, c2 = map(int, parts[2:6])
                    s1, s2 = int(parts[6]), int(parts[7])
                    is_my_move = (who_moved == constants.MY_PLAYER_ID)
                    ptype = "human" if is_my_move else "ai"
                    
                    if constants.MY_PLAYER_ID == 0:
                        game_model.current_game.player_scores['human'] = s1
                        game_model.current_game.player_scores['ai'] = s2
                    else:
                        game_model.current_game.player_scores['human'] = s2
                        game_model.current_game.player_scores['ai'] = s1

                    cells = []
                    for r in range(r1, r2 + 1):
                        for c in range(c1, c2 + 1):
                            if game_model.current_game.board[r][c] != 0:
                                game_model.current_game.board[r][c] = 0
                            game_model.current_game.owner_board[r][c] = ptype 
                            cells.append((r, c))
                    root_window.after(0, lambda: _animate_cell_fill(cells, ptype))

                # 4. 턴 변경
                elif command == "TURN_CHANGE":
                    next_id = int(parts[1])
                    if next_id == constants.MY_PLAYER_ID: game_model.current_game.current_turn = "human"
                    else: game_model.current_game.current_turn = "ai"
                    root_window.after(0, update_canvas_cursor)
                    root_window.after(0, update_score_display)

                # 5. 게임 종료
                elif command == "GAME_OVER":
                    wid = int(parts[1])
                    res = "승리! 🎉" if wid == constants.MY_PLAYER_ID else "패배... 😭"
                    root_window.after(0, lambda: messagebox.showinfo("결과", res))
                    root_window.after(100, lambda: root_window.event_generate("<<ReturnToHome>>"))
                    
                    # 로비 복귀 후 정보 갱신 요청
                    root_window.after(500, send_refresh_request)

                # 6. 잘못된 이동
                elif command == "INVALID":
                     root_window.after(0, lambda: messagebox.showerror("오류", "잘못된 이동입니다."))
                     root_window.after(0, clear_selection_rectangle)

                # 7. 채팅 수신
                elif command == "CHAT":
                    if len(parts) >= 3:
                        sid = parts[1]
                        txt = " ".join(parts[2:])
                        sname = "나" if sid == str(constants.MY_PLAYER_ID) else "상대"
                        root_window.after(0, lambda: append_chat_message(sname, txt))
                
                # 8. 전적 목록 수신
                elif command == "RES_HISTORY":
                    if len(parts) < 2: data = []
                    else:
                        raw_str = " ".join(parts[1:])
                        if raw_str.strip() == "NONE": data = []
                        else: data = raw_str.rstrip("/").split("/")
                    root_window.after(0, lambda d=data: RecordDialog(root_window, d))

                # 9. 유저 정보(점수) 갱신 수신
                elif command == "RES_REFRESH":
                    if len(parts) >= 3:
                        new_mmr = int(parts[1])
                        new_tier = parts[2]
                        print(f"[갱신] 점수:{new_mmr}, 티어:{new_tier}")
                        
                        if constants.CURRENT_HOME_INSTANCE:
                            root_window.after(0, lambda: constants.CURRENT_HOME_INSTANCE.update_user_info(new_mmr, new_tier))

        except Exception as e:
            print(f"Error: {e}")
            break