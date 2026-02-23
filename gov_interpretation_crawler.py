import os
import re
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
        # 首先尝试用户提供的xpath对应的选择器
        list_container = soup.select_one('#list-1-ajax-id')
        policy_items = []
        
        print(f"\n🔍 开始查找文章项...")
        
        if list_container:
            print("✅ 找到 list-1-ajax-id 容器")
            # 检查容器是否为空
            if not list_container.find_all():
                print("⚠️  list-1-ajax-id 容器为空，可能是动态加载的")
            else:
                # 尝试在list-1-ajax-id中查找文章项
                possible_selectors = [
                    'li',                    # 所有li
                    'div',                   # 所有div
                    '.item',                 # 文章项
                    '.article-item',         # 文章项
                    '*'                      # 所有子元素
                ]
                
                for selector in possible_selectors:
                    items = list_container.select(selector)
                    if items:
                        policy_items = items
                        print(f"✅ 使用选择器 '{selector}' 找到 {len(items)} 个文章项")
                        break
        
        # 如果没有找到，尝试查找其他可能的容器
        if not policy_items:
            print("🔍 尝试查找其他可能的文章容器...")
            
            # 尝试常见的文章列表容器
            possible_containers = [
                '.news_box',              # 新闻框
                '.list_box',              # 列表框
                '.article_list',          # 文章列表
                '.news_list',             # 新闻列表
                '.content_list',          # 内容列表
                'ul',                     # 所有ul
                'ol'                      # 所有ol
            ]
            
            for container_selector in possible_containers:
                containers = soup.select(container_selector)
                for container in containers:
                    # 尝试在容器中查找文章项
                    possible_item_selectors = [
                        '.item',                 # 文章项
                        '.article-item',         # 文章项
                        'li',                    # 所有li
                    ]
                    
                    for item_selector in possible_item_selectors:
                        items = container.select(item_selector)
                        if items:
                            # 检查这些项是否真的包含文章数据（是否有链接且不是导航链接）
                            valid_items = []
                            for item in items:
                                a_tag = item.find('a')
                                if a_tag:
                                    href = a_tag.get('href', '')
                                    text = a_tag.get_text(strip=True)
                                    # 过滤掉导航链接
                                    if href and text and not any(keyword in text for keyword in ['首页', '简', '繁', 'EN', '登录', '个人中心', '退出', '邮箱', '无障碍']):
                                        valid_items.append(item)
                            
                            if valid_items:
                                policy_items = valid_items
                                print(f"✅ 在容器 '{container_selector}' 中使用选择器 '{item_selector}' 找到 {len(valid_items)} 个有效文章项")
                                # 打印前几个项的内容预览
                                for i, valid_item in enumerate(valid_items[:3]):
                                    item_content = valid_item.prettify()[:500]
                                    print(f"📝 第{i+1}个文章项内容预览：{item_content}...")
                                break
                    if policy_items:
                        break
                if policy_items:
                    break
        
        # 清除当前找到的导航链接，重新搜索
        policy_items = []
        print("🔍 清除导航链接，重新搜索实际的政策解读文章...")
        
        # 1. 首先尝试查找news_box容器
        news_box = soup.find('div', class_='news_box')
        if news_box:
            print("✅ 找到 news_box 容器，开始搜索其中的文章...")
            
            # 查找news_box中的所有子元素
            all_children = news_box.find_all(['li', 'div', 'p', 'span', 'a'])
            
            # 遍历所有元素，查找包含链接和日期的组合
            for child in all_children:
                # 查找链接
                link = child.find('a')
                if link:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # 过滤条件
                    if (href and text and 
                        not any(keyword in text for keyword in ['首页', '简', '繁', 'EN', '登录', '个人中心', '退出', '邮箱', '无障碍', '全国人大', '全国政协', '国家监察委员会', '最高人民法院', '最高人民检察院'])):
                        
                        # 查找附近的日期元素
                        # 检查当前元素
                        current_text = child.get_text()
                        date_match = re.search(r'\d{4}-\d{2}-\d{2}', current_text)
                        
                        # 检查父元素
                        if not date_match:
                            parent = child.find_parent(['li', 'div'])
                            if parent:
                                parent_text = parent.get_text()
                                date_match = re.search(r'\d{4}-\d{2}-\d{2}', parent_text)
                        
                        # 检查兄弟元素
                        if not date_match:
                            siblings = child.find_next_siblings(['span', 'div', 'p'])
                            for sibling in siblings[:3]:
                                sibling_text = sibling.get_text()
                                date_match = re.search(r'\d{4}-\d{2}-\d{2}', sibling_text)
                                if date_match:
                                    break
                        
                        if date_match:
                            # 确定包含链接和日期的容器
                            container = child.find_parent(['li', 'div']) if child.name != 'li' and child.name != 'div' else child
                            policy_items.append(container)
                            print(f"✅ 找到政策解读文章：{text[:50]}... 日期：{date_match.group(0)}")
                            # 限制找到的文章数量
                            if len(policy_items) >= 10:
                                break
            
            if policy_items:
                print(f"✅ 在 news_box 中找到 {len(policy_items)} 个政策解读文章")
        
        # 2. 如果没有找到，尝试查找所有包含日期的span元素
        if not policy_items:
            print("🔍 尝试查找所有包含日期的span元素...")
            # 导入re模块（确保在作用域内可用）
            import re
            # 查找所有span元素，然后逐个检查
            all_spans = soup.find_all('span')
            date_spans = []
            
            for span in all_spans:
                text = span.get_text(strip=True)
                if text:
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
                    if date_match:
                        date_spans.append(span)
            
            for span in date_spans:
                # 查找附近的链接
                parent = span.find_parent(['li', 'div'])
                if parent:
                    link = parent.find('a')
                    if link:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        if href and text:
                            policy_items.append(parent)
                            date_text = span.get_text(strip=True)
                            print(f"✅ 找到政策解读文章：{text[:50]}... 日期：{date_text}")
                            # 限制找到的文章数量
                            if len(policy_items) >= 10:
                                break
            
            if policy_items:
                print(f"✅ 通过日期span找到 {len(policy_items)} 个政策解读文章")
        
        # 如果仍然没有找到，尝试查看script标签中的数据
        if not policy_items:
            print("🔍 尝试查看script标签中的数据...")
            scripts = soup.find_all('script')
            
            # 查找可能包含内联文章数据的script标签
            for i, script in enumerate(scripts):
                script_content = script.string
                if script_content:
                    # 查找包含大量文本和日期的script标签
                    if len(script_content) > 1000 and re.search(r'\d{4}-\d{2}-\d{2}', script_content):
                        print(f"📝 发现可能包含内联文章数据的script标签 #{i}，长度：{len(script_content)}...")
                        # 打印前2000个字符
                        print(f"📝 script内容预览：{script_content[:2000]}...")
                        break
            
            # 查找可能包含文章列表的script标签
            for i, script in enumerate(scripts):
                script_content = script.string
                if script_content:
                    # 查找包含多个标题和链接的script标签
                    if script_content.count('title') > 3 and script_content.count('href') > 3:
                        print(f"📝 发现可能包含文章列表的script标签 #{i}，长度：{len(script_content)}...")
                        # 打印前2000个字符
                        print(f"📝 script内容预览：{script_content[:2000]}...")
                        break
            
            # 查找可能包含AJAX配置的script标签
            for i, script in enumerate(scripts):
                script_content = script.string
                if script_content:
                    if 'ajax' in script_content and 'url' in script_content and ('zhengce' in script_content or 'jiedu' in script_content):
                        print(f"📝 发现可能包含AJAX配置的script标签 #{i}，长度：{len(script_content)}...")
                        # 打印前2000个字符
                        print(f"📝 script内容预览：{script_content[:2000]}...")
                        break
        
        # 检查页面中是否有iframe
        if not policy_items:
            print("🔍 尝试检查页面中的iframe...")
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src', '')
                if src:
                    print(f"📝 发现iframe：{src}")
                    # 尝试访问iframe的内容
                    try:
                        iframe_url = src if src.startswith('http') else f"https://www.gov.cn{src}"
                        print(f"📝 尝试访问iframe内容：{iframe_url}")
                        iframe_response = requests.get(iframe_url, timeout=10)
                        if iframe_response.status_code == 200:
                            print(f"✅ iframe请求成功：{iframe_url}")
                            # 检查iframe内容是否包含文章数据
                            iframe_soup = BeautifulSoup(iframe_response.content, 'html.parser')
                            iframe_articles = iframe_soup.find_all(['li', 'div'], class_=lambda x: x and 'article' in x)
                            if iframe_articles:
                                print(f"✅ 在iframe中找到 {len(iframe_articles)} 个文章项")
                                # 打印第一个文章项
                                if iframe_articles:
                                    print(f"📝 iframe文章项预览：{iframe_articles[0].prettify()[:500]}...")
                            break
                    except Exception as e:
                        print(f"⚠️  访问iframe失败：{e}")
        
        # 尝试检查页面中所有可能的文章容器
        if not policy_items:
            print("🔍 尝试检查页面中所有可能的文章容器...")
            # 查找所有可能包含文章的容器
            possible_containers = soup.find_all(['div', 'section', 'main'], class_=lambda x: x and any(keyword in x for keyword in ['content', 'article', 'list', 'news', 'body', 'main']))
            
            for i, container in enumerate(possible_containers):
                # 检查容器是否包含链接和日期
                links = container.find_all('a')
                if links:
                    # 检查是否有日期信息
                    container_text = container.get_text()
                    if re.search(r'\d{4}-\d{2}-\d{2}', container_text):
                        print(f"📝 发现可能包含文章的容器 #{i}，包含 {len(links)} 个链接")
                        print(f"📝 容器内容预览：{container.prettify()[:1000]}...")
                        # 提取可能的文章项
                        for link in links[:5]:
                            text = link.get_text(strip=True)
                            href = link.get('href', '')
                            if text and href:
                                print(f"📝 链接：{text[:50]}... {href}")
                        break
        
        # 尝试直接分析页面中的所有链接
        if not policy_items:
            print("🔍 尝试分析页面中的所有链接...")
            all_links = soup.find_all('a')
            print(f"📝 找到 {len(all_links)} 个链接")
            
            # 过滤出可能的政策解读文章链接
            for link in all_links:
                text = link.get_text(strip=True)
                href = link.get('href', '')
                
                if (text and href and 
                    not any(keyword in text for keyword in ['首页', '简', '繁', 'EN', '登录', '个人中心', '退出', '邮箱', '无障碍', '全国人大', '全国政协', '国家监察委员会', '最高人民法院', '最高人民检察院']) and
                    ('zhengce' in href or 'jiedu' in href)):
                    
                    print(f"📝 可能的政策解读链接：{text[:50]}... {href}")
                    # 查找链接附近的日期
                    parent = link.find_parent(['li', 'div', 'p'])
                    if parent:
                        parent_text = parent.get_text()
                        date_match = re.search(r'\d{4}-\d{2}-\d{2}', parent_text)
                        if date_match:
                            print(f"✅ 找到带日期的政策解读链接：{text[:50]}... 日期：{date_match.group(0)}")
                            policy_items.append(parent)
                            if len(policy_items) >= 5:
                                break
        
        # 尝试检查页面中是否有与list-1-ajax-id相关的AJAX请求
        json_url = None
        if not policy_items:
            print("🔍 尝试检查页面中是否有与list-1-ajax-id相关的AJAX请求...")
            # 查找所有script标签
            scripts = soup.find_all('script')
            for i, script in enumerate(scripts):
                script_content = script.string
                if script_content:
                    # 查找与list-1-ajax-id相关的代码
                    if 'list-1-ajax-id' in script_content:
                        print(f"📝 发现与list-1-ajax-id相关的script标签 #{i}，长度：{len(script_content)}...")
                        print(f"📝 script内容预览：{script_content[:2000]}...")
                        # 尝试提取JSON文件URL
                        import re
                        json_match = re.search(r'url:\s*["\']([^"\']+)ZCJD_QZ\.json["\']', script_content)
                        if json_match:
                            json_path = json_match.group(1) + "ZCJD_QZ.json"
                            print(f"📝 提取到JSON文件路径：{json_path}")
                            # 转换为绝对路径
                            if json_path.startswith('./'):
                                json_url = f"https://www.gov.cn/zhengce/jiedu/{json_path[2:]}"
                            else:
                                json_url = f"https://www.gov.cn/zhengce/jiedu/{json_path}"
                            print(f"✅ 构建绝对JSON文件URL：{json_url}")
                        break
        
        # 尝试访问找到的JSON数据文件
        json_policies = []
        try:
            print("🔍 尝试访问找到的JSON数据文件...")
            # 使用提取的URL或默认URL
            if not json_url:
                json_url = "https://www.gov.cn/zhengce/jiedu/ZCJD_QZ.json"
            
            print(f"📝 尝试访问JSON文件：{json_url}")
            response = requests.get(json_url, timeout=15)
            if response.status_code == 200:
                print(f"✅ JSON请求成功：{json_url}")
                print(f"📝 JSON响应内容预览：{response.text[:500]}...")
                # 尝试解析JSON
                try:
                    import json
                    data = response.json()
                    print("✅ 成功解析JSON数据")
                    
                    # 检查数据结构
                    if isinstance(data, list):
                        print(f"✅ 发现文章列表数据，包含 {len(data)} 个文章")
                        # 遍历文章数据
                        for article in data:
                            # 检查文章数据结构
                            if isinstance(article, dict) and 'TITLE' in article and 'URL' in article and 'DOCRELPUBTIME' in article:
                                # 构建政策数据
                                pub_at = None
                                try:
                                    pub_at = datetime.strptime(article['DOCRELPUBTIME'], '%Y-%m-%d').date()
                                except Exception as e:
                                    print(f"⚠️  解析日期失败：{e}")
                                
                                if pub_at:
                                    # 检查是否是前一天的文章
                                    if pub_at == yesterday:
                                        policy_data = {
                                            'title': article['TITLE'],
                                            'url': article['URL'] if article['URL'].startswith('http') else f"https://www.gov.cn{article['URL']}",
                                            'pub_at': pub_at,
                                            'content': '',  # 可以后续实现详情页抓取
                                            'selected': False,
                                            'category': '',
                                            'source': '中国政府网'
                                        }
                                        json_policies.append(policy_data)
                                        print(f"✅ 找到目标日期文章：{article['TITLE'][:50]}... 日期：{article['DOCRELPUBTIME']}")
                        
                        print(f"✅ 总共找到 {len(json_policies)} 条目标日期的文章")
                        
                        if json_policies:
                            print(f"✅ 使用JSON数据构建政策列表，包含 {len(json_policies)} 条数据")
                            print(f"✅ 中国政府网政策解读爬虫：成功抓取 {len(json_policies)} 条前一天数据")
                            return json_policies
                    else:
                        print(f"📝 数据结构：{type(data)}")
                        if isinstance(data, dict):
                            print(f"📝 字典键：{list(data.keys())}")
                except Exception as e:
                    print(f"⚠️  解析JSON失败：{e}")
            else:
                print(f"⚠️  JSON请求失败：{json_url}，状态码：{response.status_code}")
        except Exception as e:
            print(f"⚠️  访问JSON文件失败：{e}")
        
        # 最后，尝试打印整个页面的前3000个字符，详细了解页面结构
        if not policy_items:
            print("⚠️  仍然没有找到文章项，打印页面前3000个字符详细了解结构...")
            page_preview = soup.prettify()[:3000]
            print(f"📝 页面预览：{page_preview}...")
        
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
            # 首先尝试用户提供的xpath对应的结构：h4/span
            date_selectors = [
                'h4 > span',         # h4下的span元素（用户提供的xpath结构）
                '.date',            # class为date的元素
                'span.date',        # span标签且class为date
                '.time',            # class为time的元素
                'span.time',        # span标签且class为time
                'span'              # 所有span元素
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
