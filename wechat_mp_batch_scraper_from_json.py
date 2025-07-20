import json
import time
import re
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

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
    print("📅 请选择抓取文章的时间范围：")
    print("="*50)
    print("1. 过去一年 (365天)")
    print("2. 过去半年 (180天)")
    print("3. 过去三个月 (90天)")
    print("4. 过去一个月 (30天)")
    print("5. 过去一周 (7天)")
    print("6. 今年 (1月1日至今)")
    print("7. 去年 (全年)")
    print("8. 自定义时间范围")
    print("9. 抓取所有文章")
    print("0. 退出程序")
    print("="*50)

def fetch_article_content(url, retry_count=5):
    """抓取单篇文章的详细信息，支持重试"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 设置更长的超时时间
        page.set_default_timeout(45000)
        
        for attempt in range(retry_count):
            try:
                print(f"    尝试第 {attempt + 1} 次访问...")
                page.goto(url, timeout=45000)
                
                # 等待页面基本加载完成
                page.wait_for_load_state('domcontentloaded', timeout=20000)
                
                # 额外等待一下，确保内容加载
                page.wait_for_timeout(5000)
                
                # 提取文章信息
                article_data = {
                    'url': url,
                    'title': '',
                    'author': '',
                    'publish_time': '',
                    'read_count': '',
                    'like_count': '',
                    'content': ''
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
                
                # 提取正文内容
                try:
                    content_element = page.query_selector('div#js_content')
                    if content_element:
                        article_data['content'] = content_element.inner_text().strip()
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
                        'error': f"重试 {retry_count} 次后仍然失败: {str(e)}"
                    }
                
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
                        'error': f"重试 {retry_count} 次后仍然失败: {str(e)}"
                    }

def main():
    print("微信公众号文章批量抓取工具 (JSON 版)")
    print("从 ArticleList.json 文件读取文章链接并批量抓取")
    
    # 读取 ArticleList.json 文件
    try:
        with open("ArticleList.json", "r", encoding="utf-8") as f:
            all_articles = json.load(f)
        print(f"✅ 成功读取 ArticleList.json，共 {len(all_articles)} 篇文章")
    except Exception as e:
        print(f"❌ 读取 ArticleList.json 失败: {e}")
        return
    
    # 显示时间范围选择菜单
    while True:
        show_time_range_menu()
        choice = input("请选择 (0-9): ").strip()
        
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
        
        else:
            print("❌ 无效选择，请重新输入")
            continue
    
    # 根据时间范围筛选文章
    if start_date or end_date:
        filtered_articles = filter_articles_by_date(all_articles, start_date, end_date)
        print(f"\n📊 时间范围: {range_name}")
        print(f"📅 筛选条件: {start_date.strftime('%Y-%m-%d') if start_date else '不限'} 至 {end_date.strftime('%Y-%m-%d') if end_date else '不限'}")
        print(f"📝 筛选结果: {len(filtered_articles)} 篇文章")
        
        if len(filtered_articles) == 0:
            print("❌ 该时间范围内没有找到文章")
            return
        
        # 确认是否继续
        confirm = input(f"\n是否开始抓取这 {len(filtered_articles)} 篇文章？(y/n): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("👋 已取消抓取")
            return
    else:
        filtered_articles = all_articles
        print(f"\n📊 时间范围: {range_name}")
        print(f"📝 将抓取所有 {len(filtered_articles)} 篇文章")
    
    # 提取所有链接
    urls = []
    for item in filtered_articles:
        if 'link' in item:
            urls.append(item['link'])
        elif 'url' in item:
            urls.append(item['url'])
    
    print(f"\n🚀 开始抓取 {len(urls)} 篇文章...")
    
    # 批量抓取文章
    articles = []
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] 正在抓取: {url}")
        
        try:
            article_data = fetch_article_content(url)
            articles.append(article_data)
            
            # 显示抓取结果
            if article_data.get('title'):
                print(f"  ✅ 成功: {article_data['title'][:50]}...")
            else:
                print(f"  ❌ 失败: 未获取到标题")
            
        except Exception as e:
            print(f"  ❌ 抓取异常: {e}")
            articles.append({
                'url': url,
                'title': '',
                'author': '',
                'publish_time': '',
                'read_count': '',
                'like_count': '',
                'content': '',
                'error': str(e)
            })
        
        # 防止过快被封，每次抓取间隔 5 秒
        time.sleep(5)
    
    # 创建输出文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"articles_batch_{timestamp}"
    
    # 确保文件夹名称唯一
    counter = 1
    original_folder_name = folder_name
    while os.path.exists(folder_name):
        folder_name = f"{original_folder_name}_{counter}"
        counter += 1
    
    # 创建文件夹
    os.makedirs(folder_name, exist_ok=True)
    print(f"📁 创建输出文件夹: {folder_name}")
    
    # 保存结果文件
    output_file = os.path.join(folder_name, "articles_detailed.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    # 统计结果
    success_count = sum(1 for article in articles if article.get('title'))
    fail_count = len(articles) - success_count
    success_rate = success_count/len(articles)*100 if len(articles) > 0 else 0
    
    # 分析失败原因
    failed_articles = [article for article in articles if not article.get('title')]
    error_analysis = {}
    for article in failed_articles:
        error_msg = article.get('error', '未知错误')
        error_analysis[error_msg] = error_analysis.get(error_msg, 0) + 1
    
    # 保存抓取信息
    info_file = os.path.join(folder_name, "crawl_info.json")
    crawl_info = {
        "crawl_time": datetime.now().isoformat(),
        "time_range": range_name,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "total_articles": len(articles),
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": f"{success_rate:.1f}%",
        "source_file": "ArticleList.json",
        "error_analysis": error_analysis
    }
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(crawl_info, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 抓取完成！")
    print(f"📊 统计信息:")
    print(f"   时间范围: {range_name}")
    print(f"   总计: {len(articles)} 篇文章")
    print(f"   成功: {success_count} 篇")
    print(f"   失败: {fail_count} 篇")
    print(f"   成功率: {success_rate:.1f}%")
    
    # 显示失败分析
    if fail_count > 0:
        print(f"\n❌ 失败分析:")
        for error_msg, count in error_analysis.items():
            print(f"   {error_msg}: {count} 篇")
        
        # 提供改进建议
        if success_rate < 80:
            print(f"\n💡 改进建议:")
            print(f"   - 成功率较低，建议增加抓取间隔时间")
            print(f"   - 可以尝试在网络较好的时段进行抓取")
            print(f"   - 考虑分批抓取，减少单次抓取数量")
    
    print(f"\n📁 结果已保存到文件夹: {folder_name}")
    print(f"   📄 文章数据: {output_file}")
    print(f"   📋 抓取信息: {info_file}")

if __name__ == "__main__":
    main() 