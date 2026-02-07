# -*- coding: utf-8 -*-
"""
千问翻译检查器
使用阿里千问大模型检查和修复翻译不准确问题
"""
import json
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

try:
    from dashscope import Generation
except ImportError:
    print("警告：未安装dashscope，请运行: pip install dashscope")
    Generation = None


class TranslationChecker:
    """翻译检查器类"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-plus"):
        """
        初始化翻译检查器
        
        Args:
            api_key: DashScope API密钥，如果为None则从环境变量读取
            model: 使用的模型名称，默认qwen-turbo
        """
        if Generation is None:
            raise ImportError("请先安装dashscope: pip install dashscope")
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "需要提供API密钥。可以通过以下方式设置：\n"
                "1. 环境变量: export DASHSCOPE_API_KEY=your_key\n"
                "2. 命令行参数: --api-key your_key"
            )
        
        # 设置API密钥
        os.environ["DASHSCOPE_API_KEY"] = self.api_key
        
        self.model = model
        
        # 模型token限制（根据官方文档配置）
        # 根据阿里云DashScope官方文档（参考：https://help.aliyun.com/zh/model-studio/models）：
        # 
        # 官方规格表：
        # | 模型名称 | 最大上下文长度 | 最大输出长度 | 是否支持超长上下文 | 典型用途 |
        # |---------|---------------|-------------|-------------------|---------|
        # | qwen-turbo | 32,768 tokens | ≤ 8,192 | ❌ 否 | 快速问答、简单摘要、高并发客服 |
        # | qwen-plus  | 32,768 tokens | ≤ 8,192 | ❌ 否 | 内容生成、多轮对话、中等复杂分析 |
        # | qwen-max   | 32,768 tokens（默认） | ≤ 8,192 | ✅ 是（需申请） | 复杂推理、代码、金融法律等高精度任务 |
        # 
        # 代码逻辑说明：
        # - batch_by_tokens() 中判断：current_tokens + record_tokens + reserved_tokens > max_tokens
        # - reserved_tokens = system_tokens + user_prompt_tokens + 500（提示词+缓冲）
        # - max_tokens 表示：输入部分（数据内容 + 提示词）的最大值
        # 
        # 分配策略（总上下文 = 输入 + 输出）：
        # 1. 输入部分：系统提示词(~300) + 用户提示词模板(~200) + 数据内容
        # 2. 输出部分：模型响应（最大输出 ≤ 8,192 tokens，批量处理时需考虑）
        # 3. 安全边界：为输出预留足够空间，避免响应被截断导致JSON解析失败
        #
        # 配置说明：
        # - max_tokens 值 = 总上下文 - 输出预留空间
        # - 所有模型最大输出都是 ≤ 8,192 tokens，输出预留需保守设置（建议7,500-8,000）
        # - 实际数据部分 = max_tokens - reserved_tokens（reserved_tokens ≈ 1000，包含提示词）
        # - 可处理记录数取决于每条记录的实际长度，而非总记录数
        # 
        # 精确计算（32,768 tokens 总上下文）：
        # - 输出预留：7,500 tokens（保守，小于8,192限制）
        # - max_tokens = 32,768 - 7,500 = 25,268 ≈ 24,500（保守取整）
        # - 实际数据部分 ≈ 24,500 - 1,000 = 23,500 tokens
        # - 每条记录约200-300 tokens，可处理约80-120条记录
        self.max_tokens_map = {
            "qwen-turbo": 24500,  # 32,768总上下文：24,500(输入) + 7,500(输出预留) + 768(缓冲) = 32,768
                                   # 最大输出限制：≤ 8,192 tokens（硬限制）
                                   # 实际数据部分：≈ 23,500 tokens（24,500 - 1,000提示词）
                                   # 可处理约80-120条记录（每条200-300 tokens）
                                   # 推荐：快速问答、简单摘要、高并发场景
            "qwen-plus": 24500,  # 32,768总上下文：24,500(输入) + 7,500(输出预留) + 768(缓冲) = 32,768
                                  # 最大输出限制：≤ 8,192 tokens（硬限制）
                                  # 实际数据部分：≈ 23,500 tokens（24,500 - 1,000提示词）
                                  # 可处理约80-120条记录（每条200-300 tokens）
                                  # 推荐：内容生成、多轮对话、中等复杂分析
            "qwen-max": 24500,  # 32,768总上下文：24,500(输入) + 7,500(输出预留) + 768(缓冲) = 32,768
                                 # 最大输出限制：≤ 8,192 tokens（硬限制）
                                 # 实际数据部分：≈ 23,500 tokens（24,500 - 1,000提示词）
                                 # 可处理约80-120条记录（每条200-300 tokens）
                                 # 支持超长上下文扩展（需申请）
                                 # 推荐：复杂推理、代码、金融法律等高精度任务
        }
        self.max_tokens = self.max_tokens_map.get(model, 7000)
        
        # 统计信息
        self.stats = {
            "total": 0,
            "processed": 0,
            "fixed": 0,
            "failed": 0,
            "errors": []
        }
    
    def load_jsonl(self, file_path: str) -> List[Dict]:
        """
        加载JSONL文件
        
        Args:
            file_path: JSONL文件路径
            
        Returns:
            记录列表
        """
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    record['_line_number'] = line_num  # 保存行号用于追踪
                    records.append(record)
                except json.JSONDecodeError as e:
                    print(f"警告：第 {line_num} 行JSON解析失败: {e}")
                    continue
        
        self.stats["total"] = len(records)
        return records
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数
        
        Args:
            text: 文本内容
            
        Returns:
            估算的token数
        """
        # 粗略估算：中文约1.5字符/token，英文约4字符/token
        # 混合文本取平均值约2.5字符/token
        return len(text) // 2 + 50  # 保守估计，加50作为缓冲
    
    def batch_by_tokens(self, records: List[Dict]) -> List[List[Dict]]:
        """
        根据token数量将记录分批
        
        Args:
            records: 记录列表
            
        Returns:
            分批后的记录列表
        """
        batches = []
        current_batch = []
        current_tokens = 0
        
        # 系统提示词的token数
        system_prompt = self._get_system_prompt()
        system_tokens = self.estimate_tokens(system_prompt)
        
        # 用户提示词模板的token数（估算）
        user_prompt_template = self._get_user_prompt_template()
        user_prompt_tokens = self.estimate_tokens(user_prompt_template)
        
        # 预留空间（提示词 + 响应空间）
        reserved_tokens = system_tokens + user_prompt_tokens + 500
        
        for record in records:
            # 估算当前记录的token数
            record_json = json.dumps(record, ensure_ascii=False)
            record_tokens = self.estimate_tokens(record_json)
            
            # 如果加上这条记录会超过限制，则开始新批次
            if current_tokens + record_tokens + reserved_tokens > self.max_tokens:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [record]
                current_tokens = record_tokens
            else:
                current_batch.append(record)
                current_tokens += record_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的翻译质量检查员。请仔细检查以下翻译条目，识别并修正翻译中的问题。

