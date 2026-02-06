# TSV翻译语料提取工具

用于处理包含多语言翻译语料的TSV文件，提取并转换为适合训练翻译大模型的JSONL格式对话数据集。

## 功能特性

- 批量处理文件夹中的所有TSV文件
- 自动识别源语言（从文件名或配置）
- 数据清洗（去重、过滤空值、长度限制）
- 转换为对话格式（user/assistant）
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
- `--language-config`: 语言映射配置文件路径（可选，JSON格式）
- `--encoding`: 文件编码（默认：utf-8）

### 示例

```bash
# 基本使用
python main.py -i ./tsv_files -o ./output.jsonl

# 指定长度限制
python main.py -i ./tsv_files -o ./output.jsonl --min-length 10 --max-length 500

# 使用语言配置文件
python main.py -i ./tsv_files -o ./output.jsonl --language-config lang_map.json
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

## 语言识别

工具支持以下方式识别源语言：

1. **从文件名提取**：如果文件名包含语言代码（如 `de-zh.tsv`、`en_chinese.tsv`），会自动提取
2. **配置文件映射**：通过 `--language-config` 参数提供JSON配置文件
3. **自动检测**：使用langdetect库自动检测（可能不够准确）

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
