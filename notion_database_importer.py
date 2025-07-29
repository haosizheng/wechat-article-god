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
                new_properties["Summary"] = {"rich_text": [{"text": {"content": summary}}]}
            
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
                
                # 准备内容块
                print(f"    📝 准备新内容...")
                content_blocks = self.prepare_content_blocks(title, author, publish_date, url, content)
                
                # 删除现有内容
                if not self.api_client.delete_page_content(existing_page_id):
                    return False
                
                # 更新页面属性
                if not self.api_client.update_page_properties(existing_page_id, merged_properties):
                    return False
                
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
                summary = article.get('summary', '')
                
                # 转换发布日期格式
                if publish_date:
                    publish_date = self.text_processor.convert_chinese_date_to_iso(publish_date)
                
                # 更新或创建页面
                if self.update_or_create_page(
                    title, content, publish_date, author, url, base_dir, summary
                ):
                    success += 1
                
            except Exception as e:
                print(f"❌ 处理失败: {str(e)}")
            
            # 添加延迟以避免超出 Notion API 限制
            time.sleep(0.5)
        
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
    
    # 显示找到的文件
    print(f"\n📝 找到 {len(json_files)} 个文章列表文件:")
    for i, f in enumerate(json_files, 1):
        folder_name = os.path.basename(os.path.dirname(f))
        print(f"{i}. {folder_name}")
    
    # 确认是否继续
    confirm = input("\n是否开始导入这些文件到Notion？(y/n): ").strip().lower()
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
            importer.import_from_json(json_file)
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