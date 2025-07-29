from datetime import datetime, timedelta

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