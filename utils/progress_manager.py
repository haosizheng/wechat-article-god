import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class ProgressManager:
    def __init__(self, batch_folder: str):
        self.batch_folder = batch_folder
        self.progress_file = os.path.join(batch_folder, "progress.json")
        
    def create_progress_file(self, urls: List[str]) -> None:
        """创建新的进度文件"""
        progress_data = {
            'batch_start_time': datetime.now().isoformat(),
            'total_urls': len(urls),
            'completed_count': 0,
            'articles': {url: {'status': 'pending', 'attempts': 0} for url in urls}
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
    def update_progress(self, url: str, status: str, error: str = None) -> None:
        """更新文章爬取状态"""
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            if url in progress_data['articles']:
                article_data = progress_data['articles'][url]
                article_data['status'] = status
                article_data['last_attempt'] = datetime.now().isoformat()
                article_data['attempts'] = article_data.get('attempts', 0) + 1
                if error:
                    article_data['last_error'] = error
                
                if status == 'completed':
                    progress_data['completed_count'] += 1
                    
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 更新进度文件失败: {e}")

def find_incomplete_batch() -> Optional[str]:
    """
    在 Output 目录中查找未完成的批次
    返回未完成批次的文件夹路径，如果没有则返回 None
    """
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Output")
    if not os.path.exists(output_dir):
        return None
        
    # 遍历所有批次文件夹
    for batch_dir in sorted(os.listdir(output_dir), reverse=True):  # 从最新的开始查找
        batch_path = os.path.join(output_dir, batch_dir)
        progress_file = os.path.join(batch_path, "progress.json")
        
        if os.path.isfile(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    
                # 检查是否有未完成的文章
                pending_articles = [url for url, data in progress_data['articles'].items() 
                                 if data['status'] in ['pending', 'failed']]
                                 
                if pending_articles:
                    return batch_path
            except:
                continue
                
    return None

def get_pending_articles(batch_folder: str) -> Tuple[List[str], Dict]:
    """
    获取指定批次中未完成的文章列表
    返回: (待爬取URL列表, 进度数据)
    """
    progress_file = os.path.join(batch_folder, "progress.json")
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
            
        pending_urls = [url for url, data in progress_data['articles'].items() 
                       if data['status'] in ['pending', 'failed']]
        
        return pending_urls, progress_data
    except Exception as e:
        print(f"⚠️ 读取进度文件失败: {e}")
        return [], {} 