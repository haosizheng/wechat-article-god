import json
import os
from datetime import datetime
import requests
from typing import Dict, List, Optional
import re

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

    def split_content_into_blocks(self, content: str, max_length: int = 2000) -> List[Dict]:
        """将长文本分割成多个块"""
        # 首先清理文本
        content = self.clean_text(content)
        
        blocks = []
        
        # 按段落分割
        paragraphs = content.split('\n\n')
        current_block = []
        current_length = 0
        
        for paragraph in paragraphs:
            # 如果单个段落超过限制，需要进一步分割
            if len(paragraph) > max_length:
                # 按句子分割
                sentences = paragraph.replace('。', '。\n').replace('！', '！\n').replace('？', '？\n').split('\n')
                for sentence in sentences:
                    if len(sentence.strip()) == 0:
                        continue
                    
                    if current_length + len(sentence) + 1 > max_length:
                        # 创建新块
                        if current_block:
                            blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"type": "text", "text": {"content": '\n\n'.join(current_block)}}]
                                }
                            })
                        current_block = [sentence]
                        current_length = len(sentence)
                    else:
                        current_block.append(sentence)
                        current_length += len(sentence) + 1
            else:
                if current_length + len(paragraph) + 2 > max_length:
                    # 创建新块
                    if current_block:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": '\n\n'.join(current_block)}}]
                            }
                        })
                    current_block = [paragraph]
                    current_length = len(paragraph)
                else:
                    current_block.append(paragraph)
                    current_length += len(paragraph) + 2

        # 添加最后一个块
        if current_block:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": '\n\n'.join(current_block)}}]
                }
            })

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
            # 修改为 select 类型
            properties["作者"] = {"select": {"name": author}}
        
        # 将 URL 作为页面属性
        if url:
            properties["URL"] = {"url": url}

        # 将内容分割成多个块
        children = self.split_content_into_blocks(content)

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

    def import_from_json(self, json_file: str) -> None:
        """从 JSON 文件导入文章到 Notion database"""
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)

        total = len(articles)
        success = 0
        
        for idx, article in enumerate(articles, 1):
            print(f"Processing article {idx}/{total}: {article.get('title', 'Untitled')}")
            
            # 确保所有必要字段都存在
            title = article.get('title', 'Untitled')
            content = article.get('content', '')
            publish_date = article.get('publish_time', '')  # 不再预处理日期
            author = article.get('author', 'Unknown')
            url = article.get('url', '')

            # 打印日期信息以便调试
            print(f"  Original publish date: {publish_date}")
            formatted_date = self.parse_date(publish_date)
            print(f"  Formatted date: {formatted_date}")

            if self.create_page(title, content, publish_date, author, url):
                success += 1
                print(f"✓ Successfully imported: {title}")
            else:
                print(f"✗ Failed to import: {title}")

        print(f"\nImport completed: {success}/{total} articles successfully imported")

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