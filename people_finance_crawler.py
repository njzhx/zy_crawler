import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 导入数据库工具
from db_utils import save_to_policy

# ==========================================
# 1. 网页抓取逻辑
# ==========================================
def scrape_data():
    """抓取人民网财经频道数据
    
    只抓取前一天发布的文章
    例如：运行时是2026年2月18日，只抓取2026年2月17日的文章
    """
    policies = []
    url = "http://finance.people.com.cn/GB/70846/index.html"
    
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
        
        # 查找文章列表（直接查找所有li元素）
        policy_items = soup.find_all('li')
        
        filtered_count = 0
        
        for item in policy_items:
            # 提取标题和链接
            title_elem = item.find('a')
            if not title_elem:
                continue
            
            # 提取文本
            text = item.get_text(strip=True)
            
            # 提取日期（从文本末尾提取）
            import re
            date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})$')
            date_match = date_pattern.search(text)
            
            pub_at = None
            if date_match:
                date_str = date_match.group(1)
                try:
                    pub_at = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # 提取标题（去除日期部分）
            if date_match:
                title = text[:date_match.start()].strip()
            else:
                title = title_elem.get_text(strip=True)
            
            # 提取链接
            policy_url = title_elem.get('href')
            
            # 确保URL是完整的
            if policy_url and not policy_url.startswith('http'):
                # 检查是否是相对路径
                if policy_url.startswith('/'):
                    policy_url = f"http://finance.people.com.cn{policy_url}"
                else:
                    policy_url = f"http://finance.people.com.cn/GB/70846/{policy_url}"
            
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
                'category': '财经新闻',
                'source': '人民网财经'
            }
            
            policies.append(policy_data)
        
        print(f"✅ 人民网财经爬虫：成功抓取 {len(policies)} 条前一天数据")
        print(f"⏭️  过滤掉 {filtered_count} 条非目标日期的数据")
        
    except Exception as e:
        print(f"❌ 人民网财经爬虫：抓取失败 - {e}")
    
    return policies

# ==========================================
# 3. 数据入库逻辑
# ==========================================
def save_to_supabase(data_list):
    """保存数据到数据库
    
    使用统一的数据库工具函数
    """
    return save_to_policy(data_list, "人民网财经爬虫")

# ==========================================
# 主函数
# ==========================================
def run():
    """运行人民网财经爬虫"""
    try:
        data = scrape_data()
        result = save_to_supabase(data)
        # 返回实际抓取的数据，爬虫管理器会根据此计算数量
        return result
    except Exception as e:
        print(f"❌ 人民网财经爬虫：运行过程中发生未捕获的异常 - {e}")
        return []

if __name__ == "__main__":
    run()
