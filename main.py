"""
TSV翻译语料提取工具 - 主程序
"""
import argparse
import json
from pathlib import Path
from tqdm import tqdm
from tsv_processor import TSVProcessor
from data_cleaner import DataCleaner
from conversation_formatter import ConversationFormatter
from config import load_language_config


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="TSV翻译语料提取工具 - 将TSV文件转换为JSONL格式的对话数据集",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="输入TSV文件所在文件夹路径"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="输出JSONL文件路径"
    )
    
    parser.add_argument(
        "--min-length",
        type=int,
        default=1,
        help="最小文本长度（默认：1）"
    )
    
    parser.add_argument(
        "--max-length",
        type=int,
        default=10000,
        help="最大文本长度（默认：10000）"
    )
    
    parser.add_argument(
        "--language-config",
        type=str,
        default=None,
        help="语言映射配置文件路径（JSON格式）"
    )
    
    parser.add_argument(
        "--encoding",
        type=str,
        default="utf-8",
        help="文件编码（默认：utf-8）"
    )
    
    parser.add_argument(
        "--max-per-language",
        type=int,
        default=700,
        help="每种语言最多输出的翻译对数量（默认：700）"
    )
    
    args = parser.parse_args()
    
    # 加载语言配置
    language_map = {}
    if args.language_config:
        language_map = load_language_config(args.language_config)
        print(f"已加载语言配置文件: {args.language_config}")
    
    # 初始化组件
    processor = TSVProcessor(
        input_dir=args.input,
        encoding=args.encoding,
        language_map=language_map
    )
    
    cleaner = DataCleaner(
        min_length=args.min_length,
        max_length=args.max_length
    )
    
    formatter = ConversationFormatter()
    
    # 统计信息
    stats = {
        "total_files": 0,
        "total_pairs": 0,
        "valid_pairs": 0,
        "invalid_pairs": 0,
        "duplicate_pairs": 0,
        "skipped_pairs": 0,  # 因达到语言限制而跳过的翻译对
        "by_language": {}
    }
    
    # 每种语言的输出计数器
    language_counters = {}
    
    # 准备输出文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"开始处理...")
    print(f"输入文件夹: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"长度限制: {args.min_length} - {args.max_length} 字符")
    print(f"每种语言最多输出: {args.max_per_language} 条")
    if language_map:
        print(f"语言配置文件: {args.language_config}")
        print(f"将只处理配置文件中的 {len(language_map)} 个文件")
    else:
        print(f"将处理所有TSV文件")
    print("-" * 60)
    
    # 处理所有文件
    try:
        # 先扫描文件以获取总数
        tsv_files = processor.scan_tsv_files()
        stats["total_files"] = len(tsv_files)
        
        # 计算实际要处理的文件数
        if processor.target_files:
            actual_files = [f for f in tsv_files if f.name in processor.target_files]
            print(f"找到 {stats['total_files']} 个TSV文件，将处理 {len(actual_files)} 个文件（配置文件中的文件）")
        else:
            print(f"找到 {stats['total_files']} 个TSV文件")
        print("-" * 60)
        
        # 打开输出文件
        with open(output_path, 'w', encoding='utf-8') as outfile:
            # 使用process_all_files方法，它会自动处理文件过滤
            current_file = None
            files_processed = set()
            
            # 使用tqdm显示进度（需要先计算要处理的文件数）
            if processor.target_files:
                files_to_process = [f for f in tsv_files if f.name in processor.target_files]
            else:
                files_to_process = tsv_files
            
            with tqdm(total=len(files_to_process), desc="处理文件") as pbar:
                for language, source_text, target_text, file_name in processor.process_all_files():
                    # 跟踪文件处理
                    if file_name != current_file:
                        if current_file is not None:
                            pbar.update(1)
                        current_file = file_name
                        if file_name not in files_processed:
                            files_processed.add(file_name)
                            if language not in stats["by_language"]:
                                stats["by_language"][language] = {
                                    "files": 0,
                                    "pairs": 0,
                                    "valid": 0,
                                    "output": 0  # 实际输出的数量
                                }
                                language_counters[language] = 0
                            stats["by_language"][language]["files"] += 1
                    
                    # 检查该语言是否已达到限制
                    if language_counters[language] >= args.max_per_language:
                        stats["skipped_pairs"] += 1
                        continue
                    
                    # 处理翻译对
                    try:
                        stats["total_pairs"] += 1
                        stats["by_language"][language]["pairs"] += 1
                        
                        # 数据清洗
                        is_valid, cleaned_source, cleaned_target, is_duplicate = cleaner.clean(
                            language, source_text, target_text
                        )
                        
                        if is_valid:
                            # 检查是否已达到该语言的输出限制
                            if language_counters[language] >= args.max_per_language:
                                stats["skipped_pairs"] += 1
                                continue
                            
                            # 格式化对话
                            conversation = formatter.format_conversation(
                                language, cleaned_source, cleaned_target
                            )
                            
                            # 写入JSONL
                            outfile.write(json.dumps(conversation, ensure_ascii=False) + '\n')
                            
                            stats["valid_pairs"] += 1
                            stats["by_language"][language]["valid"] += 1
                            stats["by_language"][language]["output"] += 1
                            language_counters[language] += 1
                        else:
                            stats["invalid_pairs"] += 1
                            
                            # 如果是重复导致的无效
                            if is_duplicate:
                                stats["duplicate_pairs"] += 1
                    
                    except Exception as e:
                        print(f"\n错误：处理翻译对时出错: {e}")
                        continue
                
                # 更新最后一个文件的进度
                if current_file is not None:
                    pbar.update(1)
        
        # 输出统计信息
        print("\n" + "=" * 60)
        print("处理完成！")
        print("=" * 60)
        print(f"总文件数: {stats['total_files']}")
        print(f"总翻译对: {stats['total_pairs']}")
        print(f"有效翻译对: {stats['valid_pairs']}")
        print(f"无效翻译对: {stats['invalid_pairs']}")
        print(f"重复翻译对: {stats['duplicate_pairs']}")
        print(f"因限制跳过: {stats['skipped_pairs']}")
        print(f"实际输出: {sum(lang_stats['output'] for lang_stats in stats['by_language'].values())} 条")
        print(f"输出文件: {args.output}")
        print("-" * 60)
        
        if stats["by_language"]:
            print("按语言统计:")
            for lang, lang_stats in sorted(stats["by_language"].items()):
                print(f"  {lang}:")
                print(f"    文件数: {lang_stats['files']}")
                print(f"    翻译对: {lang_stats['pairs']}")
                print(f"    有效对: {lang_stats['valid']}")
                print(f"    实际输出: {lang_stats['output']} 条")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误：{e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
