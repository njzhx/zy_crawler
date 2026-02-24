import time
import sys
from datetime import datetime
from io import StringIO

# 导入飞书通知模块
try:
    from feishu_notifier import send_crawler_result
except ImportError:
    send_crawler_result = None


class DualOutput:
    """双输出流，同时输出到控制台和缓冲区"""
    
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        self.buffer = StringIO()
    
    def write(self, text):
        self.original_stdout.write(text)
        self.buffer.write(text)
    
    def flush(self):
        self.original_stdout.flush()
        self.buffer.flush()
    
    def getvalue(self):
        return self.buffer.getvalue()


# ==========================================
# 爬虫管理系统
# 功能：执行多个爬虫，一个爬虫出错不影响其他爬虫
# ==========================================

class CrawlerManager:
    def __init__(self):
        """初始化爬虫管理器"""
        self.crawlers = []
        self.results = {}
    
    def register_crawler(self, name, crawler_func, crawler_module):
        """注册爬虫
        
        Args:
            name: 爬虫名称
            crawler_func: 爬虫执行函数
            crawler_module: 爬虫模块对象，用于获取 TARGET_URL
        """
        target_url = getattr(crawler_module, 'TARGET_URL', '')
        self.crawlers.append((name, crawler_func, target_url))
        if target_url:
            print(f"✅ 已注册爬虫: {name} ({target_url})")
        else:
            print(f"✅ 已注册爬虫: {name}")
    
    def run_all_crawlers(self):
        """执行所有爬虫
        
        Returns:
            dict: 各爬虫执行结果
        """
        # 开始捕获输出
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        dual_out = DualOutput(original_stdout)
        dual_err = DualOutput(original_stderr)
        sys.stdout = dual_out
        sys.stderr = dual_err
        
        start_datetime = datetime.now()
        print(f"\n🚀 开始执行爬虫任务 - {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        total_start_time = time.time()
        
        for name, crawler_func, target_url in self.crawlers:
            if target_url:
                print(f"\n📦 开始执行爬虫: {name}")
                print(f"🔗 目标网址: {target_url}")
                print(f"   (HTML: <a href='{target_url}' target='_blank'>{name}</a>)")
            else:
                print(f"\n📦 开始执行爬虫: {name}")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                # 执行爬虫
                result = crawler_func()
                
                # 记录结果
                execution_time = time.time() - start_time
                
                # 区分抓取数量和写入数量
                # 假设 result 包含实际写入的数据（即使写入失败也返回抓取的数据）
                crawl_count = len(result)
                
                self.results[name] = {
                    'status': 'success',
                    'crawl_count': crawl_count,
                    'write_count': crawl_count,  # 暂时使用相同值，后续可从爬虫返回值中获取
                    'execution_time': round(execution_time, 2),
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"✅ 爬虫 {name} 执行成功")
                print(f"📊 抓取数据: {crawl_count} 条")
                print(f"💾 写入数据库: {crawl_count} 条")
                print(f"⏱️  执行时间: {round(execution_time, 2)} 秒")
                
            except Exception as e:
                # 捕获异常，确保其他爬虫继续执行
                execution_time = time.time() - start_time
                self.results[name] = {
                    'status': 'error',
                    'crawl_count': 0,
                    'write_count': 0,
                    'error_message': str(e),
                    'execution_time': round(execution_time, 2),
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"❌ 爬虫 {name} 执行失败")
                print(f"💥 错误信息: {str(e)}")
                print(f"📊 抓取数据: 0 条")
                print(f"💾 写入数据库: 0 条")
                print(f"⏱️  执行时间: {round(execution_time, 2)} 秒")
            
            print("-" * 40)
        
        total_execution_time = time.time() - total_start_time
        end_datetime = datetime.now()
        
        print("=" * 60)
        print(f"📋 爬虫执行完成 - {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  总执行时间: {round(total_execution_time, 2)} 秒")
        print(f"📦 执行爬虫数: {len(self.crawlers)}")
        
        # 统计结果
        success_count = sum(1 for r in self.results.values() if r['status'] == 'success')
        error_count = sum(1 for r in self.results.values() if r['status'] == 'error')
        
        # 统计总抓取和写入数量
        total_crawl = sum(r.get('crawl_count', 0) for r in self.results.values())
        total_write = sum(r.get('write_count', 0) for r in self.results.values())
        
        print(f"✅ 成功: {success_count} 个")
        print(f"❌ 失败: {error_count} 个")
        print(f"📊 总抓取数据: {total_crawl} 条")
        print(f"💾 总写入数据库: {total_write} 条")
        
        # 获取完整日志
        full_log = dual_out.getvalue() + dual_err.getvalue()
        
        # 恢复标准输出
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        # 发送飞书通知
        if send_crawler_result:
            print("\n📤 正在发送飞书通知...")
            send_crawler_result(self.results, start_datetime, end_datetime, full_log)
        
        return self.results
    
    def get_summary(self):
        """获取执行摘要"""
        if not self.results:
            return "尚未执行爬虫任务"
        
        summary = []
        for name, result in self.results.items():
            if result['status'] == 'success':
                summary.append(f"✅ {name}: 抓取 {result['crawl_count']} 条，写入数据库 {result['write_count']} 条")
            else:
                summary.append(f"❌ {name}: 执行失败 - {result['error_message'][:100]}...")
        
        return "\n".join(summary)

# ==========================================
# 主执行逻辑
# ==========================================
if __name__ == "__main__":
    # 创建爬虫管理器
    manager = CrawlerManager()
    
    # 注册爬虫
    # 注意：这里需要根据实际爬虫模块进行导入和注册
    try:
        # 导入中国政府网爬虫
        import gov_crawler
        manager.register_crawler("中国政府网", gov_crawler.run, gov_crawler)
        
        # 导入中国政府网政策解读爬虫
        import gov_interpretation_crawler
        manager.register_crawler("中国政府网政策解读", gov_interpretation_crawler.run, gov_interpretation_crawler)
        
        # 导入国家发改委爬虫
        import ndrc_crawler
        manager.register_crawler("国家发改委", ndrc_crawler.run, ndrc_crawler)
        
        # 导入人民网财经爬虫
        import people_finance_crawler
        manager.register_crawler("人民网财经", people_finance_crawler.run, people_finance_crawler)
        
        # 尝试导入测试爬虫（仅用于测试，非必需）
        try:
            import test_crawler
            manager.register_crawler("测试爬虫", test_crawler.run, test_crawler)
        except ImportError:
            print("⚠️  测试爬虫模块未找到，跳过注册")
        
        # 后续添加其他爬虫时，按照以下格式注册
        # import other_crawler
        # manager.register_crawler("其他网站", other_crawler.run)
        
    except ImportError as e:
        print(f"⚠️  导入爬虫模块失败: {e}")
    
    # 执行所有爬虫
    if manager.crawlers:
        results = manager.run_all_crawlers()
        
        # 打印执行摘要
        print("\n📊 执行摘要:")
        print("=" * 60)
        print(manager.get_summary())
    else:
        print("⚠️  没有注册任何爬虫")
