# -*- coding: utf-8 -*-
"""分析翻译质量"""
import json
import re
from collections import defaultdict
from pathlib import Path

def analyze_translation_quality(jsonl_file):
    """分析翻译质量"""
    
    def create_lang_stats():
        return {
            "count": 0,
            "issues": {
                "content_mismatch": 0,  # 内容不匹配
                "omission": 0,  # 遗漏
                "addition": 0,  # 添加
                "format_issue": 0,  # 格式问题
                "encoding_issue": 0,  # 编码问题
                "length_mismatch": 0,  # 长度差异过大
            }
        }
    
    stats = {
        "total_samples": 0,
        "by_language": defaultdict(create_lang_stats),
        "samples_with_issues": []
    }
    
    print("=" * 80)
    print("翻译质量分析报告")
    print("=" * 80)
    print(f"\n正在分析文件: {jsonl_file}")
    print("-" * 80)
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                messages = data.get("messages", [])
                
                if len(messages) < 3:
                    continue
                
                # 提取system, user, assistant消息
                system_msg = next((m for m in messages if m.get("role") == "system"), None)
                user_msg = next((m for m in messages if m.get("role") == "user"), None)
                assistant_msg = next((m for m in messages if m.get("role") == "assistant"), None)
                
                if not user_msg or not assistant_msg:
                    continue
                
                user_content = user_msg.get("content", "")
                assistant_content = assistant_msg.get("content", "")
                
                # 从user消息中提取中文文本（去掉提示部分）
                # 格式可能是："用{语言}怎么说：{中文文本}" 或类似
                chinese_text = user_content
                for pattern in [
                    r"用\w+怎么说：(.+)",
                    r"请把这段话翻译成\w+：(.+)",
                    r"将以下内容翻译为\w+：(.+)",
                    r"帮我翻译成\w+：(.+)",
                    r"作为新闻媒体翻译专家，请将以下内容翻译为\w+：(.+)",
                    r"请以新闻报道的口吻，将这段话翻译成\w+：(.+)",
                ]:
                    match = re.search(pattern, user_content)
                    if match:
                        chinese_text = match.group(1).strip()
                        break
                
                # 检测语言（从user消息中提取）
                language = "未知"
                for lang_pattern in [
                    r"用(\w+)怎么说",
                    r"翻译成(\w+)",
                    r"翻译为(\w+)",
                ]:
                    match = re.search(lang_pattern, user_content)
                    if match:
                        language = match.group(1)
                        break
                
                stats["total_samples"] += 1
                stats["by_language"][language]["count"] += 1
                
                # 检查各种问题
                issues = []
                
                # 1. 检查编码问题（乱码字符）
                if re.search(r'[^\x00-\x7F\u4e00-\u9fff\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7AF\u0600-\u06FF\u0400-\u04FF\u0020-\u007E\u00A0-\u00FF]', assistant_content):
                    # 检查是否有明显的乱码
                    if re.search(r'[""''…]', assistant_content):
                        stats["by_language"][language]["issues"]["encoding_issue"] += 1
                        issues.append("编码问题")
                
                # 2. 检查长度差异（如果翻译过短可能是遗漏，过长可能是添加）
                chinese_len = len(chinese_text)
                assistant_len = len(assistant_content)
                
                if chinese_len > 0:
                    length_ratio = assistant_len / chinese_len
                    # 如果翻译长度小于原文的30%或大于原文的300%，可能有问题
                    if length_ratio < 0.3:
                        stats["by_language"][language]["issues"]["omission"] += 1
                        issues.append("可能遗漏内容")
                    elif length_ratio > 3.0:
                        stats["by_language"][language]["issues"]["addition"] += 1
                        issues.append("可能添加内容")
                    elif abs(length_ratio - 1.0) > 0.5:
                        stats["by_language"][language]["issues"]["length_mismatch"] += 1
                
                # 3. 检查格式问题（如缺少标点、格式异常）
                if assistant_content and not assistant_content[-1] in '。！？.!?':
                    # 如果原文有标点但翻译没有，可能是格式问题
                    if chinese_text and chinese_text[-1] in '。！？':
                        stats["by_language"][language]["issues"]["format_issue"] += 1
                        issues.append("格式问题")
                
                # 4. 检查明显的错误（如数字、日期不匹配）
                # 提取数字
                chinese_numbers = re.findall(r'\d+', chinese_text)
                assistant_numbers = re.findall(r'\d+', assistant_content)
                
                # 如果原文有数字但翻译中没有对应数字，可能有问题
                if chinese_numbers and not assistant_numbers:
                    stats["by_language"][language]["issues"]["content_mismatch"] += 1
                    issues.append("数字缺失")
                
                # 记录有问题的样本
                if issues:
                    stats["samples_with_issues"].append({
                        "line": line_num,
                        "language": language,
                        "issues": issues,
                        "chinese": chinese_text[:100] + "..." if len(chinese_text) > 100 else chinese_text,
                        "translation": assistant_content[:100] + "..." if len(assistant_content) > 100 else assistant_content,
                    })
                
            except json.JSONDecodeError as e:
                print(f"警告：第 {line_num} 行JSON解析错误: {e}")
                continue
            except Exception as e:
                print(f"警告：第 {line_num} 行处理错误: {e}")
                continue
    
    # 输出统计结果
    print(f"\n总样本数: {stats['total_samples']}")
    print(f"有问题的样本数: {len(stats['samples_with_issues'])}")
    print(f"准确率估算: {(stats['total_samples'] - len(stats['samples_with_issues'])) / stats['total_samples'] * 100:.2f}%")
    print("\n" + "=" * 80)
    print("按语言统计:")
    print("=" * 80)
    
    for lang, lang_stats in sorted(stats["by_language"].items()):
        total = lang_stats["count"]
        total_issues = sum(lang_stats["issues"].values())
        accuracy = (total - total_issues) / total * 100 if total > 0 else 0
        
        print(f"\n【{lang}】")
        print(f"  总样本数: {total}")
        print(f"  有问题样本: {total_issues}")
        print(f"  准确率: {accuracy:.2f}%")
        print(f"  问题详情:")
        for issue_type, count in lang_stats["issues"].items():
            if count > 0:
                issue_names = {
                    "content_mismatch": "内容不匹配",
                    "omission": "遗漏内容",
                    "addition": "添加内容",
                    "format_issue": "格式问题",
                    "encoding_issue": "编码问题",
                    "length_mismatch": "长度差异",
                }
                print(f"    - {issue_names.get(issue_type, issue_type)}: {count} ({count/total*100:.2f}%)")
    
    # 显示一些有问题的样本示例
    if stats["samples_with_issues"]:
        print("\n" + "=" * 80)
        print("问题样本示例（前10个）:")
        print("=" * 80)
        
        for i, sample in enumerate(stats["samples_with_issues"][:10], 1):
            try:
                print(f"\n示例 {i} (第 {sample['line']} 行, {sample['language']}):")
                print(f"  问题: {', '.join(sample['issues'])}")
                print(f"  中文: {sample['chinese']}")
                print(f"  翻译: {sample['translation']}")
            except UnicodeEncodeError:
                # 如果遇到编码问题，跳过这个样本
                continue
    
    return stats

if __name__ == "__main__":
    jsonl_file = "test_output.jsonl"
    if Path(jsonl_file).exists():
        analyze_translation_quality(jsonl_file)
    else:
        print(f"错误：文件 {jsonl_file} 不存在")
