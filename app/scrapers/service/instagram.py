import os
from typing import Dict, Any
from apify_client import ApifyClient

def scrape_instagram(url: str, max_length: int = 200) -> Dict[str, Any]:
    """
    Instagram URL에서 메타데이터를 추출 (Apify 사용).
    
    Apify의 'instagram-scraper' 행위자를 사용합니다.
    환경 변수 APIFY_API_KEY이 필요

    Args:
        url: Instagram URL (포스트, 릴스 등)

    Returns:
        dict: {
            "success": bool,
            "title": str,
            "description": str,
            "thumnail_image_url": str,
            "favicon_image_url": str,
            "site_name": str,
            "url": str,
            "content": str (본문 + 댓글),
        }
    """
    api_token = os.environ.get("APIFY_API_KEY")
    if not api_token:
        return {
            "success": False,
            "error": "APIFY_API_KEY environment variable is not set",
            "url": url
        }

    try:
        # Apify Client 초기화
        client = ApifyClient(api_token)

        # Actor 입력값 구성
        run_input = {
            "directUrls": [url],
            "resultsType": "posts",
            "searchType": "hashtag", # 기본값
            "searchLimit": 1,
            "addParentData": False,
        }

        # Actor 실행 (shu8hvrXbJbY3Eb9W: Instagram Scraper)
        # 40-60초 정도 소요될 수 있음
        run = client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

        # 데이터셋 결과 가져오기
        dataset = client.dataset(run["defaultDatasetId"])
        items = dataset.list_items().items

        if not items:
            return {
                "success": False,
                "error": "No data returned from Apify",
                "url": url
            }

        post = items[0]
        
        # 필드 매핑
        # caption: 본문 내용
        caption = post.get("caption", "")
        # displayUrl: 이미지/썸네일
        image_url = post.get("displayUrl") or (post.get("images", [{}])[0].get("url") if post.get("images") else None)
        
        # icon_url: 인스타그램 파비콘 사용 (static URL)
        # Apify 결과에는 파비콘 정보가 없으므로 정적 URL 사용
        icon_url = "https://static.cdninstagram.com/rsrc.php/v3/yI/r/VsNE-OHk_8a.png" 
        
        # 댓글 처리
        comments = post.get("latestComments", [])
        comments_text = "\n".join([f"{c.get('ownerUsername', 'User')}: {c.get('text', '')}" for c in comments])
        
        # 좋아요/댓글 수 등 추가 정보
        likes_count = post.get("likesCount", 0)
        comments_count = post.get("commentsCount", 0)
        
        # content 구성: 본문 + 댓글 + 통계
        content_parts = []
        if caption:
            content_parts.append(f"[Caption]\n{caption}")
        
        content_parts.append(f"\n[Stats]\nLikes: {likes_count}, Comments: {comments_count}")
        
        if comments_text:
            content_parts.append(f"\n[Comments]\n{comments_text}")
            
        full_content = "\n\n".join(content_parts)

        # Title/Description 생성 (Caption 기반)
        title = caption.split('\n')[0][:100] if caption else "Instagram Post"
        # description 생성 (max_length 반영)
        description = caption[:max_length] + "..." if caption and len(caption) > max_length else caption

        return {
            "success": True,
            "title": title,
            "description": description,
            "thumnail_image_url": image_url,
            "favicon_image_url": icon_url,
            "site_name": "Instagram",
            "url": post.get("url", url),
            "content": full_content
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Apify scraping failed: {str(e)}",
            "url": url
        }