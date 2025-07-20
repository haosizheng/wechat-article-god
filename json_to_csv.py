import json
import csv
import pandas as pd

def json_to_csv(json_file, csv_file):
    """
    将 JSON 文件转换为 CSV 文件
    
    Args:
        json_file: JSON 文件路径
        csv_file: 输出的 CSV 文件路径
    """
    try:
        # 读取 JSON 文件
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        print(f"成功读取 {len(articles)} 篇文章")
        
        # 准备 CSV 数据
        csv_data = []
        for article in articles:
            row = {
                '标题': article.get('title', ''),
                '作者': article.get('author', ''),
                '发布时间': article.get('publish_time', ''),
                '阅读量': article.get('read_count', ''),
                '点赞量': article.get('like_count', ''),
                '链接': article.get('url', ''),
                '内容': article.get('content', '')[:1000] + '...' if len(article.get('content', '')) > 1000 else article.get('content', ''),
                '错误信息': article.get('error', '')
            }
            csv_data.append(row)
        
        # 写入 CSV 文件
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            if csv_data:
                writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)
        
        print(f"成功转换为 CSV 文件: {csv_file}")
        
    except Exception as e:
        print(f"转换失败: {e}")

def json_to_excel(json_file, excel_file):
    """
    将 JSON 文件转换为 Excel 文件
    
    Args:
        json_file: JSON 文件路径
        excel_file: 输出的 Excel 文件路径
    """
    try:
        # 读取 JSON 文件
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        print(f"成功读取 {len(articles)} 篇文章")
        
        # 准备数据
        data = []
        for article in articles:
            row = {
                '标题': article.get('title', ''),
                '作者': article.get('author', ''),
                '发布时间': article.get('publish_time', ''),
                '阅读量': article.get('read_count', ''),
                '点赞量': article.get('like_count', ''),
                '链接': article.get('url', ''),
                '内容': article.get('content', ''),
                '错误信息': article.get('error', '')
            }
            data.append(row)
        
        # 创建 DataFrame 并保存为 Excel
        df = pd.DataFrame(data)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        
        print(f"成功转换为 Excel 文件: {excel_file}")
        
    except Exception as e:
        print(f"转换失败: {e}")

def main():
    print("JSON 格式转换工具")
    print("=" * 30)
    
    json_file = "articles_detailed.json"
    
    # 转换为 CSV
    print("1. 转换为 CSV 格式...")
    json_to_csv(json_file, "articles.csv")
    
    # 转换为 Excel
    try:
        print("\n2. 转换为 Excel 格式...")
        json_to_excel(json_file, "articles.xlsx")
    except ImportError:
        print("  跳过 Excel 转换 (需要安装 pandas 和 openpyxl)")
        print("  运行: pip install pandas openpyxl")
    
    print("\n转换完成！")
    print("现在你可以:")
    print("1. 使用 articles.csv 导入到 Notion (通过 CSV 导入功能)")
    print("2. 使用 articles.xlsx 在 Excel 中查看和编辑")
    print("3. 使用 notion_importer.py 直接通过 API 导入到 Notion")

if __name__ == "__main__":
    main() 