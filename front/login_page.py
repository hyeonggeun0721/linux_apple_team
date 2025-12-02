import tkinter as tk
from tkinter import messagebox
import threading
import time
import socket
import json

# --- 1. 통신 상수 정의 ---
# 실제 C 서버가 리스닝하는 IP 주소와 포트 번호로 설정해야 합니다.
SERVER_IP = '127.0.0.1'
SERVER_PORT = 8080

# --- 2. 통신 프로토콜 OpCode 정의 (C 서버와 일치해야 함) ---
# C 서버에서 정의된 OpCode와 동일해야 합니다.
OP_CODE = {
    'REQ_LOGIN': 0x0001,
    'RES_LOGIN_SUCCESS': 0x0101,
    'RES_LOGIN_FAIL': 0x0102,
}

class LoginApp:
    def __init__(self, master):
        self.master = master
        master.title("사과 게임 - 로그인")
        master.geometry("400x300")
        master.resizable(False, False) # 창 크기 변경 불가

        # 서버 통신 상태 변수
        self.client_socket = None

        # 스타일 설정 (옵션)
        master.configure(bg="#F0F0F0")
        
        # UI 요소 생성
        self._create_widgets()

    def _create_widgets(self):
        # 중앙 프레임 (패딩을 주어 중앙에 배치)
        main_frame = tk.Frame(self.master, padx=30, pady=30, bg="#F0F0F0")
        main_frame.pack(expand=True)

        # 제목 레이블
        title_label = tk.Label(main_frame, text="🍎 사과 게임 온라인 대전", font=("Helvetica", 16, "bold"), bg="#F0F0F0", fg="#CC0000")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # ID 입력 필드
        tk.Label(main_frame, text="ID:", font=("Helvetica", 12), bg="#F0F0F0").grid(row=1, column=0, sticky="w", pady=5)
        self.id_entry = tk.Entry(main_frame, width=20, font=("Helvetica", 12))
        self.id_entry.grid(row=1, column=1, pady=5)
        self.id_entry.insert(0, "user_id_123") # 테스트를 위한 기본값

        # PW 입력 필드
        tk.Label(main_frame, text="Password:", font=("Helvetica", 12), bg="#F0F0F0").grid(row=2, column=0, sticky="w", pady=5)
        self.pw_entry = tk.Entry(main_frame, show="*", width=20, font=("Helvetica", 12))
        self.pw_entry.grid(row=2, column=1, pady=5)
        self.pw_entry.insert(0, "password123") # 테스트를 위한 기본값

        # 로그인 버튼
        login_button = tk.Button(main_frame, text="로그인", command=self.start_login_thread, width=15, font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white")
        login_button.grid(row=3, column=0, columnspan=2, pady=20)
        
        # 상태 메시지
        self.status_label = tk.Label(main_frame, text="서버 연결 대기 중...", fg="blue", bg="#F0F0F0")
        self.status_label.grid(row=4, column=0, columnspan=2)

    def start_login_thread(self):
        """GUI 블로킹을 피하기 위해 통신 작업을 별도 스레드에서 시작합니다."""
        username = self.id_entry.get()
        password = self.pw_entry.get()
        
        if not username or not password:
            messagebox.showerror("오류", "ID와 비밀번호를 입력해주세요.")
            return

        self.status_label.config(text="로그인 요청 중...")
        
        # 통신 작업을 위한 별도 스레드 생성 (GUI 블로킹 방지)
        login_thread = threading.Thread(target=self.send_login_request, args=(username, password))
        login_thread.daemon = True # 메인 프로그램 종료 시 스레드 종료
        login_thread.start()

    def send_login_request(self, username, password):
        """
        [핵심: C 서버 연동 로직]
        실제 C 서버로 로그인 패킷을 전송하고 응답을 받는 더미 함수.
        """
        try:
            # 1. 서버 연결
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            self.status_label.config(text=f"서버 연결 성공: {SERVER_IP}:{SERVER_PORT}", fg="green")
            
            # 2. 데이터 직렬화 및 패킷 생성
            # C 서버와 통신할 수 있는 형식으로 데이터를 준비합니다.
            login_data = {
                'id': username,
                'pw': password
            }
            # 실제 C 서버에서는 패킷 길이 + OpCode + Payload(바이너리 또는 JSON) 형식으로 전송해야 함
            
            # 여기서 C 서버가 이해할 수 있는 JSON/바이너리 패킷을 생성해야 합니다.
            json_payload = json.dumps(login_data).encode('utf-8')
            opcode = OP_CODE['REQ_LOGIN']
            
            # --- [C 서버 통신을 위한 길이 기반 패킷 생성] ---
            # C 서버는 'Length'를 기반으로 패킷을 읽습니다.
            
            # (예시: 4B Length + 2B OpCode + Payload)
            # 파이썬 struct 모듈을 사용하여 네트워크 바이트 순서(빅 엔디언)로 변환 필요
            # from struct import pack, unpack
            # packet_length = len(json_payload) + 2 
            # header = pack('>IH', packet_length, opcode) # I: unsigned int (4B), H: unsigned short (2B)
            # self.client_socket.sendall(header + json_payload)
            # ----------------------------------------------------
            
            # 임시로 JSON 문자열만 전송하는 것으로 가정
            self.client_socket.sendall(json_payload)

            # 3. 서버 응답 대기 및 수신
            # 실제로는 C 서버의 RES_LOGIN_SUCCESS/FAIL 패킷을 수신하고 파싱해야 합니다.
            time.sleep(2) # 서버 응답 대기 시간 가정
            
            # 4. 로그인 성공 처리 (더미 로직)
            self.master.after(0, lambda: self.handle_login_result(True, username))

        except ConnectionRefusedError:
            self.master.after(0, lambda: self.status_label.config(text="서버 연결 실패: 연결 거부", fg="red"))
        except TimeoutError:
            self.master.after(0, lambda: self.status_label.config(text="서버 연결 실패: 시간 초과", fg="red"))
        except Exception as e:
            self.master.after(0, lambda: self.status_label.config(text=f"통신 오류 발생: {e}", fg="red"))
        finally:
            if self.client_socket:
                self.client_socket.close()

    def handle_login_result(self, success, username):
        """메인 스레드에서 호출되어 UI를 업데이트합니다."""
        if success:
            messagebox.showinfo("성공", f"로그인 성공! {username}님, 환영합니다.")
            self.master.destroy() # 로그인 창 닫기
            # 여기에 로비 화면을 띄우는 로직을 추가합니다.
        else:
            messagebox.showerror("실패", "ID 또는 비밀번호가 올바르지 않습니다.")
            self.status_label.config(text="로그인 실패", fg="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = LoginApp(root)
    root.mainloop()