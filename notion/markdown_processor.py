import re
import os
from typing import List, Dict
from .image_processor import ImageProcessor
from .text_processor import TextProcessor

class MarkdownProcessor:
    @staticmethod
    def markdown_to_blocks(markdown_text: str, base_dir: str = None) -> List[Dict]:
        """
        将Markdown文本转换为Notion块
        base_dir: 用于解析相对图片路径的基础目录
        """
        if not markdown_text:
            return []

        blocks = []
        current_list_items = []
        in_code_block = False
        code_block_content = []
        
        # 清理文本，统一换行符
        markdown_text = markdown_text.replace('\r\n', '\n').replace('\r', '\n')
        lines = markdown_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # 跳过空行
            if not line:
                i += 1
                continue
            
            # 处理代码块
            if line.startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_block_content = []
                    i += 1
                    continue
                else:
                    blocks.append({
                        "type": "code",
                        "code": {
                            "language": "plain text",
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": '\n'.join(code_block_content)}
                            }]
                        }
                    })
                    in_code_block = False
                    i += 1
                    continue
            
            if in_code_block:
                code_block_content.append(line)
                i += 1
                continue
            
            # 处理标题
            header_match = re.match(r'^(#{1,4})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)
                blocks.append({
                    "type": f"heading_{level}",
                    f"heading_{level}": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                })
                i += 1
                continue
            
            # 处理引用
            if line.startswith('> '):
                quote_text = line[2:]
                blocks.append({
                    "type": "quote",
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": quote_text}}]
                    }
                })
                i += 1
                continue
            
            # 处理无序列表
            if line.startswith('- ') or line.startswith('* '):
                list_text = line[2:]
                current_list_items.append(list_text)
                
                # 检查下一行是否也是列表项
                if i + 1 >= len(lines) or not (lines[i+1].startswith('- ') or lines[i+1].startswith('* ')):
                    # 创建完整的列表块
                    blocks.append({
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": list_text}}]
                        }
                    })
                    current_list_items = []
                i += 1
                continue
            
            # 处理有序列表
            ordered_list_match = re.match(r'^\d+\.\s+(.+)$', line)
            if ordered_list_match:
                list_text = ordered_list_match.group(1)
                blocks.append({
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": list_text}}]
                    }
                })
                i += 1
                continue
            
            # 处理图片
            image_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if image_match:
                alt_text = image_match.group(1)
                image_path = image_match.group(2)
                
                # 处理本地图片路径
                if not image_path.startswith(('http://', 'https://', 'data:')):
                    if base_dir:
                        # 如果提供了基础目录，尝试从那里加载图片
                        full_path = os.path.join(base_dir, image_path)
                        if os.path.exists(full_path):
                            # 处理图片并获取 base64 URL
                            image_url = ImageProcessor.upload_image_to_notion(full_path)
                            if image_url:
                                blocks.append({
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{
                                            "type": "text",
                                            "text": {
                                                "content": f"[{alt_text}]",
                                            }
                                        }]
                                    }
                                })
                                blocks.append({
                                    "type": "image",
                                    "image": {
                                        "type": "external",
                                        "external": {
                                            "url": image_url
                                        }
                                    }
                                })
                elif image_path.startswith(('http://', 'https://', 'data:')):
                    blocks.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": f"[{alt_text}]",
                                }
                            }]
                        }
                    })
                    blocks.append({
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {
                                "url": image_path
                            }
                        }
                    })
                i += 1
                continue
            
            # 处理普通段落（包含内联格式）
            text = line
            rich_text_elements = TextProcessor.process_inline_markdown(text)
            
            if rich_text_elements:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": rich_text_elements
                    }
                })
            
            i += 1
        
        return blocks

    @staticmethod
    def create_text_block(text: str) -> List[Dict]:
        """
        创建文本块，处理长度限制和 Markdown 格式。
        每个段落都会创建为独立的块。
        """
        # 首先清理文本
        text = TextProcessor.clean_text(text)
        
        # 按换行符分割成段落
        paragraphs = text.split('\n')
        blocks = []
        
        for paragraph in paragraphs:
            # 如果段落超过长度限制，需要分割
            chunks = TextProcessor.split_text_into_chunks(paragraph)
            
            for chunk in chunks:
                # 处理内联 Markdown 格式
                rich_text_elements = TextProcessor.process_inline_markdown(chunk)
                
                # 创建新的段落块
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": rich_text_elements
                    }
                })
        
        return blocks 