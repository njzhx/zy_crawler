import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from supabase import create_client, Client

# ==========================================
# 1. 初始化 Supabase 客户端
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_PROJECT_API")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_PUBLIC")

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("缺少 Supabase 环境变量: SUPABASE_PROJECT_API 或 SUPABASE_ANON_PUBLIC")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. 网页抓取逻辑
# ==========================================
def scrape_data():
    """抓取中国政府网最新政策数据"""
    policies = []
    url = "https://www.gov.cn/zhengce/zuixin/"
    
    try:
        # 发送请求
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找政策列表（根据实际网页结构调整选择器）
        # 注意：这里需要根据实际网页结构进行调整
        policy_items = soup.select('.list > li')
        
        for item in policy_items:
            # 提取标题和链接
            title_elem = item.select_one('a')
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            policy_url = title_elem.get('href')
            
            # 确保URL是完整的
            if policy_url and not policy_url.startswith('http'):
                policy_url = f"https://www.gov.cn{policy_url}"
            
            # 提取发布日期
            date_elem = item.select_one('.date')
            pub_at = None
            if date_elem:
                date_str = date_elem.get_text(strip=True)
                try:
                    pub_at = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # 提取内容（这里只是示例，实际可能需要进入详情页抓取）
            content = ""  # 可以后续实现详情页抓取
            
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
        
        print(f"✅ 中国政府网爬虫：成功抓取 {len(policies)} 条数据")
        
    except Exception as e:
        print(f"❌ 中国政府网爬虫：抓取失败 - {e}")
    
    return policies

# ==========================================
# 3. 数据入库逻辑
# ==========================================
def save_to_supabase(data_list):
    if not data_list:
        print("⚠️ 中国政府网爬虫：没有抓取到任何数据，跳过写入。")
        return []

    try:
        supabase = get_supabase_client()
        response = supabase.table("policy").upsert(
            data_list, 
            on_conflict="title"
        ).execute()
        
        print(f"✅ 中国政府网爬虫：成功写入 {len(data_list)} 条数据到 Supabase")
        return data_list
    except Exception as e:
        print(f"❌ 中国政府网爬虫：数据库写入失败 - {e}")
        return []

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
