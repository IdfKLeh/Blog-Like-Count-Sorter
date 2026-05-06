import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
import os
import logging
from crawler import scroll_and_collect

# GUI 로그 핸들러 클래스
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.see(tk.END) # 스크롤을 항상 아래로
            self.text_widget.config(state=tk.DISABLED)
        self.text_widget.after(0, append) # 쓰레드 세이프하게 UI 업데이트

# 전역 중단 이벤트 객체
stop_event = threading.Event()

def on_mode_change(*args):
    mode = mode_var.get()
    if mode == "count":
        count_frame.grid()
        date_frame.grid_remove()
    elif mode == "date":
        count_frame.grid_remove()
        date_frame.grid()
    else:
        count_frame.grid_remove()
        date_frame.grid_remove()

def start_crawling():
    blog_id = blog_id_entry.get()
    mode = mode_var.get()
    sort_by = sort_var.get()
    
    if not blog_id:
        messagebox.showerror("오류", "블로그 ID를 입력하세요.")
        return

    target_count = 0
    start_date = None
    end_date = None

    if mode == "count":
        try:
            target_count = int(count_entry.get())
            if target_count <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("오류", "올바른 게시글 수를 입력하세요.")
            return
    elif mode == "date":
        start_date = start_date_entry.get()
        end_date = end_date_entry.get()
        if not start_date or not end_date:
            messagebox.showerror("오류", "시작일과 종료일을 모두 입력하세요.")
            return

    # 로그 영역 초기화
    log_text.config(state=tk.NORMAL)
    log_text.delete(1.0, tk.END)
    log_text.config(state=tk.DISABLED)

    stop_event.clear()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)

    def run():
        try:
            progress_label.config(text="분석 준비 중...")
            progress_bar["value"] = 0
            
            def progress_callback(current_count):
                progress_label.config(text=f"현재 {current_count}개 글 분석 완료")
                progress_bar["value"] = (current_count % 100)

            scroll_and_collect(
                blog_id, 
                mode=mode, 
                target_count=target_count, 
                start_date_str=start_date, 
                end_date_str=end_date, 
                sort_by=sort_by,
                progress_callback=progress_callback, 
                stop_event=stop_event
            )

            if stop_event.is_set():
                progress_label.config(text="사용자 중단")
            else:
                progress_label.config(text="분석 완료!")
                progress_bar["value"] = 100
                messagebox.showinfo("완료", "분석이 성공적으로 완료되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", str(e))
        finally:
            start_button.config(state=tk.NORMAL)
            stop_button.config(state=tk.DISABLED)

    threading.Thread(target=run, daemon=True).start()

def stop_crawling():
    if messagebox.askyesno("중단", "분석을 중단하시겠습니까?"):
        stop_event.set()
        stop_button.config(state=tk.DISABLED)

# GUI 구성
root = tk.Tk()
root.title("네이버 블로그 고속 분석기 (Live Console)")
root.geometry("600x550")
root.resizable(False, False)

# 상단 입력부
tk.Label(root, text="블로그 ID:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
blog_id_entry = tk.Entry(root)
blog_id_entry.insert(0, "sniperriflesr2")
blog_id_entry.grid(row=0, column=1, padx=10, pady=10, sticky="we")

tk.Label(root, text="분석 모드:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
mode_var = tk.StringVar(value="all")
mode_var.trace_add("write", on_mode_change)
mode_frame = tk.Frame(root)
mode_frame.grid(row=1, column=1, sticky="w")
tk.Radiobutton(mode_frame, text="전체", variable=mode_var, value="all").pack(side=tk.LEFT)
tk.Radiobutton(mode_frame, text="개수", variable=mode_var, value="count").pack(side=tk.LEFT)
tk.Radiobutton(mode_frame, text="기간", variable=mode_var, value="date").pack(side=tk.LEFT)

tk.Label(root, text="정렬 기준:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
sort_var = tk.StringVar(value="likes")
sort_frame = tk.Frame(root)
sort_frame.grid(row=2, column=1, sticky="w")
tk.Radiobutton(sort_frame, text="좋아요", variable=sort_var, value="likes").pack(side=tk.LEFT)
tk.Radiobutton(sort_frame, text="댓글", variable=sort_var, value="comments").pack(side=tk.LEFT)

# 가변 입력 프레임
count_frame = tk.Frame(root)
tk.Label(count_frame, text="목표 개수:").pack(side=tk.LEFT)
count_entry = tk.Entry(count_frame, width=10); count_entry.insert(0, "50"); count_entry.pack(side=tk.LEFT, padx=5)
count_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
count_frame.grid_remove()

date_frame = tk.Frame(root)
tk.Label(date_frame, text="기간:").pack(side=tk.LEFT)
start_date_entry = tk.Entry(date_frame, width=12); start_date_entry.insert(0, "2026-01-01"); start_date_entry.pack(side=tk.LEFT, padx=2)
tk.Label(date_frame, text="~").pack(side=tk.LEFT)
end_date_entry = tk.Entry(date_frame, width=12); end_date_entry.insert(0, "2026-02-28"); end_date_entry.pack(side=tk.LEFT, padx=2)
date_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
date_frame.grid_remove()

# 실시간 로그 콘솔 (기존 사용팁 제거)
tk.Label(root, text="실시간 분석 로그:", font=("Helvetica", 9, "bold")).grid(row=4, column=0, padx=10, pady=(10,0), sticky="w")
log_text = tk.Text(root, wrap="word", height=12, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
log_text.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
log_text.config(state=tk.DISABLED)

# 로그 연동
logger = logging.getLogger("api_logger")
text_handler = TextHandler(log_text)
text_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S"))
logger.addHandler(text_handler)

# 하단 버튼 및 진행바
btn_frame = tk.Frame(root)
btn_frame.grid(row=6, column=0, columnspan=2, pady=10)
start_button = tk.Button(btn_frame, text="분석 시작", command=start_crawling, width=12, bg="#e1f5fe")
start_button.pack(side=tk.LEFT, padx=5)
stop_button = tk.Button(btn_frame, text="중단", command=stop_crawling, width=12, bg="#ffebee", state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, padx=5)

progress_label = tk.Label(root, text="준비 완료")
progress_label.grid(row=7, column=0, columnspan=2)
progress_bar = ttk.Progressbar(root, orient="horizontal", length=560, mode="determinate")
progress_bar.grid(row=8, column=0, columnspan=2, padx=10, pady=(5, 15))

root.mainloop()
