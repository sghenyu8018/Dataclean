# -*- coding: utf-8 -*-
"""
翻译验证脚本
从JSONL文件中提取指定行的中文和译文，在TSV文件中查找匹配并比较译文是否一致
"""
import json
import csv
import re
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 语言名称到语言代码的映射（反向映射）
LANGUAGE_NAME_TO_CODE = {
    "英语": "en",
    "德语": "de",
    "法语": "fr",
    "西班牙语": "es",
    "意大利语": "it",
    "葡萄牙语": "pt",
    "俄语": "ru",
    "日语": "ja",
    "韩语": "ko",
    "阿拉伯语": "ar",
    "印地语": "hi",
    "泰语": "th",
    "越南语": "vi",
    "印尼语": "id",
    "土耳其语": "tr",
    "波兰语": "pl",
    "荷兰语": "nl",
    "瑞典语": "sv",
    "丹麦语": "da",
    "挪威语": "no",
    "芬兰语": "fi",
    "捷克语": "cs",
    "匈牙利语": "hu",
    "罗马尼亚语": "ro",
    "希腊语": "el",
    "希伯来语": "he",
    "乌克兰语": "uk",
    "保加利亚语": "bg",
    "克罗地亚语": "hr",
    "斯洛伐克语": "sk",
    "斯洛文尼亚语": "sl",
    "爱沙尼亚语": "et",
    "拉脱维亚语": "lv",
    "立陶宛语": "lt",
    "马耳他语": "mt",
    "爱尔兰语": "ga",
    "威尔士语": "cy",
    "巴斯克语": "eu",
    "加泰罗尼亚语": "ca",
    "加利西亚语": "gl",
    "冰岛语": "is",
    "马其顿语": "mk",
    "阿尔巴尼亚语": "sq",
    "塞尔维亚语": "sr",
    "波斯尼亚语": "bs",
    "黑山语": "me",
    "格鲁吉亚语": "ka",
    "亚美尼亚语": "hy",
    "阿塞拜疆语": "az",
    "哈萨克语": "kk",
    "吉尔吉斯语": "ky",
    "乌兹别克语": "uz",
    "蒙古语": "mn",
    "尼泊尔语": "ne",
    "僧伽罗语": "si",
    "缅甸语": "my",
    "高棉语": "km",
    "老挝语": "lo",
    "阿姆哈拉语": "am",
    "斯瓦希里语": "sw",
    "祖鲁语": "zu",
    "南非荷兰语": "af",
    "科萨语": "xh",
    "约鲁巴语": "yo",
    "伊博语": "ig",
}


def extract_target_language(user_content: str) -> Optional[str]:
    """
    从user消息中提取目标语言名称
    
    Args:
        user_content: user消息的完整内容
        
    Returns:
        目标语言名称（如"西班牙语"），如果无法提取则返回None
    """
    # 匹配模式：提取语言名称
    patterns = [
        r'^用(\w+语)怎么说：',
        r'^请把这段话翻译成(\w+语)：',
        r'^将以下内容翻译为(\w+语)：',
        r'^作为.*?，请将以下内容翻译为(\w+语)：',
        r'^请以.*?的口吻，将这段话翻译成(\w+语)：',
        r'^帮我翻译成(\w+语)：',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, user_content.strip())
        if match:
            lang_name = match.group(1)
            # 验证是否是有效的语言名称
            if lang_name in LANGUAGE_NAME_TO_CODE:
                return lang_name
    
    return None


def extract_chinese_from_user(user_content: str) -> str:
    """
    从user消息中提取中文（去除前缀）
    
    Args:
        user_content: user消息的完整内容
        
    Returns:
        提取的中文内容
    """
    # 匹配模式：去除各种前缀
    patterns = [
        r'^用\w+语怎么说：(.+)',
        r'^请把这段话翻译成\w+语：(.+)',
        r'^将以下内容翻译为\w+语：(.+)',
        r'^作为.*?，请将以下内容翻译为\w+语：(.+)',
        r'^请以.*?的口吻，将这段话翻译成\w+语：(.+)',
        r'^帮我翻译成\w+语：(.+)',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, user_content.strip())
        if match:
            return match.group(1).strip()
    
    # 如果没有匹配到前缀，返回原内容
    return user_content.strip()


