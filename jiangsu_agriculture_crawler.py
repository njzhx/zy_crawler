import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re

# 目标网站URL
TARGET_URL = "https://nynct.jiangsu.gov.cn/col/col11977/index.html"
SOURCE_NAME = "江苏省农业农村厅"

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
        print(f"📅 运行日期（北京时间）：{today}")
        print(f"🎯 目标抓取日期：{yesterday}")
        
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
            print("❌ 未找到datastore脚本标签")
            return policies, all_items
        
        # 提取recordset内容
        recordset_match = re.search(r'<recordset>([\s\S]*?)</recordset>', datastore_script)
        if not recordset_match:
            print("❌ 未找到recordset")
            return policies, all_items
        
        recordset_content = recordset_match.group(1)
        
        # 提取所有record
        records = re.findall(r'<record><!\[CDATA\[(.*?)\]\]></record>', recordset_content, re.DOTALL)
        all_items = len(records)
        
        print(f"📋 找到 {all_items} 条数据")
        
        target_date_items = 0
        non_target_date_items = 0
        
        # 遍历记录
        for record in records:
            # 提取标题、URL和日期
            title_match = re.search(r'title=(["\'])(.*?)\1', record)
            url_match = re.search(r'href=(["\'])(.*?)\1', record)
            date_match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', record)
            
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
                # 处理URL
                if not url.startswith('http'):
                    if url.startswith('/'):
                        url = f"https://nynct.jiangsu.gov.cn{url}"
                    else:
                        url = f"https://nynct.jiangsu.gov.cn/{url}"
                
                # 抓取详情页内容
                content = ""
                try:
                    detail_response = requests.get(url, headers=headers, timeout=15)
                    detail_response.raise_for_status()
                    detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                    # 查找内容容器
                    content_elem = detail_soup.select_one('.bt-content.zoom.clearfix')
                    if content_elem:
                        content = content_elem.get_text(strip=True)
                        # 移除来源信息
                        content = re.sub(r'来源：.*$', '', content, flags=re.DOTALL)
                except Exception as e:
                    print(f"⚠️  抓取详情页失败：{url} - {e}")
                
                policy_data = {
                    'title': title,
                    'url': url,
                    'pub_at': pub_at,
                    'content': content,
                    'selected': False,
                    'category': '',
                    'source': '江苏省农业农村厅通知公告'
                }
                policies.append(policy_data)
            else:
                non_target_date_items += 1
        
        print(f"✅ 目标日期条目：{target_date_items} 条")
        print(f"⏭️  非目标日期条目：{non_target_date_items} 条")
        
        if policies:
            print(f"✅ 成功抓取 {len(policies)} 条目标日期的文章")
            print("📊 页面最新5条是：")
            for i, policy in enumerate(policies[:5]):
                print(f"✅ {policy['title']} [{policy['pub_at']}]")
        
    except Exception as e:
        print(f"❌ 爬虫：抓取失败 - {e}")
    
    return policies, all_items

# ==========================================
# 2. 数据入库逻辑
# ==========================================
def save_to_supabase(data_list):
    if not data_list:
        print("⚠️ 没有抓取到任何数据，跳过写入。")
        return []

    try:
        from supabase import create_client, Client
        SUPABASE_URL = os.environ.get("SUPABASE_PROJECT_API")
        SUPABASE_KEY = os.environ.get("SUPABASE_ANON_PUBLIC")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("缺少 Supabase 环境变量")
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 处理日期对象
        processed_data = []
        for item in data_list:
            processed_item = item.copy()
            if hasattr(processed_item.get('pub_at'), 'isoformat'):
                processed_item['pub_at'] = processed_item['pub_at'].isoformat()
            processed_data.append(processed_item)
        
        # 使用upsert插入数据
        response = supabase.table("policy").upsert(
            processed_data, 
            on_conflict="title"
        ).execute()
        
        print(f"✅ 成功写入 {len(processed_data)} 条数据到 Supabase")
        return data_list
    except Exception as e:
        print(f"❌ 爬虫/数据库写入失败：{e}")
        return data_list

# ==========================================
# 3. 主函数
# ==========================================
def run():
    """运行爬虫"""
    try:
        print("🔍 开始执行爬虫: 江苏省农业农村厅通知公告")
        print("----------------------------------------")
        print(f"🔗 目标网址: {TARGET_URL}")
        print("----------------------------------------")
        data, all_items = scrape_data()
        if data:
            result = save_to_supabase(data)
            print(f"📊 抓取数据: {len(data)} 条")
            print(f"💾 写入数据库: {len(result)} 条")
            print("✅ 爬虫 江苏省农业农村厅通知公告 执行成功")
        else:
            print("⚠️  未找到目标日期的文章")
            print("✅ 爬虫 江苏省农业农村厅通知公告 执行完成")
        return data
    except Exception as e:
        print(f"❌ 爬虫 江苏省农业农村厅通知公告 运行失败 - {e}")
        return []

# ==========================================
# 主入口
# ==========================================
if __name__ == "__main__":
    run()
