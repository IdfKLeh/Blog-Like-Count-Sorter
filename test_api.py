import requests
import re

user_id = "sniperriflesr2"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": f"https://m.blog.naver.com/{user_id}",
}

def get_blog_no():
    # 블로그 모바일 메인 페이지에서 blogNo(숫자 ID) 추출
    url = f"https://m.blog.naver.com/{user_id}"
    res = requests.get(url, headers=headers)
    match = re.search(r'"blogNo"\s*:\s*(\d+)', res.text)
    if match:
        return match.group(1)
    return None

def check_page_with_no(blog_no, page_num):
    # 진짜 작동하는 모바일 API (숫자 ID 필요)
    url = f"https://m.blog.naver.com/api/blogs/{blog_no}/post-list?itemCount=24&page={page_num}"
    print(f"Requesting: {url}")
    res = requests.get(url, headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        items = data.get("result", {}).get("items", [])
        if items:
            print(f"✅ Success! Page {page_num} first post date: {items[0].get('addDate')}")
            return True
    return False

blog_no = get_blog_no()
print(f"Found BlogNo: {blog_no}")

if blog_no:
    check_page_with_no(blog_no, 1)
    check_page_with_no(blog_no, 50)
else:
    print("❌ Failed to find BlogNo.")
