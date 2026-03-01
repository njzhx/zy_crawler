
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
    all_items = []
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        

        
        # 使用 API 接口获取数据
        api_url = "https://fzggw.jiangsu.gov.cn/module/jslib/zcjd/right.jsp"
        page_no = 1
        page_size = 10
        
        filtered_count = 0
        
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
                    
                    # 保存到 all_items 用于显示最新5条
                    all_items.append({'title': title, 'pub_at': pub_at})
                    
                    if pub_at != yesterday:
                        filtered_count += 1
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
        
        print(f"✅ 江苏省发改委爬虫：成功抓取 {len(policies)} 条前一天数据")
        print(f"⏭️  过滤掉 {filtered_count} 条非目标日期的数据")
        
        # 显示页面最新5条
        if all_items:
            print("📊 页面最新5条是：")
            for i, item in enumerate(all_items[:5], 1):
                date_str = item['pub_at'].strftime('%Y-%m-%d') if item['pub_at'] else '未知日期'
                print(f"✅ {item['title']} {date_str}")
        
    except Exception as e:
        print(f"❌ 江苏省发改委爬虫：抓取失败 - {e}")
        print("----------------------------------------")
    
    return policies, all_items


def save_to_supabase(data_list):
    try:
        from db_utils import save_to_policy
        return save_to_policy(data_list, "江苏省发改委_政策文件")
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
        print(f"❌ 江苏省发改委爬虫：运行失败 - {e}")
        print("----------------------------------------")
        return []


if __name__ == "__main__":
    run()