def load_jsonl_lines(jsonl_file: str, line_numbers: Optional[List[int]] = None) -> List[Dict]:
    """
    加载JSONL文件的指定行或所有行
    
    Args:
        jsonl_file: JSONL文件路径
        line_numbers: 要提取的行号列表（从1开始），如果为None则加载所有行
        
    Returns:
        记录列表，每个记录包含行号和JSON数据
    """
    records = []
    jsonl_path = Path(jsonl_file)
    
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL文件不存在: {jsonl_file}")
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # 如果指定了行号列表，只处理指定的行
            if line_numbers is not None and line_num not in line_numbers:
                continue
            
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append({
                    'line_number': line_num,
                    'data': record
                })
            except json.JSONDecodeError as e:
                print(f"警告：第 {line_num} 行JSON解析失败: {e}")
                continue
    
    return records


def scan_tsv_files(tsv_dir: str) -> List[Path]:
    """
    扫描TSV目录下的所有TSV文件
    
    Args:
        tsv_dir: TSV文件目录路径
        
    Returns:
        TSV文件路径列表
    """
    tsv_path = Path(tsv_dir)
    if not tsv_path.exists():
        raise FileNotFoundError(f"TSV目录不存在: {tsv_dir}")
    
    tsv_files = list(tsv_path.glob("*.tsv"))
    return sorted(tsv_files)


def get_tsv_file_by_language(tsv_dir: str, language_name: str) -> Optional[Path]:
    """
    根据语言名称获取对应的TSV文件路径
    
    Args:
        tsv_dir: TSV文件目录路径
        language_name: 语言名称（如"西班牙语"）
        
    Returns:
        TSV文件路径，如果找不到则返回None
    """
    lang_code = LANGUAGE_NAME_TO_CODE.get(language_name)
    if not lang_code:
        return None
    
    tsv_path = Path(tsv_dir)
    # 查找格式：news-commentary-v18.{lang_code}-zh.tsv
    pattern = f"*{lang_code}-zh.tsv"
    matches = list(tsv_path.glob(pattern))
    
    if matches:
        return matches[0]
    return None


def search_tsv_by_chinese(tsv_file: str, chinese_text: str) -> List[Dict]:
    """
    在TSV文件中查找中文（精确匹配）
    
    Args:
        tsv_file: TSV文件路径
        chinese_text: 要查找的中文文本
        
    Returns:
        匹配的行列表，每个元素包含行号、TSV数据（源语言，中文）和文件名
    """
    matches = []
    tsv_path = Path(tsv_file)
    
    if not tsv_path.exists():
        return matches  # 文件不存在，返回空列表
    
    # 增加CSV字段大小限制
    csv.field_size_limit(min(2**31-1, 10 * 1024 * 1024))
    
    # 尝试多种编码
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']
    
    for enc in encodings:
        try:
            with open(tsv_path, 'r', encoding=enc, newline='') as f:
                # 检测分隔符
                first_line = f.readline()
                f.seek(0)
                
                delimiter = '\t' if '\t' in first_line else ','
                
                reader = csv.reader(f, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=1):
                    if len(row) < 2:
                        continue
                    
                    tsv_source = row[0].strip()  # 源语言文本
                    tsv_chinese = row[1].strip()  # 中文文本
                    
                    # 精确匹配中文
                    if tsv_chinese == chinese_text:
                        matches.append({
                            'line_number': row_num,
                            'source_text': tsv_source,
                            'chinese': tsv_chinese,
                            'file_name': tsv_path.name
                        })
            
            # 如果成功读取，跳出编码循环
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            # 静默处理错误，继续尝试下一个编码
            continue
    
    return matches


