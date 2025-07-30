import requests
import time
from typing import Dict, List, Optional
import concurrent.futures

class NotionApiClient:
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
        self.max_workers = 5  # 并发请求数限制

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
        合并新旧属性，只更新新数据中存在的字段
        """
        merged = old_props.copy()  # 保留所有旧属性
        
        # 只更新新数据中有值的字段
        for key, new_value in new_props.items():
            if new_value is not None:  # 只更新有值的字段
                merged[key] = new_value
        
        return merged

    def delete_blocks_batch(self, block_ids):
        """删除一批块，遇到409错误时会重试
        
        Args:
            block_ids: 要删除的块ID列表
        """
        success_count = 0
        
        for block_id in block_ids:
            # 最多重试2次
            for attempt in range(2):
                try:
                    response = requests.delete(
                        f"{self.base_url}/blocks/{block_id}",
                        headers=self.headers
                    )
                    response.raise_for_status()
                    success_count += 1
                    # 每次删除后短暂等待
                    time.sleep(0.1)
                    break
                except Exception as e:
                    if "409" in str(e) and attempt < 1:
                        # 如果是409错误且还可以重试，等待后重试
                        time.sleep(0.5)
                        continue
                    else:
                        print(f"      ⚠️ 删除块 {block_id} 失败: {e}")
                        break
        
        # 如果至少删除了一半的块，就认为基本成功
        return success_count >= len(block_ids) / 2

    def delete_page_content(self, page_id: str):
        """
        删除页面的所有内容块
        """
        try:
            print(f"    🔍 获取页面内容...")
            response = requests.get(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self.headers
            )
            response.raise_for_status()
            existing_blocks = response.json().get("results", [])
            
            if not existing_blocks:
                print(f"    ℹ️ 页面没有内容需要删除")
                return True

            print(f"    🗑️ 删除 {len(existing_blocks)} 个内容块...")
            block_ids = [block["id"] for block in existing_blocks]
            success = self.delete_blocks_batch(block_ids)
            
            if success:
                print(f"    ✅ 内容已删除")
            else:
                print(f"    ⚠️ 部分内容删除失败")
            return success

        except Exception as e:
            print(f"    ❌ 删除内容失败: {str(e)}")
            return False

    def update_page_properties(self, page_id: str, properties: Dict) -> bool:
        """
        更新页面属性
        """
        try:
            print(f"    📝 更新页面属性...")
            response = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=self.headers,
                json={"properties": properties}
            )
            response.raise_for_status()
            print(f"    ✅ 页面属性已更新")
            return True
        except Exception as e:
            print(f"    ❌ 更新属性失败: {str(e)}")
            return False

    def create_page(self, properties: Dict, content_blocks: List[Dict] = None) -> Optional[str]:
        """
        创建新页面
        返回: 页面ID（如果成功）
        """
        try:
            print(f"    📄 创建新页面...")
            page_data = {
                "parent": {"database_id": self.database_id},
                "properties": properties
            }
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_data
            )
            response.raise_for_status()
            
            new_page_id = response.json().get("id")
            print(f"    ✅ 新页面创建成功，ID: {new_page_id}")
            
            # 如果有内容块，添加它们
            if content_blocks:
                self.add_blocks_in_batches(new_page_id, content_blocks)
                print(f"    ✅ 内容添加成功")
            
            return new_page_id
            
        except Exception as e:
            print(f"    ❌ 创建页面失败: {str(e)}")
            return None 

    def add_blocks_in_batches(self, page_id: str, blocks: List[Dict], batch_size: int = 100):
        """
        分批添加内容块，每批最多100个
        """
        total_batches = (len(blocks) + batch_size - 1) // batch_size
        
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            current_batch = i // batch_size + 1
            print(f"    📝 添加内容 ({current_batch}/{total_batches}): {len(batch)} 个块...")
            
            try:
                response = requests.patch(
                    f"{self.base_url}/blocks/{page_id}/children",
                    headers=self.headers,
                    json={"children": batch}
                )
                response.raise_for_status()
                
                # 只在批次之间添加很短的延迟
                if i + batch_size < len(blocks):
                    time.sleep(0.1)
                    
            except requests.exceptions.RequestException as e:
                if hasattr(e.response, 'text'):
                    print(f"    ❌ 批次 {current_batch} 失败: {e.response.text}")
                else:
                    print(f"    ❌ 批次 {current_batch} 失败: {str(e)}")
                raise 