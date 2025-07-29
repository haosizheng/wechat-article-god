import re
from datetime import datetime
from typing import List, Dict, Optional

class TextProcessor:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本内容：
        1. 将多个连续的换行符替换为单个换行符
        2. 删除段落开头和结尾的空白字符
        3. 确保段落之间只有一个空行
        """
        if not text:
            return ""
        
        # 统一换行符为 \n
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 将任意数量的连续换行符替换为单个换行符
        text = re.sub(r'\n+', '\n', text)
        
        # 清理每个段落的首尾空白字符
        lines = [line.strip() for line in text.split('\n')]
        
        # 过滤掉空行
        lines = [line for line in lines if line]
        
        # 用单个换行符重新连接行
        return '\n'.join(lines)

    @staticmethod
    def parse_date(date_str: str) -> Optional[str]:
        """
        解析多种格式的日期字符串，返回标准格式 (YYYY-MM-DD)
        """
        if not date_str:
            return None

        # 清理日期字符串
        date_str = date_str.strip().replace('：', ':').replace('\u3000', ' ').replace('\xa0', ' ')
        
        # 尝试不同的日期格式
        date_formats = [
            # 标准格式
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            # 带时间的格式
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y.%m.%d %H:%M:%S",
            "%Y.%m.%d %H:%M",
            # 中文格式
            "%Y年%m月%d日",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日 %H:%M:%S"
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # 如果上述格式都不匹配，尝试从字符串中提取日期
        # 匹配 YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY.MM.DD 格式
        date_pattern = r'(\d{4})[-./年](\d{1,2})[-./月](\d{1,2})[日]?'
        match = re.search(date_pattern, date_str)
        if match:
            year, month, day = match.groups()
            try:
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        print(f"Warning: Could not parse date string: {date_str}")
        return None

    @staticmethod
    def convert_chinese_date_to_iso(date_str: str) -> str:
        """
        将中文日期格式转换为 ISO 8601 格式
        例如：'2025年02月07日 17:40' -> '2025-02-07T17:40:00Z'
        """
        try:
            # 处理中文日期格式
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
            # 解析日期时间
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            # 转换为 ISO 格式
            return dt.strftime('%Y-%m-%dT%H:%M:00Z')
        except Exception as e:
            print(f"    ⚠️ 日期转换失败: {date_str} -> {str(e)}")
            return None

    @staticmethod
    def split_text_into_chunks(text: str, max_length: int = 2000) -> List[str]:
        """
        将长文本分割成不超过指定长度的块
        """
        # 如果文本长度在限制内，直接返回
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # 按句子分割（用中文句号、英文句号、感叹号、问号作为分隔符）
        sentences = re.split('([。.!?！？])', text)
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            # 如果有标点符号，加上标点
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
                
            # 如果当前块加上新句子会超出长度限制
            if len(current_chunk) + len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = sentence
                else:
                    # 如果单个句子超过长度限制，强制分割
                    while len(sentence) > max_length:
                        chunks.append(sentence[:max_length])
                        sentence = sentence[max_length:]
                    if sentence:
                        current_chunk = sentence
            else:
                current_chunk += sentence
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    @staticmethod
    def process_inline_markdown(text: str) -> List[Dict]:
        """
        处理内联 Markdown 格式，包括加粗、斜体等
        """
        rich_text_elements = []
        
        # 保存当前处理位置
        current_pos = 0
        
        # 查找所有格式标记
        patterns = [
            (r'\*\*(.+?)\*\*', {'bold': True}),  # 加粗
            (r'\*(.+?)\*', {'italic': True}),     # 斜体
            (r'`(.+?)`', {'code': True}),         # 代码
            (r'~~(.+?)~~', {'strikethrough': True}),  # 删除线
            (r'\[(.+?)\]\((.+?)\)', None)         # 链接
        ]
        
        while current_pos < len(text):
            earliest_match = None
            earliest_pos = len(text)
            matched_pattern = None
            
            # 查找最早出现的格式标记
            for pattern, _ in patterns:
                match = re.search(pattern, text[current_pos:])
                if match and current_pos + match.start() < earliest_pos:
                    earliest_match = match
                    earliest_pos = current_pos + match.start()
                    matched_pattern = pattern
            
            if earliest_match and earliest_pos > current_pos:
                # 添加格式标记之前的普通文本
                if text[current_pos:earliest_pos].strip():
                    rich_text_elements.append({
                        "type": "text",
                        "text": {"content": text[current_pos:earliest_pos]}
                    })
            
            if earliest_match:
                # 处理找到的格式
                pattern_idx = next(i for i, (p, _) in enumerate(patterns) if p == matched_pattern)
                _, annotations = patterns[pattern_idx]
                
                if annotations:  # 处理加粗、斜体等
                    content = earliest_match.group(1)
                    element = {
                        "type": "text",
                        "text": {"content": content},
                        "annotations": annotations
                    }
                    rich_text_elements.append(element)
                else:  # 处理链接
                    if matched_pattern == r'\[(.+?)\]\((.+?)\)':
                        text_content = earliest_match.group(1)
                        url = earliest_match.group(2)
                        element = {
                            "type": "text",
                            "text": {
                                "content": text_content,
                                "link": {"url": url}
                            }
                        }
                        rich_text_elements.append(element)
                
                current_pos = earliest_pos + len(earliest_match.group(0))
            else:
                # 添加剩余的文本
                if text[current_pos:].strip():
                    rich_text_elements.append({
                        "type": "text",
                        "text": {"content": text[current_pos:]}
                    })
                break
        
        return rich_text_elements 