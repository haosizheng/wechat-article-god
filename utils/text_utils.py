import re

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

def filter_articles_by_date(articles, start_date=None, end_date=None):
    """根据时间范围筛选文章"""
    from .date_utils import parse_date  # 导入parse_date函数
    
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

def get_latest_n_articles(articles, n):
    """获取最新的N篇文章"""
    from .date_utils import parse_date  # 导入parse_date函数
    
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