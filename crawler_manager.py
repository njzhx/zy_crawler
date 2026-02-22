import time
from datetime import datetime

# ==========================================
# 爬虫管理系统
# 功能：执行多个爬虫，一个爬虫出错不影响其他爬虫
# ==========================================

class CrawlerManager:
    def __init__(self):
        """初始化爬虫管理器"""
        self.crawlers = []
        self.results = {}
    
    def register_crawler(self, name, crawler_func):
        """注册爬虫
        
        Args:
            name: 爬虫名称
            crawler_func: 爬虫执行函数
        """
        self.crawlers.append((name, crawler_func))
        print(f"✅ 已注册爬虫: {name}")
    
    def run_all_crawlers(self):
        """执行所有爬虫
        
        Returns:
            dict: 各爬虫执行结果
        """
        print(f"\n🚀 开始执行爬虫任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        total_start_time = time.time()
        
        for name, crawler_func in self.crawlers:
            print(f"\n📦 开始执行爬虫: {name}")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                # 执行爬虫
                result = crawler_func()
                
                # 记录结果
                execution_time = time.time() - start_time
                self.results[name] = {
                    'status': 'success',
                    'data_count': len(result),
                    'execution_time': round(execution_time, 2),
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"✅ 爬虫 {name} 执行成功")
                print(f"📊 抓取数据: {len(result)} 条")
                print(f"⏱️  执行时间: {round(execution_time, 2)} 秒")
                
            except Exception as e:
                # 捕获异常，确保其他爬虫继续执行
                execution_time = time.time() - start_time
                self.results[name] = {
                    'status': 'error',
                    'error_message': str(e),
                    'execution_time': round(execution_time, 2),
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"❌ 爬虫 {name} 执行失败")
                print(f"💥 错误信息: {str(e)}")
                print(f"⏱️  执行时间: {round(execution_time, 2)} 秒")
            
            print("-" * 40)
        
        total_execution_time = time.time() - total_start_time
        
        print("=" * 60)
        print(f"📋 爬虫执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  总执行时间: {round(total_execution_time, 2)} 秒")
        print(f"📦 执行爬虫数: {len(self.crawlers)}")
        
        # 统计结果
        success_count = sum(1 for r in self.results.values() if r['status'] == 'success')
        error_count = sum(1 for r in self.results.values() if r['status'] == 'error')
        
        print(f"✅ 成功: {success_count} 个")
        print(f"❌ 失败: {error_count} 个")
        
        return self.results
    
    def get_summary(self):
        """获取执行摘要"""
        if not self.results:
            return "尚未执行爬虫任务"
        
        summary = []
        for name, result in self.results.items():
            if result['status'] == 'success':
                summary.append(f"✅ {name}: 成功抓取 {result['data_count']} 条数据")
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
        manager.register_crawler("中国政府网", gov_crawler.run)
        
        # 导入测试爬虫（用于测试错误处理）
        import test_crawler
        manager.register_crawler("测试爬虫", test_crawler.run)
        
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
