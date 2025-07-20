#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动输入完整文章URL工具
用于处理微信短链接无法自动展开的情况
"""

import json
import os
from datetime import datetime

def load_articles(input_file):
    """加载文章数据"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载文章数据失败: {e}")
        return None

def save_articles_with_full_urls(articles, output_file):
    """保存包含完整URL的文章数据"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return False

def get_full_url_from_user(article):
    """从用户获取完整URL"""
    print(f"\n📝 文章: {article.get('title', '无标题')}")
    print(f"   作者: {article.get('author', '未知')}")
    print(f"   发布时间: {article.get('publish_time', '未知')}")
    print(f"   短链接: {article.get('url', '无链接')}")
    print()
    
    while True:
        full_url = input("请输入完整文章URL (包含__biz, mid, idx, sn参数): ").strip()
        
        if not full_url:
            print("❌ URL不能为空，请重新输入")
            continue
        
        if not full_url.startswith('https://mp.weixin.qq.com/'):
            print("❌ 请输入正确的微信公众号文章URL")
            continue
        
        # 检查是否包含必要参数
        if '__biz=' in full_url and 'mid=' in full_url and 'idx=' in full_url and 'sn=' in full_url:
            print("✅ URL格式正确")
            return full_url
        else:
            print("❌ URL缺少必要参数(__biz, mid, idx, sn)，请重新输入")
            print("   示例: https://mp.weixin.qq.com/s?__biz=MzI4MTI3MzgxNA==&mid=2651234567&idx=1&sn=abcdef123456")

def main():
    print("🔗 手动输入完整文章URL工具")
    print("="*50)
    print()
    print("由于微信短链接访问限制，需要手动输入完整URL")
    print("完整URL格式: https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx&idx=xxx&sn=xxx")
    print()
    
    # 选择输入文件
    input_files = [
        "articles_detailed_20250720_165023.json",
        "articles_batch_20250720_170202/articles_detailed.json",
        "articles_batch_20250720_170816/articles_detailed.json",
        "articles_batch_20250720_172001/articles_detailed.json"
    ]
    
    print("可用的文章数据文件:")
    for i, file_path in enumerate(input_files, 1):
        if os.path.exists(file_path):
            print(f"   {i}. {file_path}")
    
    print()
    choice = input("请选择文件编号 (1-4): ").strip()
    
    try:
        file_index = int(choice) - 1
        if 0 <= file_index < len(input_files):
            input_file = input_files[file_index]
        else:
            print("❌ 无效选择")
            return
    except ValueError:
        print("❌ 请输入数字")
        return
    
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        return
    
    # 加载文章数据
    articles = load_articles(input_file)
    if not articles:
        return
    
    print(f"\n📊 加载了 {len(articles)} 篇文章")
    
    # 处理每篇文章
    updated_articles = []
    skipped_count = 0
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] 处理文章...")
        
        current_url = article.get('url', '')
        
        # 检查是否已经是完整URL
        if current_url and '__biz=' in current_url and 'mid=' in current_url and 'idx=' in current_url and 'sn=' in current_url:
            print(f"   ✅ 已经是完整URL，跳过")
            updated_articles.append(article)
            continue
        
        # 询问用户是否处理这篇文章
        action = input(f"   是否处理这篇文章? (y/n/s=跳过所有): ").strip().lower()
        
        if action == 's':
            print(f"   ⏭️  跳过剩余 {len(articles) - i + 1} 篇文章")
            # 将剩余文章直接添加
            updated_articles.extend(articles[i-1:])
            break
        elif action not in ['y', 'yes', '是']:
            print(f"   ⏭️  跳过此文章")
            skipped_count += 1
            updated_articles.append(article)
            continue
        
        # 获取完整URL
        full_url = get_full_url_from_user(article)
        if full_url:
            article['url'] = full_url
            article['full_url_added'] = True
            article['url_updated_at'] = datetime.now().isoformat()
            updated_articles.append(article)
        else:
            print(f"   ❌ 跳过此文章")
            skipped_count += 1
            updated_articles.append(article)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"articles_with_full_urls_{timestamp}.json"
    
    if save_articles_with_full_urls(updated_articles, output_file):
        print(f"\n🎉 处理完成！")
        print(f"   总计: {len(articles)} 篇")
        print(f"   更新: {len([a for a in updated_articles if a.get('full_url_added')])} 篇")
        print(f"   跳过: {skipped_count} 篇")
        print(f"   输出文件: {output_file}")
        print(f"\n🚀 现在可以使用以下命令批量获取统计数据:")
        print(f"   python3 batch_stats_scraper.py --input {output_file} --delay 1.0")

if __name__ == "__main__":
    main() 