#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试微信公众号页面结构
检查阅读量和点赞量的实际元素位置
"""

import re
from playwright.sync_api import sync_playwright
import time

def debug_page_structure(url):
    """调试页面结构，查找阅读量和点赞量元素"""
    print(f"🔍 调试页面: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 设置为可见模式便于调试
        page = browser.new_page()
        
        try:
            # 访问页面
            page.goto(url, timeout=30000)
            page.wait_for_load_state('domcontentloaded', timeout=15000)
            page.wait_for_timeout(5000)
            
            print("✅ 页面加载完成")
            
            # 检查页面标题
            title_element = page.query_selector('h1.rich_media_title')
            if title_element:
                title = title_element.inner_text().strip()
                print(f"📰 文章标题: {title}")
            else:
                print("❌ 未找到文章标题")
            
            # 查找所有包含"阅读"的元素
            print("\n🔍 查找阅读量相关元素:")
            read_elements = page.query_selector_all('*')
            read_found = False
            
            for element in read_elements:
                try:
                    text = element.inner_text().strip()
                    if '阅读' in text and re.search(r'\d+', text):
                        tag_name = element.evaluate('el => el.tagName')
                        class_name = element.evaluate('el => el.className')
                        id_name = element.evaluate('el => el.id')
                        print(f"   📖 找到阅读元素: {tag_name}.{class_name}#{id_name} = '{text}'")
                        read_found = True
                except:
                    continue
            
            if not read_found:
                print("   ❌ 未找到阅读量元素")
            
            # 查找所有包含"赞"的元素
            print("\n🔍 查找点赞量相关元素:")
            like_elements = page.query_selector_all('*')
            like_found = False
            
            for element in like_elements:
                try:
                    text = element.inner_text().strip()
                    if '赞' in text and re.search(r'\d+', text):
                        tag_name = element.evaluate('el => el.tagName')
                        class_name = element.evaluate('el => el.className')
                        id_name = element.evaluate('el => el.id')
                        print(f"   👍 找到点赞元素: {tag_name}.{class_name}#{id_name} = '{text}'")
                        like_found = True
                except:
                    continue
            
            if not like_found:
                print("   ❌ 未找到点赞量元素")
            
            # 查找所有span元素
            print("\n🔍 查找所有span元素:")
            span_elements = page.query_selector_all('span')
            for i, span in enumerate(span_elements[:20]):  # 只显示前20个
                try:
                    text = span.inner_text().strip()
                    if text and len(text) < 50:  # 只显示短文本
                        class_name = span.evaluate('el => el.className')
                        id_name = span.evaluate('el => el.id')
                        print(f"   span[{i}]: {class_name}#{id_name} = '{text}'")
                except:
                    continue
            
            # 查找所有包含数字的元素
            print("\n🔍 查找包含数字的元素:")
            number_elements = page.query_selector_all('*')
            number_found = 0
            
            for element in number_elements:
                try:
                    text = element.inner_text().strip()
                    if re.search(r'\d+', text) and len(text) < 20:
                        tag_name = element.evaluate('el => el.tagName')
                        class_name = element.evaluate('el => el.className')
                        id_name = element.evaluate('el => el.id')
                        print(f"   🔢 {tag_name}.{class_name}#{id_name} = '{text}'")
                        number_found += 1
                        if number_found >= 10:  # 只显示前10个
                            break
                except:
                    continue
            
            # 等待用户查看
            print(f"\n⏰ 页面将保持打开状态 30 秒，请手动检查页面结构...")
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ 调试失败: {e}")
        finally:
            browser.close()

def main():
    print("🔧 微信公众号页面结构调试工具")
    print("="*50)
    
    # 可以添加测试URL
    test_urls = [
        # 在这里添加要调试的URL
        # "https://mp.weixin.qq.com/s/example1",
        # "https://mp.weixin.qq.com/s/example2",
    ]
    
    if not test_urls:
        print("请在脚本中添加要调试的URL")
        url = input("或者直接输入URL进行调试: ").strip()
        if url:
            debug_page_structure(url)
    else:
        for url in test_urls:
            debug_page_structure(url)
            print("-" * 50)

if __name__ == "__main__":
    main() 