
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
import time

# Selenium 为可选依赖
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

TARGET_URL = "https://www.miit.gov.cn/search/zcwjk.html?websiteid=110000000000000&pg=&p=&tpl=14&category=183&q="


def scrape_data():
    policies = []
    url = TARGET_URL
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        # 使用前一天的日期
        yesterday = today - timedelta(days=1)
        # yesterday = datetime(2026, 2, 24).date()  # 测试用户提到的日期
        print(f"Date (Beijing): {today}")
        print(f"Target date: {yesterday}")
        
        print("Note: This site uses dynamic loading, trying different approaches...")
        
        # 尝试直接构造搜索URL，包含日期参数
        search_url = f"https://www.miit.gov.cn/search/zcwjk.html?websiteid=110000000000000&pg=10&p=1&tpl=14&category=183&q=&begin={yesterday}&end={yesterday}"
        print(f"Trying search URL: {search_url}")
        
        # 尝试直接搜索用户提到的具体文件
        specific_url = f"https://www.miit.gov.cn/search/zcwjk.html?websiteid=110000000000000&pg=10&p=1&tpl=14&category=183&q=工业和信息化部办公厅关于公布数字赋能基层减负典型案例名单的通知"
        print(f"Trying specific file URL: {specific_url}")
        
        # 尝试直接调用API
        print("\nTrying API approach...")
        api_url = "https://www.miit.gov.cn/search-front-server/api/search/info"
        
        # 构建查询参数 - 基于search.js的分析
        # 先使用简单搜索词测试API是否能返回结果
        params = {
            "websiteid": "110000000000000",
            "scope": "basic",
            "q": "数字赋能基层减负",
            "pg": 10,
            "p": 1,
            "cateid": "183",
            "pos": "title_text,infocontent,titlepy",
            "_cus_eq_typename": "",  # 公文种类
            "_cus_eq_publishgroupname": "",  # 发布机构
            "_cus_eq_themename": "",  # 主题分类
            # 暂时移除日期限制，测试API是否能返回结果
            "dateField": "deploytime",
            "selectFields": "title,content,deploytime,_index,url,cdate,infoextends,infocontentattribute,columnname,filenumbername,publishgroupname,publishtime,metaid,bexxgk,columnid,xxgkextend1,xxgkextend2,themename,typename,indexcode,createdate",
            "group": "distinct",
            "highlightConfigs": "[{\"field\":\"infocontent\",\"numberOfFragments\":2,\"fragmentOffset\":0,\"fragmentSize\":30,\"noMatchSize\":145}]",
            "highlightFields": "title_text,infocontent,webid",
            "level": 6,
            "sortFields": "[{\"name\":\"deploytime\",\"type\":\"desc\"}]"
        }
        
        # 移除Content-Type头，使用默认的GET请求
        if 'Content-Type' in headers:
            del headers['Content-Type']
        response = requests.get(api_url, params=params, headers=headers, timeout=30)
        print(f"API Response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"API Response received: {type(data)}")
                # 保存API响应以便分析
                with open('miit_api_response.json', 'w', encoding='utf-8') as f:
                    import json
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print("Saved API response to miit_api_response.json")
                
                # 处理API响应
                if data and 'data' in data and 'searchResult' in data['data']:
                    search_result = data['data']['searchResult']
                    print(f"Total hits: {search_result.get('totalHits', 0)}")
                    
                    if 'dataResults' in search_result and search_result['dataResults']:
                        data_results = search_result['dataResults']
                        print(f"Found {len(data_results)} items")
                        
                        for result in data_results:
                            try:
                                # 处理结果数据
                                if 'groupData' in result and result['groupData']:
                                    group_data = result['groupData'][0]['data']
                                else:
                                    group_data = result['data']
                                
                                title = group_data.get('title', '') or group_data.get('title_text', '')
                                url = group_data.get('url', '')
                                deploytime = group_data.get('deploytime', '')
                                
                                if not title or not url:
                                    continue
                                
                                # 构建完整URL
                                if url.startswith('/'):
                                    article_url = "https://www.miit.gov.cn" + url
                                else:
                                    article_url = url
                                
                                # 解析日期
                                pub_at = None
                                if deploytime:
                                    try:
                                        # 处理不同格式的日期
                                        if isinstance(deploytime, str):
                                            if len(deploytime) == 10:
                                                pub_at = datetime.strptime(deploytime, '%Y-%m-%d').date()
                                            elif len(deploytime) == 19:
                                                pub_at = datetime.strptime(deploytime, '%Y-%m-%d %H:%M:%S').date()
                                    except ValueError:
                                        pass
                                
                                if pub_at != yesterday:
                                    continue
                                
                                # 抓取内容
                                content = ""
                                try:
                                    detail_resp = requests.get(article_url, headers=headers, timeout=15)
                                    detail_soup = BeautifulSoup(detail_resp.content, 'html.parser')
                                    # 尝试多种内容选择器
                                    content_elem = detail_soup.select_one('.content') or detail_soup.select_one('#content') or detail_soup.select_one('.article-content') or detail_soup.select_one('.TRS_Editor')
                                    if content_elem:
                                        content = content_elem.get_text(strip=True)
                                except Exception as e:
                                    print(f"  Error fetching content: {e}")
                                    pass
                                
                                policy_data = {
                                    'title': title,
                                    'url': article_url,
                                    'pub_at': pub_at,
                                    'content': content,
                                    'selected': False,
                                    'category': '文件库',
                                    'source': '工信部'
                                }
                                policies.append(policy_data)
                                print(f"  Found: {title}")
                                print(f"  URL: {article_url}")
                                print(f"  Date: {pub_at}")
                                print(f"  Content length: {len(content)} chars")
                                print("-" * 60)
                                
                            except Exception as e:
                                print(f"  Error processing API result: {e}")
                                continue
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                # 保存原始响应
                with open('miit_api_raw.txt', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("Saved raw API response to miit_api_raw.txt")
        
        # 尝试传统方法 - 日期筛选
        response = requests.get(search_url, headers=headers, timeout=30)
        print(f"\nTraditional approach - Response status: {response.status_code}")
        
        if response.status_code == 200:
            # 保存页面内容以便分析
            with open('miit_search_date.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("Saved date search page to miit_search_date.html")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            print(f"Page title: {soup.title.string}")
            
            # 查找搜索结果容器
            search_content = soup.find('div', class_='search-conent')
            if search_content:
                print("Found search_content div")
                
                # 查找所有可能的文章项
                items = search_content.find_all(['div', 'li'], class_=re.compile('result|item|article|list'))
                print(f"Found {len(items)} potential items")
        
        # 尝试直接搜索具体文件
        print(f"\nTrying specific file search...")
        response = requests.get(specific_url, headers=headers, timeout=30)
        print(f"Specific search response status: {response.status_code}")
        
        if response.status_code == 200:
            # 保存页面内容以便分析
            with open('miit_search_specific.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("Saved specific search page to miit_search_specific.html")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            print(f"Page title: {soup.title.string}")
            
            # 查找搜索结果容器
            search_content = soup.find('div', class_='search-conent')
            if search_content:
                print("Found search_content div")
                
                # 查找所有可能的文章项
                items = search_content.find_all(['div', 'li'], class_=re.compile('result|item|article|list'))
                print(f"Found {len(items)} potential items")
                
                for item in items:
                    try:
                        # 查找标题和链接
                        title_elem = item.find('h3') or item.find('a')
                        if title_elem:
                            if title_elem.name == 'h3':
                                a_tag = title_elem.find('a')
                            else:
                                a_tag = title_elem
                            
                            if a_tag:
                                title = a_tag.get('title', '').strip() or a_tag.get_text(strip=True)
                                href = a_tag.get('href', '')
                                
                                if not title or len(title) < 5:
                                    continue
                                
                                # 构建完整URL
                                if href.startswith('/'):
                                    article_url = "https://www.miit.gov.cn" + href
                                elif not href.startswith('http'):
                                    article_url = "https://www.miit.gov.cn/search/" + href
                                else:
                                    article_url = href
                                
                                # 查找日期
                                pub_at = None
                                # 尝试从不同位置查找日期
                                date_elems = item.find_all(['span', 'div'], class_=re.compile('date|time|发布日期'))
                                for date_elem in date_elems:
                                    date_text = date_elem.get_text(strip=True)
                                    date_match = re.search(r'(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})', date_text)
                                    if date_match:
                                        try:
                                            pub_at = datetime.strptime(f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}", '%Y-%m-%d').date()
                                            break
                                        except ValueError:
                                            pass
                                
                                # 如果没找到日期，尝试从文本中提取
                                if not pub_at:
                                    date_match = re.search(r'(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})', item.get_text())
                                    if date_match:
                                        try:
                                            pub_at = datetime.strptime(f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}", '%Y-%m-%d').date()
                                        except ValueError:
                                            pass
                                
                                # 抓取内容
                                content = ""
                                try:
                                    detail_resp = requests.get(article_url, headers=headers, timeout=15)
                                    detail_soup = BeautifulSoup(detail_resp.content, 'html.parser')
                                    # 尝试多种内容选择器
                                    content_elem = detail_soup.select_one('.content') or detail_soup.select_one('#content') or detail_soup.select_one('.article-content') or detail_soup.select_one('.TRS_Editor')
                                    if content_elem:
                                        content = content_elem.get_text(strip=True)
                                except Exception as e:
                                    print(f"  Error fetching content: {e}")
                                    pass
                                
                                policy_data = {
                                    'title': title,
                                    'url': article_url,
                                    'pub_at': pub_at,
                                    'content': content,
                                    'selected': False,
                                    'category': '文件库',
                                    'source': '工信部'
                                }
                                policies.append(policy_data)
                                print(f"  Found: {title}")
                                print(f"  URL: {article_url}")
                                print(f"  Date: {pub_at}")
                                print(f"  Content length: {len(content)} chars")
                                print("-" * 60)
                                
                    except Exception as e:
                        print(f"  Error processing item: {e}")
                        continue
            else:
                print("No search content found")
        
        # 尝试另一种方法：直接访问可能的列表页
        alternative_urls = [
            "https://www.miit.gov.cn/zwgk/zcwj/index.html",
            "https://www.miit.gov.cn/zwgk/zcwj/zfxxgk/index.html",
            "https://www.miit.gov.cn/search/xzgfxwjnew/index.html?websiteid=110000000000000&pg=&p=&tpl=14&category=51&q="  # 行政规范性文件实际内容
        ]
        
        for alt_url in alternative_urls:
            if policies:
                break
            
            print(f"\nTrying alternative URL: {alt_url}")
            try:
                response = requests.get(alt_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    # 保存页面内容以便分析
                    if 'xzgfxwj' in alt_url:
                        with open('miit_xzgfxwj.html', 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        print("Saved xzgfxwj page to miit_xzgfxwj.html")
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    items = soup.find_all('li')
                    print(f"Found {len(items)} items")
                    
                    for item in items:
                        try:
                            a_tag = item.find('a')
                            if not a_tag:
                                continue
                            
                            title = a_tag.get('title', '').strip() or a_tag.get_text(strip=True)
                            href = a_tag.get('href', '')
                            
                            if not title or len(title) < 5:
                                continue
                            
                            if href.startswith('/'):
                                article_url = "https://www.miit.gov.cn" + href
                            else:
                                article_url = href
                            
                            # 查找日期
                            pub_at = None
                            date_match = re.search(r'(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})', item.get_text())
                            if date_match:
                                try:
                                    pub_at = datetime.strptime(f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}", '%Y-%m-%d').date()
                                except ValueError:
                                    pass
                            
                            if pub_at != yesterday:
                                continue
                            
                            # 抓取内容
                            content = ""
                            try:
                                detail_resp = requests.get(article_url, headers=headers, timeout=15)
                                detail_soup = BeautifulSoup(detail_resp.content, 'html.parser')
                                content_elem = detail_soup.select_one('.content') or detail_soup.select_one('#content')
                                if content_elem:
                                    content = content_elem.get_text(strip=True)
                            except Exception:
                                pass
                            
                            policy_data = {
                                'title': title,
                                'url': article_url,
                                'pub_at': pub_at,
                                'content': content,
                                'selected': False,
                                'category': '文件库',
                                'source': '工信部'
                            }
                            policies.append(policy_data)
                            print(f"  Found: {title}")
                            print(f"  URL: {article_url}")
                            print(f"  Date: {pub_at}")
                            print(f"  Content length: {len(content)} chars")
                            print("-" * 60)
                            
                        except Exception as e:
                            print(f"  Error processing alternative item: {e}")
                            continue
            except Exception as e:
                print(f"Error with alternative URL {alt_url}: {e}")
                continue
        
        # 尝试使用Selenium获取动态内容
        if not policies and SELENIUM_AVAILABLE:
            print("\nTrying Selenium approach...")
            try:
                # 配置Chrome选项
                chrome_options = Options()
                chrome_options.add_argument('--headless')  # 无头模式
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument(f'user-agent={headers["User-Agent"]}')
                
                # 初始化浏览器 - 使用webdriver-manager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(60)
                
                # 访问搜索页面
                search_url = f"https://www.miit.gov.cn/search/zcwjk.html?websiteid=110000000000000&pg=10&p=1&tpl=14&category=183&q=数字赋能基层减负"
                print(f"Selenium visiting: {search_url}")
                driver.get(search_url)
                
                # 等待页面加载
                time.sleep(5)  # 给JavaScript时间加载内容
                
                # 保存页面内容
                page_source = driver.page_source
                with open('miit_selenium_page.html', 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print("Saved Selenium page to miit_selenium_page.html")
                
                # 解析页面
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # 查找搜索结果
                search_content = soup.find('div', class_='search-con')
                if search_content:
                    print("Found search-con div with Selenium")
                    
                    # 查找所有文章项
                    items = search_content.find_all('div', class_='jcse-result-box')
                    print(f"Found {len(items)} items with Selenium")
                    
                    for item in items:
                        try:
                            # 查找标题和链接
                            title_elem = item.find('a')
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                href = title_elem.get('href', '')
                                
                                if not title or len(title) < 5:
                                    continue
                                
                                # 构建完整URL
                                if href.startswith('/'):
                                    article_url = "https://www.miit.gov.cn" + href
                                else:
                                    article_url = href
                                
                                # 查找日期
                                pub_at = None
                                date_elem = item.find('span', text=re.compile(r'\d{4}-\d{2}-\d{2}'))
                                if date_elem:
                                    date_text = date_elem.get_text(strip=True)
                                    date_match = re.search(r'(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})', date_text)
                                    if date_match:
                                        try:
                                            pub_at = datetime.strptime(f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}", '%Y-%m-%d').date()
                                        except ValueError:
                                            pass
                                
                                # 如果没找到日期，尝试从文本中提取
                                if not pub_at:
                                    date_match = re.search(r'(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})', item.get_text())
                                    if date_match:
                                        try:
                                            pub_at = datetime.strptime(f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}", '%Y-%m-%d').date()
                                        except ValueError:
                                            pass
                                
                                if pub_at != yesterday:
                                    continue
                                
                                # 抓取内容
                                content = ""
                                try:
                                    driver.get(article_url)
                                    time.sleep(5)  # 增加等待时间
                                    detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                    # 尝试多种内容选择器
                                    content_selectors = [
                                        '.content',
                                        '#content',
                                        '.article-content',
                                        '.TRS_Editor',
                                        '.article-body',
                                        '.main-content',
                                        '.article-main'
                                    ]
                                    for selector in content_selectors:
                                        content_elem = detail_soup.select_one(selector)
                                        if content_elem:
                                            content = content_elem.get_text(strip=True)
                                            if content:
                                                break
                                    # 如果还是没有找到，尝试获取所有p标签内容
                                    if not content:
                                        paragraphs = detail_soup.find_all('p')
                                        if paragraphs:
                                            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                                    print(f"  Content fetched successfully: {len(content) > 0}")
                                except Exception as e:
                                    print(f"  Error fetching content with Selenium: {e}")
                                    pass
                                
                                policy_data = {
                                    'title': title,
                                    'url': article_url,
                                    'pub_at': pub_at,
                                    'content': content,
                                    'selected': False,
                                    'category': '文件库',
                                    'source': '工信部'
                                }
                                policies.append(policy_data)
                                print(f"  Found with Selenium: {title}")
                                print(f"  URL: {article_url}")
                                print(f"  Date: {pub_at}")
                                print(f"  Content length: {len(content)} chars")
                                print("-" * 60)
                                
                        except Exception as e:
                            print(f"  Error processing Selenium item: {e}")
                            continue
                else:
                    print("No search content found with Selenium")
                
                # 关闭浏览器
                driver.quit()
                
            except Exception as e:
                print(f"Selenium error: {e}")
                try:
                    driver.quit()
                except:
                    pass
        elif not policies and not SELENIUM_AVAILABLE:
            print("\nSelenium not available, skipping Selenium approach")
        
        print(f"Found {len(policies)} items for target date")
        
    except Exception as e:
        print(f"Error: {e}")
    
    return policies


def save_to_supabase(data_list):
    try:
        from db_utils import save_to_policy
        return save_to_policy(data_list, "工信部_文件库")
    except Exception as e:
        print(f"Error saving to database: {e}")
        return data_list


def run():
    try:
        data = scrape_data()
        save_to_supabase(data)
        return data
    except Exception as e:
        print(f"Run failed: {e}")
        return []


def run_test():
    """测试版本"""
    print("=" * 60)
    print("🧪 Testing MIIT File Library Crawler")
    print("=" * 60)
    
    try:
        tz_utc8 = timezone(timedelta(hours=8))
        today = datetime.now(tz_utc8).date()
        yesterday = today - timedelta(days=1)
        print(f"Date (Beijing): {today}")
        print(f"Target date: {yesterday}")
        
        # 测试直接搜索URL
        search_url = f"https://www.miit.gov.cn/search/zcwjk.html?websiteid=110000000000000&pg=10&p=1&tpl=14&category=183&q=&begin={yesterday}&end={yesterday}"
        print(f"Testing search URL: {search_url}")
        
        response = requests.get(search_url, headers=headers, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            # 保存整个页面
            with open('miit_full_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("Saved full page to miit_full_page.html")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            print(f"Page title: {soup.title.string}")
            
            # 查找搜索结果
            search_content = soup.find('div', class_='search-conent')
            if search_content:
                print("Found search content div")
                # 保存内容以便分析
                with open('miit_search_result.html', 'w', encoding='utf-8') as f:
                    f.write(str(search_content))
                print("Saved search content to miit_search_result.html")
            else:
                print("No search content found")
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    # 默认运行正式版本
    run()
    # 如需运行测试版本，取消下面的注释
    # run_test()

