# 翻译检查和修复工具使用说明

## 功能简介

本工具使用阿里千问大模型自动检查和修复 `output3.jsonl` 文件中的翻译不准确问题。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置API密钥

### 方法1：环境变量（推荐）

```bash
# Linux/Mac
export DASHSCOPE_API_KEY=your_api_key_here

# Windows PowerShell
$env:DASHSCOPE_API_KEY="your_api_key_here"

# Windows CMD
set DASHSCOPE_API_KEY=your_api_key_here
```

### 方法2：使用 .env 文件

1. 复制 `.env.example` 为 `.env`
2. 在 `.env` 文件中填入您的API密钥

### 方法3：命令行参数

使用 `--api-key` 参数直接指定（不推荐，密钥会出现在命令历史中）

## 使用方法

### 基本使用

```bash
python fix_translations.py -i output3.jsonl -o output3_fixed.jsonl -r fix_report.md
```

### 参数说明

- `-i, --input`: 输入JSONL文件路径（默认：output3.jsonl）
- `-o, --output`: 修正后的JSONL输出路径（默认：output3_fixed.jsonl）
- `-r, --report`: 详细检查报告输出路径（默认：translation_fix_report.md）
- `--api-key`: DashScope API密钥（如不提供，从环境变量读取）
- `--model`: 使用的模型（qwen-turbo/qwen-plus/qwen-max，默认：qwen-turbo）
- `--delay`: API调用间隔（秒，默认：1.0）

### 使用示例

```bash
# 使用默认设置
python fix_translations.py -i output3.jsonl

# 指定API密钥
python fix_translations.py -i output3.jsonl --api-key your_key

# 使用qwen-plus模型（处理能力更强）
python fix_translations.py -i output3.jsonl --model qwen-plus

# 增加API调用间隔（避免频率限制）
python fix_translations.py -i output3.jsonl --delay 2
```

## 输出文件说明

### 1. 修正后的JSONL文件

- 保持原有格式
- 如果翻译被修正，`assistant` 字段会被更新为修正后的翻译
- 添加了以下元数据字段：
  - `_fixed`: 标记是否被修正（true/false）
  - `_original_translation`: 保存原翻译（如果被修正）
  - `_issues`: 发现的问题列表

### 2. 详细检查报告

报告包含：
- 统计信息（总条数、问题数、修正数等）
- 问题分类统计
- 详细修正记录（前50个）
- 错误日志（如果有）

## 工作原理

1. **加载文件**：读取JSONL文件中的所有翻译记录
2. **智能分批**：根据模型token限制自动分批处理
3. **调用API**：使用千问模型检查每批翻译
4. **解析结果**：提取修正后的翻译
5. **保存结果**：生成修正后的JSONL和详细报告

## 注意事项

1. **API密钥安全**：请妥善保管API密钥，不要提交到代码仓库
2. **频率限制**：大批量处理时注意API调用频率限制，可通过 `--delay` 参数调整
3. **结果审核**：修正结果需要人工审核确认，工具只是辅助
4. **备份原文件**：建议在处理前备份原始文件
5. **成本考虑**：API调用会产生费用，请注意使用量

## 故障排除

### 问题1：提示未安装dashscope

```bash
pip install dashscope
```

### 问题2：API密钥错误

检查环境变量或命令行参数是否正确设置。

### 问题3：API调用失败

- 检查网络连接
- 确认API密钥有效
- 检查账户余额
- 增加 `--delay` 参数值

### 问题4：处理速度慢

- 使用 `qwen-turbo` 模型（更快）
- 减少 `--delay` 值（注意频率限制）

## 技术支持

如有问题，请检查：
1. 依赖是否正确安装
2. API密钥是否有效
3. 输入文件格式是否正确
4. 查看生成的错误日志
