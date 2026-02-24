import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 导入数据库工具
from db_utils import save_to_policy

# 爬虫配置
TARGET_URL = "https://www.gov.cn/zhengce/zuixin/"

# ==========================================
# 2. 网页抓取逻辑
# ==========================================
def scrape_data():
    """抓取中国政府网最新政策数据
    
    只抓取前一天发布的文章
    例如：运行时是2026年2月18日，只抓取2026年2月17日的文章
    """
    policies = []
    url = TARGET_URL
    
    try:
        # 计算前一天日期（使用北京时间 UTC+8）
        from datetime import timezone
        # 创建 UTC+8 时区
        tz_utc8 = timezone(timedelta(hours=8))
        # 获取北京时间
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        print(f"📅 运行日期（北京时间）：{today}")
        print(f"🎯 目标抓取日期：{yesterday}")
        # 同时显示 UTC 时间，便于调试
        utc_now = datetime.utcnow()
        print(f"🌍 运行时间（UTC）：{utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 发送请求
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找AJAX数据URL
        ajax_url = None
        scripts = soup.find_all('script')
        for script in scripts:
            script_content = script.string
            if script_content and 'list-1-ajax-id' in script_content:
                import re
                # 尝试多种模式匹配AJAX URL
                patterns = [
                    r'url:\s*["\']([^"\']+)\.json["\']',
                    r'url:\s*["\']([^"\']+)\.json["\']',
                    r'ajax\s*:\s*["\']([^"\']+)["\']'
                ]
                
                for pattern in patterns:
                    ajax_match = re.search(pattern, script_content)
                    if ajax_match:
                        ajax_path = ajax_match.group(1)
                        if not ajax_path.endswith('.json'):
                            ajax_path += '.json'
                        
                        if ajax_path.startswith('http'):
                            ajax_url = ajax_path
                        elif ajax_path.startswith('./'):
                            ajax_url = f"https://www.gov.cn/zhengce/zuixin/{ajax_path[2:]}"
                        else:
                            ajax_url = f"https://www.gov.cn/zhengce/zuixin/{ajax_path}"
                        break
                if ajax_url:
                    break
        
        # 如果没有找到AJAX URL，尝试常见的JSON文件名
        if not ajax_url:
            common_json_names = [
                "https://www.gov.cn/zhengce/zuixin/data.json",
                "https://www.gov.cn/zhengce/zuixin/list.json",
                "https://www.gov.cn/zhengce/zuixin/zuixin.json"
            ]
            # 尝试第一个常见URL
            ajax_url = common_json_names[0]
        
        # 请求AJAX数据
        policy_items = []
        try:
            ajax_response = requests.get(ajax_url, timeout=15)
            if ajax_response.status_code == 200:
                import json
                data = ajax_response.json()
                
                if isinstance(data, list):
                    policy_items = data
        except Exception as e:
            print(f"⚠️  AJAX请求异常: {e}")
        
        filtered_count = 0
        
        for item in policy_items:
            if not isinstance(item, dict):
                continue
            
            # 提取标题和链接
            title = item.get('TITLE', '')
            policy_url = item.get('URL', '')
            
            if not title or not policy_url:
                continue
            
            # 确保URL是完整的
            if not policy_url.startswith('http'):
                policy_url = f"https://www.gov.cn{policy_url}"
            
            # 提取发布日期
            date_str = item.get('DOCRELPUBTIME', '')
            pub_at = None
            if date_str:
                try:
                    pub_at = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            

            
            # 过滤：只保留前一天的文章
            if pub_at != yesterday:
                filtered_count += 1
                continue
            
            # 提取内容 - 抓取详情页内容
            content = ""
            try:
                detail_response = requests.get(policy_url, timeout=15)
                detail_response.raise_for_status()
                detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                content_elem = detail_soup.select_one('#UCAP-CONTENT')
                if content_elem:
                    content = content_elem.get_text(strip=True)
            except Exception:
                pass
            
            # 构建政策数据
            policy_data = {
                'title': title,
                'url': policy_url,
                'pub_at': pub_at,
                'content': content,
                'selected': False,
                'category': '政策',
                'source': '中国政府网'
            }
            
            policies.append(policy_data)
        
        print(f"✅ 中国政府网爬虫：成功抓取 {len(policies)} 条前一天数据")
        print(f"⏭️  过滤掉 {filtered_count} 条非目标日期的数据")
        
    except Exception as e:
        print(f"❌ 中国政府网爬虫：抓取失败 - {e}")
    
    return policies

# ==========================================
# 3. 数据入库逻辑
# ==========================================
def save_to_supabase(data_list):
    """保存数据到数据库
    
    使用统一的数据库工具函数
    """
    return save_to_policy(data_list, "中国政府网爬虫")

# ==========================================
# 主函数
# ==========================================
def run():
    """运行中国政府网爬虫"""
    try:
        data = scrape_data()
        result = save_to_supabase(data)
        return result
    except Exception as e:
        print(f"❌ 中国政府网爬虫：运行过程中发生未捕获的异常 - {e}")
        return []

if __name__ == "__main__":
    run()
