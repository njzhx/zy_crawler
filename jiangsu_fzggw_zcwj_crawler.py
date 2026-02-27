
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://fzggw.jiangsu.gov.cn/module/jslib/zcjd/zcjd.htm',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
}

TARGET_URL = "https://fzggw.jiangsu.gov.cn/module/jslib/zcjd/zcjd.htm"


def scrape_data():
    policies = []
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        print(f"Date (Beijing): {today}")
        print(f"Target date: {yesterday}")
        
        # 使用 API 接口获取数据
        api_url = "https://fzggw.jiangsu.gov.cn/module/jslib/zcjd/right.jsp"
        page_no = 1
        page_size = 10
        
        while True:
            data = {
                "name": "",
                "keytype": "",
                "year": "2026",
                "ztflid": "",
                "fwlbbm": "",
                "pageSize": page_size,
                "pageNo": page_no
            }
            
            response = requests.post(api_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            # 解析 JSON 响应
            import json
            json_data = json.loads(response.text)
            
            if not json_data.get('result'):
                break
            
            items = json_data.get('data', [])
            if not items:
                break
            
            for item in items:
                try:
                    title = item.get('vc_title', '').strip()
                    url = item.get('url', '')
                    c_deploytime = item.get('c_deploytime', '')
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # 构建完整的文章 URL
                    if url.startswith('/'):
                        article_url = "https://fzggw.jiangsu.gov.cn" + url
                    elif not url.startswith('http'):
                        article_url = "https://fzggw.jiangsu.gov.cn/module/jslib/zcjd/" + url
                    else:
                        article_url = url
                    
                    # 解析发布时间
                    pub_at = None
                    if c_deploytime:
                        try:
                            # 假设日期格式为 YYYY-MM-DD
                            pub_at = datetime.strptime(c_deploytime, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    
                    if pub_at != yesterday:
                        continue
                    
                    # 获取文章内容
                    content = ""
                    try:
                        detail_resp = requests.get(article_url, headers=headers, timeout=15)
                        detail_soup = BeautifulSoup(detail_resp.content, 'html.parser')
                        content_elem = detail_soup.select_one('.content') or detail_soup.select_one('#content')
                        if content_elem:
                            content = content_elem.get_text(strip=True)
                    except Exception:
                        pass
                    
                    policy_data = {
                        'title': title,
                        'url': article_url,
                        'pub_at': pub_at,
                        'content': content,
                        'selected': False,
                        'category': '',
                        'source': '江苏省发改委'
                    }
                    policies.append(policy_data)
                    
                except Exception:
                    continue
            
            # 检查是否还有更多页面
            if len(items) < page_size:
                break
            page_no += 1
        
        print(f"Found {len(policies)} items for target date")
        
    except Exception as e:
        print(f"Error: {e}")
    
    return policies


def save_to_supabase(data_list):
    try:
        from db_utils import save_to_policy
        return save_to_policy(data_list, "江苏省发改委_政策文件")
    except Exception:
        return data_list


def run():
    try:
        data = scrape_data()
        save_to_supabase(data)
        return data
    except Exception as e:
        print(f"Run failed: {e}")
        return []


if __name__ == "__main__":
    run()

