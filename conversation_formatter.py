"""
对话格式转换模块
"""
from typing import Dict, List


class ConversationFormatter:
    """对话格式化器"""
    
    @staticmethod
    def format_conversation(language: str, source_text: str, target_text: str) -> Dict:
        """
        将翻译对转换为对话格式
        
        Args:
            language: 源语言名称
            source_text: 源语言文本
            target_text: 中文文本
            
        Returns:
            对话格式的字典
        """
        # 构建user消息：用{语言}怎么说：{中文文本}
        user_content = f"用{language}怎么说：{target_text}"
        
        # assistant消息：源语言文本
        assistant_content = source_text
        
        # 构建对话格式
        conversation = {
            "messages": [
                {
                    "role": "user",
                    "content": user_content
                },
                {
                    "role": "assistant",
                    "content": assistant_content
                }
            ]
        }
        
        return conversation
    
    @staticmethod
    def format_conversation_alternative(language: str, source_text: str, target_text: str) -> Dict:
        """
        将翻译对转换为对话格式（替代格式：包含源语言和目标语言）
        
        Args:
            language: 源语言名称
            source_text: 源语言文本
            target_text: 中文文本
            
        Returns:
            对话格式的字典
        """
        # 构建user消息：包含源语言和中文
        user_content = f"{source_text} -> {target_text}"
        
        # assistant消息：确认翻译
        assistant_content = f"这是{language}到中文的翻译。"
        
        conversation = {
            "messages": [
                {
                    "role": "user",
                    "content": user_content
                },
                {
                    "role": "assistant",
                    "content": assistant_content
                }
            ]
        }
        
        return conversation
