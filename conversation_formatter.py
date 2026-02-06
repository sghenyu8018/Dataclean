"""
对话格式转换模块
"""
import random
from typing import Dict, List


class ConversationFormatter:
    """对话格式化器"""
    
    # 多样化的提问模板
    PROMPT_TEMPLATES = [
        "请把这段话翻译成{lang_name}：",
        "用{lang_name}怎么说：",
        "将以下内容翻译为{lang_name}：",
        "帮我翻译成{lang_name}：",
        "作为新闻媒体翻译专家，请将以下内容翻译为{lang_name}：",
        "请以新闻报道的口吻，将这段话翻译成{lang_name}："
    ]
    
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
        # system消息
        system_content = "你是一个专业的翻译大模型。"
        
        # 随机选择一个提问模板
        template = random.choice(ConversationFormatter.PROMPT_TEMPLATES)
        user_content = template.format(lang_name=language) + target_text
        
        # assistant消息：源语言文本
        assistant_content = source_text
        
        # 构建对话格式
        conversation = {
            "messages": [
                {
                    "role": "system",
                    "content": system_content
                },
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
