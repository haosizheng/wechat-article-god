import os
import json

def extract_summary(content, max_length=100):
    """从文章内容中提取摘要
    
    Args:
        content: 文章内容
        max_length: 摘要最大长度,默认100字符
        
    Returns:
        str: 提取的摘要
    """
    if not content:
        return ""
        
    # 清理多余的换行和空格
    content = content.strip()
    
    # 如果内容少于最大长度,直接返回
    if len(content) <= max_length:
        return content
        
    # 截取指定长度
    summary = content[:max_length]
    
    # 避免在句子中间截断
    last_punct = -1
    for punct in ['。', '！', '？', '…', '.', '!', '?']:
        pos = summary.rfind(punct)
        if pos > last_punct:
            last_punct = pos
            
    if last_punct > 0:
        summary = summary[:last_punct + 1]
    
    return summary.strip()

def process_file(file_path):
    """处理单个JSON文件
    
    Args:
        file_path: JSON文件路径
    """
    print(f"\n处理文件: {file_path}")
    
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
            
        modified = False
        
        # 处理每篇文章
        for article in articles:
            if 'summary' not in article:
                summary = extract_summary(article.get('content', ''))
                if summary:
                    article['summary'] = summary
                    modified = True
                    print(f"已添加摘要: {summary[:30]}...")
                    
        # 如果有修改则保存
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            print("文件已更新")
        else:
            print("文件无需更新")
            
    except Exception as e:
        print(f"处理文件时出错: {e}")

def main():
    """主函数"""
    # 获取Output目录路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(os.path.dirname(script_dir), "Output")
    
    if not os.path.exists(output_dir):
        print(f"Output目录不存在: {output_dir}")
        return
        
    # 遍历Output目录下的所有子目录
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file == 'articles_detailed.json':
                file_path = os.path.join(root, file)
                process_file(file_path)
                
if __name__ == '__main__':
    main() 