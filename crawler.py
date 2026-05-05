"""
================================================================================
[ 네이버 블로그 포스트 분석기 개발 히스토리 및 기술 결정 사유 ]
================================================================================

1. 실험 1: Selenium 기반 크롤링 (실패/비효율)
   - 방법: 헤드리스 브라우저를 띄워 실제 스크롤을 내리며 DOM 요소 파싱.
   - 결과: 속도가 매우 느리고 네이버의 잦은 UI 변경에 취약함. (기존 방식의 한계)

2. 실험 2: viewDate 파라미터를 활용한 날짜 점프 (실패)
   - 방법: API 호출 시 &viewDate=YYYYMMDD를 넣어 특정 날짜로 직접 이동 시도.
   - 결과: 네이버 최신 API에서 해당 파라미터를 무시함. 무조건 1페이지 데이터만 반환.

3. 실험 3: 이진 탐색(Binary Search) 및 갤로핑 탐색(Leap) (실패)
   - 방법: 전체 글 개수를 파악한 뒤, 중간 페이지(ex. 500페이지)를 직접 호출하여 날짜 탐색.
   - 결과: 네이버 API는 '순차적 접근'만 허용함을 확인. 이전 페이지를 거치지 않은 
          비순차적 페이지 호출 시 404 에러 혹은 빈 데이터를 반환함.

4. 최종 해결책: 초고속 순차 JSON 스캔 (현재 방식)
   - 방법: 브라우저 없이 네이버 내부 API(JSON)를 직접 호출하여 1페이지부터 순차 분석.
   - 장점: 렌더링 과정이 없어 1페이지 처리에 0.1초 수준의 극강의 속도 발휘. 
          순차적임에도 불구하고 수천 개의 포스트를 수십 초 내에 돌파 가능.
          날짜 범위를 벗어나는 즉시 종료하여 효율성 극대화.

5. 추가 기능 (v3.0)
   - 메타데이터 저장: JSON 상단에 수집 시점 및 정렬 기준 자동 기록.
   - 다중 정렬: 좋아요(마음) 수 뿐만 아니라 댓글 수 기준으로도 정렬 가능.
================================================================================
"""

import requests
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime
import random

def get_base_dir():
    """EXE로 빌드되었을 때와 스크립트로 실행될 때의 실제 기준 경로를 반환합니다."""
    if getattr(sys, 'frozen', False):
        # EXE 실행 시: EXE 파일이 있는 폴더
        return os.path.dirname(os.path.abspath(sys.executable))
    # 스크립트 실행 시: crawler.py가 있는 폴더
    return os.path.dirname(os.path.abspath(__file__))

# 로깅 설정
def setup_logger(log_dir_name="logs", log_file="crawl.log"):
    base_dir = get_base_dir()
    log_dir = os.path.join(base_dir, log_dir_name)
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
    """다양한 형식의 날짜 문자열을 datetime 객체로 변환"""
    if not date_str: return None
    # 기호 정리
    date_str = date_str.replace(".", "-").replace(" ", "").replace("/", "-")
    
    formats = ["%Y-%m-%d", "%Y%m%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return None

def finalize_and_save(posts, blog_id, logger, sort_by="likes"):
    """결과 정렬 및 'results' 폴더에 파일 저장"""
    if not posts:
        logger.warning("⚠️ 수집된 데이터가 없어 파일을 저장하지 않습니다.")
        return []

    if sort_by == "comments":
        sorted_posts = sorted(posts, key=lambda x: -x["comments"])
        sort_label = "댓글 수"
    else:
        sorted_posts = sorted(posts, key=lambda x: -x["likes"])
        sort_label = "좋아요 수"

    for i, post in enumerate(sorted_posts, start=1):
        post["index"] = i

    base_dir = get_base_dir()
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    file_path = os.path.join(results_dir, f"{blog_id}_posts_scroll.json")

    result_data = {
        "metadata": {
            "blogId": blog_id,
            "collectedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "totalCount": len(sorted_posts),
            "sortedBy": sort_label
        },
        "posts": sorted_posts
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✨ 완료: 총 {len(sorted_posts)}개 수집됨 ({sort_label} 정렬)")
    logger.info(f"📍 저장 위치: {file_path}")
    return sorted_posts

def scroll_and_collect(blog_id, mode="all", target_count=0, start_date_str=None, end_date_str=None, sort_by="likes", progress_callback=None, stop_event=None):
    """
    최종 안정화된 고속 순차 수집 로직
    """
    logger = setup_logger()
    
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    # 날짜 모드 예외 처리
    if mode == "date":
        if not start_date or not end_date:
            logger.error(f"❌ 날짜 형식이 잘못되었습니다. (입력: {start_date_str} ~ {end_date_str})")
            return []
        if start_date > end_date:
            logger.error("❌ 시작일이 종료일보다 늦을 수 없습니다.")
            return []

    logger.info(f"🚀 분석 시작 (ID: {blog_id}, 모드: {mode}, 정렬기준: {sort_by})")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": f"https://m.blog.naver.com/{blog_id}",
        "Accept": "application/json, text/plain, */*"
    }
    
    posts = []
    page = 1
    item_count_per_page = 24
    
    while True:
        if stop_event and stop_event.is_set():
            logger.info("🛑 사용자가 중단 버튼을 클릭했습니다.")
            break

        api_url = f"https://m.blog.naver.com/api/blogs/{blog_id}/post-list?categoryNo=0&itemCount={item_count_per_page}&page={page}"
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"❌ 서버 응답 에러 (상태코드: {response.status_code})")
                break
            
            data = response.json()
            items = data.get("result", {}).get("items", [])
            
            if not items: 
                logger.info("🏁 더 이상 분석할 포스트가 없습니다.")
                break
            
            # 날짜 로그 표시
            current_first_date = datetime.fromtimestamp(items[0].get("addDate") / 1000.0).strftime("%Y-%m-%d")
            logger.info(f"📄 {page}페이지 분석 중... (날짜: {current_first_date})")

            for item in items:
                add_date_ts = item.get("addDate")
                dt = datetime.fromtimestamp(add_date_ts / 1000.0)
                date_only = datetime(dt.year, dt.month, dt.day)

                if mode == "date":
                    # ✅ 범위 밖의 미래 글은 수집하지 않음
                    if date_only > end_date:
                        continue
                    # ✅ 시작일보다 과거 글이 나오면 전체 종료
                    if date_only < start_date:
                        logger.info(f"🏁 시작일({start_date.strftime('%Y-%m-%d')}) 이전 글 도달. 분석을 종료합니다.")
                        return finalize_and_save(posts, blog_id, logger, sort_by=sort_by)

                # ✅ 조건 통과 시에만 추가
                posts.append({
                    "title": item.get("titleWithInspectMessage"),
                    "url": f"https://blog.naver.com/{blog_id}/{item.get('logNo')}",
                    "likes": item.get("sympathyCnt", 0),
                    "comments": item.get("commentCnt", 0),
                    "time": dt.strftime("%Y. %m. %d"),
                    "logNo": item.get("logNo")
                })

                if mode == "count" and len(posts) >= target_count:
                    logger.info(f"✅ 목표 개수({target_count}개)를 모두 수집했습니다.")
                    return finalize_and_save(posts, blog_id, logger, sort_by=sort_by)

            if progress_callback: progress_callback(len(posts))
            page += 1
            time.sleep(random.uniform(0.1, 0.2))
            
        except Exception as e:
            logger.error(f"⚠️ 데이터 처리 중 오류 발생: {e}")
            break

    return finalize_and_save(posts, blog_id, logger, sort_by=sort_by)
