import os
import json
import argparse

def remove_field_from_file(file_path, field_name):
    """从JSON文件中删除指定字段
    
    Args:
        file_path: JSON文件路径
        field_name: 要删除的字段名
    """
    print(f"\n处理文件: {file_path}")
    
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
            
        modified = False
        removed_count = 0
        total_count = len(articles)
        
        print(f"文件中共有 {total_count} 篇文章")
        
        # 处理每篇文章
        for i, article in enumerate(articles):
            if field_name in article:
                print(f"删除第 {i+1} 篇文章的 {field_name} 字段")
                del article[field_name]
                modified = True
                removed_count += 1
                    
        # 如果有修改则保存
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            print(f"已删除 {removed_count} 条 {field_name} 字段")
            print("文件已更新")
        else:
            print(f"未找到 {field_name} 字段,文件无需更新")
            
    except Exception as e:
        print(f"处理文件时出错: {e}")

def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='删除JSON文件中的指定字段')
    parser.add_argument('field', help='要删除的字段名')
    args = parser.parse_args()
    
    field_name = args.field
    print(f"准备删除字段: {field_name}")
    
    # 获取当前工作目录
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    
    # 遍历当前目录下的所有子目录
    found_files = False
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file == 'articles_detailed.json':
                found_files = True
                file_path = os.path.join(root, file)
                remove_field_from_file(file_path, field_name)
    
    if not found_files:
        print("未找到任何 articles_detailed.json 文件")
                
if __name__ == '__main__':
    main() 