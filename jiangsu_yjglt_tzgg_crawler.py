import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re

# 目标网站URL - 江苏省应急管理厅 通知公告
TARGET_URL = "https://yjglt.jiangsu.gov.cn/col/col3154/index.html"
SOURCE_NAME = "江苏省应急管理厅_通知公告"

# ==========================================
# 1. 网页抓取逻辑
# ==========================================
def scrape_data():
    """抓取数据，返回与表结构一致的字典列表"""
    policies = []
    all_items = 0
    
    try:
        # 计算前一天日期（使用北京时间 UTC+8）
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        
        # 发送请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        response = requests.get(TARGET_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找datastore脚本标签
        datastore_script = None
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '<datastore>' in script.string:
                datastore_script = script.string
                break
        
        if not datastore_script:
            print(f"❌ [{SOURCE_NAME}] 未找到datastore脚本标签")
            return policies, all_items
        
        # 提取recordset内容
        recordset_match = re.search(r'<recordset>([\s\S]*?)</recordset>', datastore_script)
        if not recordset_match:
            print(f"❌ [{SOURCE_NAME}] 未找到recordset")
            return policies, all_items
        
        recordset_content = recordset_match.group(1)
        
        # 提取所有record
        records = re.findall(r'<record><!\[CDATA\[(.*?)\]\]></record>', recordset_content, re.DOTALL)
        all_items = len(records)
        
        print(f"📋 [{SOURCE_NAME}] 找到 {all_items} 篇文章")
        
        target_date_items = 0
        non_target_date_items = 0
        
        # 遍历记录
        for record in records:
            # 提取标题、URL和日期 (应急管理厅日期通常为 YYYY-MM-DD 格式)
            title_match = re.search(r'title=(["\'])(.*?)\1', record)
            url_match = re.search(r'href=(["\'])(.*?)\1', record)
            # 应急管理厅日期正则适配
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', record)
            
            if not all([title_match, url_match, date_match]):
                continue
            
            title = title_match.group(2)
            url = url_match.group(2)
            date_str = date_match.group(1)
            
            # 解析日期
            try:
                pub_at = datetime.strptime(date_str, '%Y-%m-%d').date()
            except Exception:
                continue
            
            # 检查是否为目标日期
            if pub_at == yesterday:
                target_date_items += 1
                # 处理相对URL
                if not url.startswith('http'):
                    if url.startswith('/'):
                        url = f"https://yjglt.jiangsu.gov.cn{url}"
                    else:
                        url = f"https://yjglt.jiangsu.gov.cn/{url}"
                
                # 抓取详情页内容
                content = ""
                try:
                    detail_response = requests.get(url, headers=headers, timeout=15)
                    detail_response.raise_for_status()
                    # 应急厅详情页通常为 UTF-8
                    detail_response.encoding = detail_response.apparent_encoding 
                    detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                    
                    # 应急管理厅常见的详情内容容器
                    content_elem = detail_soup.select_one('.bt-content') or detail_soup.select_one('#zoom')
                    if content_elem:
                        # 移除无关标签
                        for extra in content_elem.select('script, style, .printer'):
                            extra.decompose()
                        content = content_elem.get_text(strip=True)
                        # 移除来源、日期等页脚/页头干扰
                        content = re.sub(r'浏览次数：.*$|来源：.*$|发布日期：.*$', '', content, flags=re.MULTILINE)
                except Exception as e:
                    print(f"⚠️  抓取详情页失败：{url} - {e}")
                
                policy_data = {
                    'title': title,
                    'url': url,
                    'pub_at': pub_at,
                    'content': content,
                    'selected': False,
                    'category': '',
                    'source': SOURCE_NAME
                }
                policies.append(policy_data)
            else:
                non_target_date_items += 1
        
        print(f"✅ {SOURCE_NAME}爬虫：成功抓取 {target_date_items} 条昨日数据")
        print(f"⏭️  过滤掉 {non_target_date_items} 条非目标日期的数据")
        
        # 收集显示最新5条
        all_articles = []
        for record in records[:5]:
            t_m = re.search(r'title=(["\'])(.*?)\1', record)
            d_m = re.search(r'(\d{4}-\d{2}-\d{2})', record)
            if t_m and d_m:
                all_articles.append((t_m.group(2), d_m.group(1)))
        
        print("📊 页面最新5条是：")
        for title, date_str in all_articles:
            print(f"✅ {title} {date_str}")
        
    except Exception as e:
        print(f"❌ [{SOURCE_NAME}] 爬虫：抓取失败 - {e}")
    
    return policies, all_items

# ==========================================
# 2. 数据入库逻辑
# ==========================================
def save_to_supabase(data_list):
    """保存数据到Supabase，使用db_utils统一处理"""
    try:
        from db_utils import save_to_policy
        return save_to_policy(data_list, SOURCE_NAME)
    except Exception as e:
        print(f"⚠️  无法调用入库工具: {e}")
        return data_list, None

# ==========================================
# 3. 主函数
# ==========================================
def run():
    """运行爬虫"""
    try:
        data, all_items = scrape_data()
        if data:
            result, api_push_result = save_to_supabase(data)
            print(f"💾 写入数据库: {len(result)} 条")
            print("----------------------------------------")
            return result
        else:
            print("💾 写入数据库: 0 条")
            print("----------------------------------------")
            print("⚠️  未找到目标日期的文章")
            return data
    except Exception as e:
        print(f"❌ 爬虫 {SOURCE_NAME} 运行失败 - {e}")
        print("----------------------------------------")
        return []

if __name__ == "__main__":
    run()
