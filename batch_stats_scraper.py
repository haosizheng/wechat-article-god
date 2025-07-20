#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量获取微信公众号文章阅读量、点赞量
适用于大量文章场景
"""

import requests
import json
import time
import re
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import argparse

class BatchStatsScraper:
    def __init__(self, config_file="wechat_config.json"):
        self.session = requests.Session()
        self.config = self.load_config(config_file)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.setup_session()
    
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ 配置文件 {config_file} 不存在")
            print("请先运行 wechat_client_scraper.py 创建配置模板")
            return None
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return None
    
    def setup_session(self):
        """设置会话"""
        if not self.config:
            return
        
        # 设置cookies
        cookies = self.config.get('cookies', {})
        self.session.cookies.update(cookies)
        
        # 设置appmsg_token
        self.appmsg_token = cookies.get('appmsg_token', '')
        
        print(f"✅ 会话设置完成")
        print(f"   Token: {self.appmsg_token[:20]}...")
    
    def expand_short_url(self, url):
        """展开短链接为完整链接"""
        try:
            if '/s/' in url:  # 短链接格式
                print(f"🔗 检测到短链接，正在展开...")
                # 禁用SSL验证
                response = self.session.get(url, headers=self.headers, timeout=10, allow_redirects=False, verify=False)
                if response.status_code in [301, 302]:
                    expanded_url = response.headers.get('Location')
                    print(f"   ✅ 展开成功: {expanded_url}")
                    return expanded_url
                else:
                    print(f"   ⚠️  无法展开短链接，尝试直接访问...")
                    # 尝试直接访问获取完整URL
                    response = self.session.get(url, headers=self.headers, timeout=10, allow_redirects=True, verify=False)
                    final_url = response.url
                    if final_url != url:
                        print(f"   ✅ 获取到完整URL: {final_url}")
                        return final_url
                    else:
                        print(f"   ❌ 短链接展开失败，无法获取参数")
                        return None
            return url
        except Exception as e:
            print(f"   ⚠️  展开短链接失败: {e}")
            return None

    def extract_params_from_url(self, url):
        """从URL中提取必要参数"""
        try:
            # 先展开短链接
            full_url = self.expand_short_url(url)
            
            if not full_url:
                print(f"❌ 无法获取完整URL，跳过此文章")
                return None
            
            parsed = urlparse(full_url)
            query_params = parse_qs(parsed.query)
            
            required_params = ['__biz', 'mid', 'idx', 'sn']
            params = {}
            
            for param in required_params:
                value = query_params.get(param, [''])[0]
                if not value:
                    print(f"❌ URL缺少必要参数: {param}")
                    print(f"   当前URL参数: {list(query_params.keys())}")
                    print(f"   完整URL: {full_url}")
                    return None
                params[param] = value
            
            return params
        except Exception as e:
            print(f"❌ URL参数提取失败: {e}")
            return None
    
    def get_article_stats(self, url, retry_count=3):
        """获取单篇文章统计数据"""
        for attempt in range(retry_count):
            try:
                # 提取URL参数
                params = self.extract_params_from_url(url)
                if not params:
                    return None
                
                # 构建API请求
                api_url = "https://mp.weixin.qq.com/mp/getappmsgext"
                data = {
                    '__biz': params['__biz'],
                    'mid': params['mid'],
                    'sn': params['sn'],
                    'idx': params['idx'],
                    'appmsg_type': '9',
                    'appmsg_token': self.appmsg_token,
                    'f': 'json',
                    'pass_ticket': '',
                    'wxtoken': '',
                    'x5': '0'
                }
                
                # 发送请求
                response = self.session.post(api_url, data=data, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 检查是否成功
                    if 'appmsgstat' in result:
                        stats = result['appmsgstat']
                        return {
                            'read_num': stats.get('read_num', 0),
                            'like_num': stats.get('like_num', 0),
                            'reward_num': stats.get('reward_num', 0),
                            'reward_total_count': stats.get('reward_total_count', 0),
                            'success': True
                        }
                    else:
                        print(f"⚠️  API返回数据格式异常: {result}")
                        return {'success': False, 'error': '数据格式异常'}
                else:
                    print(f"❌ API请求失败: {response.status_code}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    return {'success': False, 'error': f'HTTP {response.status_code}'}
                    
            except requests.exceptions.Timeout:
                print(f"⏰ 请求超时，尝试重试...")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {'success': False, 'error': '请求超时'}
            except Exception as e:
                print(f"❌ 获取统计数据失败: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': '重试次数已用完'}
    
    def batch_get_stats(self, urls, delay=1.0):
        """批量获取统计数据"""
        if not self.config:
            print("❌ 请先配置微信参数")
            return None
        
        results = []
        total = len(urls)
        
        print(f"🚀 开始批量获取 {total} 篇文章的统计数据")
        print(f"   延迟设置: {delay} 秒")
        print(f"   预计时间: {total * delay / 60:.1f} 分钟")
        print()
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{total}] 正在处理: {url}")
            
            # 获取统计数据
            stats = self.get_article_stats(url)
            
            if stats and stats.get('success'):
                results.append({
                    'url': url,
                    'read_count': stats['read_num'],
                    'like_count': stats['like_num'],
                    'reward_count': stats['reward_num'],
                    'reward_total_count': stats['reward_total_count'],
                    'success': True,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"   ✅ 成功: 阅读量={stats['read_num']}, 点赞量={stats['like_num']}")
            else:
                error_msg = stats.get('error', '未知错误') if stats else '请求失败'
                results.append({
                    'url': url,
                    'success': False,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"   ❌ 失败: {error_msg}")
            
            # 延迟，避免请求过快
            if i < total:
                time.sleep(delay)
        
        return results
    
    def save_results(self, results, output_file="stats_results.json"):
        """保存结果"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            # 统计结果
            success_count = sum(1 for r in results if r.get('success'))
            fail_count = len(results) - success_count
            
            print(f"\n🎉 批量获取完成！")
            print(f"   总计: {len(results)} 篇")
            print(f"   成功: {success_count} 篇")
            print(f"   失败: {fail_count} 篇")
            print(f"   成功率: {success_count/len(results)*100:.1f}%")
            print(f"   结果已保存: {output_file}")
            
            return True
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")
            return False

