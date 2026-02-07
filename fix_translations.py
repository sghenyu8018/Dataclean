# -*- coding: utf-8 -*-
"""
翻译检查和修复工具主程序
使用阿里千问大模型检查和修复翻译不准确问题
"""
import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from qwen_translation_checker import TranslationChecker


def main():
    """主函数"""
    # 加载环境变量
    if load_dotenv:
        load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='翻译检查和修复工具 - 使用阿里千问大模型检查和修复翻译不准确问题',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用（使用环境变量中的API密钥）
  python fix_translations.py -i output3.jsonl -o output3_fixed.jsonl -r fix_report.md
  
  # 指定API密钥
  python fix_translations.py -i output3.jsonl -o output3_fixed.jsonl --api-key your_key
  
  # 使用不同的模型
  python fix_translations.py -i output3.jsonl -o output3_fixed.jsonl --model qwen-plus
  
  # 设置API调用间隔
  python fix_translations.py -i output3.jsonl -o output3_fixed.jsonl --delay 2
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default='output3.jsonl',
        help='输入JSONL文件路径（默认：output3.jsonl）'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='output3_fixed.jsonl',
        help='修正后的JSONL输出路径（默认：output3_fixed.jsonl）'
    )
    
    parser.add_argument(
        '-r', '--report',
        type=str,
        default='translation_fix_report.md',
        help='详细检查报告输出路径（默认：translation_fix_report.md）'
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='DashScope API密钥（如不提供，从环境变量DASHSCOPE_API_KEY读取）'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='qwen-turbo',
        choices=['qwen-turbo', 'qwen-plus', 'qwen-max'],
        help='使用的模型（默认：qwen-turbo）'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='API调用间隔（秒，默认：1.0）'
    )
    
    args = parser.parse_args()
    
    # 验证输入文件
    if not os.path.exists(args.input):
        print(f"错误：输入文件不存在: {args.input}")
        sys.exit(1)
    
    # 检查输出目录
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("翻译检查和修复工具")
    print("=" * 80)
    print(f"输入文件: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"报告文件: {args.report}")
    print(f"使用模型: {args.model}")
    print(f"API调用间隔: {args.delay}秒")
    print("=" * 80)
    print()
    
    try:
        # 初始化检查工具
        checker = TranslationChecker(api_key=args.api_key, model=args.model)
        
        # 执行检查和修复
        print("开始检查翻译...")
        fixed_records, check_results = checker.fix_translations(
            args.input,
            args.output,
            delay=args.delay
        )
        
        # 生成报告
        if check_results:
            checker.generate_report(check_results, args.report)
        
        # 输出统计信息
        print("\n" + "=" * 80)
        print("处理完成！")
        print("=" * 80)
        print(f"总记录数: {checker.stats['total']}")
        print(f"成功处理: {checker.stats['processed']}")
        print(f"修正记录: {checker.stats['fixed']}")
        print(f"处理失败: {checker.stats['failed']}")
        if checker.stats['errors']:
            print(f"API错误: {len(checker.stats['errors'])}")
        print(f"\n修正后的文件: {args.output}")
        print(f"详细报告: {args.report}")
        print("=" * 80)
        
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
