import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 导入数据库工具
from db_utils import save_to_policy

# 爬虫配置
TARGET_URL = "https://www.ndrc.gov.cn/xxgk/wjk/"

# ==========================================
# 2. 网页抓取逻辑
# ==========================================
def scrape_data():
    """抓取国家发改委文件库数据
    
    只抓取前一天发布的文章
    例如：运行时是2026年2月18日，只抓取2026年2月17日的文章
    """
    policies = []
    
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
        
        # 直接调用API接口
        print("\n🚀 直接调用API接口获取数据...")
        api_url = "https://fwfx.ndrc.gov.cn/api/query"
        
        # 构建请求参数
        params = {
            'qt': '',  # 搜索关键词
            'tab': 'all',  # 所有文件类型
            'page': 1,  # 页码
            'pageSize': 20,  # 每页数量
            'siteCode': 'bm04000fgk',  # 站点代码
            'key': 'CAB549A94CF659904A7D6B0E8FC8A7E9',  # 密钥
            'startDateStr': yesterday.strftime('%Y-%m-%d'),  # 开始日期
            'endDateStr': yesterday.strftime('%Y-%m-%d'),  # 结束日期
            'timeOption': 2,  # 时间选项：2表示具体日期
            'sort': 'dateDesc'  # 按日期降序排序
        }
        
        # 发送请求
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        # 解析JSON响应
        import json
        data = response.json()
        print(f"✅ API请求成功，状态：{data.get('ok', False)}")
        
        # 处理响应数据
        if data.get('ok', False):
            result_list = data.get('data', {}).get('resultList', [])
            print(f"📋 找到 {len(result_list)} 条数据")
            filtered_count = 0
            
            for item in result_list:
                # 提取数据
                title = item.get('title', '')
                policy_url = item.get('url', '')
                doc_date = item.get('docDate', '')
                
                # 解析日期
                pub_at = None
                if doc_date:
                    try:
                        pub_at = datetime.strptime(doc_date.split(' ')[0], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                # 过滤：只保留目标日期的文章
                if pub_at == yesterday:
                    # 提取内容（这里只是示例，实际可能需要进入详情页抓取）
                    content = ""  # 可以后续实现详情页抓取
                    
                    # 构建政策数据
                    policy_data = {
                        'title': title,
                        'url': policy_url,
                        'pub_at': pub_at,
                        'content': content,
                        'selected': False,
                        'category': '',
                        'source': '国家发展和改革委员会发改委文件'
                    }
                    
                    policies.append(policy_data)
                else:
                    filtered_count += 1
        else:
            print(f"❌ API请求失败：{data.get('msg', '未知错误')}")
        
        print(f"✅ 国家发改委爬虫：成功抓取 {len(policies)} 条前一天数据")
        print(f"⏭️  过滤掉 {filtered_count} 条非目标日期的数据")
        
    except Exception as e:
        print(f"❌ 国家发改委爬虫：抓取失败 - {e}")
    
    return policies

# ==========================================
# 3. 数据入库逻辑
# ==========================================
def save_to_supabase(data_list):
    """保存数据到数据库
    
    使用统一的数据库工具函数
    """
    return save_to_policy(data_list, "国家发改委爬虫")

# ==========================================
# 主函数
# ==========================================
def run():
    """运行国家发改委爬虫"""
    try:
        data = scrape_data()
        result = save_to_supabase(data)
        return result
    except Exception as e:
        print(f"❌ 国家发改委爬虫：运行过程中发生未捕获的异常 - {e}")
        return []

if __name__ == "__main__":
    run()
