from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import deque
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timedelta


# 로깅 설정
def setup_logger(log_dir="logs", log_file="crawl.log"):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("scroll_logger")
    logger.setLevel(logging.DEBUG)

    # 로그 포맷 (시간 포함)
    formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    # 터미널 출력 핸들러
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 파일 출력 핸들러 (최대 5개 파일, 각 파일 1MB)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, log_file), maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def convert_relative_time(text):
    if "시간 전" in text:
        try:
            hours = int(text.replace("시간 전", "").strip())
            date = datetime.now() - timedelta(hours=hours)
            return date.strftime("%Y. %m. %d")
        except:
            pass
    return text 

def scroll_and_collect(blog_id, max_scroll=0, wait_timeout=100, progress_callback=None):
    logger = setup_logger()
    url = f"https://m.blog.naver.com/PostList.naver?blogId={blog_id}&tab=1"

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1080x800")
    options.add_argument("--headless")  # 테스트 시 비활성화 가능

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.card__reUkU"))
    )

    posts = {}
    seen_urls = deque(maxlen=96)
    scroll_count = 0

    logger.info(f"블로그 ID: {blog_id}")
    logger.info(f"크롤링 시작 URL: {url}")
    logger.info(f"최대 스크롤 횟수: {max_scroll if max_scroll > 0 else '제한 없음'}")
    logger.info("크롤링 시작...")
    

    while True:
        scroll_start_time = time.time()
        cards = driver.find_elements(By.CSS_SELECTOR, "div.card__reUkU")
        curr_card_count = len(cards)
        logger.info(f"스크롤 {scroll_count + 1}회")

        # ✅ 현재 카드에서 정보 수집
        new_cards_added = 0
        for card in cards:
            try:
                link_el = card.find_element(By.CSS_SELECTOR, "a.link__Awlz5")
                url = link_el.get_attribute("href")

                url = url.replace("://m.blog.naver.com", "://blog.naver.com")

                if url in seen_urls:
                    continue

                title_el = card.find_element(By.CSS_SELECTOR, "strong.title__UUn4H span")
                like_el = card.find_element(By.CSS_SELECTOR, "em.u_cnt._count")
                time_el = card.find_element(By.CSS_SELECTOR, "span.time__mHZOn")

                title = title_el.text.strip()
                likes_text = like_el.text.strip()
                time_text = time_el.text.strip() if time_el else "N/A"

                likes = int(likes_text) if likes_text.isdigit() else 0

                if scroll_count < 5:
                    date_str = convert_relative_time(time_text)
                else:
                    date_str = time_text

                posts[url] = {
                    "title": title,
                    "url": url,
                    "likes": likes,
                    "time": date_str
                }
                seen_urls.append(url)
                new_cards_added += 1
            except:
                continue

        logger.info(f"→ 이번 스크롤에서 새로 수집된 카드 수: {new_cards_added}")
        if new_cards_added != 24:
            logger.info("생성된 카드 수가 예상과 다릅니다. 오류 가능성 확인 필요")

        if max_scroll > 0 and scroll_count >= max_scroll:
            logger.info("지정된 최대 스크롤 수 도달")
            break

        

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # ✅ 중복 없이 카드 수 증가 확인
        prev_card_count = curr_card_count

        try:
            WebDriverWait(driver, wait_timeout).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.card__reUkU")) > prev_card_count
            )
        except:
            logger.info("대기 시간 내에 새 글이 로딩되지 않았습니다.")
            break

        
        scroll_count += 1
        if progress_callback:
            progress_callback(scroll_count)

        # ✅ 스크롤 이후 불필요한 카드 제거 (스크롤 3회 이후)
        if scroll_count > 3:
            removable_cards = driver.find_elements(By.CSS_SELECTOR, "div.card__reUkU")[:24]
            for card in removable_cards:
                try:
                    driver.execute_script("arguments[0].remove();", card)
                except:
                    continue


        # ✅ 디버깅용 현재 카드 수
        current_count = len(driver.find_elements(By.CSS_SELECTOR, "div.card__reUkU"))
        logger.info(f"스크롤 직후 현재 카드 수: {current_count}")

        # ✅ 스크롤 시간 체크
        elapsed_time = time.time() - scroll_start_time
        logger.info(f"스크롤 {scroll_count}회 소요 시간: {elapsed_time:.2f}초")

    driver.quit()

    # ✅ 정렬 + index 부여
    sorted_posts = sorted(posts.values(), key=lambda x: -x["likes"])
    for i, post in enumerate(sorted_posts, start=1):
        post["index"] = i

    with open(f"{blog_id}_posts_scroll.json", "w", encoding="utf-8") as f:
        json.dump(sorted_posts, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✔ 최종 수집된 글 수: {len(sorted_posts)}개")
    logger.info(f"\n 최종 수집되었어야 하는 글 수: {24+scroll_count*24}개")
    return sorted_posts

# 실행 예시
if __name__ == "__main__":
    scroll_and_collect("sniperriflesr2", max_scroll=3)
    

