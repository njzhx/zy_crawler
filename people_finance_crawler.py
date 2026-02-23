import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 导入数据库工具
from db_utils import save_to_policy

# ==========================================
# 辅助函数
# ==========================================

def get_article_content(url):
    """抓取文章详情页内容
    
    Args:
        url: 文章详情页链接
        
    Returns:
        str: 文章内容
    """
    if not url:
        return ""
    
    try:
        # 发送请求
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找文章内容（根据人民网详情页结构调整选择器）
        # 常见的内容容器选择器
        content_selectors = [
            '.article-content',       # 人民网常见的内容容器
            '.content',                # 通用内容容器
            '.article-body',           # 另一种常见结构
            '.main-content',           # 主内容区
            '.text_con',               # 人民网特定结构
            'div[id*="content"]'      # 包含content的id
        ]
        
        content = ""
        
        # 尝试不同的选择器
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 提取文本，去除多余空白
                content = ' '.join(content_elem.stripped_strings)
                break
        
        # 如果没有找到内容，尝试查找所有p标签
        if not content:
            p_elems = soup.find_all('p')
            if p_elems:
                content = ' '.join([p.get_text(strip=True) for p in p_elems[:10]])  # 取前10个p标签
        
        # 过滤开头的"点击播报本文，约  "
        if content.startswith("点击播报本文，约  "):
            # 找到"约  "后面的内容
            prefix_part = "点击播报本文，约  "
            after_prefix = content[len(prefix_part):]
            
            # 尝试找到"字"字符，这应该是字数描述的结束
            char_pos = after_prefix.find("字")
            if char_pos != -1:
                # 保留"字"后的所有内容
                content = after_prefix[char_pos+1:].strip()
            else:
                # 如果没有找到"字"字符，尝试找到第一个空格
                space_pos = after_prefix.find(" ")
                if space_pos != -1:
                    # 保留空格后的所有内容
                    content = after_prefix[space_pos:].strip()
                else:
                    # 如果既没有找到"字"也没有找到空格，直接保留前缀后的所有内容
                    content = after_prefix.strip()
        
        # 限制内容长度，避免存储过大的数据
        if len(content) > 5000:
            content = content[:5000] + "..."
        
        return content
        
    except Exception as e:
        # 静默失败，不影响主爬虫执行
        print(f"⚠️  抓取详情页失败 - {url[:50]}...")
        return ""

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
            
            # 提取内容（抓取详情页内容）
            content = get_article_content(policy_url)
            
            # 构建政策数据
            policy_data = {
                'title': title,
                'url': policy_url,
                'pub_at': pub_at,
                'content': content,
                'selected': False,
                'category': '',  # 留空，不设置默认值
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
