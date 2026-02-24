import os
import requests
import json
from datetime import datetime


class FeishuNotifier:
    """飞书机器人通知器"""
    
    def __init__(self, webhook_url=None):
        """初始化飞书通知器
        
        Args:
            webhook_url: 飞书机器人 webhook 地址，如果为 None 则从环境变量 FEISHU_BOT_WEBHOOK 获取
        """
        self.webhook_url = webhook_url or os.getenv('FEISHU_BOT_WEBHOOK')
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            print("⚠️  飞书机器人未配置（FEISHU_BOT_WEBHOOK 环境变量未设置）")
    
    def send_text(self, text):
        """发送文本消息
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            return False
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        return self._send(payload)
    
    def send_rich_text(self, title, content):
        """发送富文本消息
        
        Args:
            title: 标题
            content: 富文本内容列表，格式为 [
                [{"tag": "text", "text": "文本"}, {"tag": "a", "text": "链接", "href": "url"}],
                ...
            ]
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            return False
        
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content
                    }
                }
            }
        }
        
        return self._send(payload)
    
    def send_interactive(self, card):
        """发送交互式卡片消息
        
        Args:
            card: 卡片内容（dict 格式）
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            return False
        
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        return self._send(payload)
    
    def send_crawler_result(self, results, start_time, end_time):
        """发送爬虫执行结果
        
        Args:
            results: 爬虫执行结果字典
            start_time: 开始时间 (datetime)
            end_time: 结束时间 (datetime)
            
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            return False
        
        total_crawl = sum(r.get('crawl_count', 0) for r in results.values())
        total_write = sum(r.get('write_count', 0) for r in results.values())
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        total_time = (end_time - start_time).total_seconds()
        
        # 构建富文本内容
        content = []
        
        # 第一行：执行时间
        content.append([
            {"tag": "text", "text": "🕐 执行时间："},
            {"tag": "text", "text": f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}"}
        ])
        
        # 第二行：执行时长
        content.append([
            {"tag": "text", "text": "⏱️  执行时长："},
            {"tag": "text", "text": f"{total_time:.2f} 秒"}
        ])
        
        # 空行
        content.append([])
        
        # 统计信息
        content.append([
            {"tag": "text", "text": "📊 统计信息："}
        ])
        content.append([
            {"tag": "text", "text": f"   ✅ 成功：{success_count} 个"}
        ])
        content.append([
            {"tag": "text", "text": f"   ❌ 失败：{error_count} 个"}
        ])
        content.append([
            {"tag": "text", "text": f"   📦 总抓取：{total_crawl} 条"}
        ])
        content.append([
            {"tag": "text", "text": f"   💾 总写入：{total_write} 条"}
        ])
        
        # 空行
        content.append([])
        
        # 各爬虫详情
        content.append([
            {"tag": "text", "text": "📋 各爬虫详情："}
        ])
        
        for name, result in results.items():
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            line = [
                {"tag": "text", "text": f"   {status_emoji} {name}："}
            ]
            if result['status'] == 'success':
                line.append({"tag": "text", "text": f"抓取 {result['crawl_count']} 条，写入 {result['write_count']} 条 ({result['execution_time']}s)"})
            else:
                line.append({"tag": "text", "text": f"执行失败 - {result.get('error_message', '未知错误')[:50]}..."})
            content.append(line)
        
        # 发送富文本消息
        title = f"🤖 政策爬虫执行结果 - {end_time.strftime('%Y-%m-%d')}"
        return self.send_rich_text(title, content)
    
    def _send(self, payload):
        """发送消息到飞书
        
        Args:
            payload: 消息 payload
            
        Returns:
            bool: 是否发送成功
        """
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                print("✅ 飞书消息发送成功")
                return True
            else:
                print(f"❌ 飞书消息发送失败：{result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ 飞书消息发送异常：{e}")
            return False


# 全局实例
_notifier = None


def get_notifier():
    """获取飞书通知器全局实例"""
    global _notifier
    if _notifier is None:
        _notifier = FeishuNotifier()
    return _notifier


def send_crawler_result(results, start_time, end_time):
    """发送爬虫执行结果（便捷函数）"""
    notifier = get_notifier()
    return notifier.send_crawler_result(results, start_time, end_time)
