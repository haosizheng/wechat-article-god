import os
import time
import requests
from urllib.parse import urlparse, unquote
import re

def download_image(img_url: str, save_dir: str) -> str:
    """
    下载图片并返回本地路径
    """
    try:
        # 解析URL，获取文件名
        parsed_url = urlparse(img_url)
        img_name = os.path.basename(unquote(parsed_url.path))
        
        # 确保文件名有效且唯一
        img_name = re.sub(r'[<>:"/\\|?*]', '_', img_name)  # 替换非法字符
        if not img_name or len(img_name) > 255 or not re.search(r'\.(jpg|jpeg|png|gif|webp)$', img_name, re.I):
            # 如果没有有效的扩展名，默认使用.jpg
            img_name = f"img_{int(time.time()*1000)}.jpg"
        
        # 构建保存路径
        img_path = os.path.join(save_dir, img_name)
        
        # 如果文件已存在，添加数字后缀
        base, ext = os.path.splitext(img_path)
        counter = 1
        while os.path.exists(img_path):
            img_path = f"{base}_{counter}{ext}"
            counter += 1
        
        # 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(img_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 验证是否为有效的图片文件
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise Exception(f"Invalid content type: {content_type}")
        
        # 保存图片
        with open(img_path, 'wb') as f:
            f.write(response.content)
        
        print(f"    ✓ 图片已保存: {os.path.basename(img_path)}")
        return img_path
    except Exception as e:
        print(f"    ⚠️ 图片下载失败 ({img_url}): {e}")
        return None 