import json
import requests
import time
from datetime import datetime

class NotionImporter:
    def __init__(self, token, database_id):
        """
        初始化 Notion 导入器
        
        Args:
            token: Notion API 集成令牌
            database_id: Notion 数据库 ID
        """
        self.token = token
        self.database_id = database_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def create_page(self, article_data):
        """
        在 Notion 数据库中创建一篇文章页面
        
        Args:
            article_data: 文章数据字典
        """
        # 准备页面属性
        properties = {
            "标题": {
                "title": [
                    {
                        "text": {
                            "content": article_data.get('title', '无标题')[:2000]  # Notion 标题限制
                        }
                    }
                ]
            },
            "作者": {
                "rich_text": [
                    {
                        "text": {
                            "content": article_data.get('author', '未知作者')
                        }
                    }
                ]
            },
            "发布时间": {
                "date": {
                    "start": self._parse_date(article_data.get('publish_time', ''))
                }
            },
            "阅读量": {
                "number": self._parse_number(article_data.get('read_count', ''))
            },
            "点赞量": {
                "number": self._parse_number(article_data.get('like_count', ''))
            },
            "链接": {
                "url": article_data.get('url', '')
            }
        }
        
        # 准备页面内容
        content_blocks = []
        
        # 添加文章内容
        if article_data.get('content'):
            # 将长内容分段
            content = article_data['content']
            chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]  # Notion 块限制
            
            for chunk in chunks:
                content_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": chunk
                                }
                            }
                        ]
                    }
                })
        
        # 创建页面
        page_data = {
            "parent": {
                "database_id": self.database_id
            },
            "properties": properties,
            "children": content_blocks
        }
        
        try:
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers,
                json=page_data
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)
    
    def _parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str:
            return None
        
        try:
            # 尝试解析常见的日期格式
            for fmt in ['%Y-%m-%d', '%Y年%m月%d日', '%Y/%m/%d']:
                try:
                    return datetime.strptime(date_str, fmt).isoformat()
                except:
                    continue
            return None
        except:
            return None
    
    def _parse_number(self, num_str):
        """解析数字字符串"""
        if not num_str:
            return None
        
        try:
            return int(num_str)
        except:
            return None
    
    def import_articles(self, json_file_path):
        """
        批量导入文章到 Notion
        
        Args:
            json_file_path: JSON 文件路径
        """
        # 读取 JSON 文件
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            print(f"成功读取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"读取文件失败: {e}")
            return
        
        # 批量导入
        success_count = 0
        fail_count = 0
        
        for idx, article in enumerate(articles, 1):
            print(f"[{idx}/{len(articles)}] 正在导入: {article.get('title', '无标题')[:50]}...")
            
            success, result = self.create_page(article)
            
            if success:
                print(f"  ✓ 成功导入")
                success_count += 1
            else:
                print(f"  ✗ 导入失败: {result}")
                fail_count += 1
            
            # 避免 API 限制，每次请求间隔 1 秒
            time.sleep(1)
        
        print(f"\n导入完成！")
        print(f"成功: {success_count} 篇")
        print(f"失败: {fail_count} 篇")

def main():
    print("Notion 文章导入工具")
    print("=" * 50)
    
    # 获取用户输入
    token = input("请输入你的 Notion API 集成令牌: ").strip()
    database_id = input("请输入 Notion 数据库 ID: ").strip()
    
    if not token or not database_id:
        print("错误: 请提供有效的 API 令牌和数据库 ID")
        return
    
    # 创建导入器
    importer = NotionImporter(token, database_id)
    
    # 导入文章
    json_file = "articles_detailed.json"
    importer.import_articles(json_file)

if __name__ == "__main__":
    main() 