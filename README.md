# TSV翻译语料提取工具

用于处理包含多语言翻译语料的TSV文件，提取并转换为适合训练翻译大模型的JSONL格式对话数据集。

## 文档目录

详细文档和报告请查看 `docs/` 目录：
- `TRANSLATION_FIX_README.md` - 翻译检查和修复工具使用说明
- `translation_quality_summary.md` - 翻译质量分析摘要
- `detailed_translation_report.md` - 详细翻译检查报告
- 其他分析报告和文档

## 功能特性

- 批量处理文件夹中的所有TSV文件
- 自动识别源语言（从文件名或配置）
- 数据清洗（去重、过滤空值、长度限制）
- 转换为对话格式（user/assistant）
- 支持限制每种语言的输出数量（默认每种语言700条）
- 输出JSONL格式数据集

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
python main.py --input <输入文件夹路径> --output <输出文件路径> [选项]
```

### 参数说明

- `--input, -i`: 输入TSV文件所在文件夹路径（必需）
- `--output, -o`: 输出JSONL文件路径（必需）
- `--min-length`: 最小文本长度（默认：1）
- `--max-length`: 最大文本长度（默认：10000）
- `--max-per-language`: 每种语言最多输出的翻译对数量（默认：700）
- `--language-config`: 语言映射配置文件路径（可选，JSON格式）。如果提供此参数，将只处理配置文件中列出的文件
- `--encoding`: 文件编码（默认：utf-8）

### 示例

```bash
# 基本使用
python main.py -i ./tsv_files -o ./output.jsonl

# 指定长度限制
python main.py -i ./tsv_files -o ./output.jsonl --min-length 10 --max-length 500

# 指定每种语言最多输出数量（默认700条）
python main.py -i ./tsv_files -o ./output.jsonl --max-per-language 1000

# 使用语言配置文件（只处理配置文件中的文件）
python main.py -i ./tsv_files -o ./output.jsonl --language-config example_lang_config.json
```

## TSV文件格式

TSV文件应包含两列（使用Tab分隔）：
- 第一列：源语言文本
- 第二列：中文文本

示例：
```
Hello world	你好世界
Good morning	早上好
```

## 语言识别和文件过滤

工具支持以下方式识别源语言：

1. **从文件名提取**：如果文件名包含语言代码（如 `de-zh.tsv`、`en_chinese.tsv`），会自动提取
2. **配置文件映射**：通过 `--language-config` 参数提供JSON配置文件
3. **自动检测**：使用langdetect库自动检测（可能不够准确）

**重要**：如果提供了 `--language-config` 参数，工具将**只处理配置文件中列出的文件**，其他文件会被自动跳过。这样可以精确控制要处理哪些语言的语料。

## 输出格式

每个JSONL行包含一个对话样本：

```json
{"messages": [{"role": "user", "content": "用德语怎么说：你好世界"}, {"role": "assistant", "content": "Hallo Welt"}]}
```

## 语言配置文件格式

```json
{
  "de-zh.tsv": "德语",
  "en-zh.tsv": "英语",
  "fr-zh.tsv": "法语"
}
```
