
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

TARGET_URL = "https://gxt.jiangsu.gov.cn/col/col6281/index.html"


def scrape_data():
    policies = []
    url = TARGET_URL
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        print(f"Date (Beijing): {today}")
        print(f"Target date: {yesterday}")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        items = soup.find_all('li')
        filtered_count = 0
        
        for item in items:
            try:
                a_tag = item.find('a')
                if not a_tag:
                    continue
                
                title = a_tag.get('title', '').strip() or a_tag.get_text(strip=True)
                href = a_tag.get('href', '')
                
                if not title or len(title) < 5:
                    continue
                
                if href.startswith('/'):
                    article_url = "https://gxt.jiangsu.gov.cn" + href
                elif not href.startswith('http'):
                    article_url = "https://gxt.jiangsu.gov.cn/col/col6281/" + href
                else:
                    article_url = href
                
                pub_at = None
                date_text = item.get_text()
                date_match = re.search(r'(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})', date_text)
                if date_match:
                    try:
                        pub_at = datetime.strptime(f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}", '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                if pub_at != yesterday:
                    filtered_count += 1
                    continue
                
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
                    'category': '公示公告',
                    'source': '江苏省工信厅'
                }
                policies.append(policy_data)
                
            except Exception:
                continue
        
        print(f"Found {len(policies)} items for target date")
        print(f"Skipped {filtered_count} items")
        
    except Exception as e:
        print(f"Error: {e}")
    
    return policies


def save_to_supabase(data_list):
    try:
        from db_utils import save_to_policy
        return save_to_policy(data_list, "江苏省工信厅_公示公告")
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