需要检查的问题包括（按优先级排序）：
1. **目标语言错误（严重错误）**：翻译是否使用了正确的目标语言
   - 从user消息中提取目标语言（如"翻译成法语"、"翻译为德语"等）
   - 验证assistant的翻译是否使用了该目标语言
   - 如果语言错误（如要求法语但输出西班牙语），必须立即修正
   - 这是最严重的错误，必须优先检查
2. 翻译准确性：是否准确表达了原文的意思
3. 年份和数字：是否完整保留了原文中的年份、日期、数字等关键信息
4. 语法和拼写：是否有语法错误或拼写错误
5. 文化适应性：翻译是否符合目标语言的表达习惯
6. 格式问题：标点符号、大小写等是否正确

对于每条翻译，请：
- 首先检查目标语言是否正确（从user消息中识别目标语言）
- 如果目标语言错误，标记为严重错误并立即修正
- 如果翻译正确，返回原翻译
- 如果发现问题，提供修正后的翻译
- 简要说明发现的问题

请以JSON格式返回结果，格式如下：
{
  "line_number": 行号,
  "has_issue": true/false,
  "issues": ["问题描述1", "问题描述2"],
  "corrected_translation": "修正后的翻译（如果有问题）",
  "original_translation": "原翻译"
}"""
    
    def _get_user_prompt_template(self) -> str:
        """获取用户提示词模板"""
        return """请检查以下翻译条目：

