import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
from crawler import scroll_and_collect

def start_crawling():
    blog_id = blog_id_entry.get()
    scroll_limit = scroll_entry.get()

    if not blog_id:
        messagebox.showerror("오류", "블로그 ID를 입력하세요.")
        return

    try:
        scroll_limit = int(scroll_limit)
    except ValueError:
        messagebox.showerror("오류", "스크롤 횟수는 숫자로 입력해야 합니다.")
        return

    if scroll_limit <= 0:
        messagebox.showerror("오류", "진행 표시를 위해 스크롤 횟수를 1 이상으로 설정해주세요.")
        return

    # 실행은 별도 쓰레드에서 수행 (GUI 멈춤 방지)
    def run():
        try:
            progress_label.config(text="진행 중: 0 / {}".format(scroll_limit))
            progress_bar["value"] = 0
            progress_bar["maximum"] = scroll_limit

            def progress_callback(current_scroll):
                progress_label.config(text=f"진행 중: {current_scroll} / {scroll_limit}")
                progress_bar["value"] = current_scroll

            scroll_and_collect(blog_id, max_scroll=scroll_limit, progress_callback=progress_callback)

            progress_label.config(text="완료됨!")
            progress_bar["value"] = scroll_limit
            messagebox.showinfo("완료", "크롤링이 완료되었습니다.")
            root.quit()
        except Exception as e:
            messagebox.showerror("오류", str(e))

    threading.Thread(target=run).start()


# GUI 구성
root = tk.Tk()
root.title("네이버 블로그 크롤러")
root.geometry("600x360")
root.resizable(False, False)

root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(3, weight=1)

tk.Label(root, text="블로그 ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
blog_id_entry = tk.Entry(root)
blog_id_entry.insert(0, "sniperriflesr2")
blog_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")

tk.Label(root, text="최대 스크롤 횟수 (0 = 제한 없음):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
scroll_entry = tk.Entry(root)
scroll_entry.insert(0, "10")
scroll_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")

start_button = tk.Button(root, text="크롤링 시작", command=start_crawling)
start_button.grid(row=2, column=0, columnspan=2, pady=10)

description_text = tk.Text(root, wrap="word", height=7)
description_text.tag_configure("warning", foreground="red")
description_text.insert(tk.END, "블로그 ID와 스크롤 횟수를 입력 후 '크롤링 시작' 버튼을 눌러주세요.\n\n0으로 입력하면 제한 없이 스크롤합니다.\n\n")
description_text.insert(tk.END,"주의 : 스크롤 횟수의 경우 n*24+24개의 포스트 수가 크롤링 됩니다.(Ex. 스크롤 횟수 5 입력시 5*24+24 = 144개의 포스트 수 크롤링)\n\n과하게 큰 포스팅 수를 크롤링 할땐 걸리는 시간이 기하급수적으로 증가합니다!(Ex. 스크롤 횟수 5일 때 30초 소요, 50일 때 10분 소요, 500일 때 180분 소요 등..)\n\n","warning")
description_text.insert(tk.END,"완료되면 결과는 현재 디렉토리에 'blogID_posts_scroll.json' 파일로 저장됩니다.")
description_text.config(state=tk.DISABLED)
description_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

# ✅ 진행 상태 표시 라벨 + 프로그레스바
progress_label = tk.Label(root, text="진행 대기 중")
progress_label.grid(row=4, column=0, columnspan=2, pady=(0, 5))

progress_bar = ttk.Progressbar(root, orient="horizontal", length=500, mode="determinate")
progress_bar.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

root.mainloop()
