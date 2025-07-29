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