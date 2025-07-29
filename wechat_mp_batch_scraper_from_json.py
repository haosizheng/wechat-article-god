import os
import json
import time
from datetime import datetime
from utils.date_utils import get_preset_date_range, get_custom_date_range
from utils.text_utils import filter_articles_by_date, get_latest_n_articles
from utils.ui_utils import show_time_range_menu, show_crawl_options, get_custom_article_count
from utils.article_scraper import fetch_article_content

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
        "time_range": date_range,
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