# 微信公众号文章导入 Notion 指南

本指南将帮助你将抓取的微信公众号文章数据导入到 Notion 数据库中。

## 方案一：使用 Notion API 直接导入（推荐）

### 1. 准备工作

#### 1.1 创建 Notion 集成
1. 访问 [Notion Developers](https://developers.notion.com/)
2. 点击 "New integration"
3. 填写集成名称（如 "WeChat Articles Importer"）
4. 选择工作区
5. 复制生成的 **Internal Integration Token**

#### 1.2 创建 Notion 数据库
1. 在 Notion 中创建新页面
2. 添加数据库（Database）
3. 设置以下属性：
   - **标题** (Title) - 文章标题
   - **作者** (Text) - 作者名称
   - **发布时间** (Date) - 发布时间
   - **阅读量** (Number) - 阅读数量
   - **点赞量** (Number) - 点赞数量
   - **链接** (URL) - 文章链接

#### 1.3 获取数据库 ID
1. 打开数据库页面
2. 从 URL 中复制数据库 ID：
   ```
   https://www.notion.so/workspace/DATABASE_ID?v=...
   ```
   其中 `DATABASE_ID` 就是你需要的信息

#### 1.4 授权集成访问数据库
1. 在数据库页面右上角点击 "Share"
2. 点击 "Invite"
3. 搜索并添加你刚创建的集成
4. 选择 "Can edit" 权限

### 2. 安装依赖

```bash
pip install requests
```

### 3. 运行导入脚本

```bash
python notion_importer.py
```

按提示输入：
- Notion API 集成令牌
- 数据库 ID

### 4. 查看结果

脚本会自动将 `articles_detailed.json` 中的所有文章导入到 Notion 数据库。

## 方案二：使用 CSV 导入（简单）

### 1. 转换为 CSV

```bash
python json_to_csv.py
```

这会生成 `articles.csv` 文件。

### 2. 导入到 Notion

1. 在 Notion 中创建新数据库
2. 点击数据库右上角的 "..." 
3. 选择 "Import"
4. 选择 "CSV"
5. 上传 `articles.csv` 文件
6. 映射字段并导入

## 方案三：使用 Excel 导入

### 1. 转换为 Excel

```bash
pip install pandas openpyxl
python json_to_csv.py
```

这会生成 `articles.xlsx` 文件。

### 2. 导入到 Notion

1. 在 Notion 中创建新数据库
2. 点击 "Import" → "Excel"
3. 上传 `articles.xlsx` 文件
4. 映射字段并导入

## 数据库字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 标题 | Title | 文章标题 |
| 作者 | Text | 作者名称 |
| 发布时间 | Date | 发布时间 |
| 阅读量 | Number | 阅读数量 |
| 点赞量 | Number | 点赞数量 |
| 链接 | URL | 文章链接 |
| 内容 | Text | 文章正文（部分） |
| 错误信息 | Text | 抓取错误信息 |

## 注意事项

### API 限制
- Notion API 有速率限制，脚本会自动添加 1 秒延迟
- 大量数据导入可能需要较长时间

### 内容长度限制
- Notion 标题限制 2000 字符
- 内容块限制 2000 字符，长内容会自动分段

### 错误处理
- 导入失败的文章会记录错误信息
- 脚本会显示成功/失败统计

## 故障排除

### 常见错误

1. **401 Unauthorized**
   - 检查 API 令牌是否正确
   - 确认集成已授权访问数据库

2. **403 Forbidden**
   - 确认数据库已共享给集成
   - 检查集成权限设置

3. **404 Not Found**
   - 检查数据库 ID 是否正确
   - 确认数据库存在且可访问

### 性能优化

- 对于大量数据，建议分批导入
- 可以修改脚本中的 `time.sleep(1)` 调整延迟时间

## 完整工作流程

1. 准备文章列表：`ArticleList.json`（包含标题、链接、发布时间）
2. 运行抓取脚本：`python wechat_mp_batch_scraper_from_json.py`
3. 等待抓取完成，生成 `articles_detailed.json`
4. 选择导入方案：
   - API 导入：`python notion_importer.py`
   - CSV 导入：`python json_to_csv.py` → Notion CSV 导入
   - Excel 导入：`python json_to_csv.py` → Notion Excel 导入
5. 在 Notion 中查看和管理文章数据

## 支持的文件格式

### ArticleList.json（文章列表格式）
```json
[
  {
    "title": "文章标题",
    "link": "https://mp.weixin.qq.com/s/...",
    "date": "2025-01-15"
  }
]
```

### articles_detailed.json（详细内容格式）
```json
[
  {
    "title": "文章标题",
    "author": "作者",
    "publish_time": "发布时间",
    "read_count": "阅读量",
    "like_count": "点赞量",
    "url": "文章链接",
    "content": "文章内容"
  }
]
```

## 自定义配置

你可以修改脚本中的字段映射，以适应不同的数据库结构：

```python
properties = {
    "你的字段名": {
        "title": [{"text": {"content": article_data.get('title', '')}}]
    }
}
```

## 支持

如果遇到问题，请检查：
1. API 令牌和数据库 ID 是否正确
2. 网络连接是否正常
3. Notion 集成权限是否设置正确 