[翻译条目JSON]

请返回JSON格式的检查结果。"""
    
    def check_batch(self, batch: List[Dict], max_retries: int = 3) -> List[Dict]:
        """
        检查一批翻译
        
        Args:
            batch: 一批记录
            max_retries: 最大重试次数
            
        Returns:
            检查结果列表
        """
        # 构建用户提示词
        batch_json = json.dumps(batch, ensure_ascii=False, indent=2)
        user_prompt = f"""请检查以下翻译条目：

{batch_json}

**重要提示**：
1. 首先从每条记录的user消息中提取目标语言（如"翻译成法语"、"翻译为德语"等）
2. 验证assistant的翻译是否使用了正确的目标语言
3. 如果目标语言错误（如要求法语但输出西班牙语），这是严重错误，必须立即修正
4. 然后检查其他翻译质量问题

请返回JSON数组，每个元素对应一条翻译的检查结果。格式如下：
[
  {{
    "line_number": 行号,
    "has_issue": true/false,
    "issues": ["问题描述（如果是语言错误，请明确标注'严重错误：目标语言错误'）"],
    "corrected_translation": "修正后的翻译",
    "original_translation": "原翻译"
  }}
]"""
        
        for attempt in range(max_retries):
            try:
                response = Generation.call(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    temperature=0.3,  # 降低温度以获得更稳定的结果
                    result_format='message'  # 返回消息格式
                )
                
                if response.status_code == 200:
                    # 提取响应内容
                    result_text = response.output.choices[0].message.content
                    return self._parse_response(result_text, batch)
                else:
                    error_msg = f"API错误 (状态码: {response.status_code}): {response.message}"
                    if attempt < max_retries - 1:
                        print(f"  重试 {attempt + 1}/{max_retries}: {error_msg}")
                        time.sleep(2 ** attempt)  # 指数退避
                    else:
                        print(f"  失败: {error_msg}")
                        self.stats["errors"].append({
                            "batch": len(batch),
                            "error": error_msg
                        })
                        return []
                        
            except Exception as e:
                error_msg = f"调用API时出错: {str(e)}"
                if attempt < max_retries - 1:
                    print(f"  重试 {attempt + 1}/{max_retries}: {error_msg}")
                    time.sleep(2 ** attempt)
                else:
                    print(f"  失败: {error_msg}")
                    self.stats["errors"].append({
                        "batch": len(batch),
                        "error": error_msg
                    })
                    return []
        
        return []
    
    def _parse_response(self, response_text: str, original_batch: List[Dict]) -> List[Dict]:
        """
        解析API响应
        
        Args:
            response_text: API返回的文本
            original_batch: 原始批次记录（用于匹配）
            
        Returns:
            解析后的结果列表
        """
        results = []
        
        # 清理响应文本：移除markdown代码块标记
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:].strip()
        elif cleaned_text.startswith('```'):
            cleaned_text = cleaned_text[3:].strip()
        if cleaned_text.endswith('```'):
            cleaned_text = cleaned_text[:-3].strip()
        
        # 尝试解析JSON数组
        try:
            # 方法1: 直接解析整个文本
            try:
                parsed_results = json.loads(cleaned_text)
                if isinstance(parsed_results, list):
                    return self._process_parsed_results(parsed_results, original_batch)
            except json.JSONDecodeError:
                pass
            
            # 方法2: 提取JSON数组部分
            json_start = cleaned_text.find('[')
            json_end = cleaned_text.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = cleaned_text[json_start:json_end]
                # 尝试修复不完整的JSON（如果被截断）
                if not json_str.strip().endswith(']'):
                    # 尝试找到最后一个完整的对象
                    last_complete_obj = json_str.rfind('}')
                    if last_complete_obj != -1:
                        json_str = json_str[:last_complete_obj + 1] + ']'
                
                try:
                    parsed_results = json.loads(json_str)
                    if isinstance(parsed_results, list):
                        return self._process_parsed_results(parsed_results, original_batch)
                except json.JSONDecodeError:
                    # 方法3: 尝试逐条解析JSON对象
                    return self._parse_individual_objects(cleaned_text, original_batch)
            
            # 方法3: 尝试逐条解析JSON对象
            return self._parse_individual_objects(cleaned_text, original_batch)
                    
        except Exception as e:
            print(f"  JSON解析错误: {str(e)}")
            print(f"  响应内容（前500字符）: {response_text[:500]}")
        
        # 如果所有解析方法都失败，返回默认结果（保持原样）
        return self._create_default_results(original_batch)
    
    def _process_parsed_results(self, parsed_results: List[Dict], original_batch: List[Dict]) -> List[Dict]:
        """处理解析后的结果"""
        results = []
        for i, result in enumerate(parsed_results):
            if i < len(original_batch):
                original_record = original_batch[i]
                line_num = original_record.get('_line_number', i + 1)
                
                # 提取assistant内容（原翻译）
                messages = original_record.get('messages', [])
                assistant_msg = next(
                    (m for m in messages if m.get('role') == 'assistant'),
                    None
                )
                original_translation = assistant_msg.get('content', '') if assistant_msg else ''
                
                # 构建结果
                check_result = {
                    'line_number': line_num,
                    'has_issue': result.get('has_issue', False),
                    'issues': result.get('issues', []),
                    'corrected_translation': result.get('corrected_translation', ''),
                    'original_translation': original_translation,
                    'original_record': original_record
                }
                results.append(check_result)
            else:
                # 如果结果数量不匹配，为多余的记录创建默认结果
                break
        
        # 如果解析的结果少于原始批次，为剩余记录创建默认结果
        while len(results) < len(original_batch):
            i = len(results)
            record = original_batch[i]
            line_num = record.get('_line_number', i + 1)
            messages = record.get('messages', [])
            assistant_msg = next(
                (m for m in messages if m.get('role') == 'assistant'),
                None
            )
            original_translation = assistant_msg.get('content', '') if assistant_msg else ''
            
            results.append({
                'line_number': line_num,
                'has_issue': False,
                'issues': [],
                'corrected_translation': '',
                'original_translation': original_translation,
                'original_record': record
            })
        
        return results
    
    def _parse_individual_objects(self, text: str, original_batch: List[Dict]) -> List[Dict]:
        """尝试逐条解析JSON对象"""
        results = []
        
        # 查找所有可能的JSON对象
        pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.finditer(pattern, text)
        
        parsed_objects = []
        for match in matches:
            try:
                obj = json.loads(match.group())
                if isinstance(obj, dict) and 'line_number' in obj:
                    parsed_objects.append(obj)
            except json.JSONDecodeError:
                continue
        
        # 按line_number排序
        parsed_objects.sort(key=lambda x: x.get('line_number', 0))
        
        # 匹配到原始批次
        for i, record in enumerate(original_batch):
            line_num = record.get('_line_number', i + 1)
            matched_obj = next(
                (obj for obj in parsed_objects if obj.get('line_number') == line_num),
                None
            )
            
            messages = record.get('messages', [])
            assistant_msg = next(
                (m for m in messages if m.get('role') == 'assistant'),
                None
            )
            original_translation = assistant_msg.get('content', '') if assistant_msg else ''
            
            if matched_obj:
                results.append({
                    'line_number': line_num,
                    'has_issue': matched_obj.get('has_issue', False),
                    'issues': matched_obj.get('issues', []),
                    'corrected_translation': matched_obj.get('corrected_translation', ''),
                    'original_translation': original_translation,
                    'original_record': record
                })
            else:
                results.append({
                    'line_number': line_num,
                    'has_issue': False,
                    'issues': [],
                    'corrected_translation': '',
                    'original_translation': original_translation,
                    'original_record': record
                })
        
        return results if results else self._create_default_results(original_batch)
    
    def _create_default_results(self, original_batch: List[Dict]) -> List[Dict]:
        """创建默认结果（保持原样）"""
        results = []
        for i, record in enumerate(original_batch):
            line_num = record.get('_line_number', i + 1)
            messages = record.get('messages', [])
            assistant_msg = next(
                (m for m in messages if m.get('role') == 'assistant'),
                None
            )
            original_translation = assistant_msg.get('content', '') if assistant_msg else ''
            
            results.append({
                'line_number': line_num,
                'has_issue': False,
                'issues': [],
                'corrected_translation': '',
                'original_translation': original_translation,
                'original_record': record
            })
        return results
    
    
    def fix_translations(self, input_file: str, output_file: str, 
                        delay: float = 1.0) -> Tuple[List[Dict], List[Dict]]:
        """
        检查并修复翻译（串行处理）
        
        Args:
            input_file: 输入JSONL文件路径
            output_file: 输出JSONL文件路径
            delay: API调用间隔（秒）
            
        Returns:
            (修正后的记录列表, 检查结果列表)
        """
        print(f"加载文件: {input_file}")
        records = self.load_jsonl(input_file)
        print(f"总共加载 {len(records)} 条记录")
        
        # 分批处理
        batches = self.batch_by_tokens(records)
        print(f"分为 {len(batches)} 批处理（每批最多 {self.max_tokens} tokens）")
        
        all_results = []
        all_fixed_records = []
        
        # 初始化输出文件（清空或创建）
        with open(output_file, 'w', encoding='utf-8') as f:
            pass  # 创建空文件
        
        with tqdm(total=len(records), desc="处理翻译") as pbar:
            for batch_idx, batch in enumerate(batches):
                batch_size = len(batch)
                print(f"\n处理第 {batch_idx + 1}/{len(batches)} 批 ({batch_size} 条记录)")
                
                # 调用千问API检查翻译
                check_results = self.check_batch(batch)
                
                batch_fixed_records = []
                
                if check_results:
                    all_results.extend(check_results)
                    
                    # 处理每条结果
                    for result in check_results:
                        original_record = result['original_record']
                        
                        # 如果翻译被修正，更新记录
                        if result['has_issue'] and result['corrected_translation']:
                            # 创建修正后的记录
                            fixed_record = original_record.copy()
                            
                            # 更新assistant消息
                            messages = fixed_record.get('messages', [])
                            for msg in messages:
                                if msg.get('role') == 'assistant':
                                    # 只更新为修正后的翻译，不添加任何额外字段
                                    msg['content'] = result['corrected_translation']
                                    break
                            
                            batch_fixed_records.append(fixed_record)
                            self.stats["fixed"] += 1
                        else:
                            # 未修正，保持原样
                            batch_fixed_records.append(original_record)
                        
                        self.stats["processed"] += 1
                        pbar.update(1)
                else:
                    # 检查失败，保持原样
                    print(f"  警告：第 {batch_idx + 1} 批处理失败，保持原记录不变")
                    for record in batch:
                        batch_fixed_records.append(record)
                        self.stats["processed"] += 1
                        self.stats["failed"] += 1
                        pbar.update(1)
                
                # 每批处理完后立即保存
                if batch_fixed_records:
                    self._append_fixed_records(batch_fixed_records, output_file)
                    all_fixed_records.extend(batch_fixed_records)
                    print(f"  已保存第 {batch_idx + 1} 批结果（{len(batch_fixed_records)} 条记录）")
                
                # 避免频率限制
                if batch_idx < len(batches) - 1:
                    time.sleep(delay)
        
        print(f"\n所有批次处理完成，共保存 {len(all_fixed_records)} 条记录到: {output_file}")
        
        return all_fixed_records, all_results
    
    def _append_fixed_records(self, records: List[Dict], output_file: str):
        """
        追加保存修正后的记录（每批处理完后调用）
        
        Args:
            records: 修正后的记录列表
            output_file: 输出文件路径
        """
        with open(output_file, 'a', encoding='utf-8') as f:
            for record in records:
                # 移除所有临时字段（以_开头的字段）
                output_record = {k: v for k, v in record.items() 
                               if not k.startswith('_')}
                f.write(json.dumps(output_record, ensure_ascii=False) + '\n')
    
    def _save_fixed_records(self, records: List[Dict], output_file: str):
        """
        保存修正后的记录（一次性保存所有记录，用于兼容）
        
        Args:
            records: 修正后的记录列表
            output_file: 输出文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for record in records:
                # 移除所有临时字段（以_开头的字段）
                output_record = {k: v for k, v in record.items() 
                               if not k.startswith('_')}
                f.write(json.dumps(output_record, ensure_ascii=False) + '\n')
        
        print(f"\n修正后的记录已保存到: {output_file}")
    
    def generate_report(self, results: List[Dict], report_file: str):
        """
        生成检查报告
        
        Args:
            results: 检查结果列表
            report_file: 报告文件路径
        """
        issues_count = sum(1 for r in results if r.get('has_issue'))
        fixed_count = sum(1 for r in results 
                         if r.get('has_issue') and r.get('corrected_translation'))
        
        report_lines = [
            "# 翻译检查和修复报告",
            "",
            "## 统计信息",
            f"- **总条数**: {len(results)}",
            f"- **有问题的条数**: {issues_count}",
            f"- **已修正的条数**: {fixed_count}",
            f"- **问题率**: {issues_count/len(results)*100:.2f}%",
            f"- **修正率**: {fixed_count/issues_count*100:.2f}%" if issues_count > 0 else "- **修正率**: 0%",
            "",
            "## 处理统计",
            f"- **成功处理**: {self.stats['processed']}",
            f"- **处理失败**: {self.stats['failed']}",
            f"- **API错误数**: {len(self.stats['errors'])}",
            ""
        ]
        
        # 问题分类统计
        issue_types = {}
        for result in results:
            if result.get('has_issue'):
                for issue in result.get('issues', []):
                    # 简单分类
                    if '年份' in issue or '年' in issue:
                        issue_types['年份问题'] = issue_types.get('年份问题', 0) + 1
                    elif '数字' in issue or '数' in issue:
                        issue_types['数字问题'] = issue_types.get('数字问题', 0) + 1
                    elif '语法' in issue:
                        issue_types['语法问题'] = issue_types.get('语法问题', 0) + 1
                    elif '拼写' in issue:
                        issue_types['拼写问题'] = issue_types.get('拼写问题', 0) + 1
                    else:
                        issue_types['其他问题'] = issue_types.get('其他问题', 0) + 1
        
        if issue_types:
            report_lines.extend([
                "## 问题分类",
                ""
            ])
            for issue_type, count in sorted(issue_types.items(), key=lambda x: -x[1]):
                report_lines.append(f"- **{issue_type}**: {count}")
            report_lines.append("")
        
        # 详细问题列表（前50个）
        report_lines.extend([
            "## 详细修正记录（前50个）",
            ""
        ])
        
        fixed_results = [r for r in results if r.get('has_issue') and r.get('corrected_translation')]
        for i, result in enumerate(fixed_results[:50], 1):
            report_lines.extend([
                f"### 修正 {i} (第 {result.get('line_number', 'N/A')} 行)",
                "",
                "**原翻译**:",
                f"```",
                result.get('original_translation', '')[:500],
                "```",
                "",
                "**修正后翻译**:",
                f"```",
                result.get('corrected_translation', '')[:500],
                "```",
                ""
            ])
            
            if result.get('issues'):
                report_lines.append("**发现的问题**:")
                for issue in result['issues']:
                    report_lines.append(f"- {issue}")
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        if len(fixed_results) > 50:
            report_lines.append(f"\n*注：还有 {len(fixed_results) - 50} 个修正记录未显示*\n")
        
        # 错误日志
        if self.stats['errors']:
            report_lines.extend([
                "## 错误日志",
                ""
            ])
            for error in self.stats['errors']:
                report_lines.append(f"- 批次大小: {error.get('batch', '?')}, 错误: {error.get('error', '未知错误')}")
            report_lines.append("")
        
        # 写入报告文件
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"检查报告已生成: {report_file}")
