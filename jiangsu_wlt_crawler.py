import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urljoin

# 导入数据库工具
from db_utils import save_to_policy

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ==========================================
# 1. 终极配置：直接访问原生网页，不碰防护接口
# ==========================================
TARGETS = [
    {
        "name": "江苏省文旅厅_焦点新闻", 
        "base_url": "https://wlt.jiangsu.gov.cn/col/col695/index.html",
        "category": "焦点新闻"
    },
    {
        "name": "江苏省文旅厅_通知公告", 
        "base_url": "https://wlt.jiangsu.gov.cn/col/col699/index.html",
        "category": "通知公告"
    }
]

def scrape_data():
    policies = []
    all_items = []
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        
        for target in TARGETS:
            try:
                # 1. 就像财政厅爬虫一样，直接 GET 请求主页！
                response = requests.get(target['base_url'], headers=headers, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 2. 直接在网页源码里找潜藏的 XML 数据包
                script_tag = soup.find('script', type='text/xml')
                if not script_tag:
                    continue
                    
                datastore_soup = BeautifulSoup(script_tag.string, 'html.parser')
                records = datastore_soup.find_all('record')
                
                filtered_count = 0
                
                # 3. 遍历提取到的文章
                for record in records:
                    cdata = record.string
                    if not cdata:
                        continue
                        
                    record_soup = BeautifulSoup(cdata, 'html.parser')
                    a_tag = record_soup.find('a')
                    if not a_tag:
                        continue
                        
                    title = a_tag.get('title') or a_tag.get_text(strip=True)
                    href = a_tag.get('href', '')
                    link = urljoin(target['base_url'], href)
                    
                    # 提取日期
                    date_match = re.search(r'202\d-\d{2}-\d{2}', cdata)
                    if not date_match:
                        continue
                        
                    pub_at = datetime.strptime(date_match.group(), '%Y-%m-%d').date()
                    
                    item_info = {'title': title, 'pub_at': pub_at, 'url': link}
                    if item_info not in all_items:
                        all_items.append(item_info)
                        
                    # 严格日期判断：只抓昨天的数据
                    if pub_at == yesterday:
                        content = ""
                        try:
                            detail_res = requests.get(link, headers=headers, timeout=20)
                            detail_res.encoding = 'utf-8'
                            detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
                            
                            content_elem = detail_soup.select_one('#UCAP-CONTENT') or detail_soup.select_one('.bt-content')
                            if content_elem:
                                content = content_elem.get_text(strip=True)
                        except Exception as e:
                            pass # 忽略详情页错误
                            
                        policies.append({
                            'title': title,
                            'url': link,
                            'pub_at': pub_at,
                            'content': content,
                            'source': '江苏省文旅厅',
                            'category': target['category']
                        })
                    else:
                        filtered_count += 1
                        
                print(f"⏭️  {target['name']}：过滤掉 {filtered_count} 条非目标日期的数据")
                
            except Exception as e:
                print(f"❌ {target['name']} 爬虫抓取失败: {e}")
                
        print(f"✅ 江苏省文旅厅爬虫：成功抓取 {len(policies)} 条前一天数据")
        
        # 将两个栏目的数据合并并按日期降序排列，打印最新 5 条
        if all_items:
            print("📊 页面最新5条是：")
            all_items.sort(key=lambda x: x['pub_at'], reverse=True)
            for i, item in enumerate(all_items[:5], 1):
                date_str = item['pub_at'].strftime('%Y-%m-%d')
                print(f"✅ {item['title']} {date_str}")
                
    except Exception as e:
        print(f"❌ 江苏省文旅厅爬虫：整体运行失败 - {e}")
        
    return policies, all_items

def run():
    try:
        data, _ = scrape_data()
        if data:
            save_to_policy(data, "江苏省文旅厅")
            print(f"💾 写入数据库: {len(data)} 条")
            return data
        else:
            print("💾 写入数据库: 0 条 (没有符合日期的数据)")
            return []
    except Exception as e:
        print(f"❌ 文旅厅爬虫运行异常: {e}")
        return []

if __name__ == "__main__":
    run()
