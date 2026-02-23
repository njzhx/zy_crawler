import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 导入数据库工具
from db_utils import save_to_policy

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
        
        # 查找政策解读列表（根据实际网页结构调整选择器）
        # 实际页面结构：.news_box .list 包含文章项
        news_box = soup.select_one('.news_box')
        policy_items = []
        
        print(f"\n🔍 开始查找文章项...")
        
        if news_box:
            print("✅ 找到 news_box 容器")
            # 尝试不同的选择器查找文章项
            possible_selectors = [
                '.list > li',            # 列表中的li
                '.list > div',           # 列表中的div
                'li',                    # 所有li
                '.item',                 # 文章项
                '.article-item'          # 文章项
            ]
            
            for selector in possible_selectors:
                items = news_box.select(selector)
                if items:
                    policy_items = items
                    print(f"✅ 使用选择器 '{selector}' 找到 {len(items)} 个文章项")
                    break
        else:
            # 如果没有找到news_box，尝试直接查找
            policy_items = soup.select('li')
            print(f"⚠️  未找到 news_box，直接查找 li 元素，找到 {len(policy_items)} 个")
        
        print(f"\n📋 最终找到 {len(policy_items)} 个文章项")
        
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
            pub_at = None
            
            # 尝试不同的日期元素选择器
            date_selectors = [
                '.date',            # class为date的元素
                'span.date',        # span标签且class为date
                '.time',            # class为time的元素
                'span.time'         # span标签且class为time
            ]
            
            for selector in date_selectors:
                date_elem = item.select_one(selector)
                if date_elem:
                    date_str = date_elem.get_text(strip=True)
                    try:
                        # 清理日期字符串（移除多余字符）
                        import re
                        date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
                        if date_match:
                            date_str = date_match.group(0)
                            pub_at = datetime.strptime(date_str, '%Y-%m-%d').date()
                            break
                    except ValueError:
                        pass
            
            # 如果没有找到日期元素，尝试从文本中提取
            if not pub_at:
                text = item.get_text(strip=True)
                import re
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
                if date_match:
                    try:
                        date_str = date_match.group(0)
                        pub_at = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
            
            # 调试：显示提取的日期
            if pub_at:
                print(f"📅 提取日期：{pub_at}，目标日期：{yesterday}")
            else:
                print(f"❓ 未提取到日期 - 标题：{title[:30]}...")
            
            # 过滤：只保留前一天的文章
            if pub_at != yesterday:
                filtered_count += 1
                if pub_at:
                    print(f"⏭️  过滤掉非目标日期文章：{pub_at}")
                else:
                    print(f"⏭️  过滤掉无日期文章")
                continue
            
            # 调试：找到符合条件的文章
            print(f"✅ 找到目标日期文章：{title[:30]}...")
            
            # 提取内容（这里只是示例，实际可能需要进入详情页抓取）
            content = ""  # 可以后续实现详情页抓取
            
            # 构建政策数据
            policy_data = {
                'title': title,
                'url': policy_url,
                'pub_at': pub_at,
                'content': content,
                'selected': False,
                'category': '',  # 留空，不设置默认值
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
    """保存数据到数据库
    
    使用统一的数据库工具函数
    """
    return save_to_policy(data_list, "中国政府网政策解读爬虫")

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
