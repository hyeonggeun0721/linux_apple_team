import tkinter as tk
from tkinter import font
from . import net_client

class ChatPanel(tk.Frame):
    def __init__(self, parent, width, height, bg_color="#f5f5f5"):
        super().__init__(parent, width=width, height=height, bg=bg_color)
        self.pack_propagate(False) # 크기 고정

        tk.Label(self, text="실시간 채팅", bg=bg_color, font=("Arial", 10, "bold"), fg="#555").pack(side=tk.TOP, pady=(5, 0))

        log_frame = tk.Frame(self, bg=bg_color)
        log_frame.pack(side=tk.TOP, fill="both", expand=True, padx=5, pady=5)

        self.log_area = tk.Text(log_frame, state=tk.DISABLED, font=("Arial", 9), 
                                bg="white", relief="flat", padx=5, pady=5)
        self.scrollbar = tk.Scrollbar(log_frame, command=self.log_area.yview)
        self.log_area.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill="y")
        self.log_area.pack(side=tk.LEFT, fill="both", expand=True)

        self.log_area.tag_config("me", foreground="#1E88E5", font=("Arial", 9, "bold"))
        self.log_area.tag_config("system", foreground="#43A047", justify="center")
        self.log_area.tag_config("other", foreground="#424242")

        input_frame = tk.Frame(self, bg=bg_color)
        input_frame.pack(side=tk.BOTTOM, fill="x", padx=5, pady=(0, 10))

        self.entry = tk.Entry(input_frame, font=("Arial", 10), relief="flat", bd=1)
        self.entry.pack(side=tk.LEFT, fill="x", expand=True, ipady=3)
        self.entry.bind("<Return>", self.send_message)

        send_btn = tk.Button(input_frame, text="전송", command=self.send_message, 
                             bg="#5C6BC0", fg="white", relief="flat", font=("Arial", 9), width=6)
        send_btn.pack(side=tk.LEFT, padx=(5, 0))

    def add_message(self, sender, msg):
        self.log_area.config(state=tk.NORMAL)
        tag = "other"
        display_text = f"[{sender}] {msg}\n"
        
        if sender == "나": tag = "me"
        elif sender == "시스템" or sender == "알림":
            tag = "system"
            display_text = f"- {msg} -\n"
        
        self.log_area.insert(tk.END, display_text, tag)
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def send_message(self, event=None):
        msg = self.entry.get().strip()
        if not msg: return
        net_client.send_chat_request(msg)
        self.entry.delete(0, tk.END)
