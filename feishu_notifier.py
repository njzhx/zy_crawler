import os
import sys
import requests
import json
from datetime import datetime
from io import StringIO


class OutputCapturer:
    """控制台输出捕获器"""
    
    def __init__(self):
        self.captured_output = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def start_capture(self):
        """开始捕获输出"""
        self.captured_output = []
        self.string_buffer = StringIO()
        sys.stdout = self.string_buffer
        sys.stderr = self.string_buffer
    
    def stop_capture(self):
        """停止捕获输出并返回捕获的内容"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        output = self.string_buffer.getvalue()
        self.captured_output.append(output)
        return output
    
    def get_full_output(self):
        """获取所有捕获的输出"""
        return ''.join(self.captured_output)


class FeishuNotifier:
    """飞书机器人通知器"""
    
    def __init__(self, webhook_url=None):
        """初始化飞书通知器
        
        Args:
            webhook_url: 飞书机器人 webhook 地址，如果为 None 则从环境变量 FEISHU_BOT_WEBHOOK 获取
        """
        self.webhook_url = webhook_url or os.getenv('FEISHU_BOT_WEBHOOK')
        self.enabled = bool(self.webhook_url)
        self.output_capturer = OutputCapturer()
        
        if not self.enabled:
            print("⚠️  飞书机器人未配置（FEISHU_BOT_WEBHOOK 环境变量未设置）")
    
    def start_capture(self):
        """开始捕获控制台输出"""
        self.output_capturer.start_capture()
    
    def stop_capture(self):
        """停止捕获控制台输出"""
        return self.output_capturer.stop_capture()
    
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
    
    def send_crawler_result(self, results, start_time, end_time, full_log=None):
        """发送爬虫执行结果
        
        Args:
            results: 爬虫执行结果字典
            start_time: 开始时间 (datetime)
            end_time: 结束时间 (datetime)
            full_log: 完整的控制台输出日志
            
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
        
        # 构建卡片内容
        elements = []
        
        # 摘要部分
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🕐 执行时间**\n{start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
        })
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**⏱️ 执行时长**\n{total_time:.2f} 秒"
            }
        })
        
        elements.append({"tag": "hr"})
        
        # 统计信息
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📊 统计信息**\n✅ 成功：{success_count} 个\n❌ 失败：{error_count} 个\n📦 总抓取：{total_crawl} 条\n💾 总写入：{total_write} 条"
            }
        })
        
        elements.append({"tag": "hr"})
        
        # 各爬虫详情
        crawler_details = []
        for name, result in results.items():
            status_emoji = "✅" if result['status'] == 'success' else "❌"
            if result['status'] == 'success':
                crawler_details.append(f"{status_emoji} {name}：抓取 {result['crawl_count']} 条，写入 {result['write_count']} 条 ({result['execution_time']}s)")
            else:
                crawler_details.append(f"{status_emoji} {name}：执行失败 - {result.get('error_message', '未知错误')[:50]}...")
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📋 各爬虫详情**\n" + "\n".join(crawler_details)
            }
        })
        
        # 如果有完整日志，添加到备注
        if full_log:
            # 限制日志长度，避免消息过大
            max_log_length = 2000
            if len(full_log) > max_log_length:
                full_log = full_log[:max_log_length] + "\n\n... (日志过长，已截断)"
            
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": "📝 完整运行日志："
                }
            })
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": full_log
                }
            })
        
        # 构建交互式卡片
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🤖 政策爬虫执行结果 - {end_time.strftime('%Y-%m-%d')}"
                },
                "template": "blue" if error_count == 0 else "red"
            },
            "elements": elements
        }
        
        return self.send_interactive(card)
    
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


def send_crawler_result(results, start_time, end_time, full_log=None):
    """发送爬虫执行结果（便捷函数）"""
    notifier = get_notifier()
    return notifier.send_crawler_result(results, start_time, end_time, full_log)
