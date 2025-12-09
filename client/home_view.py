# client/home_view.py

import tkinter as tk
from tkinter import messagebox
from . import constants
from . import net_client

class MatchingDialog(tk.Toplevel):
    def __init__(self, parent, cancel_callback):
        super().__init__(parent)
        self.cancel_callback = cancel_callback
        self.title("매칭 중...")
        self.geometry("300x150")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="white")
        
        tk.Label(self, text="🔍 상대를 찾는 중입니다...", font=("Arial", 12, "bold"), bg="white", pady=30).pack()
        tk.Button(self, text="취소", command=self.on_cancel, bg="#FFCDD2", width=10).pack(pady=10)

    def on_cancel(self):
        self.cancel_callback()
        self.destroy()

class HomeApp:
    def __init__(self, master, user_id, user_data):
        self.master = master
        self.user_id = user_id
        self.user_data = user_data
        
        # [핵심 추가] 현재 홈 화면 인스턴스를 전역 변수에 등록 (외부 접근용)
        constants.CURRENT_HOME_INSTANCE = self
        
        self.master.title("Net-Mushroom - 로비")
        self.master.resizable(False, False)
        self.master.configure(bg="#E0F7FA")
        
        self._create_widgets()

    # [핵심 추가] 외부(net_client)에서 호출하는 UI 갱신 함수
    def update_user_info(self, new_mmr, new_tier):
        # 내부 데이터 업데이트
        self.user_data['mmr'] = new_mmr
        # UI 라벨 즉시 변경
        if hasattr(self, 'mmr_label'):
            self.mmr_label.config(text=f"점수 (MMR): {new_mmr} ({new_tier})")

    def _create_widgets(self):
        main_frame = tk.Frame(self.master, bg="#E0F7FA", padx=40, pady=40)
        main_frame.pack(fill="both", expand=True)

        # 1. 정보 프레임
        info_frame = tk.LabelFrame(main_frame, text=" 내 정보 ", font=("Arial", 14, "bold"), bg="white", padx=20, pady=20)
        info_frame.pack(fill="x", pady=(0, 30))

        nick = self.user_data.get('nickname', self.user_id)
        mmr = self.user_data.get('mmr', 0)

        tk.Label(info_frame, text=f"닉네임: {nick}", font=("Arial", 16, "bold"), bg="white").pack(anchor="w", pady=5)
        
        # [수정] 나중에 텍스트를 바꾸기 위해 self 변수에 저장
        self.mmr_label = tk.Label(info_frame, text=f"점수 (MMR): {mmr}", font=("Arial", 14), bg="white", fg="#00695C")
        self.mmr_label.pack(anchor="w", pady=5)

        # 2. 메뉴 프레임
        menu_frame = tk.Frame(main_frame, bg="#E0F7FA")
        menu_frame.pack(fill="both", expand=True)

        self._create_btn(menu_frame, "⚔️ 1:1 대전 시작", "비슷한 실력의 상대와 매칭", self.request_match, "#4CAF50")
        tk.Label(menu_frame, bg="#E0F7FA").pack(pady=5)
        self._create_btn(menu_frame, "📜 전적 확인", "나의 최근 게임 기록 확인", self.show_record, "#FF9800")

    def _create_btn(self, parent, text, desc, cmd, color):
        frame = tk.Frame(parent, bg=color, bd=2, relief="raised")
        frame.pack(fill="x", ipadx=10, ipady=5)
        frame.bind("<Button-1>", lambda e: cmd())
        
        l1 = tk.Label(frame, text=text, font=("Arial", 14, "bold"), bg=color, fg="white")
        l1.pack(pady=(5, 2))
        l1.bind("<Button-1>", lambda e: cmd())
        
        l2 = tk.Label(frame, text=desc, font=("Arial", 10), bg=color, fg="#E0E0E0")
        l2.pack(pady=(0, 5))
        l2.bind("<Button-1>", lambda e: cmd())

    def request_match(self):
        if constants.CLIENT_SOCKET:
            try:
                constants.CLIENT_SOCKET.send("REQ_QUEUE\n".encode('utf-8'))
                self.matching_dialog = MatchingDialog(self.master, self.cancel_match)
            except:
                messagebox.showerror("오류", "서버 연결 끊김?")

    def cancel_match(self):
        net_client.send_cancel_queue_request()
        messagebox.showinfo("취소", "매칭을 취소했습니다.")

    def show_record(self):
        if constants.CLIENT_SOCKET:
            net_client.send_history_request()
        else:
            messagebox.showerror("오류", "서버 미연결")
