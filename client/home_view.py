# client/home_view.py

import tkinter as tk
from tkinter import messagebox, simpledialog, Menu
from tkinter import ttk 
import time
# import socket  <-- 소켓 직접 사용 안 함
# import json    <-- JSON 사용 안 함
# import struct  <-- Struct 사용 안 함
from . import constants

# =======================================================
# UI 컴포넌트 클래스 (팝업 등) - 디자인 유지
# =======================================================

# 중앙 배치 함수 (파일 맨 위에 추가하거나 클래스 안에 메서드로 넣어도 됨)
def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

class LoadingSpinner(tk.Canvas):
    """원형 로딩 애니메이션 위젯"""
    def __init__(self, parent, size=40, bg="white"):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0)
        self.size = size
        self.angle = 0
        self.is_running = False
        self.arc = self.create_arc(2, 2, size-2, size-2, start=0, extent=100, width=4, style="arc", outline="#2196F3")

    def start(self):
        self.is_running = True
        self.animate()

    def stop(self):
        self.is_running = False

    def animate(self):
        if not self.is_running: return
        self.angle = (self.angle - 10) % 360
        self.itemconfigure(self.arc, start=self.angle)
        self.after(50, self.animate)

class AIDifficultyDialog(tk.Toplevel):
    """AI 난이도 선택 팝업"""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("AI 난이도 선택")
        self.geometry("300x250")
        self.resizable(False, False)
        self.configure(bg="#F0F0F0")
        self.transient(parent)
        self.grab_set()
        self._create_widgets()

    def _create_widgets(self):
        tk.Label(self, text="난이도를 선택하세요", font=("Helvetica", 14, "bold"), bg="#F0F0F0").pack(pady=20)
        
        levels = [("쉬움 (Easy)", 1), ("보통 (Normal)", 2), ("어려움 (Hard)", 3)]
        for text, level in levels:
            tk.Button(self, text=text, font=("Helvetica", 11), width=20, 
                      command=lambda l=level: self.select_level(l), bg="white").pack(pady=5)

    def select_level(self, level):
        self.callback(level)
        self.destroy()

class MatchingDialog(tk.Toplevel):
    """매칭 대기 중 팝업 창"""
    def __init__(self, parent, cancel_callback):
        super().__init__(parent)
        self.cancel_callback = cancel_callback
        self.title("매칭 중...")
        self.geometry("300x200")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="white")
        self._create_widgets()
        
    def _create_widgets(self):
        tk.Label(self, text="🔍 상대를 찾는 중입니다...", font=("Helvetica", 12, "bold"), bg="white", pady=20).pack()
        self.spinner = LoadingSpinner(self, size=60)
        self.spinner.pack(pady=10)
        self.spinner.start()
        tk.Button(self, text="취소", command=self.on_cancel, bg="#FFCDD2", width=10).pack(pady=20)

    def on_cancel(self):
        self.spinner.stop()
        self.cancel_callback()
        self.destroy()

class GameRecordDialog(tk.Toplevel):
    """전적 확인 팝업 창"""
    def __init__(self, parent, record_data):
        super().__init__(parent)
        self.title("나의 전적 기록")
        self.geometry("600x400")
        self.resizable(False, False)
        self.configure(bg="#E0F7FA")
        
        self.record_data = record_data
        self._create_widgets()

    def _create_widgets(self):
        title_lbl = tk.Label(self, text="📜 최근 게임 기록", font=("Helvetica", 16, "bold"), bg="#E0F7FA", fg="#006064")
        title_lbl.pack(pady=15)

        # 표(Treeview) 생성
        columns = ("date", "opponent", "result", "score", "duration")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        
        # 컬럼 설정
        self.tree.heading("date", text="날짜")
        self.tree.heading("opponent", text="상대방")
        self.tree.heading("result", text="결과")
        self.tree.heading("score", text="점수 (나:상대)")
        self.tree.heading("duration", text="소요 시간")

        self.tree.column("date", width=120, anchor="center")
        self.tree.column("opponent", width=100, anchor="center")
        self.tree.column("result", width=60, anchor="center")
        self.tree.column("score", width=80, anchor="center")
        self.tree.column("duration", width=80, anchor="center")

        # 스타일 적용 (승리/패배 색상 등)
        self.tree.tag_configure("win", foreground="blue")
        self.tree.tag_configure("loss", foreground="red")
        self.tree.tag_configure("draw", foreground="gray")

        # 데이터 삽입
        for item in self.record_data:
            tag = "draw"
            if item['result'] == "승리": tag = "win"
            elif item['result'] == "패배": tag = "loss"
            
            self.tree.insert("", "end", values=(item['date'], item['opponent'], item['result'], item['score'], item['duration']), tags=(tag,))

        self.tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        btn_close = tk.Button(self, text="닫기", command=self.destroy, bg="#00838F", fg="white", font=("Helvetica", 10, "bold"), width=10)
        btn_close.pack(pady=(0, 15))