def load_article_urls(input_file):
    """加载文章URL列表"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        urls = []
        for item in data:
            if isinstance(item, dict):
                url = item.get('url') or item.get('link')
                if url:
                    urls.append(url)
            elif isinstance(item, str):
                urls.append(item)
        
        return urls
    except Exception as e:
        print(f"❌ 加载文章列表失败: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='批量获取微信公众号文章统计数据')
    parser.add_argument('--input', '-i', default='articles_detailed.json', 
                       help='输入文件路径 (默认: articles_detailed.json)')
    parser.add_argument('--output', '-o', default='stats_results.json',
                       help='输出文件路径 (默认: stats_results.json)')
    parser.add_argument('--config', '-c', default='wechat_config.json',
                       help='配置文件路径 (默认: wechat_config.json)')
    parser.add_argument('--delay', '-d', type=float, default=1.0,
                       help='请求延迟秒数 (默认: 1.0)')
    parser.add_argument('--urls', nargs='+',
                       help='直接指定URL列表')
    
    args = parser.parse_args()
    
    print("📊 批量获取微信公众号文章统计数据")
    print("="*50)
    
    # 初始化抓取器
    scraper = BatchStatsScraper(args.config)
    
    # 获取URL列表
    if args.urls:
        urls = args.urls
        print(f"📝 使用命令行指定的 {len(urls)} 个URL")
    else:
        urls = load_article_urls(args.input)
        if not urls:
            print(f"❌ 无法从 {args.input} 加载URL列表")
            return
        print(f"📝 从 {args.input} 加载了 {len(urls)} 个URL")
    
    # 确认开始
    print(f"\n⚠️  即将开始批量获取 {len(urls)} 篇文章的统计数据")
    print(f"   预计时间: {len(urls) * args.delay / 60:.1f} 分钟")
    confirm = input("是否继续? (y/n): ").strip().lower()
    
    if confirm not in ['y', 'yes', '是']:
        print("👋 已取消操作")
        return
    
    # 开始批量获取
    results = scraper.batch_get_stats(urls, args.delay)
    
    if results:
        scraper.save_results(results, args.output)

if __name__ == "__main__":
    main() 