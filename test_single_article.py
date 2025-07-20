#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单篇文章统计数据获取
"""

import requests
import json
from urllib.parse import urlparse, parse_qs
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_config():
    """测试配置文件"""
    try:
        with open("wechat_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        print("✅ 配置文件加载成功")
        print(f"   appmsg_token: {config['cookies']['appmsg_token'][:30]}...")
        print(f"   wxuin: {config['cookies']['wxuin']}")
        return config
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return None

def test_article_url(url):
    """测试文章URL"""
    print(f"\n🔗 测试文章URL: {url}")
    
    # 创建会话
    session = requests.Session()
    session.verify = False  # 禁用SSL验证
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # 获取重定向后的URL
        response = session.get(url, headers=headers, allow_redirects=True)
        final_url = response.url
        print(f"   ✅ 最终URL: {final_url}")
        
        # 解析参数
        parsed = urlparse(final_url)
        query_params = parse_qs(parsed.query)
        
        print(f"   📋 URL参数:")
        for key, value in query_params.items():
            print(f"      {key}: {value[0]}")
        
        # 检查必要参数
        required_params = ['__biz', 'mid', 'idx', 'sn']
        missing_params = []
        
        for param in required_params:
            if param not in query_params:
                missing_params.append(param)
        
        if missing_params:
            print(f"   ❌ 缺少参数: {missing_params}")
            return None
        else:
            print(f"   ✅ 所有必要参数都存在")
            return query_params
            
    except Exception as e:
        print(f"   ❌ URL测试失败: {e}")
        return None

def test_api_request(config, url_params):
    """测试API请求"""
    print(f"\n🚀 测试API请求...")
    
    session = requests.Session()
    session.verify = False
    
    # 设置cookies
    cookies = config['cookies']
    session.cookies.update(cookies)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # 构建API请求
        api_url = "https://mp.weixin.qq.com/mp/getappmsgext"
        data = {
            '__biz': url_params['__biz'][0],
            'mid': url_params['mid'][0],
            'sn': url_params['sn'][0],
            'idx': url_params['idx'][0],
            'appmsg_type': '9',
            'appmsg_token': cookies['appmsg_token'],
            'f': 'json',
            'pass_ticket': cookies['pass_ticket'],
            'wxtoken': cookies['wxtoken'],
            'x5': '0'
        }
        
        print(f"   📤 发送请求到: {api_url}")
        print(f"   📋 请求参数: {list(data.keys())}")
        
        # 发送请求
        response = session.post(api_url, data=data, headers=headers, timeout=30)
        
        print(f"   📥 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   📄 响应内容: {result}")
            
            if 'appmsgstat' in result:
                stats = result['appmsgstat']
                print(f"   ✅ 成功获取统计数据:")
                print(f"      阅读量: {stats.get('read_num', 0)}")
                print(f"      点赞量: {stats.get('like_num', 0)}")
                print(f"      赞赏量: {stats.get('reward_num', 0)}")
                return True
            else:
                print(f"   ❌ 响应中没有统计数据")
                return False
        else:
            print(f"   ❌ API请求失败: {response.status_code}")
            print(f"   📄 响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ API请求异常: {e}")
        return False

def main():
    print("🧪 单篇文章统计数据获取测试")
    print("="*50)
    
    # 测试配置文件
    config = test_config()
    if not config:
        return
    
    # 测试文章URL
    test_url = "https://mp.weixin.qq.com/s/hh3SWJu7Uof7a2KWBAE7Vg"
    url_params = test_article_url(test_url)
    if not url_params:
        return
    
    # 测试API请求
    success = test_api_request(config, url_params)
    
    if success:
        print(f"\n🎉 测试成功！配置和API都正常工作")
    else:
        print(f"\n❌ 测试失败，请检查配置或网络连接")

if __name__ == "__main__":
    main() 