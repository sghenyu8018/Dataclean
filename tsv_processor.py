"""
TSV文件处理模块
"""
import csv
from pathlib import Path
from typing import List, Tuple, Optional, Iterator
from langdetect import detect, LangDetectException
from config import detect_language_from_filename, load_language_config


class TSVProcessor:
    """TSV文件处理器"""
    
    def __init__(self, input_dir: str, encoding: str = "utf-8", language_map: dict = None):
        """
        初始化TSV处理器
        
        Args:
            input_dir: 输入文件夹路径
            encoding: 文件编码
            language_map: 语言映射字典
        """
        self.input_dir = Path(input_dir)
        self.encoding = encoding
        self.language_map = language_map or {}
        
    def scan_tsv_files(self) -> List[Path]:
        """
        扫描文件夹中的所有TSV文件
        
        Returns:
            TSV文件路径列表
        """
        if not self.input_dir.exists():
            raise FileNotFoundError(f"输入文件夹不存在: {self.input_dir}")
        
        tsv_files = list(self.input_dir.glob("*.tsv"))
        if not tsv_files:
            raise ValueError(f"在 {self.input_dir} 中未找到TSV文件")
        
        return sorted(tsv_files)
    
    def read_tsv_file(self, file_path: Path) -> Iterator[Tuple[str, str]]:
        """
        读取TSV文件并返回翻译对
        
        Args:
            file_path: TSV文件路径
            
        Yields:
            (源语言文本, 中文文本) 元组
        """
        # 尝试多种编码
        encodings = [self.encoding, "utf-8-sig", "utf-8", "gbk", "gb2312"]
        
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc, newline='') as f:
                    # 尝试检测分隔符
                    first_line = f.readline()
                    f.seek(0)
                    
                    # 判断是Tab还是其他分隔符
                    if '\t' in first_line:
                        delimiter = '\t'
                    elif ',' in first_line:
                        delimiter = ','
                    else:
                        delimiter = '\t'
                    
                    reader = csv.reader(f, delimiter=delimiter)
                    
                    for row_num, row in enumerate(reader, start=1):
                        # 跳过空行
                        if not row or all(not cell.strip() for cell in row):
                            continue
                        
                        # 确保至少有两列
                        if len(row) < 2:
                            print(f"警告：{file_path} 第 {row_num} 行列数不足，已跳过")
                            continue
                        
                        source_text = row[0].strip()
                        target_text = row[1].strip()
                        
                        # 跳过空值
                        if not source_text or not target_text:
                            continue
                        
                        yield (source_text, target_text)
                
                # 成功读取，跳出编码循环
                break
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"错误：读取文件 {file_path} 时出错: {e}")
                break
        else:
            raise ValueError(f"无法使用任何编码读取文件: {file_path}")
    
    def get_language_from_file(self, file_path: Path) -> Optional[str]:
        """
        从文件获取语言信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            语言名称，如果无法检测则返回None
        """
        filename = file_path.name
        
        # 方法1: 从语言映射配置获取
        if filename in self.language_map:
            return self.language_map[filename]
        
        # 方法2: 从文件名提取
        language = detect_language_from_filename(filename, self.language_map)
        if language:
            return language
        
        # 方法3: 自动检测（从文件内容采样）
        try:
            # 读取前几行进行语言检测
            sample_texts = []
            count = 0
            for source_text, _ in self.read_tsv_file(file_path):
                sample_texts.append(source_text)
                count += 1
                if count >= 10:  # 采样前10条
                    break
            
            if sample_texts:
                # 合并样本文本
                combined_text = ' '.join(sample_texts[:3])  # 使用前3条
                detected_lang = detect(combined_text)
                
                # 将语言代码转换为中文名称
                from config import LANGUAGE_CODE_MAP
                if detected_lang in LANGUAGE_CODE_MAP:
                    return LANGUAGE_CODE_MAP[detected_lang]
                else:
                    return detected_lang.upper()  # 如果不在映射中，返回大写代码
                    
        except LangDetectException:
            pass
        except Exception as e:
            print(f"警告：无法检测文件 {file_path} 的语言: {e}")
        
        return None
    
    def process_all_files(self) -> Iterator[Tuple[str, str, str, str]]:
        """
        处理所有TSV文件
        
        Yields:
            (语言名称, 源语言文本, 中文文本, 文件名) 元组
        """
        tsv_files = self.scan_tsv_files()
        
        for file_path in tsv_files:
            # 获取语言信息
            language = self.get_language_from_file(file_path)
            if not language:
                language = "未知语言"
                print(f"警告：无法识别文件 {file_path.name} 的语言，使用默认值")
            
            # 读取文件内容
            for source_text, target_text in self.read_tsv_file(file_path):
                yield (language, source_text, target_text, file_path.name)
