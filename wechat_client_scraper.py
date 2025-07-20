#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章阅读量、点赞量获取工具
通过微信客户端获取真实数据
"""

import requests
import json
import re
import time
from urllib.parse import urlparse, parse_qs

class WeChatClientScraper:
    def __init__(self):
        self.session = requests.Session()
        self.cookies = {}
        self.appmsg_token = ""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def extract_params_from_url(self, url):
        """从URL中提取必要的参数"""
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # 提取关键参数
            __biz = query_params.get('__biz', [''])[0]
            mid = query_params.get('mid', [''])[0]
            idx = query_params.get('idx', [''])[0]
            sn = query_params.get('sn', [''])[0]
            
            return {
                '__biz': __biz,
                'mid': mid,
                'idx': idx,
                'sn': sn
            }
        except Exception as e:
            print(f"❌ URL参数提取失败: {e}")
            return None
    
    def get_article_data(self, url, cookies, appmsg_token):
        """获取文章详细数据"""
        try:
            # 设置cookies和token
            self.session.cookies.update(cookies)
            self.appmsg_token = appmsg_token
            
            # 提取URL参数
            params = self.extract_params_from_url(url)
            if not params:
                return None
            
            # 构建API请求URL
            api_url = "https://mp.weixin.qq.com/mp/getappmsgext"
            
            # 请求参数
            data = {
                '__biz': params['__biz'],
                'mid': params['mid'],
                'sn': params['sn'],
                'idx': params['idx'],
                'appmsg_type': '9',
                'appmsg_token': appmsg_token,
                'f': 'json',
                'pass_ticket': '',
                'wxtoken': '',
                'x5': '0'
            }
            
            # 发送请求
            response = self.session.post(api_url, data=data, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"❌ API请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取文章数据失败: {e}")
            return None
    
    def parse_article_stats(self, api_data):
        """解析文章统计数据"""
        try:
            if not api_data or 'appmsgstat' not in api_data:
                return None
            
            stats = api_data['appmsgstat']
            
            return {
                'read_num': stats.get('read_num', 0),  # 阅读数
                'like_num': stats.get('like_num', 0),  # 点赞数
                'reward_num': stats.get('reward_num', 0),  # 赞赏数
                'reward_total_count': stats.get('reward_total_count', 0),  # 赞赏总人数
            }
            
        except Exception as e:
            print(f"❌ 解析统计数据失败: {e}")
            return None

def manual_setup_guide():
    """手动设置指南"""
    print("📱 微信客户端获取阅读量、点赞量指南")
    print("="*60)
    print()
    print("步骤1: 在微信中打开文章")
    print("   - 用微信扫描文章二维码")
    print("   - 或在微信中点击文章链接")
    print()
    print("步骤2: 获取Cookie和Token")
    print("   - 在微信中打开文章后")
    print("   - 使用抓包工具（如Fiddler、Charles）")
    print("   - 或使用浏览器开发者工具")
    print()
    print("步骤3: 提取必要信息")
    print("   - 找到包含 'appmsg_token' 的请求")
    print("   - 记录Cookie和appmsg_token值")
    print()
    print("步骤4: 使用脚本获取数据")
    print("   - 将Cookie和Token填入脚本")
    print("   - 运行脚本获取统计数据")
    print()

def parse_getappmsgext_url(url):
    """解析getappmsgext URL并提取参数"""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # 提取核心参数
        config = {
            "cookies": {
                "appmsg_token": query_params.get('appmsg_token', [''])[0],
                "wxuin": query_params.get('uin', [''])[0],
                "pass_ticket": query_params.get('pass_ticket', [''])[0],
                "wxtoken": query_params.get('wxtoken', [''])[0]
            },
            "request_params": {
                "key": query_params.get('key', [''])[0],
                "devicetype": query_params.get('devicetype', [''])[0].replace('%26nbsp%3B', ' ').replace('%2C', ','),
                "clientversion": query_params.get('clientversion', [''])[0],
                "version": query_params.get('version', [''])[0],
                "__biz": query_params.get('__biz', [''])[0],
                "x5": query_params.get('x5', [''])[0]
            },
            "config_info": {
                "created_at": time.strftime("%Y-%m-%d"),
                "token_expires_in": "2小时",
                "note": "从getappmsgext URL自动解析生成"
            }
        }
        
        return config
    except Exception as e:
        print(f"❌ URL解析失败: {e}")
        return None

def create_config_from_url():
    """从URL创建配置文件"""
    print("🔗 从getappmsgext URL创建配置文件")
    print("="*50)
    print()
    print("请粘贴完整的getappmsgext URL:")
    print("(例如: https://mp.weixin.qq.com/mp/getappmsgext?f=json&appmsg_token=...)")
    print()
    
    url = input("URL: ").strip()
    
    if not url:
        print("❌ URL不能为空")
        return
    
    # 解析URL
    config = parse_getappmsgext_url(url)
    
    if not config:
        print("❌ URL解析失败，请检查URL格式")
        return
    
    # 验证必要参数
    required_params = ['appmsg_token', 'wxuin', 'pass_ticket', 'wxtoken']
    missing_params = []
    
    for param in required_params:
        if not config['cookies'].get(param):
            missing_params.append(param)
    
    if missing_params:
        print(f"❌ URL缺少必要参数: {', '.join(missing_params)}")
        return
    
    # 保存配置文件
    try:
        with open("wechat_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print("✅ 配置文件创建成功: wechat_config.json")
        print()
        print("📋 提取的参数:")
        print(f"   appmsg_token: {config['cookies']['appmsg_token'][:30]}...")
        print(f"   wxuin: {config['cookies']['wxuin']}")
        print(f"   pass_ticket: {config['cookies']['pass_ticket'][:30]}...")
        print(f"   wxtoken: {config['cookies']['wxtoken']}")
        print()
        print("🚀 现在可以使用 batch_stats_scraper.py 批量获取统计数据了！")
        
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")

def create_config_template():
    """创建配置模板"""
    config = {
        "cookies": {
            "appmsg_token": "YOUR_APPMSG_TOKEN_HERE",
            "wxuin": "YOUR_WXUIN_HERE",
            "pass_ticket": "YOUR_PASS_TICKET_HERE",
            "wxtoken": "YOUR_WXTOKEN_HERE"
        },
        "instructions": [
            "1. 在微信中打开任意公众号文章",
            "2. 使用抓包工具获取请求信息",
            "3. 将获取到的值填入上面的cookies中",
            "4. 保存文件为 wechat_config.json",
            "5. 运行脚本获取统计数据"
        ]
    }
    
    with open("wechat_config_template.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("✅ 已创建配置文件模板: wechat_config_template.json")
    print("请按照模板中的说明获取必要信息")

def main():
    print("📱 微信公众号文章统计数据获取工具")
    print("="*50)
    print()
    print("由于微信限制，阅读量和点赞量只能在微信客户端中获取")
    print("请选择操作:")
    print()
    print("1. 查看手动设置指南")
    print("2. 从URL自动创建配置文件 ⭐")
    print("3. 创建配置模板")
    print("4. 测试API连接")
    print("0. 退出")
    print()
    
    choice = input("请选择 (0-4): ").strip()
    
    if choice == "1":
        manual_setup_guide()
    elif choice == "2":
        create_config_from_url()
    elif choice == "3":
        create_config_template()
    elif choice == "4":
        print("🔧 测试功能开发中...")
        print("请先按照指南手动获取Cookie和Token")
    elif choice == "0":
        print("👋 程序已退出")
    else:
        print("❌ 无效选择")

if __name__ == "__main__":
    main() 