import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from notion.config import load_config
from notion.api_client import NotionApiClient
from notion.text_processor import TextProcessor
from notion.markdown_processor import MarkdownProcessor
import re
import requests

class ImportCheckpoint:
    def __init__(self, checkpoint_file="import_checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.processed_files = set()
        self.processed_articles = {}
        self.failed_imports = {}  # {file_path: {article_title: error_message}}
        self.load_checkpoint()

    def load_checkpoint(self):
        """加载检查点文件"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_files = set(data.get('processed_files', []))
                    self.processed_articles = {
                        k: set(v) for k, v in data.get('processed_articles', {}).items()
                    }
                    self.failed_imports = data.get('failed_imports', {})
                print(f"📋 已加载检查点: {len(self.processed_files)} 个文件, "
                      f"{sum(len(articles) for articles in self.processed_articles.values())} 篇文章, "
                      f"{sum(len(articles) for articles in self.failed_imports.values())} 篇失败")
        except Exception as e:
            print(f"⚠️ 加载检查点失败: {e}")
            self.processed_files = set()
            self.processed_articles = {}
            self.failed_imports = {}
    
    def save_checkpoint(self):
        """保存检查点"""
        try:
            data = {
                'processed_files': list(self.processed_files),
                'processed_articles': {
                    k: list(v) for k, v in self.processed_articles.items()
                },
                'failed_imports': self.failed_imports
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存检查点失败: {e}")
    
    def is_file_processed(self, file_path):
        """检查文件是否已处理"""
        return file_path in self.processed_files
    
    def is_article_processed(self, file_path, article_title):
        """检查文章是否已处理"""
        return article_title in self.processed_articles.get(file_path, set())
    
    def mark_file_processed(self, file_path):
        """标记文件为已处理"""
        self.processed_files.add(file_path)
        self.save_checkpoint()
    
    def mark_article_processed(self, file_path, article_title):
        """标记文章为已处理"""
        if file_path not in self.processed_articles:
            self.processed_articles[file_path] = set()
        self.processed_articles[file_path].add(article_title)
        self.save_checkpoint()
    
    def mark_import_failed(self, file_path, article_title, error_message):
        """记录导入失败的文章"""
        if file_path not in self.failed_imports:
            self.failed_imports[file_path] = {}
        self.failed_imports[file_path][article_title] = error_message
        self.save_checkpoint()
        print(f"❌ 记录失败: {article_title}")
    
    def get_failed_imports(self):
        """获取所有失败的导入"""
        return self.failed_imports
    
    def remove_from_failed(self, file_path, article_title):
        """从失败列表中移除（当重试成功时）"""
        if file_path in self.failed_imports and article_title in self.failed_imports[file_path]:
            del self.failed_imports[file_path][article_title]
            if not self.failed_imports[file_path]:  # 如果文件的所有文章都已处理
                del self.failed_imports[file_path]
            self.save_checkpoint()
            print(f"✅ 从失败列表移除: {article_title}")

def normalize_text(text):
    """将文本中的多个连续换行符合并为一个
    
    Args:
        text: 原始文本
        
    Returns:
        str: 处理后的文本
    """
    if not text:
        return text
        
    # 使用正则表达式替换2个或更多连续的换行符为单个换行符
    normalized = re.sub(r'\n{2,}', '\n', text)
    return normalized

class NotionDatabaseImporter:
    def __init__(self, notion_token: str, database_id: str):
        self.api_client = NotionApiClient(notion_token, database_id)
        self.text_processor = TextProcessor()
        self.markdown_processor = MarkdownProcessor()

    def update_or_create_page(self, title: str, content: str, publish_date: Optional[str] = None,
                             author: Optional[str] = None, url: Optional[str] = None,
                             base_dir: str = None, summary: Optional[str] = None) -> bool:
        """
        更新已存在的页面或创建新页面
        """
        try:
            # 构建新的属性（只包含有值的字段）
            new_properties = {}
            
            # 标题总是需要的
            if title:
                new_properties["Title"] = {"title": [{"text": {"content": title}}]}
            
            # 其他字段只在有值时添加
            if author:
                new_properties["Author"] = {"select": {"name": author}}
            if url:
                new_properties["URL"] = {"url": url}
            if publish_date:
                new_properties["Publish Date"] = {"date": {"start": publish_date}}
            if summary:
                # 确保summary的换行符被正确处理
                normalized_summary = normalize_text(summary)
                new_properties["Summary"] = {"rich_text": [{"text": {"content": normalized_summary}}]}
            
            # 查找已存在的页面
            existing_page_id = self.api_client.find_page_by_title(title)
            
            if existing_page_id:
                print(f"    📝 找到已存在的页面，准备更新...")
                print(f"    📄 页面ID: {existing_page_id}")
                
                # 获取现有属性
                print(f"    📑 获取现有属性...")
                current_properties = self.api_client.get_page_properties(existing_page_id)
                
                # 合并属性（保留未更新的字段）
                print(f"    🔄 合并属性...")
                merged_properties = self.api_client.merge_properties(current_properties, new_properties)
                
                # 检查页面是否有内容
                has_content = False
                try:
                    response = requests.get(
                        f"{self.api_client.base_url}/blocks/{existing_page_id}/children",
                        headers=self.api_client.headers
                    )
                    response.raise_for_status()
                    existing_blocks = response.json().get("results", [])
                    has_content = len(existing_blocks) > 0
                except Exception as e:
                    print(f"    ⚠️ 检查页面内容时出错: {str(e)}")
                    has_content = True  # 如果检查失败，假设有内容以避免覆盖
                
                # 更新页面属性
                if not self.api_client.update_page_properties(existing_page_id, merged_properties):
                    return False
                
                if not has_content:
                    print(f"    📄 页面内容为空，添加新内容...")
                    # 准备内容块
                    content_blocks = self.prepare_content_blocks(title, author, publish_date, url, content)
                    
                    # 分批添加新内容
                    try:
                        self.api_client.add_blocks_in_batches(existing_page_id, content_blocks)
                        print(f"    ✅ 新内容已添加")
                    except Exception as e:
                        print(f"    ❌ 添加内容失败: {str(e)}")
                        if hasattr(e, 'response') and hasattr(e.response, 'text'):
                            error_data = e.response.text
                            print(f"    📝 错误详情: {error_data}")
                        return False
                else:
                    print(f"    ℹ️ 页面已有内容，保持不变")
                
                print(f"    ✨ 页面更新成功")
                return True
                
            else:
                # 创建新页面
                print(f"    📄 创建新页面...")
                content_blocks = self.prepare_content_blocks(title, author, publish_date, url, content)
                new_page_id = self.api_client.create_page(new_properties, content_blocks)
                return new_page_id is not None
            
        except Exception as e:
            print(f"    ❌ 更新/创建页面失败: {str(e)}")
            return False

    def prepare_content_blocks(self, title: str, author: str, publish_date: str, url: str, content: str) -> List[Dict]:
        """
        准备页面内容块
        """
        content_blocks = []
        
        # 添加标题
        content_blocks.append({
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": title}}]
            }
        })
            
        # 添加作者和日期信息
        info_text = f"作者：{author if author else '未知'}"
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
            content_blocks.extend(self.markdown_processor.create_text_block(content))
        
        return content_blocks

    def import_from_json(self, json_file: str, checkpoint: ImportCheckpoint) -> None:
        """从 JSON 文件导入文章到 Notion database"""
        print(f"正在从 {json_file} 导入文章...")
        
        # 如果文件已经完全处理过，跳过
        if checkpoint.is_file_processed(json_file):
            print(f"✅ 文件已完全处理过，跳过: {json_file}")
            return
        
        # 获取文件所在目录（用于解析相对图片路径）
        base_dir = os.path.dirname(os.path.abspath(json_file))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)

        total = len(articles)
        success = 0
        
        for idx, article in enumerate(articles, 1):
            title = article.get('title', 'Untitled')
            print(f"\n处理第 {idx}/{total} 篇文章: {title}")
            
            # 如果文章已处理过，跳过
            if checkpoint.is_article_processed(json_file, title):
                print(f"    ✅ 文章已处理过，跳过")
                success += 1
                continue
            
            try:
                # 确保所有必要字段都存在
                content = article.get('content', '')
                publish_date = article.get('publish_time', '')
                author = article.get('author', 'Unknown')
                url = article.get('url', '')
                summary = article.get('summary', '')
                
                # 转换发布日期格式
                if publish_date:
                    publish_date = self.text_processor.convert_chinese_date_to_iso(publish_date)
                
                # 处理content和summary的换行符
                if 'content' in article:
                    article['content'] = normalize_text(article['content'])
                if 'summary' in article:
                    article['summary'] = normalize_text(article['summary'])
                
                # 更新或创建页面
                if self.update_or_create_page(
                    title, content, publish_date, author, url, base_dir, summary
                ):
                    success += 1
                    # 标记文章为已处理
                    checkpoint.mark_article_processed(json_file, title)
                
            except Exception as e:
                print(f"❌ 处理失败: {str(e)}")
                # 记录失败的文章
                checkpoint.mark_import_failed(json_file, title, str(e))
            
            # 添加延迟以避免超出 Notion API 限制
            time.sleep(0.5)
        
        # 如果所有文章都处理成功，标记文件为已处理
        if success == total:
            checkpoint.mark_file_processed(json_file)

        print(f"\n导入完成: {success}/{total} 篇文章成功导入/更新")

def main():
    # 从配置文件加载设置
    config = load_config()
    
    if not config:
        return
    
    notion_token = config.get("notion_token")
    database_id = config.get("database_id")
    
    if not notion_token or not database_id:
        print("Error: Please set notion_token and database_id in notion_config.json")
        return

    # 初始化检查点系统
    checkpoint = ImportCheckpoint()
    importer = NotionDatabaseImporter(notion_token, database_id)
    
    # 查找Output文件夹
    output_dir = os.path.join(os.path.dirname(__file__), "Output")
    if not os.path.exists(output_dir):
        print(f"❌ Output文件夹不存在: {output_dir}")
        return
    
    # 查找所有子文件夹中的articles_detailed.json文件
    json_files = []
    for root, dirs, files in os.walk(output_dir):
        if "articles_detailed.json" in files:
            json_files.append(os.path.join(root, "articles_detailed.json"))
    
    if not json_files:
        print("❌ 在Output文件夹中没有找到任何articles_detailed.json文件")
        return
    
    # 显示找到的文件和处理进度
    print(f"\n📝 找到 {len(json_files)} 个文章列表文件:")
    for i, f in enumerate(json_files, 1):
        folder_name = os.path.basename(os.path.dirname(f))
        status = "✅ 已处理" if checkpoint.is_file_processed(f) else "⏳ 待处理"
        if not checkpoint.is_file_processed(f) and f in checkpoint.processed_articles:
            processed_count = len(checkpoint.processed_articles[f])
            with open(f, 'r', encoding='utf-8') as file:
                total_count = len(json.load(file))
            status = f"🔄 进行中 ({processed_count}/{total_count})"
        print(f"{i}. {folder_name} - {status}")
    
    # 确认是否继续
    confirm = input("\n是否继续导入这些文件到Notion？(y/n): ").strip().lower()
    if confirm not in ['y', 'yes', '是']:
        print("👋 已取消导入")
        return
    
    # 导入所有文件
    total_success = 0
    total_articles = 0
    
    for i, json_file in enumerate(json_files, 1):
        folder_name = os.path.basename(os.path.dirname(json_file))
        print(f"\n{'='*50}")
        print(f"处理第 {i}/{len(json_files)} 个文件: {folder_name}")
        print(f"{'='*50}")
        
        try:
            # 读取文件内容以获取文章数量
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
                total_articles += len(articles)
            
            # 导入文件
            print(f"开始导入 {json_file}...")
            importer.import_from_json(json_file, checkpoint)
            print(f"✅ {folder_name} 导入完成")
            total_success += 1
            
        except Exception as e:
            print(f"❌ 处理失败: {str(e)}")
        
        # 在处理文件之间添加短暂延迟
        if i < len(json_files):
            print("等待3秒后处理下一个文件...")
            time.sleep(3)
    
    # 显示总体导入结果
    print(f"\n📊 导入总结:")
    print(f"- 成功处理文件: {total_success}/{len(json_files)}")
    print(f"- 总文章数量: {total_articles}")
    print("✨ 所有文件处理完成")

if __name__ == "__main__":
    main() 