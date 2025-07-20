#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试页面有效性检测功能
"""

import re
from playwright.sync_api import sync_playwright

def test_page_detection(url):
    """测试页面有效性检测"""
    print(f"🔍 测试页面: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state('domcontentloaded', timeout=15000)
            page.wait_for_timeout(3000)
            
            # 获取页面内容
            page_content = page.content()
            
            # 检测删除/违规页面的关键词
            invalid_keywords = [
                "此内容发送失败无法查看",
                "此内容因涉嫌违反相关法律法规和政策发送失败",
                "内容已删除",
                "文章不存在",
                "该内容已被删除",
                "内容违规",
                "无法查看",
                "发送失败",
                "违规内容",
                "内容不存在"
            ]
            
            is_invalid_page = any(keyword in page_content for keyword in invalid_keywords)
            
            if is_invalid_page:
                print("❌ 检测到无效页面")
                # 显示页面中的相关文本
                for keyword in invalid_keywords:
                    if keyword in page_content:
                        print(f"   发现关键词: {keyword}")
                return False
            else:
                print("✅ 页面有效")
                return True
                
        except Exception as e:
            print(f"❌ 访问失败: {e}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    # 测试一些已知的URL
    test_urls = [
        # 这里可以添加一些测试URL
        # "https://mp.weixin.qq.com/s/example1",
        # "https://mp.weixin.qq.com/s/example2",
    ]
    
    if not test_urls:
        print("请在脚本中添加测试URL")
    else:
        for url in test_urls:
            test_page_detection(url)
            print("-" * 50) 