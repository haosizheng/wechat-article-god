# 步骤1
点击链接将这个插件加入到你的chrome插件：
https://extension.automa.site/workflow/qDMr7a6TVA6L3rMa4HUer

# 步骤2
登录微信公众平台->新建图文消息->超链接->选择一个公众号打开.
在当前页面运行这个插件，将自动翻页抓取所有文章的标题、链接（短链接）、发布日期，并保存为一个 json 文件。

# 步骤3

用步骤 2 的文件，替换名为“ArticleList.json”的文件。

# 步骤4
打开 terminal，输入：

如果你使用的是 python3
```
python3 wechat_mp_batch_scraper_from_json.py
```

如果你使用的是 python
```
python wechat_mp_batch_scraper_from_json.py
```

# 测试环境
mac系统
chrome 浏览器

# 支持自由时间区间选择
<img width="545" height="247" alt="image" src="https://github.com/user-attachments/assets/392002a5-7935-4656-b91e-f36072079293" />