def search_all_tsv_files(tsv_dir: str, chinese_text: str, target_language: Optional[str] = None) -> List[Dict]:
    """
    在所有TSV文件中查找中文，或根据目标语言在对应文件中查找
    
    Args:
        tsv_dir: TSV文件目录路径
        chinese_text: 要查找的中文文本
        target_language: 目标语言名称（可选），如果提供则只在对应语言的TSV文件中查找
        
    Returns:
        匹配的行列表
    """
    all_matches = []
    
    if target_language:
        # 如果指定了目标语言，只在对应的TSV文件中查找
        tsv_file = get_tsv_file_by_language(tsv_dir, target_language)
        if tsv_file:
            matches = search_tsv_by_chinese(str(tsv_file), chinese_text)
            all_matches.extend(matches)
    else:
        # 在所有TSV文件中查找
        tsv_files = scan_tsv_files(tsv_dir)
        for tsv_file in tsv_files:
            matches = search_tsv_by_chinese(str(tsv_file), chinese_text)
            all_matches.extend(matches)
    
    return all_matches


def compare_translations(jsonl_translation: str, tsv_source_text: str) -> Dict:
    """
    比较JSONL中的译文与TSV中的源语言文本是否一致
    
    Args:
        jsonl_translation: JSONL中的译文
        tsv_source_text: TSV中的源语言文本
        
    Returns:
        比较结果字典，包含是否一致、差异信息等
    """
    jsonl_clean = jsonl_translation.strip()
    tsv_clean = tsv_source_text.strip()
    
    is_match = jsonl_clean == tsv_clean
    
    result = {
        'is_match': is_match,
        'jsonl_translation': jsonl_clean,
        'tsv_source_text': tsv_clean
    }
    
    if not is_match:
        # 计算差异
        result['length_diff'] = abs(len(jsonl_clean) - len(tsv_clean))
        result['jsonl_length'] = len(jsonl_clean)
        result['tsv_length'] = len(tsv_clean)
        
        # 找出不同的部分（简单比较）
        if len(jsonl_clean) == len(tsv_clean):
            differences = []
            for i, (c1, c2) in enumerate(zip(jsonl_clean, tsv_clean)):
                if c1 != c2:
                    start = max(0, i - 10)
                    end = min(len(jsonl_clean), i + 10)
                    differences.append(f"位置 {i}: JSONL='{jsonl_clean[start:end]}' vs TSV='{tsv_clean[start:end]}'")
                    if len(differences) >= 5:  # 最多显示5处差异
                        break
            result['differences'] = differences
    
    return result


