import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from .html_to_markdown import html_to_markdown
from .text_utils import extract_summary
import re

def fetch_article_content(url, folder_name, save_images=False, retry_count=5):
    """
    抓取单篇文章的详细信息，支持重试
    save_images: 是否保存图片
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 注入辅助函数
        page.add_init_script("""
            window.getComputedStyle = window.getComputedStyle || function(element) {
                return element.currentStyle;
            };
        """)
        
        # 设置更长的超时时间
        page.set_default_timeout(45000)
        
        for attempt in range(retry_count):
            try:
                print(f"    尝试第 {attempt + 1} 次访问...")
                page.goto(url, timeout=45000)
                
                # 等待页面基本加载完成
                page.wait_for_load_state('domcontentloaded', timeout=20000)
                
                # 等待主要内容加载
                page.wait_for_selector('div#js_content', timeout=20000)
                
                # 额外等待一下，确保内容加载
                page.wait_for_timeout(5000)
                
                # 检查页面是否有效（文章是否存在）
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
                    print(f"    ⚠️  检测到无效页面，文章可能已被删除或违规")
                    browser.close()
                    return {
                        'url': url,
                        'title': '',
                        'author': '',
                        'publish_time': '',
                        'read_count': '',
                        'like_count': '',
                        'content': '',
                        'error': '文章已被删除或违规，无法查看',
                        'status': 'deleted'
                    }
                
                # 提取文章信息
                article_data = {
                    'url': url,
                    'title': '',
                    'author': '',
                    'publish_time': '',
                    'read_count': '',
                    'like_count': '',
                    'content': '',
                    'summary': '',
                    'content_format': 'markdown',
                    'images': [] if save_images else None,  # 只在需要时初始化图片列表
                    'metadata': {
                        'crawl_time': datetime.now().isoformat(),
                        'markdown_enabled': True,
                        'images_saved': False,
                        'image_count': 0,
                        'version': '1.0'
                    }
                }
                
                # 提取标题
                try:
                    title_element = page.query_selector('h1.rich_media_title')
                    if title_element:
                        article_data['title'] = title_element.inner_text().strip()
                except:
                    pass
                
                # 提取作者
                try:
                    author_element = page.query_selector('a#js_name')
                    if author_element:
                        article_data['author'] = author_element.inner_text().strip()
                except:
                    pass
                
                # 提取发布时间
                try:
                    time_element = page.query_selector('em#publish_time')
                    if time_element:
                        article_data['publish_time'] = time_element.inner_text().strip()
                except:
                    pass
                
                # 提取阅读量和点赞量
                try:
                    read_element = page.query_selector('span#js_read_area')
                    if read_element:
                        read_text = read_element.inner_text().strip()
                        read_match = re.search(r'(\d+)', read_text)
                        if read_match:
                            article_data['read_count'] = read_match.group(1)
                except:
                    pass
                
                try:
                    like_element = page.query_selector('span#like_area')
                    if like_element:
                        like_text = like_element.inner_text().strip()
                        like_match = re.search(r'(\d+)', like_text)
                        if like_match:
                            article_data['like_count'] = like_match.group(1)
                except:
                    pass
                
                # 创建图片保存目录（仅在需要时）
                images_dir = os.path.join(folder_name, 'images') if save_images else None
                if save_images:
                    os.makedirs(images_dir, exist_ok=True)
                    article_data['images_dir'] = os.path.relpath(images_dir, folder_name)
                
                # 提取正文内容
                try:
                    content_element = page.query_selector('div#js_content')
                    if content_element:
                        # 将内容转换为Markdown格式
                        content, images = html_to_markdown(content_element, page, images_dir, save_images)
                        article_data['content'] = content
                        if save_images:
                            article_data['images'] = images
                            if images:
                                article_data['metadata']['images_saved'] = True
                                article_data['metadata']['image_count'] = len(images)
                        
                        # 提取摘要
                        article_data['summary'] = extract_summary(content)
                        
                        if not content:
                            raise Exception("内容转换后为空")
                        
                except Exception as e:
                    print(f"    ⚠️ 内容转换失败: {e}")
                    # 尝试基本的文本提取
                    try:
                        content_element = page.query_selector('div#js_content')
                        if content_element:
                            content = content_element.inner_text().strip()
                            article_data['content'] = content
                            article_data['content_format'] = 'plain'
                            article_data['metadata']['markdown_enabled'] = False
                            # 即使是纯文本也尝试提取摘要
                            article_data['summary'] = extract_summary(content)
                    except:
                        pass
                
                # 检查是否成功抓取到有效内容
                if article_data.get('title') and len(article_data.get('title', '').strip()) > 0:
                    browser.close()
                    return article_data
                else:
                    # 如果没有抓取到标题，继续重试
                    raise Exception("未抓取到文章标题，可能页面未完全加载")
                
            except Exception as e:
                print(f"    第 {attempt + 1} 次尝试失败: {e}")
                if attempt < retry_count - 1:
                    # 递增等待时间，避免频繁请求
                    wait_time = (attempt + 1) * 3
                    print(f"    等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"    所有重试都失败了")
                    browser.close()
                    return {
                        'url': url,
                        'title': '',
                        'author': '',
                        'publish_time': '',
                        'read_count': '',
                        'like_count': '',
                        'content': '',
                        'summary': '',
                        'error': f"重试 {retry_count} 次后仍然失败: {str(e)}",
                        'images': [] if save_images else None
                    } 