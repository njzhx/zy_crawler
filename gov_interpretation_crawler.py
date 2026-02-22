import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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
    """抓取中国政府网政策解读数据
    
    只抓取前一天发布的文章
    例如：运行时是2026年2月18日，只抓取2026年2月17日的文章
    """
    policies = []
    url = "https://www.gov.cn/zhengce/jiedu/index.htm"
    
    try:
        # 计算前一天日期
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        print(f"📅 运行日期：{today}")
        print(f"🎯 目标抓取日期：{yesterday}")
        
        # 发送请求
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找政策解读列表（根据实际网页结构调整选择器）
        # 注意：这里需要根据实际网页结构进行调整
        policy_items = soup.select('.list > li')
        
        filtered_count = 0
        
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
            
            # 过滤：只保留前一天的文章
            if pub_at != yesterday:
                filtered_count += 1
                continue
            
            # 提取内容（这里只是示例，实际可能需要进入详情页抓取）
            content = ""  # 可以后续实现详情页抓取
            
            # 构建政策数据
            policy_data = {
                'title': title,
                'url': policy_url,
                'pub_at': pub_at,
                'content': content,
                'selected': False,
                'category': '政策解读',
                'source': '中国政府网'
            }
            
            policies.append(policy_data)
        
        print(f"✅ 中国政府网政策解读爬虫：成功抓取 {len(policies)} 条前一天数据")
        print(f"⏭️  过滤掉 {filtered_count} 条非目标日期的数据")
        
    except Exception as e:
        print(f"❌ 中国政府网政策解读爬虫：抓取失败 - {e}")
    
    return policies

# ==========================================
# 3. 数据入库逻辑
# ==========================================
def save_to_supabase(data_list):
    if not data_list:
        print("⚠️ 中国政府网政策解读爬虫：没有抓取到任何数据，跳过写入。")
        return []

    try:
        # 转换date对象为字符串，避免JSON序列化错误
        processed_data = []
        for item in data_list:
            processed_item = item.copy()
            # 检查pub_at是否为日期对象
            if hasattr(processed_item.get('pub_at'), 'isoformat'):
                processed_item['pub_at'] = processed_item['pub_at'].isoformat()
            processed_data.append(processed_item)
        
        supabase = get_supabase_client()
        response = supabase.table("policy").upsert(
            processed_data, 
            on_conflict="title"
        ).execute()
        
        print(f"✅ 中国政府网政策解读爬虫：成功写入 {len(processed_data)} 条数据到 Supabase")
        return data_list  # 返回原始数据，保持一致性
    except Exception as e:
        print(f"❌ 中国政府网政策解读爬虫：数据库写入失败 - {e}")
        return data_list  # 即使写入失败，也返回抓取的数据，确保统计正确

# ==========================================
# 主函数
# ==========================================
def run():
    """运行中国政府网政策解读爬虫"""
    try:
        data = scrape_data()
        result = save_to_supabase(data)
        return result
    except Exception as e:
        print(f"❌ 中国政府网政策解读爬虫：运行过程中发生未捕获的异常 - {e}")
        return []

if __name__ == "__main__":
    run()
