import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
from crawler import scroll_and_collect

# 전역 중단 이벤트 객체
stop_event = threading.Event()

def on_mode_change(*args):
    mode = mode_var.get()
    # 입력 필드 표시/숨기기
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
    
    if not blog_id:
        messagebox.showerror("오류", "블로그 ID를 입력하세요.")
        return

    # 파라미터 준비
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

    stop_event.clear()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)

    def run():
        try:
            progress_label.config(text="수집 준비 중...")
            progress_bar["value"] = 0
            
            def progress_callback(current_count):
                progress_label.config(text=f"현재 수집된 글: {current_count}개")
                # 프로그레스바 애니메이션
                progress_bar["value"] = (current_count % 100)

            scroll_and_collect(
                blog_id, 
                mode=mode, 
                target_count=target_count, 
                start_date_str=start_date, 
                end_date_str=end_date, 
                progress_callback=progress_callback, 
                stop_event=stop_event
            )

            if stop_event.is_set():
                progress_label.config(text="중단됨")
                messagebox.showwarning("중단", "작업이 중단되었습니다.")
            else:
                progress_label.config(text="완료됨!")
                progress_bar["value"] = 100
                messagebox.showinfo("완료", "크롤링이 완료되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", str(e))
        finally:
            start_button.config(state=tk.NORMAL)
            stop_button.config(state=tk.DISABLED)

    threading.Thread(target=run, daemon=True).start()

def stop_crawling():
    if messagebox.askyesno("중단", "정말로 중단하시겠습니까?"):
        stop_event.set()
        stop_button.config(state=tk.DISABLED)

# GUI 구성
root = tk.Tk()
root.title("네이버 블로그 고속 크롤러 (v2.0)")
root.geometry("600x480")
root.resizable(False, False)

# 스타일 설정
style = ttk.Style()
style.configure("TLabel", font=("Helvetica", 10))

# 상단: 블로그 ID
tk.Label(root, text="블로그 ID:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
blog_id_entry = tk.Entry(root, font=("Helvetica", 10))
blog_id_entry.insert(0, "sniperriflesr2")
blog_id_entry.grid(row=0, column=1, padx=10, pady=10, sticky="we")

# 수집 모드 선택
tk.Label(root, text="수집 모드:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
mode_var = tk.StringVar(value="all")
mode_var.trace_add("write", on_mode_change)

mode_frame = tk.Frame(root)
mode_frame.grid(row=1, column=1, sticky="w")
tk.Radiobutton(mode_frame, text="전체", variable=mode_var, value="all").pack(side=tk.LEFT)
tk.Radiobutton(mode_frame, text="개수 지정", variable=mode_var, value="count").pack(side=tk.LEFT)
tk.Radiobutton(mode_frame, text="날짜 범위", variable=mode_var, value="date").pack(side=tk.LEFT)

# 조건 입력 프레임 (개수)
count_frame = tk.Frame(root)
tk.Label(count_frame, text="목표 게시글 수:").pack(side=tk.LEFT)
count_entry = tk.Entry(count_frame, width=10)
count_entry.insert(0, "50")
count_entry.pack(side=tk.LEFT, padx=5)
count_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
count_frame.grid_remove()

# 조건 입력 프레임 (날짜)
date_frame = tk.Frame(root)
tk.Label(date_frame, text="기간:").pack(side=tk.LEFT)
start_date_entry = tk.Entry(date_frame, width=12)
start_date_entry.insert(0, "2026-02-01")
start_date_entry.pack(side=tk.LEFT, padx=2)
tk.Label(date_frame, text="~").pack(side=tk.LEFT)
end_date_entry = tk.Entry(date_frame, width=12)
end_date_entry.insert(0, "2026-03-31")
end_date_entry.pack(side=tk.LEFT, padx=2)
tk.Label(date_frame, text="(YYYY-MM-DD)", font=("Helvetica", 8), fg="gray").pack(side=tk.LEFT)
date_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
date_frame.grid_remove()

# 버튼 프레임
btn_frame = tk.Frame(root)
btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
start_button = tk.Button(btn_frame, text="크롤링 시작", command=start_crawling, width=15, bg="#e1f5fe")
start_button.pack(side=tk.LEFT, padx=5)
stop_button = tk.Button(btn_frame, text="크롤링 중단", command=stop_crawling, width=15, bg="#ffebee", state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, padx=5)

# 설명란
description_text = tk.Text(root, wrap="word", height=8, bg="#f9f9f9")
description_text.tag_configure("info", foreground="#2196f3")
description_text.insert(tk.END, "💡 사용 팁:\n", "info")
description_text.insert(tk.END, "- '전체': 블로그의 모든 글을 가져옵니다.\n")
description_text.insert(tk.END, "- '개수 지정': 입력한 숫자만큼 최신글부터 가져옵니다.\n")
description_text.insert(tk.END, "- '날짜 범위': 지정한 기간 내에 작성된 글만 가져옵니다.\n\n")
description_text.insert(tk.END, "⚠️ 날짜는 2026-05-05 형식으로 정확히 입력해주세요.")
description_text.config(state=tk.DISABLED)
description_text.grid(row=4, column=0, columnspan=2, padx=15, pady=5, sticky="nsew")

# 진행 상태
progress_label = tk.Label(root, text="준비 완료")
progress_label.grid(row=5, column=0, columnspan=2, pady=(10, 0))
progress_bar = ttk.Progressbar(root, orient="horizontal", length=540, mode="determinate")
progress_bar.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

root.mainloop()
