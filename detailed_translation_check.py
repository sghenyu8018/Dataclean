# -*- coding: utf-8 -*-
"""逐条检查翻译准确性"""
import json
import re
from pathlib import Path
from collections import defaultdict

def extract_chinese_text(user_content):
    """从user消息中提取中文文本"""
    patterns = [
        r"用\w+怎么说：(.+)",
        r"请把这段话翻译成\w+：(.+)",
        r"将以下内容翻译为\w+：(.+)",
        r"帮我翻译成\w+：(.+)",
        r"作为新闻媒体翻译专家，请将以下内容翻译为\w+：(.+)",
        r"请以新闻报道的口吻，将这段话翻译成\w+：(.+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_content)
        if match:
            return match.group(1).strip()
    
    return user_content

def detect_language(user_content):
    """从user消息中检测目标语言"""
    patterns = [
        r"用(\w+)怎么说",
        r"翻译成(\w+)",
        r"翻译为(\w+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_content)
        if match:
            return match.group(1)
    
    return "未知"

def check_translation_accuracy(chinese_text, translation_text, language):
    """检查翻译准确性，返回问题列表"""
    issues = []
    
    # 1. 检查关键数字是否匹配
    chinese_numbers = set(re.findall(r'\d+', chinese_text))
    translation_numbers = set(re.findall(r'\d+', translation_text))
    
    missing_numbers = chinese_numbers - translation_numbers
    extra_numbers = translation_numbers - chinese_numbers
    
    if missing_numbers:
        issues.append({
            "type": "数字缺失",
            "severity": "高",
            "details": f"原文中的数字 {', '.join(missing_numbers)} 在翻译中缺失"
        })
    
    if extra_numbers and not missing_numbers:
        # 如果翻译中有额外数字但原文没有，可能是问题
        issues.append({
            "type": "数字不匹配",
            "severity": "中",
            "details": f"翻译中有额外数字 {', '.join(extra_numbers)}"
        })
    
    # 2. 检查关键日期
    date_patterns = [
        r'\d{4}年',
        r'\d{1,2}月\d{1,2}日',
        r'\d{4}-\d{2}-\d{2}',
    ]
    
    chinese_dates = set()
    for pattern in date_patterns:
        chinese_dates.update(re.findall(pattern, chinese_text))
    
    translation_dates = set()
    for pattern in date_patterns:
        translation_dates.update(re.findall(pattern, translation_text))
    
    # 检查年份
    chinese_years = set(re.findall(r'(\d{4})年', chinese_text))
    translation_years = set()
    
    # 根据语言提取年份
    if language in ['英语', '英语', 'English']:
        translation_years = set(re.findall(r'\b(19|20)\d{2}\b', translation_text))
    elif language in ['德语', '德语', 'German']:
        translation_years = set(re.findall(r'\b(19|20)\d{2}\b', translation_text))
    elif language in ['法语', '法语', 'French']:
        translation_years = set(re.findall(r'\b(19|20)\d{2}\b', translation_text))
    elif language in ['西班牙语', '西班牙语', 'Spanish']:
        translation_years = set(re.findall(r'\b(19|20)\d{2}\b', translation_text))
    elif language in ['日语', '日语', 'Japanese']:
        translation_years = set(re.findall(r'(\d{4})年', translation_text))
    
    missing_years = chinese_years - translation_years
    if missing_years:
        issues.append({
            "type": "年份缺失",
            "severity": "高",
            "details": f"原文中的年份 {', '.join(missing_years)} 在翻译中缺失"
        })
    
    # 3. 检查长度异常
    chinese_len = len(chinese_text)
    translation_len = len(translation_text)
    
    if chinese_len > 0:
        ratio = translation_len / chinese_len
        
        # 如果翻译过短（可能是遗漏）
        if ratio < 0.3:
            issues.append({
                "type": "可能遗漏内容",
                "severity": "高",
                "details": f"翻译长度仅为原文的 {ratio*100:.1f}%，可能遗漏了大量内容"
            })
        # 如果翻译过长（可能是添加）
        elif ratio > 3.0:
            issues.append({
                "type": "可能添加内容",
                "severity": "中",
                "details": f"翻译长度为原文的 {ratio*100:.1f}%，可能添加了额外内容"
            })
    
    # 4. 检查关键人名、地名（简单检查）
    # 提取可能的人名（大写字母开头的词）
    chinese_proper_nouns = set(re.findall(r'[A-Z][a-z]+', chinese_text))
    translation_proper_nouns = set(re.findall(r'[A-Z][a-z]+', translation_text))
    
    # 检查一些常见的关键词是否被翻译
    key_terms = {
        '中国': ['China', 'Chine', 'China', '中国'],
        '美国': ['USA', 'US', 'United States', 'États-Unis', 'États-Unis', 'Estados Unidos', 'アメリカ'],
        '欧洲': ['Europe', 'Europe', 'Europe', 'Europa', 'ヨーロッパ'],
        '德国': ['Germany', 'Allemagne', 'Alemania', 'ドイツ'],
        '法国': ['France', 'France', 'Francia', 'フランス'],
    }
    
    # 5. 检查标点符号完整性
    if chinese_text and chinese_text[-1] in '。！？' and translation_text:
        if translation_text[-1] not in '.!?。！？':
            issues.append({
                "type": "标点缺失",
                "severity": "低",
                "details": "原文有句末标点，但翻译缺少对应标点"
            })
    
    # 6. 检查编码问题
    if re.search(r'[""''…]', translation_text):
        issues.append({
            "type": "编码问题",
            "severity": "中",
            "details": "翻译中包含可能的乱码字符"
        })
    
    return issues

def analyze_file_detailed(jsonl_file):
    """详细分析文件"""
    
    results = {
        "total_samples": 0,
        "samples_with_issues": [],
        "by_language": defaultdict(lambda: {
            "count": 0,
            "issues_count": 0,
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int)
        }),
        "summary": {
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0,
        }
    }
    
    print("=" * 80)
    print("详细翻译准确性检查")
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
                
                user_msg = next((m for m in messages if m.get("role") == "user"), None)
                assistant_msg = next((m for m in messages if m.get("role") == "assistant"), None)
                
                if not user_msg or not assistant_msg:
                    continue
                
                user_content = user_msg.get("content", "")
                assistant_content = assistant_msg.get("content", "")
                
                chinese_text = extract_chinese_text(user_content)
                language = detect_language(user_content)
                
                results["total_samples"] += 1
                results["by_language"][language]["count"] += 1
                
                # 检查翻译准确性
                issues = check_translation_accuracy(chinese_text, assistant_content, language)
                
                if issues:
                    results["by_language"][language]["issues_count"] += 1
                    
                    sample_info = {
                        "line": line_num,
                        "language": language,
                        "chinese": chinese_text[:200] + "..." if len(chinese_text) > 200 else chinese_text,
                        "translation": assistant_content[:200] + "..." if len(assistant_content) > 200 else assistant_content,
                        "issues": issues
                    }
                    
                    results["samples_with_issues"].append(sample_info)
                    
                    # 统计严重程度
                    for issue in issues:
                        severity = issue["severity"]
                        issue_type = issue["type"]
                        results["by_language"][language]["by_severity"][severity] += 1
                        results["by_language"][language]["by_type"][issue_type] += 1
                        # 映射中文严重程度到英文键
                        severity_map = {"高": "high", "中": "medium", "低": "low"}
                        severity_key = f"{severity_map.get(severity, 'unknown')}_severity"
                        results["summary"][severity_key] += 1
                
            except Exception as e:
                print(f"警告：第 {line_num} 行处理错误: {e}")
                continue
    
    return results

def generate_report(results, output_file="detailed_translation_report.md"):
    """生成详细报告"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 翻译准确性详细检查报告\n\n")
        f.write("## 总体统计\n\n")
        f.write(f"- **总样本数**: {results['total_samples']}\n")
        f.write(f"- **有问题的样本数**: {len(results['samples_with_issues'])}\n")
        f.write(f"- **问题率**: {len(results['samples_with_issues'])/results['total_samples']*100:.2f}%\n\n")
        
        f.write(f"- **高严重性问题**: {results['summary']['high_severity']}\n")
        f.write(f"- **中严重性问题**: {results['summary']['medium_severity']}\n")
        f.write(f"- **低严重性问题**: {results['summary']['low_severity']}\n\n")
        
        f.write("## 按语言统计\n\n")
        
        for lang, lang_stats in sorted(results["by_language"].items()):
            total = lang_stats["count"]
            issues_count = lang_stats["issues_count"]
            issue_rate = issues_count / total * 100 if total > 0 else 0
            
            f.write(f"### {lang}\n\n")
            f.write(f"- **总样本数**: {total}\n")
            f.write(f"- **有问题的样本**: {issues_count} ({issue_rate:.2f}%)\n\n")
            
            f.write("**按严重程度分类**:\n")
            for severity in ["高", "中", "低"]:
                count = lang_stats["by_severity"].get(severity, 0)
                if count > 0:
                    f.write(f"- {severity}严重性: {count}\n")
            f.write("\n")
            
            f.write("**按问题类型分类**:\n")
            for issue_type, count in sorted(lang_stats["by_type"].items(), key=lambda x: x[1], reverse=True):
                f.write(f"- {issue_type}: {count}\n")
            f.write("\n")
        
        f.write("## 详细问题列表\n\n")
        f.write("### 高严重性问题\n\n")
        
        high_severity_samples = [s for s in results["samples_with_issues"] 
                                if any(issue["severity"] == "高" for issue in s["issues"])]
        
        for i, sample in enumerate(high_severity_samples[:50], 1):  # 只显示前50个
            f.write(f"#### 问题 {i} (第 {sample['line']} 行, {sample['language']})\n\n")
            f.write(f"**中文原文**:\n```\n{sample['chinese']}\n```\n\n")
            f.write(f"**翻译**:\n```\n{sample['translation']}\n```\n\n")
            f.write("**发现的问题**:\n")
            for issue in sample["issues"]:
                if issue["severity"] == "高":
                    f.write(f"- **{issue['type']}** ({issue['severity']}严重性): {issue['details']}\n")
            f.write("\n---\n\n")
        
        if len(high_severity_samples) > 50:
            f.write(f"\n*注：还有 {len(high_severity_samples) - 50} 个高严重性问题未显示*\n\n")
        
        f.write("### 中严重性问题（前30个）\n\n")
        
        medium_severity_samples = [s for s in results["samples_with_issues"] 
                                  if any(issue["severity"] == "中" for issue in s["issues"]) 
                                  and not any(issue["severity"] == "高" for issue in s["issues"])]
        
        for i, sample in enumerate(medium_severity_samples[:30], 1):
            f.write(f"#### 问题 {i} (第 {sample['line']} 行, {sample['language']})\n\n")
            f.write(f"**中文原文**:\n```\n{sample['chinese']}\n```\n\n")
            f.write(f"**翻译**:\n```\n{sample['translation']}\n```\n\n")
            f.write("**发现的问题**:\n")
            for issue in sample["issues"]:
                if issue["severity"] == "中":
                    f.write(f"- **{issue['type']}** ({issue['severity']}严重性): {issue['details']}\n")
            f.write("\n---\n\n")
    
    print(f"\n详细报告已保存到: {output_file}")

if __name__ == "__main__":
    jsonl_file = "output3.jsonl"
    if Path(jsonl_file).exists():
        print("开始分析...")
        results = analyze_file_detailed(jsonl_file)
        
        print(f"\n分析完成！")
        print(f"总样本数: {results['total_samples']}")
        print(f"有问题的样本: {len(results['samples_with_issues'])}")
        print(f"高严重性问题: {results['summary']['high_severity']}")
        print(f"中严重性问题: {results['summary']['medium_severity']}")
        print(f"低严重性问题: {results['summary']['low_severity']}")
        
        print("\n正在生成详细报告...")
        generate_report(results)
        print("完成！")
    else:
        print(f"错误：文件 {jsonl_file} 不存在")
