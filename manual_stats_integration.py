#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动获取阅读量、点赞量并整合到抓取结果
适用于文章数量较少的情况
"""

import json
import os
from datetime import datetime

def load_article_data(json_file):
    """加载文章数据"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载文章数据失败: {e}")
        return None

def save_article_data(articles, json_file):
    """保存文章数据"""
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已保存到: {json_file}")
    except Exception as e:
        print(f"❌ 保存数据失败: {e}")

def manual_input_stats():
    """手动输入统计数据"""
    print("\n📊 手动输入文章统计数据")
    print("="*40)
    
    stats = {}
    
    while True:
        url = input("\n请输入文章链接 (输入 'done' 完成): ").strip()
        if url.lower() == 'done':
            break
        
        if not url.startswith('https://mp.weixin.qq.com/'):
            print("❌ 请输入有效的微信公众号文章链接")
            continue
        
        print(f"\n🔍 正在处理: {url}")
        
        try:
            read_count = input("阅读量 (直接回车跳过): ").strip()
            like_count = input("点赞量 (直接回车跳过): ").strip()
            
            # 验证输入
            if read_count and not read_count.isdigit():
                print("❌ 阅读量必须是数字")
                continue
            
            if like_count and not like_count.isdigit():
                print("❌ 点赞量必须是数字")
                continue
            
            stats[url] = {
                'read_count': read_count if read_count else '',
                'like_count': like_count if like_count else '',
                'updated_at': datetime.now().isoformat()
            }
            
            print(f"✅ 已记录: 阅读量={read_count or '未填写'}, 点赞量={like_count or '未填写'}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 输入被中断")
            break
        except Exception as e:
            print(f"❌ 输入错误: {e}")
            continue
    
    return stats

def integrate_stats(articles, manual_stats):
    """整合手动输入的统计数据到文章数据中"""
    updated_count = 0
    
    for article in articles:
        url = article.get('url', '')
        if url in manual_stats:
            stats = manual_stats[url]
            
            # 更新统计数据
            if stats.get('read_count'):
                article['read_count'] = stats['read_count']
            if stats.get('like_count'):
                article['like_count'] = stats['like_count']
            
            # 添加更新标记
            article['stats_updated'] = True
            article['stats_updated_at'] = stats['updated_at']
            
            updated_count += 1
            print(f"✅ 已更新: {article.get('title', '未知标题')}")
    
    return updated_count

def show_integration_menu():
    """显示整合菜单"""
    print("\n" + "="*50)
    print("📊 手动统计数据整合工具")
    print("="*50)
    print("1. 查看可用的文章文件")
    print("2. 手动输入统计数据")
    print("3. 整合统计数据到文章文件")
    print("4. 查看整合结果")
    print("0. 退出")
    print("="*50)

def find_article_files():
    """查找所有文章文件"""
    article_files = []
    
    # 查找当前目录的文章文件
    if os.path.exists("articles_detailed.json"):
        article_files.append(("当前目录", "articles_detailed.json"))
    
    # 查找抓取结果文件夹
    import glob
    batch_folders = glob.glob("articles_batch_*")
    for folder in batch_folders:
        json_file = os.path.join(folder, "articles_detailed.json")
        if os.path.exists(json_file):
            article_files.append((folder, json_file))
    
    return article_files

def main():
    print("📊 手动统计数据整合工具")
    print("适用于文章数量较少的情况")
    
    manual_stats = {}
    
    while True:
        show_integration_menu()
        choice = input("请选择 (0-4): ").strip()
        
        if choice == "0":
            print("👋 程序已退出")
            break
            
        elif choice == "1":
            # 查看可用的文章文件
            article_files = find_article_files()
            if not article_files:
                print("❌ 未找到任何文章文件")
            else:
                print(f"\n📁 找到 {len(article_files)} 个文章文件:")
                for i, (folder, json_file) in enumerate(article_files, 1):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            articles = json.load(f)
                        print(f"   {i}. {folder}/{os.path.basename(json_file)} ({len(articles)} 篇文章)")
                    except:
                        print(f"   {i}. {folder}/{os.path.basename(json_file)} (读取失败)")
                        
        elif choice == "2":
            # 手动输入统计数据
            manual_stats = manual_input_stats()
            print(f"\n✅ 已记录 {len(manual_stats)} 篇文章的统计数据")
            
        elif choice == "3":
            # 整合统计数据
            if not manual_stats:
                print("❌ 请先手动输入统计数据")
                continue
                
            article_files = find_article_files()
            if not article_files:
                print("❌ 未找到任何文章文件")
                continue
            
            print(f"\n📁 可用的文章文件:")
            for i, (folder, json_file) in enumerate(article_files, 1):
                print(f"   {i}. {folder}")
            
            try:
                file_choice = int(input("\n请选择要整合的文件编号: ").strip())
                if 1 <= file_choice <= len(article_files):
                    folder, json_file = article_files[file_choice - 1]
                    
                    # 加载文章数据
                    articles = load_article_data(json_file)
                    if not articles:
                        continue
                    
                    # 整合统计数据
                    updated_count = integrate_stats(articles, manual_stats)
                    
                    # 保存更新后的数据
                    save_article_data(articles, json_file)
                    
                    print(f"\n🎉 整合完成！")
                    print(f"   更新了 {updated_count} 篇文章的统计数据")
                    print(f"   文件已保存: {json_file}")
                    
                else:
                    print("❌ 无效的文件编号")
            except ValueError:
                print("❌ 请输入有效的数字")
                
        elif choice == "4":
            # 查看整合结果
            if not manual_stats:
                print("❌ 还没有输入统计数据")
                continue
                
            print(f"\n📊 已记录的统计数据 ({len(manual_stats)} 篇):")
            for url, stats in manual_stats.items():
                print(f"   📄 {url}")
                print(f"      阅读量: {stats.get('read_count', '未填写')}")
                print(f"      点赞量: {stats.get('like_count', '未填写')}")
                print(f"      更新时间: {stats.get('updated_at', '未知')}")
                print()
                
        else:
            print("❌ 无效的选择")

if __name__ == "__main__":
    main() 