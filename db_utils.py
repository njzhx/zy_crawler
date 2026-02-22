import os
from supabase import create_client, Client
from datetime import date

# ==========================================
# 数据库工具模块
# 功能：提供统一的数据库操作功能，避免重复代码
# ==========================================

class DBUtils:
    def __init__(self):
        """初始化数据库工具"""
        self.supabase_url = os.environ.get("SUPABASE_PROJECT_API")
        self.supabase_key = os.environ.get("SUPABASE_ANON_PUBLIC")
        self.client = None
    
    def get_client(self) -> Client:
        """获取 Supabase 客户端
        
        Returns:
            Client: Supabase 客户端实例
        """
        if not self.client:
            if not self.supabase_url or not self.supabase_key:
                raise ValueError("缺少 Supabase 环境变量: SUPABASE_PROJECT_API 或 SUPABASE_ANON_PUBLIC")
            self.client = create_client(self.supabase_url, self.supabase_key)
        return self.client
    
    def process_data(self, data_list):
        """处理数据，准备写入数据库
        
        Args:
            data_list: 原始数据列表
            
        Returns:
            list: 处理后的数据列表
        """
        processed_data = []
        
        for item in data_list:
            processed_item = item.copy()
            
            # 转换日期对象为字符串
            if hasattr(processed_item.get('pub_at'), 'isoformat'):
                processed_item['pub_at'] = processed_item['pub_at'].isoformat()
            
            # 确保必要字段存在
            if 'selected' not in processed_item:
                processed_item['selected'] = False
            
            processed_data.append(processed_item)
        
        return processed_data
    
    def save_to_policy(self, data_list, source_name):
        """保存数据到 policy 表
        
        Args:
            data_list: 数据列表
            source_name: 数据源名称
            
        Returns:
            list: 成功写入的数据列表
        """
        if not data_list:
            print(f"⚠️  {source_name}：没有数据需要写入，跳过。")
            return []
        
        try:
            # 处理数据
            processed_data = self.process_data(data_list)
            
            # 获取客户端
            supabase = self.get_client()
            
            # 尝试写入数据（不使用 on_conflict，避免约束错误）
            # 先获取现有数据，然后进行去重
            success_count = 0
            
            for item in processed_data:
                try:
                    # 检查是否已存在
                    existing = supabase.table("policy").select("id").eq("title", item.get("title")).execute()
                    
                    if existing.data:
                        # 已存在，更新数据
                        response = supabase.table("policy").update(item).eq("title", item.get("title")).execute()
                    else:
                        # 不存在，插入数据
                        response = supabase.table("policy").insert(item).execute()
                    
                    success_count += 1
                    
                except Exception as item_e:
                    print(f"⚠️  {source_name}：单条数据处理失败 - {item_e}")
                    continue
            
            print(f"✅ {source_name}：成功写入 {success_count} 条数据到 Supabase")
            return data_list[:success_count]
            
        except Exception as e:
            print(f"❌ {source_name}：数据库写入失败 - {e}")
            return []

# 创建全局实例
db_utils = DBUtils()

# 便捷函数
def save_to_policy(data_list, source_name):
    """便捷函数：保存数据到 policy 表
    
    Args:
        data_list: 数据列表
        source_name: 数据源名称
        
    Returns:
        list: 成功写入的数据列表
    """
    return db_utils.save_to_policy(data_list, source_name)
