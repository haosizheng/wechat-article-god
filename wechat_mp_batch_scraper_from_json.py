import json
import time
import re
import os
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, unquote
from pathlib import Path

def extract_summary(content: str, max_length: int = 100) -> str:
    """
    从文章内容中提取摘要（第一段的前N个字）
    """
    if not content:
        return ""
    
    # 按段落分割内容
    paragraphs = [p.strip() for p in content.split('\n\n')]
    
    # 过滤掉空段落
    paragraphs = [p for p in paragraphs if p]
    
    if not paragraphs:
        return ""
    
    # 获取第一段
    first_para = paragraphs[0]
    
    # 去除 Markdown 格式
    first_para = re.sub(r'\*\*|\*|`|#|>|\[.*?\]\(.*?\)', '', first_para)
    
    # 截取指定长度
    if len(first_para) > max_length:
        # 尝试在标点符号处截断
        punctuation_marks = ['。', '！', '？', '；', '，', '.', '!', '?', ';', ',']
        for i in range(max_length, -1, -1):
            if i < len(first_para) and first_para[i] in punctuation_marks:
                return first_para[:i+1]
        # 如果没有找到合适的标点，直接截断
        return first_para[:max_length] + "..."
    
    return first_para

def parse_date(date_str):
    """解析日期字符串，支持多种格式"""
    if not date_str:
        return None
    
    date_formats = [
        '%Y-%m-%d',
        '%Y年%m月%d日',
        '%Y/%m/%d',
        '%Y.%m.%d'
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def filter_articles_by_date(articles, start_date=None, end_date=None):
    """根据时间范围筛选文章"""
    filtered_articles = []
    
    for article in articles:
        article_date_str = article.get('date', '')
        article_date = parse_date(article_date_str)
        
        if not article_date:
            continue
        
        # 检查是否在时间范围内
        if start_date and article_date < start_date:
            continue
        if end_date and article_date > end_date:
            continue
        
        filtered_articles.append(article)
    
    return filtered_articles

def get_preset_date_range(option):
    """获取预设的时间范围"""
    today = datetime.now()
    
    if option == "1":  # 过去一年
        start_date = today - timedelta(days=365)
        return start_date, today, "过去一年"
    elif option == "2":  # 过去半年
        start_date = today - timedelta(days=180)
        return start_date, today, "过去半年"
    elif option == "3":  # 过去三个月
        start_date = today - timedelta(days=90)
        return start_date, today, "过去三个月"
    elif option == "4":  # 过去一个月
        start_date = today - timedelta(days=30)
        return start_date, today, "过去一个月"
    elif option == "5":  # 过去一周
        start_date = today - timedelta(days=7)
        return start_date, today, "过去一周"
    elif option == "6":  # 今年
        start_date = datetime(today.year, 1, 1)
        return start_date, today, "今年"
    elif option == "7":  # 去年
        start_date = datetime(today.year - 1, 1, 1)
        end_date = datetime(today.year - 1, 12, 31)
        return start_date, end_date, "去年"
    else:
        return None, None, None

def get_custom_date_range():
    """获取用户自定义的时间范围"""
    print("\n请输入自定义时间范围：")
    
    while True:
        start_str = input("开始日期 (格式: YYYY-MM-DD，如 2024-01-01): ").strip()
        if not start_str:
            return None, None
        
        start_date = parse_date(start_str)
        if start_date:
            break
        else:
            print("❌ 日期格式错误，请重新输入")
    
    while True:
        end_str = input("结束日期 (格式: YYYY-MM-DD，如 2024-12-31): ").strip()
        if not end_str:
            end_date = datetime.now()
            break
        
        end_date = parse_date(end_str)
        if end_date:
            break
        else:
            print("❌ 日期格式错误，请重新输入")
    
    return start_date, end_date

def show_time_range_menu():
    """显示时间范围选择菜单"""
    print("\n" + "="*50)
    print("📅 请选择抓取范围：")
    print("="*50)
    print("时间范围选项：")
    print("1. 过去一年 (365天)")
    print("2. 过去半年 (180天)")
    print("3. 过去三个月 (90天)")
    print("4. 过去一个月 (30天)")
    print("5. 过去一周 (7天)")
    print("6. 今年 (1月1日至今)")
    print("7. 去年 (全年)")
    print("8. 自定义时间范围")
    print("-"*50)
    print("快速测试选项：")
    print("10. 最新1篇文章 (快速测试)")
    print("11. 最新3篇文章 (基本测试)")
    print("12. 最新10篇文章 (完整测试)")
    print("13. 自定义数量")
    print("-"*50)
    print("其他选项：")
    print("9. 抓取所有文章")
    print("0. 退出程序")
    print("="*50)

def show_crawl_options():
    """显示爬取选项菜单"""
    print("\n" + "="*50)
    print("📝 爬取选项设置：")
    print("="*50)
    print("是否爬取文章图片？")
    print("1. 是 - 同时爬取文章和图片（速度较慢）")
    print("2. 否 - 仅爬取文章文本（速度较快）[默认]")
    print("="*50)

def get_latest_n_articles(articles, n):
    """获取最新的N篇文章"""
    # 按日期排序（如果有日期）
    dated_articles = []
    undated_articles = []
    
    for article in articles:
        date_str = article.get('date', '')
        date = parse_date(date_str)
        if date:
            dated_articles.append((date, article))
        else:
            undated_articles.append(article)
    
    # 按日期降序排序
    dated_articles.sort(key=lambda x: x[0], reverse=True)
    
    # 获取前N篇文章
    result = []
    
    # 首先添加有日期的文章
    for _, article in dated_articles[:n]:
        result.append(article)
    
    # 如果还不够N篇，添加无日期的文章
    remaining = n - len(result)
    if remaining > 0:
        result.extend(undated_articles[:remaining])
    
    actual_count = len(result)
    if actual_count < n:
        print(f"\n⚠️ 警告：要求抓取{n}篇文章，但只找到{actual_count}篇")
    
    return result

def get_custom_article_count():
    """获取用户自定义的文章数量"""
    while True:
        try:
            count = input("\n请输入要抓取的文章数量: ").strip()
            count = int(count)
            if count <= 0:
                print("❌ 请输入大于0的数字")
                continue
            return count
        except ValueError:
            print("❌ 请输入有效的数字")

def download_image(img_url: str, save_dir: str) -> str:
    """
    下载图片并返回本地路径
    """
    try:
        # 解析URL，获取文件名
        parsed_url = urlparse(img_url)
        img_name = os.path.basename(unquote(parsed_url.path))
        
        # 确保文件名有效且唯一
        img_name = re.sub(r'[<>:"/\\|?*]', '_', img_name)  # 替换非法字符
        if not img_name or len(img_name) > 255 or not re.search(r'\.(jpg|jpeg|png|gif|webp)$', img_name, re.I):
            # 如果没有有效的扩展名，默认使用.jpg
            img_name = f"img_{int(time.time()*1000)}.jpg"
        
        # 构建保存路径
        img_path = os.path.join(save_dir, img_name)
        
        # 如果文件已存在，添加数字后缀
        base, ext = os.path.splitext(img_path)
        counter = 1
        while os.path.exists(img_path):
            img_path = f"{base}_{counter}{ext}"
            counter += 1
        
        # 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(img_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 验证是否为有效的图片文件
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise Exception(f"Invalid content type: {content_type}")
        
        # 保存图片
        with open(img_path, 'wb') as f:
            f.write(response.content)
        
        print(f"    ✓ 图片已保存: {os.path.basename(img_path)}")
        return img_path
    except Exception as e:
        print(f"    ⚠️ 图片下载失败 ({img_url}): {e}")
        return None

def html_to_markdown(element, page, images_dir, save_images=False) -> tuple[str, list]:
    """
    将HTML元素转换为Markdown格式，并返回图片信息
    save_images: 是否保存图片
    返回: (markdown_content, images_info)
    """
    if not element:
        return "", []

    try:
        images_info = []  # 存储图片信息
        
        # 只在需要保存图片时处理图片元素
        if save_images:
            # 首先处理所有图片元素
            img_elements = element.query_selector_all('img')
            print(f"    找到 {len(img_elements)} 个图片元素")
            
            for img in img_elements:
                try:
                    # 获取图片URL和替代文本
                    img_url = img.get_attribute('data-src') or img.get_attribute('src')
                    alt_text = img.get_attribute('alt') or '图片'
                    
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif not img_url.startswith(('http://', 'https://')):
                            img_url = 'https://' + img_url
                        
                        print(f"    正在处理图片: {img_url}")
                        # 下载图片
                        local_path = download_image(img_url, images_dir)
                        if local_path:
                            images_info.append({
                                'original_url': img_url,
                                'local_path': local_path,
                                'alt_text': alt_text,
                                'filename': os.path.basename(local_path)
                            })
                except Exception as e:
                    print(f"    ⚠️ 处理图片元素失败: {e}")
            
            print(f"    ✓ 成功处理 {len(images_info)} 张图片")

        # 获取元素的HTML内容并转换为Markdown
        formatted_content = element.evaluate("""(element, shouldSaveImages) => {
            function getMarkdown(node) {
                if (!node) return '';
                
                let result = '';
                
                // 处理文本节点
                if (node.nodeType === Node.TEXT_NODE) {
                    let text = node.textContent.trim();
                    if (text) return text;
                    return '';
                }
                
                // 处理元素节点
                if (node.nodeType === Node.ELEMENT_NODE) {
                    let nodeName = node.nodeName.toLowerCase();
                    
                    // 跳过样式和脚本标签
                    if (['style', 'script'].includes(nodeName)) {
                        return '';
                    }
                    
                    // 获取所有子节点的内容
                    let childContent = Array.from(node.childNodes)
                        .map(child => getMarkdown(child))
                        .filter(text => text)
                        .join(' ')
                        .trim();
                    
                    if (!childContent) return '';
                    
                    // 处理不同类型的元素
                    switch (nodeName) {
                        case 'h1': return `\\n# ${childContent}\\n`;
                        case 'h2': return `\\n## ${childContent}\\n`;
                        case 'h3': return `\\n### ${childContent}\\n`;
                        case 'h4': return `\\n#### ${childContent}\\n`;
                        case 'p': return `\\n${childContent}\\n`;
                        case 'strong':
                        case 'b': return `**${childContent}**`;
                        case 'em':
                        case 'i': return `*${childContent}*`;
                        case 'code': return `\`${childContent}\``;
                        case 'pre': return `\\n\`\`\`\\n${childContent}\\n\`\`\`\\n`;
                        case 'blockquote': return `\\n> ${childContent}\\n`;
                        case 'a': return `[${childContent}](${node.href || ''})`;
                        case 'img': {
                            // 如果不保存图片，直接跳过图片处理
                            if (!shouldSaveImages) return '';
                            let src = node.src || node.dataset.src;
                            let alt = node.alt || '图片';
                            return src ? `\\n![${alt}](${src})\\n` : '';
                        }
                        case 'ul': {
                            return '\\n' + Array.from(node.children)
                                .map(li => `- ${getMarkdown(li).trim()}`)
                                .join('\\n') + '\\n';
                        }
                        case 'ol': {
                            return '\\n' + Array.from(node.children)
                                .map((li, i) => `${i + 1}. ${getMarkdown(li).trim()}`)
                                .join('\\n') + '\\n';
                        }
                        case 'li': return childContent;
                        case 'br': return '\\n';
                        default: return childContent;
                    }
                }
                
                return '';
            }
            
            return getMarkdown(element);
        }""", element, save_images)  # 传递参数的正确方式
        
        # 处理JavaScript转义的换行符
        formatted_content = formatted_content.replace('\\n', '\n')
        
        # 清理多余的空行
        formatted_content = re.sub(r'\n{3,}', '\n\n', formatted_content)
        
        return formatted_content.strip(), images_info
        
    except Exception as e:
        print(f"    ⚠️ Markdown转换出错: {str(e)}")
        return "", []

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
                
                # 提取阅读量
                try:
                    read_element = page.query_selector('span#js_read_area')
                    if read_element:
                        read_text = read_element.inner_text().strip()
                        # 提取数字
                        read_match = re.search(r'(\d+)', read_text)
                        if read_match:
                            article_data['read_count'] = read_match.group(1)
                    else:
                        # 尝试其他可能的选择器
                        read_elements = page.query_selector_all('span')
                        for element in read_elements:
                            text = element.inner_text().strip()
                            if '阅读' in text and re.search(r'\d+', text):
                                read_match = re.search(r'(\d+)', text)
                                if read_match:
                                    article_data['read_count'] = read_match.group(1)
                                    break
                except:
                    pass
                
                # 提取点赞量
                try:
                    like_element = page.query_selector('span#like_area')
                    if like_element:
                        like_text = like_element.inner_text().strip()
                        like_match = re.search(r'(\d+)', like_text)
                        if like_match:
                            article_data['like_count'] = like_match.group(1)
                    else:
                        # 尝试其他可能的选择器
                        like_elements = page.query_selector_all('span')
                        for element in like_elements:
                            text = element.inner_text().strip()
                            if '赞' in text and re.search(r'\d+', text):
                                like_match = re.search(r'(\d+)', text)
                                if like_match:
                                    article_data['like_count'] = like_match.group(1)
                                    break
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

def process_single_list(json_file: str, output_base_dir: str, 
                     start_date=None, end_date=None, save_images=False, 
                     latest_n=None) -> None:
    """
    处理单个文章列表文件
    Args:
        json_file: JSON文件的完整路径
        output_base_dir: 输出目录的基础路径（Output文件夹）
        start_date: 开始日期
        end_date: 结束日期
        save_images: 是否保存图片
        latest_n: 如果设置，则只处理最新的N篇文章
    """
    print(f"\n处理文章列表: {os.path.basename(json_file)}")
    
    # 读取文章列表文件
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            all_articles = json.load(f)
        print(f"✅ 成功读取文章列表，共 {len(all_articles)} 篇文章")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return

    # 根据时间范围筛选文章
    if start_date or end_date:
        filtered_articles = filter_articles_by_date(all_articles, start_date, end_date)
        date_range = f"({start_date.strftime('%Y-%m-%d') if start_date else '不限'} 至 {end_date.strftime('%Y-%m-%d') if end_date else '不限'})"
    else:
        filtered_articles = all_articles
        date_range = "(全部)"

    # 如果指定了获取最新的N篇文章
    if latest_n is not None:
        filtered_articles = get_latest_n_articles(filtered_articles, latest_n)
        date_range = f"(最新 {latest_n} 篇)"

    print(f"📝 符合条件的文章数量: {len(filtered_articles)} {date_range}")
    
    if len(filtered_articles) == 0:
        print("❌ 没有找到符合条件的文章，跳过此文件")
        return
    
    print(f"\n🚀 开始爬取 {len(filtered_articles)} 篇文章...")
    
    # 在Output文件夹下创建输出子文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    list_name = os.path.splitext(os.path.basename(json_file))[0]
    batch_folder = os.path.join(output_base_dir, f"{list_name}_batch_{timestamp}")
    
    # 确保文件夹名称唯一
    counter = 1
    original_folder_name = batch_folder
    while os.path.exists(batch_folder):
        batch_folder = f"{original_folder_name}_{counter}"
        counter += 1
    
    # 创建主文件夹和图片文件夹
    os.makedirs(batch_folder, exist_ok=True)
    batch_images_dir = os.path.join(batch_folder, 'images')
    if save_images:
        os.makedirs(batch_images_dir, exist_ok=True)
    
    print(f"📁 创建输出文件夹: {batch_folder}")
    if save_images:
        print(f"📁 创建图片文件夹: {batch_images_dir}")

    # 提取所有链接
    urls = []
    for item in filtered_articles:
        if 'link' in item:
            urls.append(item['link'])
        elif 'url' in item:
            urls.append(item['url'])

    # 批量抓取文章
    articles = []
    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}] 正在抓取: {url}")
        
        try:
            # 确保每篇文章都使用正确的图片保存路径
            article_data = fetch_article_content(url, batch_folder, save_images)
            
            # 添加调试信息（仅在保存图片时显示）
            if save_images:
                print(f"    图片保存目录: {batch_images_dir}")
                print(f"    文章图片数量: {len(article_data.get('images', []))}")
            
            articles.append(article_data)
            
            # 显示抓取结果
            if article_data.get('title'):
                print(f"    ✅ 成功: {article_data['title'][:50]}...")
                if save_images and article_data.get('metadata', {}).get('images_saved'):
                    print(f"       📸 已保存 {article_data.get('metadata', {}).get('image_count', 0)} 张图片")
            else:
                print(f"    ❌ 失败: 未获取到标题")
            
        except Exception as e:
            print(f"    ❌ 抓取异常: {e}")
            articles.append({
                'url': url,
                'title': '',
                'author': '',
                'publish_time': '',
                'read_count': '',
                'like_count': '',
                'content': '',
                'summary': '',
                'error': str(e),
                'content_format': 'plain',
                'images': [],
                'metadata': {
                    'crawl_time': datetime.now().isoformat(),
                    'markdown_enabled': False,
                    'images_saved': False,
                    'image_count': 0,
                    'version': '1.0'
                }
            })
        
        # 检查图片文件夹（仅在保存图片时）
        if save_images and os.path.exists(batch_images_dir):
            image_files = os.listdir(batch_images_dir)
            print(f"    📁 图片文件夹状态: {len(image_files)} 个文件")
        
        # 防止过快被封，每次抓取间隔 5 秒
        time.sleep(5)

    # 保存结果文件
    output_file = os.path.join(batch_folder, "articles_detailed.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    # 统计结果
    success_count = sum(1 for article in articles if article.get('title'))
    fail_count = len(articles) - success_count
    success_rate = success_count/len(articles)*100 if len(articles) > 0 else 0
    
    # 分析失败原因
    failed_articles = [article for article in articles if not article.get('title')]
    deleted_articles = [article for article in articles if article.get('status') == 'deleted']
    error_analysis = {}
    
    for article in failed_articles:
        error_msg = article.get('error', '未知错误')
        error_analysis[error_msg] = error_analysis.get(error_msg, 0) + 1
    
    # 保存抓取信息
    info_file = os.path.join(batch_folder, "crawl_info.json")
    crawl_info = {
        "crawl_time": datetime.now().isoformat(),
        "time_range": date_range, # 使用传入的date_range
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "total_articles": len(articles),
        "success_count": success_count,
        "fail_count": fail_count,
        "deleted_count": len(deleted_articles),
        "success_rate": f"{success_rate:.1f}%",
        "source_file": os.path.basename(json_file),
        "error_analysis": error_analysis,
        "format_version": "1.0",
        "markdown_enabled": True,
        "image_support": True,
        "images_dir": "images"
    }
    
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(crawl_info, f, ensure_ascii=False, indent=2)

    print(f"\n📁 结果已保存到文件夹: {batch_folder}")
    print(f"   📄 文章数据: {output_file}")
    print(f"   📋 抓取信息: {info_file}")
    print(f"   🖼️  图片目录: {os.path.join(batch_folder, 'images')}")

def main():
    print("微信公众号文章批量抓取工具 (JSON 版)")
    print("从 ArticleList 文件夹读取文章列表并批量抓取")
    
    # 检查必要的文件夹
    article_list_dir = os.path.join(os.path.dirname(__file__), "ArticleList")
    output_dir = os.path.join(os.path.dirname(__file__), "Output")
    
    # 确保文件夹存在
    os.makedirs(article_list_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有JSON文件
    json_files = [f for f in os.listdir(article_list_dir) 
                 if f.endswith('.json') and os.path.isfile(os.path.join(article_list_dir, f))]
    
    if not json_files:
        print(f"\n❌ 在 ArticleList 文件夹中没有找到 JSON 文件")
        print(f"请将文章列表文件放入: {article_list_dir}")
        return
    
    # 显示找到的文件
    print(f"\n📝 找到 {len(json_files)} 个文章列表文件:")
    for i, f in enumerate(json_files, 1):
        print(f"{i}. {f}")
    
    # 统一选择时间范围
    print("\n首先，让我们选择要处理的时间范围...")
    latest_n = None  # 用于存储最新N篇的设置
    
    while True:
        show_time_range_menu()
        choice = input("请选择 (0-13): ").strip()
        
        if choice == "0":
            print("👋 程序已退出")
            return
        
        elif choice == "9":
            # 抓取所有文章
            start_date = None
            end_date = None
            range_name = "所有文章"
            break
        
        elif choice == "8":
            # 自定义时间范围
            start_date, end_date = get_custom_date_range()
            if start_date and end_date:
                range_name = f"自定义范围 ({start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')})"
                break
            else:
                print("❌ 自定义时间范围设置失败")
                continue
        
        elif choice in ["1", "2", "3", "4", "5", "6", "7"]:
            # 预设时间范围
            start_date, end_date, range_name = get_preset_date_range(choice)
            if start_date and end_date:
                break
            else:
                print("❌ 预设时间范围获取失败")
                continue
        
        elif choice == "10":
            # 最新1篇（快速测试）
            start_date = end_date = None
            latest_n = 1
            range_name = "最新1篇文章 (快速测试)"
            break
            
        elif choice == "11":
            # 最新3篇（基本测试）
            start_date = end_date = None
            latest_n = 3
            range_name = "最新3篇文章 (基本测试)"
            break
            
        elif choice == "12":
            # 最新10篇（完整测试）
            start_date = end_date = None
            latest_n = 10
            range_name = "最新10篇文章 (完整测试)"
            break
            
        elif choice == "13":
            # 自定义数量
            start_date = end_date = None
            latest_n = get_custom_article_count()
            range_name = f"最新{latest_n}篇文章"
            break
        
        else:
            print("❌ 无效选择，请重新输入")
            continue
    
    # 统一选择是否爬取图片
    print("\n接下来，选择是否爬取文章图片...")
    show_crawl_options()
    image_choice = input("请选择 (1-2): ").strip() or "2"
    save_images = image_choice == "1"
    
    if save_images:
        print("\n⚠️ 您选择了同时爬取图片，这可能会显著增加爬取时间")
    else:
        print("\n✓ 您选择了仅爬取文本，这将加快爬取速度")
    
    print(f"\n📊 处理配置:")
    print(f"时间范围: {range_name}")
    print(f"爬取图片: {'是' if save_images else '否'}")
    print(f"文件数量: {len(json_files)} 个")
    if latest_n:
        print(f"每个文件处理: 最新 {latest_n} 篇文章")
    
    # 处理每个文件
    for i, json_file in enumerate(json_files, 1):
        print(f"\n{'='*50}")
        print(f"处理第 {i}/{len(json_files)} 个文件: {json_file}")
        print(f"{'='*50}")
        
        full_path = os.path.join(article_list_dir, json_file)
        process_single_list(full_path, output_dir, start_date, end_date, save_images, latest_n)
    
    print("\n✨ 所有文件处理完成")
    print(f"📁 所有结果已保存到: {output_dir}")

if __name__ == "__main__":
    main() 