def main():
    """主函数"""
    # 设置输出编码（Windows兼容）
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="翻译验证脚本 - 从JSONL文件中提取中文和译文，在TSV文件中查找匹配并比较",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--lines',
        type=str,
        default=None,
        help='要处理的行号，格式：3957,3958 或 3957-3958。如果不指定则处理所有行'
    )
    
    parser.add_argument(
        '--jsonl',
        type=str,
        default=None,
        help='JSONL文件路径（默认：翻译数据集_de_en_fr_es_ja_ru_20260206.jsonl）'
    )
    
    parser.add_argument(
        '--tsv-dir',
        type=str,
        default=None,
        help='TSV文件目录路径（默认：tsvfile）'
    )
    
    parser.add_argument(
        '--tsv',
        type=str,
        default=None,
        help='单个TSV文件路径（如果指定，则只在该文件中查找，忽略--tsv-dir）'
    )
    
    parser.add_argument(
        '--auto-detect-language',
        action='store_true',
        default=True,
        help='自动检测目标语言并在对应的TSV文件中查找（默认：启用）'
    )
    
    parser.add_argument(
        '--search-all',
        action='store_true',
        help='在所有TSV文件中查找（忽略自动检测语言）'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出结果到文件（可选）'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式，只输出统计信息'
    )
    
    args = parser.parse_args()
    
    # 文件路径（相对于项目根目录）
    project_root = Path(__file__).parent.parent
    
    if args.jsonl:
        jsonl_file = Path(args.jsonl)
    else:
        jsonl_file = project_root / "翻译数据集_de_en_fr_es_ja_ru_20260206.jsonl"
    
    # TSV文件或目录
    if args.tsv:
        # 如果指定了单个TSV文件，使用该文件
        tsv_file_or_dir = Path(args.tsv)
        search_all = False
        auto_detect = False
    else:
        # 使用TSV目录
        if args.tsv_dir:
            tsv_file_or_dir = Path(args.tsv_dir)
        else:
            tsv_file_or_dir = project_root / "tsvfile"
        
        search_all = args.search_all
        auto_detect = args.auto_detect_language and not search_all
    
    # 解析行号
    line_numbers = None
    if args.lines:
        line_numbers = []
        # 支持多种格式：3957,3958 或 3957-3958 或混合
        parts = args.lines.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # 范围格式：3957-3958
                start, end = part.split('-', 1)
                line_numbers.extend(range(int(start.strip()), int(end.strip()) + 1))
            else:
                # 单个行号
                line_numbers.append(int(part.strip()))
        line_numbers = sorted(set(line_numbers))  # 去重并排序
    
    # 输出文件
    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
    
    def print_output(*args, **kwargs):
        """统一的输出函数"""
        msg = ' '.join(str(a) for a in args)
        print(msg, **kwargs)
        if output_file:
            print(msg, file=output_file, **kwargs)
    
    print_output("=" * 80)
    print_output("翻译验证脚本")
    print_output("=" * 80)
    print_output(f"JSONL文件: {jsonl_file}")
    if args.tsv:
        print_output(f"TSV文件: {tsv_file_or_dir}")
    else:
        print_output(f"TSV目录: {tsv_file_or_dir}")
        if search_all:
            print_output("查找模式: 在所有TSV文件中查找")
        elif auto_detect:
            print_output("查找模式: 自动检测语言并在对应TSV文件中查找")
        else:
            print_output("查找模式: 在所有TSV文件中查找")
    if line_numbers:
        print_output(f"处理行号: {line_numbers} (共 {len(line_numbers)} 行)")
    else:
        print_output("处理所有行")
    print_output("=" * 80)
    print_output()
    
    try:
        # 1. 加载JSONL文件的指定行或所有行
        if not args.quiet:
            print_output("步骤1: 加载JSONL文件...")
        records = load_jsonl_lines(str(jsonl_file), line_numbers)
        
        if not records:
            print_output("错误：未找到指定的行")
            if output_file:
                output_file.close()
            return
        
        if not args.quiet:
            print_output(f"成功加载 {len(records)} 条记录")
            print_output()
        
        # 统计信息
        stats = {
            'total': len(records),
            'found_in_tsv': 0,
            'matched': 0,
            'not_matched': 0,
            'not_found': 0
        }
        
        # 2. 处理每条记录
        for idx, record_info in enumerate(records, 1):
            line_num = record_info['line_number']
            record = record_info['data']
            
            if not args.quiet:
                print_output(f"{'=' * 80}")
                print_output(f"处理第 {line_num} 行 ({idx}/{len(records)})")
                print_output(f"{'=' * 80}")
            
            # 提取user和assistant消息
            messages = record.get('messages', [])
            user_msg = next((m for m in messages if m.get('role') == 'user'), None)
            assistant_msg = next((m for m in messages if m.get('role') == 'assistant'), None)
            
            if not user_msg or not assistant_msg:
                if not args.quiet:
                    print_output(f"警告：第 {line_num} 行缺少user或assistant消息")
                continue
            
            # 提取中文和目标语言
            user_content = user_msg.get('content', '')
            chinese_text = extract_chinese_from_user(user_content)
            target_language = extract_target_language(user_content) if auto_detect else None
            
            # 提取译文
            translation = assistant_msg.get('content', '')
            
            if not args.quiet:
                print_output(f"提取的中文: {chinese_text[:100]}..." if len(chinese_text) > 100 else f"提取的中文: {chinese_text}")
                if target_language:
                    print_output(f"检测到的目标语言: {target_language}")
                print_output(f"JSONL中的译文: {translation[:100]}..." if len(translation) > 100 else f"JSONL中的译文: {translation}")
                print_output()
                print_output("步骤2: 在TSV文件中查找匹配的中文...")
            
            # 3. 在TSV文件中查找中文
            if args.tsv:
                # 使用指定的单个TSV文件
                matches = search_tsv_by_chinese(str(tsv_file_or_dir), chinese_text)
            else:
                # 在所有TSV文件或对应语言的TSV文件中查找
                matches = search_all_tsv_files(str(tsv_file_or_dir), chinese_text, 
                                               target_language if auto_detect and not search_all else None)
            
            if not matches:
                stats['not_found'] += 1
                if not args.quiet:
                    print_output(f"[X] 未在TSV文件中找到匹配的中文")
                    print_output()
                continue
            
            stats['found_in_tsv'] += 1
            
            if not args.quiet:
                print_output(f"[OK] 找到 {len(matches)} 条匹配记录")
            
            # 4. 比较译文
            found_match = False
            for i, match in enumerate(matches, 1):
                if not args.quiet:
                    file_info = f" ({match.get('file_name', 'unknown')})" if 'file_name' in match else ""
                    print_output(f"\n匹配记录 {i} (TSV第 {match['line_number']} 行{file_info}):")
                    print_output(f"TSV中的源语言文本: {match['source_text'][:100]}..." if len(match['source_text']) > 100 else f"TSV中的源语言文本: {match['source_text']}")
                
                comparison = compare_translations(translation, match['source_text'])
                
                if comparison['is_match']:
                    stats['matched'] += 1
                    found_match = True
                    if not args.quiet:
                        print_output("[OK] 译文完全一致！")
                else:
                    if not found_match:  # 只统计第一次不匹配
                        stats['not_matched'] += 1
                    if not args.quiet:
                        print_output("[X] 译文不一致")
                        print_output(f"   JSONL长度: {comparison['jsonl_length']} 字符")
                        print_output(f"   TSV长度: {comparison['tsv_length']} 字符")
                        print_output(f"   长度差异: {comparison['length_diff']} 字符")
                        
                        if 'differences' in comparison and comparison['differences']:
                            print_output("   差异位置:")
                            for diff in comparison['differences']:
                                print_output(f"     - {diff}")
            
            if not args.quiet:
                print_output()
        
        # 输出统计信息
        print_output()
        print_output("=" * 80)
        print_output("统计信息")
        print_output("=" * 80)
        print_output(f"总处理行数: {stats['total']}")
        print_output(f"在TSV中找到匹配: {stats['found_in_tsv']} ({stats['found_in_tsv']/stats['total']*100:.2f}%)")
        print_output(f"译文完全一致: {stats['matched']} ({stats['matched']/stats['total']*100:.2f}%)")
        print_output(f"译文不一致: {stats['not_matched']} ({stats['not_matched']/stats['total']*100:.2f}%)")
        print_output(f"未在TSV中找到: {stats['not_found']} ({stats['not_found']/stats['total']*100:.2f}%)")
        if stats['found_in_tsv'] > 0:
            print_output(f"匹配率（在找到的记录中）: {stats['matched']/stats['found_in_tsv']*100:.2f}%")
        print_output("=" * 80)
    
    except FileNotFoundError as e:
        print_output(f"错误：{e}")
    except Exception as e:
        print_output(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if output_file:
            output_file.close()
            print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
