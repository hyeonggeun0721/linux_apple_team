import tkinter as tk
from tkinter import ttk

class RecordDialog(tk.Toplevel):
    def __init__(self, parent, history_data):
        super().__init__(parent)
        self.title("나의 전적 기록")
        self.geometry("600x400")
        self.resizable(False, False)
        self.configure(bg="white")
        
        tk.Label(self, text="🏆 경기 기록 (최근 10게임) 🏆", font=("Arial", 16, "bold"), bg="white", pady=15).pack()

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        style.configure("Treeview", font=("Arial", 10), rowheight=25)

        columns = ("date", "result", "opponent", "score")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        
        self.tree.heading("date", text="날짜")
        self.tree.column("date", width=180, anchor="center")
        self.tree.heading("result", text="결과")
        self.tree.column("result", width=80, anchor="center")
        self.tree.heading("opponent", text="상대방")
        self.tree.column("opponent", width=80, anchor="center")
        self.tree.heading("score", text="점수 (나:상대)")
        self.tree.column("score", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=20, pady=5)

        if not history_data:
            self.tree.insert("", "end", values=("기록 없음", "-", "-", "-"))
        else:
            for record in history_data:
                try:
                    if not record.strip(): continue
                    date, res, opp, score = record.split("|")
                    self.tree.insert("", "end", values=(date, res, opp, score))
                except Exception as e:
                    print(f"전적 파싱 에러: {e}")
                    continue

        tk.Button(self, text="닫기", command=self.destroy, bg="#ddd", width=10, relief="flat", pady=5).pack(pady=15)
