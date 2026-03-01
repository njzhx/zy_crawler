
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

TARGET_URL = "https://www.mohurd.gov.cn/gongkai/zc/wjk/index.html"
API_URL = "https://www.mohurd.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
API_PARAMS = {
    'parseType': 'bulidstatic',
    'webId': '86ca573ec4df405db627fdc2493677f3',
    'tplSetId': 'fc259c381af3496d85e61997ea7771cb',
    'pageType': 'column',
    'tagId': '内容1',
    'editType': 'null',
    'pageId': 'vhiC3JxmPC8o7Lqg4Jw0E'
}

# 增加重试机制
def get_with_retry(url, headers, params=None, max_retries=5, timeout=30):
    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            retries += 1
            if retries >= max_retries:
                raise
            print(f"请求失败 ({type(e).__name__})，{retries}秒后重试...")
            print(f"错误详情: {str(e)}")
            time.sleep(retries * 2)  # 增加等待时间


def scrape_data():
    policies = []
    all_items = []
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        
        print(f"🎯 目标抓取日期：{yesterday}")

        response = get_with_retry(API_URL, headers=headers, params=API_PARAMS, max_retries=3, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        items = soup.find_all('tr')
        filtered_count = 0
        
        for item in items:
            try:
                a_tag = item.find('a')
                if not a_tag:
                    continue
                
                title = a_tag.get('title', '').strip() or a_tag.get_text(strip=True)
                title = title.strip('"\'\\')
                href = a_tag.get('href', '').strip('"\'\\')
                href = href.replace('\\', '').replace('"', '').replace("'", '')
                
                if not title or len(title) < 5:
                    continue
                
                if href.startswith('/'):
                    article_url = "https://www.mohurd.gov.cn" + href
                elif not href.startswith('http'):
                    article_url = "https://www.mohurd.gov.cn/gongkai/zc/wjk/" + href
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
                
                # 保存到 all_items 用于显示最新5条
                all_items.append({'title': title, 'pub_at': pub_at})
                
                if pub_at != yesterday:
                    filtered_count += 1
                    continue
                
                content = ""
                try:
                    detail_resp = get_with_retry(article_url, headers=headers, max_retries=3, timeout=15)
                    detail_soup = BeautifulSoup(detail_resp.content, 'html.parser')
                    content_elem = detail_soup.find('div', class_='editor-content') or detail_soup.find('div', class_='ccontent') or detail_soup.find('div', class_='content') or detail_soup.find('div', id='content')
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
                    'source': '住建部文件库'
                }
                policies.append(policy_data)
                
            except Exception:
                continue
        
        print(f"✅ 住建部文件库爬虫：成功抓取 {len(policies)} 条前一天数据")
        print(f"⏭️  过滤掉 {filtered_count} 条非目标日期的数据")
        
        # 显示页面最新5条
        if all_items:
            print("📊 页面最新5条是：")
            for i, item in enumerate(all_items[:5], 1):
                date_str = item['pub_at'].strftime('%Y-%m-%d') if item['pub_at'] else '未知日期'
                print(f"✅ {item['title']} {date_str}")
        
    except Exception as e:
        print(f"❌ 住建部文件库爬虫：抓取失败 - {e}")
        print("----------------------------------------")
    
    return policies, all_items


def save_to_supabase(data_list):
    try:
        from db_utils import save_to_policy
        return save_to_policy(data_list, "住建部_文件库")
    except Exception:
        return data_list


def run():
    try:
        print("📦 开始执行爬虫: 住建部文件库")
        print(f"🔗 目标网址: `{TARGET_URL}`")
        print("----------------------------------------")
        data, _ = scrape_data()
        result = save_to_supabase(data)
        print(f"💾 写入数据库: {len(data)} 条")
        print("----------------------------------------")
        return result
    except Exception as e:
        print(f"❌ 住建部文件库爬虫：运行失败 - {e}")
        print("----------------------------------------")
        return []


if __name__ == "__main__":
    run()

