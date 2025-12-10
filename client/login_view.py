# client/login_view.py

import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading
from . import constants 

# 창을 화면 중앙에 배치하는 함수
def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

class RegisterDialog(tk.Toplevel):
    """회원가입 팝업 창"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("회원가입")
        self.resizable(False, False)
        self.parent = parent
        self.configure(bg="#F0F0F0")

        center_window(self, 400, 500)
        
        self.socket = None
        self._connect_to_server()
        
        self._create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((constants.SERVER_IP, constants.SERVER_PORT))
        except:
            messagebox.showerror("연결 실패", "서버에 연결할 수 없습니다.")
            self.destroy()

    def on_close(self):
        if self.socket: self.socket.close()
        self.destroy()

    def _create_widgets(self):
        tk.Label(self, text="새 계정 만들기", font=("Helvetica", 18, "bold"), bg="#F0F0F0", fg="#333").pack(pady=20)
        
        form_frame = tk.Frame(self, bg="#F0F0F0")
        form_frame.pack(pady=10)
        
        tk.Label(form_frame, text="닉네임:", bg="#F0F0F0").grid(row=0, column=0, sticky="e", pady=5)
        self.entry_nick = tk.Entry(form_frame)
        self.entry_nick.grid(row=0, column=1, pady=5, padx=5)
        
        tk.Label(form_frame, text="아이디:", bg="#F0F0F0").grid(row=1, column=0, sticky="e", pady=5)
        self.entry_id = tk.Entry(form_frame)
        self.entry_id.grid(row=1, column=1, pady=5, padx=5)

        tk.Label(form_frame, text="비밀번호:", bg="#F0F0F0").grid(row=2, column=0, sticky="e", pady=5)
        self.entry_pw = tk.Entry(form_frame, show="*")
        self.entry_pw.grid(row=2, column=1, pady=5, padx=5)

        tk.Button(self, text="가입하기", command=self.request_register, bg="#2196F3", fg="white", width=15, height=2).pack(pady=20)

    def request_register(self):
        nick = self.entry_nick.get()
        uid = self.entry_id.get()
        upw = self.entry_pw.get()

        if not nick or not uid or not upw:
            messagebox.showwarning("입력", "모든 내용을 입력해주세요.")
            return

        if not self.socket: return

        try:
            msg = f"REQ_REGISTER {uid} {upw} {nick}\n"
            self.socket.send(msg.encode())
            
            data = self.socket.recv(1024).decode().strip()
            
            if "RES_REGISTER_SUCCESS" in data:
                messagebox.showinfo("성공", "가입되었습니다! 로그인해주세요.")
                self.on_close()
            else:
                messagebox.showerror("실패", "이미 존재하는 아이디입니다.")
                
        except Exception as e:
            messagebox.showerror("오류", f"통신 중 오류: {e}")
            self.on_close()


class LoginApp:
    """로그인 메인 화면"""
    def __init__(self, master, on_login_success):
        self.master = master
        self.on_login_success = on_login_success
        master.title("Net-Mushroom - 접속")
        master.resizable(False, False)
        center_window(master, 350, 450)
        
        self.socket = None
        self._connect_to_server()
        
        self._create_widgets()
        master.protocol("WM_DELETE_WINDOW", self.on_close)

    def _connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((constants.SERVER_IP, constants.SERVER_PORT))
        except:
            self.socket = None

    def on_close(self):
        if self.socket: self.socket.close()
        self.master.destroy()

    def _create_widgets(self):
        frame = tk.Frame(self.master, padx=20, pady=20)
        frame.pack(expand=True)

        tk.Label(frame, text="🍎 Net-Apple", font=("Helvetica", 20, "bold"), fg="#FF5722").pack(pady=20)

        tk.Label(frame, text="아이디").pack(anchor="w")
        self.id_entry = tk.Entry(frame, font=("Arial", 12))
        self.id_entry.pack(fill="x", pady=(0, 10))

        tk.Label(frame, text="비밀번호").pack(anchor="w")
        self.pw_entry = tk.Entry(frame, show="*", font=("Arial", 12))
        self.pw_entry.pack(fill="x", pady=(0, 20))

        tk.Button(frame, text="로그인", command=self.handle_login, 
                  bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), height=2).pack(fill="x", pady=5)

        tk.Button(frame, text="회원가입", command=self.open_register,
                  bg="#2196F3", fg="white", font=("Arial", 11, "bold"), height=2).pack(fill="x", pady=5)

        self.status_label = tk.Label(frame, text="서버 연결 대기 중...", fg="gray")
        self.status_label.pack(pady=10)

        if self.socket:
            self.status_label.config(text="서버 연결됨", fg="green")
        else:
            self.status_label.config(text="서버 연결 실패", fg="red")

    def open_register(self):
        RegisterDialog(self.master)

    def handle_login(self):
        uid = self.id_entry.get()
        upw = self.pw_entry.get()
        if not uid or not upw: return
        
        if not self.socket:
            self._connect_to_server()
            if not self.socket:
                messagebox.showerror("오류", "서버에 연결할 수 없습니다.")
                return

        try:
            msg = f"REQ_LOGIN {uid} {upw}\n"
            self.socket.send(msg.encode())
            
            data = self.socket.recv(1024).decode().strip()
            
            if "RES_LOGIN_SUCCESS" in data:
                connected_socket = self.socket
                self.master.after(0, lambda: self.on_login_success(connected_socket, uid))
                self.socket = None 
            else:
                self.status_label.config(text="로그인 실패", fg="red")
                messagebox.showerror("실패", "아이디 또는 비밀번호가 틀렸습니다.")
                
        except Exception as e:
            self.status_label.config(text="통신 오류", fg="red")
            print(e)