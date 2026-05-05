import requests
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import random

# 로깅 설정
def setup_logger(log_dir="logs", log_file="crawl.log"):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("api_logger")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, log_file), maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

def parse_date(date_str):
    """'YYYY-MM-DD' 문자열을 datetime 객체로 변환"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None

def finalize_and_save(posts, blog_id, logger):
    """결과 정렬 및 파일 저장 (스크립트 위치 기준)"""
    # 좋아요 순 정렬
    sorted_posts = sorted(posts, key=lambda x: -x["likes"])
    for i, post in enumerate(sorted_posts, start=1):
        post["index"] = i

    # 실행 위치에 상관없이 스크립트 파일이 있는 폴더에 저장
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, f"{blog_id}_posts_scroll.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sorted_posts, f, ensure_ascii=False, indent=2)

    logger.info(f"✨ 완료: 총 {len(sorted_posts)}개 수집됨")
    logger.info(f"📍 저장 위치: {file_path}")
    return sorted_posts

def scroll_and_collect(blog_id, mode="all", target_count=0, start_date_str=None, end_date_str=None, progress_callback=None, stop_event=None):
    """
    최종 안정화된 고속 순차 수집 로직
    """
    logger = setup_logger()
    logger.info(f"🚀 크롤링 시작 (모드: {mode}, ID: {blog_id})")
    
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": f"https://m.blog.naver.com/PostList.naver?blogId={blog_id}",
        "Accept": "application/json, text/plain, */*"
    }
    
    posts = []
    page = 1
    item_count_per_page = 24
    
    while True:
        if stop_event and stop_event.is_set():
            logger.info("🛑 사용자 요청으로 중단됨")
            break

        # API 호출
        api_url = f"https://m.blog.naver.com/api/blogs/{blog_id}/post-list?categoryNo=0&itemCount={item_count_per_page}&page={page}"
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"❌ 수집 중단: 서버 응답 실패 (상태 코드: {response.status_code})")
                break
            
            data = response.json()
            items = data.get("result", {}).get("items", [])
            if not items: 
                logger.info("🏁 마지막 페이지까지 수집 완료!")
                break
            
            # 날짜 정보 로깅 (현재 페이지의 범위)
            current_first_date = datetime.fromtimestamp(items[0].get("addDate") / 1000.0).strftime("%Y-%m-%d")
            logger.info(f"📄 {page}페이지 분석 중... (현재 날짜: {current_first_date})")

            for item in items:
                add_date_ts = item.get("addDate")
                dt = datetime.fromtimestamp(add_date_ts / 1000.0)
                date_only = datetime(dt.year, dt.month, dt.day)

                if mode == "date":
                    if end_date and date_only > end_date:
                        continue
                    if start_date and date_only < start_date:
                        logger.info(f"🏁 시작일({start_date_str}) 이전 글 도달. 수집을 종료합니다.")
                        return finalize_and_save(posts, blog_id, logger)

                # 데이터 추출
                post_data = {
                    "title": item.get("titleWithInspectMessage"),
                    "url": f"https://blog.naver.com/{blog_id}/{item.get('logNo')}",
                    "likes": item.get("sympathyCnt", 0),
                    "comments": item.get("commentCnt", 0),
                    "time": dt.strftime("%Y. %m. %d"),
                    "timestamp": add_date_ts
                }
                posts.append(post_data)

                if mode == "count" and len(posts) >= target_count:
                    logger.info(f"✅ 목표 개수({target_count}개) 달성!")
                    return finalize_and_save(posts, blog_id, logger)

            if progress_callback: progress_callback(len(posts))
            page += 1
            # 속도와 안전의 균형 (0.1~0.3초)
            time.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            logger.error(f"⚠️ 수집 중 예기치 못한 오류: {e}")
            break

    return finalize_and_save(posts, blog_id, logger)
