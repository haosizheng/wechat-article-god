import os
import json
from typing import Dict

def load_config() -> Dict[str, str]:
    """
    从配置文件加载 Notion 配置
    如果配置文件不存在，创建一个模板
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "notion_config.json")
    
    # 如果配置文件不存在，创建一个模板
    if not os.path.exists(config_path):
        default_config = {
            "notion_token": "your_notion_token_here",
            "database_id": "your_database_id_here"
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print(f"⚠️ 配置文件已创建在 {config_path}")
        print("请编辑配置文件，填入你的 Notion Token 和 Database ID")
        return default_config
    
    # 读取配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 验证配置
        if config["notion_token"] == "your_notion_token_here" or \
           config["database_id"] == "your_database_id_here":
            print("⚠️ 请先在配置文件中填入正确的 Notion Token 和 Database ID")
            return {}
            
        return config
    except Exception as e:
        print(f"❌ 读取配置文件失败: {str(e)}")
        return {} 