
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

TARGET_URL = "https://www.jiangsu.gov.cn/col/col81677/index.html"


def scrape_data():
    policies = []
    all_items = []
    url = TARGET_URL
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        

        
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
                    article_url = "https://www.jiangsu.gov.cn" + href
                elif not href.startswith('http'):
                    article_url = "https://www.jiangsu.gov.cn/col/col81677/" + href
                else:
                    article_url = href
                
                pub_at = None
                date_text = item.get_text()
                # 匹配 MM-DD 格式的日期
                date_match = re.search(r'(\d{1,2})[-/\.](\d{1,2})', date_text)
                if date_match:
                    try:
                        # 使用当前年份（2026）与匹配到的月日组合
                        pub_at = datetime(2026, int(date_match.group(1)), int(date_match.group(2))).date()
                    except ValueError:
                        pass
                
                # 保存到 all_items 用于显示最新5条
                all_items.append({'title': title, 'pub_at': pub_at})
                
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
                    'category': '',
                    'source': '江苏省政府公报'
                }
                policies.append(policy_data)
                
            except Exception:
                continue
        
        print(f"✅ 江苏省政府公报爬虫：成功抓取 {len(policies)} 条前一天数据")
        print(f"⏭️  过滤掉 {filtered_count} 条非目标日期的数据")
        
        # 显示页面最新5条
        if all_items:
            print("📊 页面最新5条是：")
            for i, item in enumerate(all_items[:5], 1):
                date_str = item['pub_at'].strftime('%Y-%m-%d') if item['pub_at'] else '未知日期'
                print(f"✅ {item['title']} {date_str}")
        
    except Exception as e:
        print(f"❌ 江苏省政府公报爬虫：抓取失败 - {e}")
        print("----------------------------------------")
    
    return policies, all_items


def save_to_supabase(data_list):
    try:
        from db_utils import save_to_policy
        return save_to_policy(data_list, "江苏省政府_省政府公报")
    except Exception:
        return data_list


def run():
    try:
        data, _ = scrape_data()
        result = save_to_supabase(data)
        print(f"💾 写入数据库: {len(data)} 条")
        print("----------------------------------------")
        return result
    except Exception as e:
        print(f"❌ 江苏省政府公报爬虫：运行失败 - {e}")
        print("----------------------------------------")
        return []


if __name__ == "__main__":
    run()

