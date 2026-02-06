"""
数据清洗模块
"""
from typing import List, Tuple, Set
import re


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self, min_length: int = 1, max_length: int = 10000):
        """
        初始化数据清洗器
        
        Args:
            min_length: 最小文本长度
            max_length: 最大文本长度
        """
        self.min_length = min_length
        self.max_length = max_length
        self.seen_pairs: Set[Tuple[str, str]] = set()
    
    def is_valid_text(self, text: str) -> bool:
        """
        检查文本是否有效
        
        Args:
            text: 待检查的文本
            
        Returns:
            是否有效
        """
        if not text or not text.strip():
            return False
        
        # 检查长度
        text_length = len(text.strip())
        if text_length < self.min_length or text_length > self.max_length:
            return False
        
        # 检查是否包含过多空白字符
        if len(text.strip()) == 0:
            return False
        
        # 检查是否全是标点符号或数字
        text_stripped = text.strip()
        if not any(c.isalnum() for c in text_stripped):
            return False
        
        return True
    
    def normalize_text(self, text: str) -> str:
        """
        标准化文本
        
        Args:
            text: 原始文本
            
        Returns:
            标准化后的文本
        """
        # 去除首尾空白
        text = text.strip()
        
        # 规范化空白字符（多个空格/制表符/换行符替换为单个空格）
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def is_duplicate(self, source_text: str, target_text: str) -> bool:
        """
        检查是否为重复的翻译对
        
        Args:
            source_text: 源语言文本
            target_text: 目标语言文本
            
        Returns:
            是否重复
        """
        # 标准化文本
        normalized_source = self.normalize_text(source_text).lower()
        normalized_target = self.normalize_text(target_text).lower()
        
        # 创建唯一键
        pair_key = (normalized_source, normalized_target)
        
        if pair_key in self.seen_pairs:
            return True
        
        self.seen_pairs.add(pair_key)
        return False
    
    def clean(self, language: str, source_text: str, target_text: str) -> Tuple[bool, str, str, bool]:
        """
        清洗单个翻译对
        
        Args:
            language: 语言名称
            source_text: 源语言文本
            target_text: 目标语言文本
            
        Returns:
            (是否有效, 清洗后的源语言文本, 清洗后的目标语言文本, 是否重复)
        """
        # 标准化文本
        source_text = self.normalize_text(source_text)
        target_text = self.normalize_text(target_text)
        
        # 检查有效性
        if not self.is_valid_text(source_text) or not self.is_valid_text(target_text):
            return False, source_text, target_text, False
        
        # 检查重复（在检查前先判断，避免添加到seen_pairs）
        normalized_source = source_text.lower()
        normalized_target = target_text.lower()
        pair_key = (normalized_source, normalized_target)
        is_dup = pair_key in self.seen_pairs
        
        if is_dup:
            return False, source_text, target_text, True
        
        # 不是重复，添加到seen_pairs
        self.seen_pairs.add(pair_key)
        
        return True, source_text, target_text, False
    
    def get_statistics(self) -> dict:
        """
        获取清洗统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "unique_pairs": len(self.seen_pairs),
            "min_length": self.min_length,
            "max_length": self.max_length
        }
    
    def reset(self):
        """重置清洗器状态（清空已见过的对）"""
        self.seen_pairs.clear()
