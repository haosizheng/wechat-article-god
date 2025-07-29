import json
import os
from datetime import datetime
import requests
from typing import Dict, List, Optional, Union
import re
import mimetypes
import time
import base64

class NotionDatabaseImporter:
    def __init__(self, notion_token: str, database_id: str):
        """
        初始化 Notion API 客户端
        
        Args:
            notion_token: Notion API integration token
            database_id: 目标 database 的 ID
        """
        self.notion_token = notion_token
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"

    def clean_text(self, text: str) -> str:
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
        
        # 将三个或更多连续的换行符替换为两个换行符
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 清理每个段落的首尾空白字符
        paragraphs = [p.strip() for p in text.split('\n\n')]
        
        # 过滤掉空段落
        paragraphs = [p for p in paragraphs if p]
        
        # 用两个换行符重新连接段落
        return '\n\n'.join(paragraphs)

    def parse_date(self, date_str: str) -> Optional[str]:
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

    def upload_image_to_notion(self, image_path: str) -> str:
        """
        将本地图片转换为 base64 URL
        返回: 图片的 base64 URL
        """
        try:
            from PIL import Image
            import io
            import base64
            
            # 打开并压缩图片
            with Image.open(image_path) as img:
                # 转换为 RGB 模式（处理 RGBA 图片）
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 如果图片太大，进行压缩
                max_size = (800, 800)  # 最大尺寸
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 转换为 JPEG 格式并压缩
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                image_data = output.getvalue()
            
            # 转换为 base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{base64_data}"
            
            return image_url
        
        except Exception as e:
            print(f"    ⚠️ 图片处理失败 ({image_path}): {e}")
            return None

    def markdown_to_blocks(self, markdown_text: str, base_dir: str = None) -> List[Dict]:
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
                            image_url = self.upload_image_to_notion(full_path)
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
            rich_text_elements = []
            
            # 处理加粗
            bold_segments = re.split(r'(\*\*.*?\*\*)', text)
            for segment in bold_segments:
                if segment.startswith('**') and segment.endswith('**'):
                    content = segment[2:-2]
                    rich_text_elements.append({
                        "type": "text",
                        "text": {"content": content},
                        "annotations": {"bold": True}
                    })
                else:
                    if segment:
                        rich_text_elements.append({
                            "type": "text",
                            "text": {"content": segment}
                        })
            
            if rich_text_elements:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": rich_text_elements
                    }
                })
            
            i += 1
        
        return blocks

    def create_page(self, title: str, content: str, publish_date: Optional[str] = None,
                   author: Optional[str] = None, url: Optional[str] = None) -> Dict:
        """
        在 Notion database 中创建新页面，将文章内容放在页面正文中
        
        Args:
            title: 文章标题
            content: 文章正文
            publish_date: 发布日期
            author: 作者
            url: 原文链接
        """
        try:
            # 构建页面属性
            properties = {
                "标题": {"title": [{"text": {"content": title}}]},
            }
            
            # 解析并添加发布日期
            if publish_date:
                formatted_date = self.parse_date(publish_date)
                if formatted_date:
                    properties["发布日期"] = {"date": {"start": formatted_date}}
            
            if author:
                properties["作者"] = {"select": {"name": author}}
            
            if url:
                properties["URL"] = {"url": url}

            # 将Markdown内容转换为Notion块
            children = self.markdown_to_blocks(content)

            # 创建页面
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": children
            }

            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=payload
            )

            if response.status_code != 200:
                print(f"Error creating page for {title}: {response.text}")
                return None

            return response.json()
            
        except Exception as e:
            print(f"Error creating page: {str(e)}")
            return None

    def convert_chinese_date_to_iso(self, date_str: str) -> str:
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

    def split_text_into_chunks(self, text: str, max_length: int = 2000) -> List[str]:
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

    def process_inline_markdown(self, text: str) -> List[Dict]:
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

    def create_text_block(self, text: str) -> List[Dict]:
        """
        创建文本块，处理长度限制和 Markdown 格式
        """
        chunks = self.split_text_into_chunks(text)
        blocks = []
        
        for chunk in chunks:
            # 处理内联 Markdown 格式
            rich_text_elements = self.process_inline_markdown(chunk)
            
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text_elements
                }
            })
        
        return blocks

    def find_page_by_title(self, title: str) -> Optional[str]:
        """
        在数据库中查找指定标题的页面
        返回: 页面 ID（如果找到）
        """
        try:
            # 使用 Notion 搜索 API
            response = requests.post(
                "https://api.notion.com/v1/databases/" + self.database_id + "/query",
                headers=self.headers,
                json={
                    "filter": {
                        "property": "Title",
                        "title": {
                            "equals": title
                        }
                    }
                }
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            
            if results:
                # 返回第一个匹配的页面 ID
                return results[0]["id"]
            
            return None
            
        except Exception as e:
            print(f"    ⚠️ 查找页面失败: {e}")
            return None

    def get_page_properties(self, page_id: str) -> Dict:
        """
        获取页面的现有属性
        """
        try:
            response = requests.get(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("properties", {})
        except Exception as e:
            print(f"    ⚠️ 获取页面属性失败: {e}")
            return {}

    def merge_properties(self, old_props: Dict, new_props: Dict) -> Dict:
        """
        合并新旧属性，保留旧属性中新属性没有的值
        """
        merged = old_props.copy()
        
        # 更新新属性中有值的字段
        for key, new_value in new_props.items():
            if key in merged:
                # 检查新值是否为空
                if key == "Title" and new_value.get("title"):
                    merged[key] = new_value
                elif key == "Author" and new_value.get("select", {}).get("name"):
                    merged[key] = new_value
                elif key == "URL" and new_value.get("url"):
                    merged[key] = new_value
                elif key == "Publish Date" and new_value.get("date", {}).get("start"):
                    merged[key] = new_value
        
        return merged

    def update_or_create_page(self, title: str, content: str, publish_date: Optional[str] = None,
                             author: Optional[str] = None, url: Optional[str] = None,
                             base_dir: str = None) -> bool:
        """
        更新已存在的页面或创建新页面
        """
        try:
            # 构建新的属性
            new_properties = {
                "Title": {"title": [{"text": {"content": title}}]},
                "Author": {"select": {"name": author}} if author else None,
                "URL": {"url": url} if url else None,
                "Publish Date": {"date": {"start": publish_date}} if publish_date else None
            }
            
            # 移除空值
            new_properties = {k: v for k, v in new_properties.items() if v is not None}
            
            # 查找已存在的页面
            existing_page_id = self.find_page_by_title(title)
            
            if existing_page_id:
                print(f"    📝 找到已存在的页面，准备更新...")
                print(f"    📄 页面ID: {existing_page_id}")
                
                try:
                    # 首先删除所有现有内容
                    print(f"    🗑️ 删除现有内容...")
                    response = requests.get(
                        f"https://api.notion.com/v1/blocks/{existing_page_id}/children",
                        headers=self.headers
                    )
                    response.raise_for_status()
                    existing_blocks = response.json().get("results", [])
                    
                    for block in existing_blocks:
                        requests.delete(
                            f"https://api.notion.com/v1/blocks/{block['id']}",
                            headers=self.headers
                        )
                    print(f"    ✅ 现有内容已删除")
                    
                    # 准备内容块
                    print(f"    📝 准备新内容...")
                    content_blocks = []
                    
                    # 添加标题
                    content_blocks.append({
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": title}}]
                        }
                    })
                    
                    # 添加作者和日期信息
                    info_text = f"作者：{author}"
                    if publish_date:
                        info_text += f" | 发布时间：{publish_date}"
                    content_blocks.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": info_text}}]
                        }
                    })
                    
                    # 添加原文链接
                    if url:
                        content_blocks.append({
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": "原文链接：",
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": url,
                                            "link": {"url": url}
                                        }
                                    }
                                ]
                            }
                        })
                    
                    # 添加分隔线
                    content_blocks.append({
                        "type": "divider",
                        "divider": {}
                    })
                    
                    # 处理正文内容
                    if content:
                        content_blocks.extend(self.create_text_block(content))
                    
                    # 更新页面属性
                    print(f"    📝 更新页面属性...")
                    update_data = {
                        "properties": new_properties
                    }
                    
                    response = requests.patch(
                        f"https://api.notion.com/v1/pages/{existing_page_id}",
                        headers=self.headers,
                        json=update_data
                    )
                    response.raise_for_status()
                    print(f"    ✅ 页面属性已更新")
                    
                    # 添加新内容
                    print(f"    📝 添加新内容...")
                    response = requests.patch(
                        f"https://api.notion.com/v1/blocks/{existing_page_id}/children",
                        headers=self.headers,
                        json={"children": content_blocks}
                    )
                    response.raise_for_status()
                    print(f"    ✅ 新内容已添加")
                    
                    print(f"    ✨ 页面更新成功")
                    return True
                    
                except requests.exceptions.RequestException as e:
                    print(f"    ❌ API请求失败: {str(e)}")
                    if hasattr(e.response, 'text'):
                        error_data = e.response.text
                        print(f"    📝 错误详情: {error_data}")
                    return False
                    
            else:
                print(f"    📄 创建新页面...")
                try:
                    # 创建新页面
                    page_data = {
                        "parent": {"database_id": self.database_id},
                        "properties": new_properties,
                        "children": []
                    }
                    
                    response = requests.post(
                        "https://api.notion.com/v1/pages",
                        headers=self.headers,
                        json=page_data
                    )
                    response.raise_for_status()
                    
                    new_page_id = response.json().get("id")
                    print(f"    ✅ 新页面创建成功，ID: {new_page_id}")
                    
                    # 添加内容
                    content_blocks = []
                    
                    # 添加标题
                    content_blocks.append({
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": title}}]
                        }
                    })
                    
                    # 添加作者和日期信息
                    info_text = f"作者：{author}"
                    if publish_date:
                        info_text += f" | 发布时间：{publish_date}"
                    content_blocks.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": info_text}}]
                        }
                    })
                    
                    # 添加原文链接
                    if url:
                        content_blocks.append({
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": "原文链接：",
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": url,
                                            "link": {"url": url}
                                        }
                                    }
                                ]
                            }
                        })
                    
                    # 添加分隔线
                    content_blocks.append({
                        "type": "divider",
                        "divider": {}
                    })
                    
                    # 处理正文内容
                    if content:
                        content_blocks.extend(self.create_text_block(content))
                    
                    # 添加内容
                    print(f"    📝 添加页面内容...")
                    response = requests.patch(
                        f"https://api.notion.com/v1/blocks/{new_page_id}/children",
                        headers=self.headers,
                        json={"children": content_blocks}
                    )
                    response.raise_for_status()
                    print(f"    ✅ 内容添加成功")
                    
                    return True
                    
                except requests.exceptions.RequestException as e:
                    print(f"    ❌ API请求失败: {str(e)}")
                    if hasattr(e.response, 'text'):
                        error_data = e.response.text
                        print(f"    📝 错误详情: {error_data}")
                    return False
            
        except Exception as e:
            print(f"    ❌ 更新/创建页面失败: {str(e)}")
            return False

    def import_from_json(self, json_file: str) -> None:
        """从 JSON 文件导入文章到 Notion database"""
        print(f"正在从 {json_file} 导入文章...")
        
        # 获取文件所在目录（用于解析相对图片路径）
        base_dir = os.path.dirname(os.path.abspath(json_file))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)

        total = len(articles)
        success = 0
        
        for idx, article in enumerate(articles, 1):
            print(f"\n处理第 {idx}/{total} 篇文章: {article.get('title', 'Untitled')}")
            
            try:
                # 确保所有必要字段都存在
                title = article.get('title', 'Untitled')
                content = article.get('content', '')
                publish_date = article.get('publish_time', '')
                author = article.get('author', 'Unknown')
                url = article.get('url', '')
                
                # 转换发布日期格式
                if publish_date:
                    publish_date = self.convert_chinese_date_to_iso(publish_date)
                
                # 更新或创建页面
                if self.update_or_create_page(title, content, publish_date, author, url, base_dir):
                    success += 1
                
            except Exception as e:
                print(f"❌ 处理失败: {str(e)}")
            
            # 添加延迟以避免超出 Notion API 限制
            time.sleep(0.5)
        
        print(f"\n导入完成: {success}/{total} 篇文章成功导入/更新")

def main():
    # 这些值需要从环境变量或配置文件中获取
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_token or not database_id:
        print("Error: Please set NOTION_TOKEN and NOTION_DATABASE_ID environment variables")
        return

    importer = NotionDatabaseImporter(notion_token, database_id)
    
    # 假设我们使用最新的 articles_detailed.json 文件
    # 首先找到最新的文章文件夹
    base_dir = "."
    article_folders = [d for d in os.listdir(base_dir) 
                      if d.startswith("articles_batch_") and 
                      os.path.isdir(os.path.join(base_dir, d))]
    
    if not article_folders:
        print("Error: No articles_batch folders found")
        return
    
    # 获取最新的文件夹
    latest_folder = max(article_folders)
    json_file = os.path.join(base_dir, latest_folder, "articles_detailed.json")
    
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found")
        return
    
    print(f"Importing articles from {json_file}")
    importer.import_from_json(json_file)

if __name__ == "__main__":
    main() 