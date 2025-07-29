#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级 JSON 格式转换工具
支持处理多个抓取结果文件夹
"""

import json
import csv
import os
import glob
from datetime import datetime
import re

# 尝试导入 pandas，如果失败则设置为 None
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

def format_date_for_notion(date_str):
    """将各种日期字符串格式化为YYYY-MM-DD，Notion友好"""
    if not date_str:
        return ''
    try:
        # 预处理：去除全角冒号、特殊空白
        date_str = date_str.strip().replace('：', ':').replace('\u3000', '').replace('\xa0', '').replace('\u200b', '')
        date_formats = [
            '%Y年%m月%d日 %H:%M',
            '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y.%m.%d %H:%M',
            '%Y-%m-%d', '%Y年%m月%d日', '%Y/%m/%d', '%Y.%m.%d'
        ]
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except Exception:
                continue
        # 尝试只取前10位
        if len(date_str) >= 10:
            return date_str[:10]
        print(f"⚠️ 无法识别日期格式: {date_str}")
    except Exception as e:
        print(f"⚠️ 日期解析异常: {date_str} ({e})")
    return date_str  # 保底返回原始

def clean_content(text):
    if not text:
        return ''
    # 替换多个连续换行为一个
    return re.sub(r'(\r\n|\r|\n)+', '\n', text)

def json_to_csv(json_file, csv_file, filter_failed=True):
    """
    将 JSON 文件转换为 CSV 文件
    
    Args:
        json_file: JSON 文件路径
        csv_file: 输出的 CSV 文件路径
        filter_failed: 是否过滤失败的文章
    """
    try:
        # 读取 JSON 文件
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        print(f"✅ 成功读取 {len(articles)} 篇文章")
        
        # 准备 CSV 数据
        csv_data = []
        failed_count = 0
        
        for article in articles:
            title = article.get('title', '').strip()
            error = article.get('error', '').strip()
            raw_date = article.get('publish_time', '')
            notion_date = format_date_for_notion(raw_date)
            content = clean_content(article.get('content', ''))
            
            if filter_failed:
                # 过滤模式：只保留成功抓取的文章
                if title and not error:
                    # 成功抓取的文章
                    row = {
                        '标题': title,
                        '作者': article.get('author', ''),
                        'Date': notion_date,
                        '阅读量': article.get('read_count', ''),
                        '点赞量': article.get('like_count', ''),
                        '链接': article.get('url', ''),
                        '内容': content[:1000] + '...' if len(content) > 1000 else content,
                        '状态': 'success'
                    }
                    csv_data.append(row)
                else:
                    # 失败的文章，统计数量但不添加到输出
                    failed_count += 1
            else:
                # 不过滤模式：保留所有文章
                row = {
                    '标题': title,
                    '作者': article.get('author', ''),
                    'Date': notion_date,
                    '阅读量': article.get('read_count', ''),
                    '点赞量': article.get('like_count', ''),
                    '链接': article.get('url', ''),
                    '内容': content[:1000] + '...' if len(content) > 1000 else content,
                    '错误信息': error,
                    '状态': article.get('status', '')
                }
                csv_data.append(row)
        
        if filter_failed:
            print(f"📊 过滤结果: 成功 {len(csv_data)} 篇，失败 {failed_count} 篇")
        else:
            print(f"📊 转换结果: 总计 {len(csv_data)} 篇")
        
        # 写入 CSV 文件
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            if csv_data:
                writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)
        
        print(f"✅ 成功转换为 CSV 文件: {csv_file}")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False

def json_to_excel(json_file, excel_file, filter_failed=True):
    """
    将 JSON 文件转换为 Excel 文件
    
    Args:
        json_file: JSON 文件路径
        excel_file: 输出的 Excel 文件路径
        filter_failed: 是否过滤失败的文章
    """
    if not PANDAS_AVAILABLE:
        print("❌ Excel 转换功能不可用，需要安装 pandas 和 openpyxl")
        print("   运行: pip install pandas openpyxl")
        return False
    
    try:
        # 读取 JSON 文件
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        print(f"✅ 成功读取 {len(articles)} 篇文章")
        
        # 准备数据
        data = []
        failed_count = 0
        
        for article in articles:
            title = article.get('title', '').strip()
            error = article.get('error', '').strip()
            
            if filter_failed:
                # 过滤模式：只保留成功抓取的文章
                if title and not error:
                    # 成功抓取的文章
                    row = {
                        '标题': title,
                        '作者': article.get('author', ''),
                        '发布时间': article.get('publish_time', ''),
                        '阅读量': article.get('read_count', ''),
                        '点赞量': article.get('like_count', ''),
                        '链接': article.get('url', ''),
                        '内容': article.get('content', ''),
                        '状态': 'success'
                    }
                    data.append(row)
                else:
                    # 失败的文章，统计数量但不添加到输出
                    failed_count += 1
            else:
                # 不过滤模式：保留所有文章
                row = {
                    '标题': title,
                    '作者': article.get('author', ''),
                    '发布时间': article.get('publish_time', ''),
                    '阅读量': article.get('read_count', ''),
                    '点赞量': article.get('like_count', ''),
                    '链接': article.get('url', ''),
                    '内容': article.get('content', ''),
                    '错误信息': error,
                    '状态': article.get('status', '')
                }
                data.append(row)
        
        if filter_failed:
            print(f"📊 过滤结果: 成功 {len(data)} 篇，失败 {failed_count} 篇")
        else:
            print(f"📊 转换结果: 总计 {len(data)} 篇")
        
        # 创建 DataFrame 并保存为 Excel
        df = pd.DataFrame(data)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        
        print(f"✅ 成功转换为 Excel 文件: {excel_file}")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False

def find_article_files():
    """查找所有抓取结果文件夹中的文章文件"""
    # 查找所有 articles_batch_* 文件夹
    batch_folders = glob.glob("articles_batch_*")
    
    article_files = []
    for folder in batch_folders:
        json_file = os.path.join(folder, "articles_detailed.json")
        if os.path.exists(json_file):
            article_files.append((folder, json_file))
    
    return article_files

def show_menu():
    """显示菜单"""
    print("\n" + "="*50)
    print("📊 JSON 格式转换工具")
    print("="*50)
    print("1. 转换当前目录的 articles_detailed.json")
    print("2. 转换所有抓取结果文件夹")
    print("3. 转换指定文件夹")
    print("4. 查看可用的文章文件")
    print("5. 设置转换选项")
    print("0. 退出")
    print("="*50)

def main():
    # 显示 pandas 状态
    if PANDAS_AVAILABLE:
        print("✅ pandas 已安装，支持 Excel 转换功能")
    else:
        print("⚠️  pandas 未安装，Excel 转换功能不可用")
        print("   如需 Excel 功能，请运行: pip install pandas openpyxl")
    
    # 转换选项
    filter_failed = True  # 默认过滤失败的文章
    
    print(f"\n⚙️  默认设置: 过滤失败文章（只保留成功抓取的文章）")
    print(f"   如需修改，请选择菜单中的 '设置转换选项'")
    
    while True:
        show_menu()
        choice = input("请选择 (0-5): ").strip()
        
        if choice == "0":
            print("👋 程序已退出")
            break
            
        elif choice == "1":
            # 转换当前目录的文件
            json_file = "articles_detailed.json"
            if os.path.exists(json_file):
                print(f"\n🔄 转换当前目录文件: {json_file}")
                json_to_csv(json_file, "articles.csv", filter_failed)
                json_to_excel(json_file, "articles.xlsx", filter_failed)
            else:
                print(f"❌ 文件不存在: {json_file}")
                
        elif choice == "2":
            # 转换所有抓取结果文件夹
            article_files = find_article_files()
            if not article_files:
                print("❌ 未找到任何抓取结果文件夹")
                continue
                
            print(f"\n🔄 找到 {len(article_files)} 个抓取结果文件夹:")
            for folder, json_file in article_files:
                print(f"   📁 {folder}")
                
            confirm = input("\n是否转换所有文件夹? (y/n): ").strip().lower()
            if confirm == 'y':
                for folder, json_file in article_files:
                    print(f"\n🔄 转换文件夹: {folder}")
                    csv_file = os.path.join(folder, "articles.csv")
                    excel_file = os.path.join(folder, "articles.xlsx")
                    
                    json_to_csv(json_file, csv_file, filter_failed)
                    json_to_excel(json_file, excel_file, filter_failed)
                        
        elif choice == "3":
            # 转换指定文件夹
            article_files = find_article_files()
            if not article_files:
                print("❌ 未找到任何抓取结果文件夹")
                continue
                
            print(f"\n📁 可用的抓取结果文件夹:")
            for i, (folder, json_file) in enumerate(article_files, 1):
                print(f"   {i}. {folder}")
                
            try:
                folder_choice = int(input("\n请选择文件夹编号: ").strip())
                if 1 <= folder_choice <= len(article_files):
                    folder, json_file = article_files[folder_choice - 1]
                    print(f"\n🔄 转换文件夹: {folder}")
                    
                    csv_file = os.path.join(folder, "articles.csv")
                    excel_file = os.path.join(folder, "articles.xlsx")
                    
                    json_to_csv(json_file, csv_file, filter_failed)
                    json_to_excel(json_file, excel_file, filter_failed)
                else:
                    print("❌ 无效的选择")
            except ValueError:
                print("❌ 请输入有效的数字")
                
        elif choice == "4":
            # 查看可用的文章文件
            article_files = find_article_files()
            if not article_files:
                print("❌ 未找到任何抓取结果文件夹")
            else:
                print(f"\n📁 找到 {len(article_files)} 个抓取结果文件夹:")
                for folder, json_file in article_files:
                    # 读取抓取信息
                    info_file = os.path.join(folder, "crawl_info.json")
                    if os.path.exists(info_file):
                        try:
                            with open(info_file, 'r', encoding='utf-8') as f:
                                info = json.load(f)
                            print(f"   📁 {folder}")
                            print(f"      📊 总计: {info.get('total_articles', 0)} 篇")
                            print(f"      ✅ 成功: {info.get('success_count', 0)} 篇")
                            print(f"      ❌ 失败: {info.get('fail_count', 0)} 篇")
                            print(f"      📄 删除: {info.get('deleted_count', 0)} 篇")
                            print(f"      📅 时间范围: {info.get('time_range', '未知')}")
                            print(f"      🕐 抓取时间: {info.get('crawl_time', '未知')}")
                        except:
                            print(f"   📁 {folder} (信息文件读取失败)")
                    else:
                        print(f"   📁 {folder} (无信息文件)")
                    print()
                    
        elif choice == "5":
            # 设置转换选项
            print(f"\n⚙️  当前设置:")
            print(f"   过滤失败文章: {'是' if filter_failed else '否'}")
            print(f"\n请选择设置:")
            print("1. 过滤失败文章（推荐，只保留成功抓取的文章）")
            print("2. 保留所有文章（包括失败的文章）")
            print("0. 返回主菜单")
            
            setting_choice = input("请选择 (0-2): ").strip()
            if setting_choice == "1":
                filter_failed = True
                print("✅ 已设置为过滤失败文章")
            elif setting_choice == "2":
                filter_failed = False
                print("✅ 已设置为保留所有文章")
            elif setting_choice == "0":
                pass
            else:
                print("❌ 无效的选择")
        else:
            print("❌ 无效的选择，请重新输入")

if __name__ == "__main__":
    main() 