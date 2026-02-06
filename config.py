"""
配置文件
"""
import json
import re
from pathlib import Path
from typing import Dict, Optional

# 默认配置
DEFAULT_CONFIG = {
    "min_length": 1,
    "max_length": 10000,
    "encoding": "utf-8",
    "language_map": {}
}

# 语言代码到中文名称的映射
LANGUAGE_CODE_MAP = {
    "en": "英语",
    "de": "德语",
    "fr": "法语",
    "es": "西班牙语",
    "it": "意大利语",
    "pt": "葡萄牙语",
    "ru": "俄语",
    "ja": "日语",
    "ko": "韩语",
    "ar": "阿拉伯语",
    "hi": "印地语",
    "th": "泰语",
    "vi": "越南语",
    "id": "印尼语",
    "tr": "土耳其语",
    "pl": "波兰语",
    "nl": "荷兰语",
    "sv": "瑞典语",
    "da": "丹麦语",
    "no": "挪威语",
    "fi": "芬兰语",
    "cs": "捷克语",
    "hu": "匈牙利语",
    "ro": "罗马尼亚语",
    "el": "希腊语",
    "he": "希伯来语",
    "uk": "乌克兰语",
    "bg": "保加利亚语",
    "hr": "克罗地亚语",
    "sk": "斯洛伐克语",
    "sl": "斯洛文尼亚语",
    "et": "爱沙尼亚语",
    "lv": "拉脱维亚语",
    "lt": "立陶宛语",
    "mt": "马耳他语",
    "ga": "爱尔兰语",
    "cy": "威尔士语",
    "eu": "巴斯克语",
    "ca": "加泰罗尼亚语",
    "gl": "加利西亚语",
    "is": "冰岛语",
    "mk": "马其顿语",
    "sq": "阿尔巴尼亚语",
    "sr": "塞尔维亚语",
    "bs": "波斯尼亚语",
    "me": "黑山语",
    "ka": "格鲁吉亚语",
    "hy": "亚美尼亚语",
    "az": "阿塞拜疆语",
    "kk": "哈萨克语",
    "ky": "吉尔吉斯语",
    "uz": "乌兹别克语",
    "mn": "蒙古语",
    "ne": "尼泊尔语",
    "si": "僧伽罗语",
    "my": "缅甸语",
    "km": "高棉语",
    "lo": "老挝语",
    "am": "阿姆哈拉语",
    "sw": "斯瓦希里语",
    "zu": "祖鲁语",
    "af": "南非荷兰语",
    "xh": "科萨语",
    "yo": "约鲁巴语",
    "ig": "伊博语",
    "ha": "豪萨语",
    "so": "索马里语",
    "om": "奥罗莫语",
    "ti": "提格雷语",
    "mg": "马达加斯加语",
    "ny": "齐切瓦语",
    "sn": "绍纳语",
    "st": "塞索托语",
    "tn": "茨瓦纳语",
    "ve": "文达语",
    "ts": "聪加语",
    "ss": "斯威士语",
    "nr": "恩德贝勒语",
    "nso": "北索托语",
    "zh": "中文",
    "zh-CN": "简体中文",
    "zh-TW": "繁体中文",
}


def load_language_config(config_path: Optional[str] = None) -> Dict[str, str]:
    """
    加载语言配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        语言映射字典 {文件名: 语言名称}
    """
    if config_path is None:
        return {}
    
    config_file = Path(config_path)
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"警告：无法加载语言配置文件 {config_path}: {e}")
        return {}


def detect_language_from_filename(filename: str, language_map: Dict[str, str] = None) -> Optional[str]:
    """
    从文件名检测语言
    
    Args:
        filename: 文件名
        language_map: 语言映射字典
        
    Returns:
        语言名称，如果无法检测则返回None
    """
    # 首先检查用户提供的语言映射
    if language_map and filename in language_map:
        return language_map[filename]
    
    # 从文件名提取语言代码
    name_without_ext = Path(filename).stem.lower()
    
    # 尝试匹配常见的语言代码格式
    # 格式1: xxx-lang-zh.tsv 或 xxx.lang-zh.tsv (如 news-commentary-v18.de-zh.tsv)
    # 查找 -lang-zh 或 .lang-zh 模式
    # 匹配 -xx-zh 或 .xx-zh 或 _xx-zh 模式（xx是2-3个字母的语言代码）
    pattern = r'[-._]([a-z]{2,3})-zh$|[-._]([a-z]{2,3})_zh$'
    match = re.search(pattern, name_without_ext)
    if match:
        lang_code = match.group(1) or match.group(2)
        if lang_code in LANGUAGE_CODE_MAP:
            return LANGUAGE_CODE_MAP[lang_code]
    
    # 格式2: lang-zh.tsv 或 lang_zh.tsv (直接以语言代码开头)
    parts = name_without_ext.replace('_', '-').split('-')
    if len(parts) >= 2:
        lang_code = parts[0]
        if lang_code in LANGUAGE_CODE_MAP and parts[1] in ['zh', 'cn']:
            return LANGUAGE_CODE_MAP[lang_code]
    
    # 格式3: 直接是语言代码
    if name_without_ext in LANGUAGE_CODE_MAP:
        return LANGUAGE_CODE_MAP[name_without_ext]
    
    # 格式4: 包含语言代码的文件名（更精确的匹配）
    # 按长度排序，优先匹配较长的语言代码
    sorted_codes = sorted(LANGUAGE_CODE_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    for lang_code, lang_name in sorted_codes:
        if lang_code != 'zh' and lang_code in name_without_ext:
            # 确保是完整的单词边界匹配，避免误匹配
            pattern = r'[-._]' + re.escape(lang_code) + r'[-._]|^' + re.escape(lang_code) + r'[-._]'
            if re.search(pattern, name_without_ext):
                return lang_name
    
    return None