# =======================================================
# III. 메인 로비 앱 클래스 (HomeApp)
# =======================================================

class HomeApp:
    def __init__(self, master, user_id, user_data):
        self.master = master
        self.user_id = user_id
        self.user_data = user_data
        
        self.master.title("🍎 사과 게임 - 메인 로비")
        #self.master.geometry("900x600") # 창 크기 확대
        self.master.resizable(False, False)
        self.master.configure(bg="#E0F7FA")

        # [수정] 중앙 배치
        center_window(self.master, 900, 600)

        self.friends_data = [] # 친구 목록 (dict list)

        self._create_widgets()
        
        # 친구 목록 요청 (서버 통신)
        self.send_packet("REQ_FRIEND_LIST") 

    def _create_widgets(self):
        # 전체 레이아웃: 좌측(정보/메뉴) + 우측(친구창)
        left_frame = tk.Frame(self.master, bg="#E0F7FA", width=600)
        left_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        right_frame = tk.Frame(self.master, bg="#B3E5FC", width=280, relief=tk.GROOVE, bd=2)
        right_frame.pack(side="right", fill="y", padx=(0, 20), pady=20)
        right_frame.pack_propagate(False) # 크기 고정

        # --- 1. 좌측 상단: 사용자 정보 ---
        info_frame = tk.LabelFrame(left_frame, text=" 내 정보 ", font=("Helvetica", 12, "bold"), bg="white", padx=10, pady=10)
        info_frame.pack(fill="x", pady=(0, 20))

        info_grid = tk.Frame(info_frame, bg="white")
        info_grid.pack(fill="x")

        # 닉네임 / 티어 / MMR / 전적 표시 (user_data 안전 접근)
        nickname = self.user_data.get('nickname', self.user_id)
        tier = self.user_data.get('tier', 'BRONZE')
        mmr = self.user_data.get('mmr', 1000)
        win = self.user_data.get('win', 0)
        loss = self.user_data.get('loss', 0)

        tk.Label(info_grid, text=f"닉네임: {nickname}", font=("Helvetica", 14, "bold"), bg="white").grid(row=0, column=0, sticky="w", padx=10)
        tk.Label(info_grid, text=f"티어: {tier}", font=("Helvetica", 12), bg="white", fg="blue").grid(row=0, column=1, sticky="w", padx=10)
        tk.Label(info_grid, text=f"MMR: {mmr}", font=("Helvetica", 12), bg="white").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        tk.Label(info_grid, text=f"전적: {win}승 {loss}패", font=("Helvetica", 12), bg="white").grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # --- 2. 좌측 하단: 게임 메뉴 ---
        menu_frame = tk.LabelFrame(left_frame, text=" 게임 시작 ", font=("Helvetica", 12, "bold"), bg="#F9F9F9", padx=0, pady=0)
        menu_frame.pack(fill="both", expand=True)
        
        menu_frame.columnconfigure(0, weight=1)
        menu_frame.columnconfigure(1, weight=1)
        menu_frame.columnconfigure(2, weight=1)
        menu_frame.rowconfigure(0, weight=1)

        self._create_menu_button(menu_frame, 0, "⚔️\n1:1 매칭", "랜덤 대전", self.request_random_match, "#4CAF50")
        self._create_menu_button(menu_frame, 1, "🤖\nAI 연습", "난이도 선택", self.start_ai_mode, "#2196F3")
        self._create_menu_button(menu_frame, 2, "📜\n전적", "기록 확인", self.show_record, "#FF9800")

        # --- 3. 우측: 친구 목록 ---
        tk.Label(right_frame, text="👥 친구 목록", font=("Helvetica", 14, "bold"), bg="#B3E5FC").pack(pady=10)
        
        # 친구 추가 버튼
        add_friend_btn = tk.Button(right_frame, text="+ 친구 추가", command=self.popup_add_friend, bg="#81D4FA", relief="flat")
        add_friend_btn.pack(fill="x", padx=10, pady=5)

        # 친구 리스트박스
        self.friends_listbox = tk.Listbox(right_frame, font=("Helvetica", 14), selectmode=tk.SINGLE, bd=0, highlightthickness=0)
        self.friends_listbox.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 우클릭 이벤트 바인딩
        if self.master.tk.call('tk', 'windowingsystem') == 'aqua': # macOS
            self.friends_listbox.bind("<Button-2>", self.show_friend_context_menu)
            self.friends_listbox.bind("<Control-1>", self.show_friend_context_menu)
        else: # Windows / Linux
            self.friends_listbox.bind("<Button-3>", self.show_friend_context_menu)

        # 컨텍스트 메뉴 생성
        self.context_menu = Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="💬 채팅하기", command=self.chat_with_friend)
        self.context_menu.add_command(label="🎮 게임 초대", command=self.invite_friend_to_game)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ 친구 삭제", command=self.delete_friend)


    def _create_menu_button(self, parent, col_idx, text, desc, command, color):
        frame = tk.Frame(parent, bg=color, bd=2, relief="raised")
        frame.grid(row=0, column=col_idx, sticky="nsew", padx=5, pady=5)
        frame.bind("<Button-1>", lambda e: command())
        
        lbl_icon = tk.Label(frame, text=text, font=("Helvetica", 20, "bold"), bg=color, fg="white")
        lbl_icon.pack(expand=True)
        lbl_icon.bind("<Button-1>", lambda e: command())
        
        lbl_desc = tk.Label(frame, text=desc, font=("Helvetica", 12), bg=color, fg="#E0E0E0")
        lbl_desc.pack(side="bottom", pady=10)
        lbl_desc.bind("<Button-1>", lambda e: command())

    # --- 통신 헬퍼 메서드 (net_client 사용) ---
    def send_packet(self, message):
        """서버로 텍스트 메시지 전송"""
        if constants.CLIENT_SOCKET:
            try:
                constants.CLIENT_SOCKET.send((message + "\n").encode('utf-8'))
                print(f"[전송]: {message}")
            except Exception as e:
                messagebox.showerror("오류", f"전송 실패: {e}")
        else:
            messagebox.showerror("오류", "서버와 연결되지 않았습니다.")

    # --- 친구 목록 기능 ---
    def update_friends_list(self, friends_str):
        """서버에서 받은 친구 목록(콤마 구분)으로 리스트박스 갱신"""
        self.friends_listbox.delete(0, tk.END)
        self.friends_data = [] # 초기화
        
        if not friends_str: return
        
        friends = friends_str.split(',')
        for friend_info in friends:
            if not friend_info.strip(): continue
            
            # friend_info가 "닉네임:상태" 형식이면 파싱, 아니면 이름만
            # (현재 서버는 이름만 주므로 이름만 처리)
            name = friend_info.strip()
            is_online = False # 추후 서버에서 상태값도 주면 수정
            
            self.friends_data.append({"name": name, "online": is_online})
            
            status_icon = "🟢" if is_online else "⚫"
            display_text = f"{name} {status_icon}"
            self.friends_listbox.insert(tk.END, display_text)
            if not is_online:
                self.friends_listbox.itemconfig(tk.END, {'fg': 'gray'})

    def popup_add_friend(self):
        nickname = simpledialog.askstring("친구 추가", "추가할 친구의 아이디를 입력하세요:", parent=self.master)
        if nickname:
            self.send_packet(f"REQ_ADD_FRIEND {nickname}")

    def show_friend_context_menu(self, event):
        try:
            index = self.friends_listbox.nearest(event.y)
            self.friends_listbox.selection_clear(0, tk.END)
            self.friends_listbox.selection_set(index)
            self.friends_listbox.activate(index)
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def get_selected_friend_name(self):
        selection = self.friends_listbox.curselection()
        if selection:
            index = selection[0]
            return self.friends_data[index]['name']
        return None

    def chat_with_friend(self):
        friend = self.get_selected_friend_name()
        if friend:
            messagebox.showinfo("채팅", f"'{friend}'님과의 채팅방을 엽니다. (준비 중)")

    def invite_friend_to_game(self):
        friend = self.get_selected_friend_name()
        if friend:
            self.send_packet(f"REQ_INVITE {friend}")
            messagebox.showinfo("초대", f"'{friend}'님에게 게임 초대를 보냈습니다.")

    def delete_friend(self):
        friend = self.get_selected_friend_name()
        if friend:
            if messagebox.askyesno("삭제", f"정말 '{friend}'님을 친구 목록에서 삭제하시겠습니까?"):
                self.send_packet(f"REQ_DEL_FRIEND {friend}")

    # --- 메뉴 기능 ---
    def request_random_match(self):
        self.send_packet(f"REQ_QUEUE {self.user_id}")
        self.matching_dialog = MatchingDialog(self.master, self.cancel_match)
            
    def cancel_match(self):
        # 대기열 취소 요청 (서버 구현 필요)
        self.send_packet(f"REQ_CANCEL_QUEUE {self.user_id}")
        messagebox.showinfo("취소", "매칭 대기를 취소했습니다.")

    def start_ai_mode(self):
        AIDifficultyDialog(self.master, self.start_ai_game)

    def start_ai_game(self, difficulty):
        diff_str = {1: "쉬움", 2: "보통", 3: "어려움"}
        messagebox.showinfo("게임 시작", f"AI ({diff_str[difficulty]}) 모드로 게임을 시작합니다.\n(준비 중)")
        # 여기서 게임 화면으로 전환하는 로직 호출 가능

    def show_record(self):
        # 전적 요청
        self.send_packet(f"REQ_RECORD {self.user_id}")
        # 서버 응답이 오면 net_client에서 open_record_popup 호출
    
    def open_record_popup(self, record_data):
        GameRecordDialog(self.master, record_data)
