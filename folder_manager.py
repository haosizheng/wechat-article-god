import os
import json
from datetime import datetime
import shutil

def list_crawl_folders():
    """列出所有抓取结果文件夹"""
    folders = []
    for item in os.listdir('.'):
        if os.path.isdir(item) and item.startswith('articles_batch_'):
            folders.append(item)
    
    return sorted(folders, reverse=True)  # 按时间倒序排列

def get_folder_info(folder_path):
    """获取文件夹的详细信息"""
    info_file = os.path.join(folder_path, "crawl_info.json")
    if os.path.exists(info_file):
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            return info
        except:
            return None
    return None

def show_folder_details(folder_name):
    """显示文件夹详细信息"""
    info = get_folder_info(folder_name)
    if info:
        print(f"\n📁 文件夹: {folder_name}")
        print(f"   抓取时间: {info.get('crawl_time', '未知')}")
        print(f"   时间范围: {info.get('time_range', '未知')}")
        print(f"   开始日期: {info.get('start_date', '不限')}")
        print(f"   结束日期: {info.get('end_date', '不限')}")
        print(f"   总文章数: {info.get('total_articles', 0)}")
        print(f"   成功数量: {info.get('success_count', 0)}")
        print(f"   失败数量: {info.get('fail_count', 0)}")
        print(f"   成功率: {info.get('success_rate', '0%')}")
    else:
        print(f"\n📁 文件夹: {folder_name} (无详细信息)")

def main():
    print("📂 微信公众号文章抓取结果管理器")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 查看所有抓取结果文件夹")
        print("2. 查看文件夹详细信息")
        print("3. 删除指定文件夹")
        print("4. 清理所有抓取结果")
        print("5. 打开指定文件夹")
        print("0. 退出")
        
        choice = input("\n请选择 (0-5): ").strip()
        
        if choice == "0":
            print("👋 退出管理器")
            break
        
        elif choice == "1":
            folders = list_crawl_folders()
            if folders:
                print(f"\n📂 找到 {len(folders)} 个抓取结果文件夹:")
                for i, folder in enumerate(folders, 1):
                    info = get_folder_info(folder)
                    if info:
                        print(f"{i:2d}. {folder}")
                        print(f"    时间范围: {info.get('time_range', '未知')} | 文章数: {info.get('total_articles', 0)} | 成功率: {info.get('success_rate', '0%')}")
                    else:
                        print(f"{i:2d}. {folder} (无详细信息)")
            else:
                print("📭 没有找到抓取结果文件夹")
        
        elif choice == "2":
            folders = list_crawl_folders()
            if not folders:
                print("📭 没有找到抓取结果文件夹")
                continue
            
            print(f"\n📂 可用的文件夹:")
            for i, folder in enumerate(folders, 1):
                print(f"{i}. {folder}")
            
            try:
                folder_idx = int(input("请输入文件夹编号: ")) - 1
                if 0 <= folder_idx < len(folders):
                    show_folder_details(folders[folder_idx])
                else:
                    print("❌ 无效的文件夹编号")
            except ValueError:
                print("❌ 请输入有效的数字")
        
        elif choice == "3":
            folders = list_crawl_folders()
            if not folders:
                print("📭 没有找到抓取结果文件夹")
                continue
            
            print(f"\n📂 可删除的文件夹:")
            for i, folder in enumerate(folders, 1):
                print(f"{i}. {folder}")
            
            try:
                folder_idx = int(input("请输入要删除的文件夹编号: ")) - 1
                if 0 <= folder_idx < len(folders):
                    folder_name = folders[folder_idx]
                    confirm = input(f"确认删除文件夹 '{folder_name}' 吗？(y/n): ").strip().lower()
                    if confirm in ['y', 'yes', '是']:
                        shutil.rmtree(folder_name)
                        print(f"✅ 已删除文件夹: {folder_name}")
                    else:
                        print("❌ 取消删除")
                else:
                    print("❌ 无效的文件夹编号")
            except ValueError:
                print("❌ 请输入有效的数字")
            except Exception as e:
                print(f"❌ 删除失败: {e}")
        
        elif choice == "4":
            folders = list_crawl_folders()
            if not folders:
                print("📭 没有找到抓取结果文件夹")
                continue
            
            print(f"\n⚠️  即将删除所有 {len(folders)} 个抓取结果文件夹:")
            for folder in folders:
                print(f"   - {folder}")
            
            confirm = input(f"\n确认删除所有文件夹吗？(y/n): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                deleted_count = 0
                for folder in folders:
                    try:
                        shutil.rmtree(folder)
                        deleted_count += 1
                        print(f"✅ 已删除: {folder}")
                    except Exception as e:
                        print(f"❌ 删除失败 {folder}: {e}")
                
                print(f"\n🎉 清理完成！共删除 {deleted_count} 个文件夹")
            else:
                print("❌ 取消清理")
        
        elif choice == "5":
            folders = list_crawl_folders()
            if not folders:
                print("📭 没有找到抓取结果文件夹")
                continue
            
            print(f"\n📂 可打开的文件夹:")
            for i, folder in enumerate(folders, 1):
                print(f"{i}. {folder}")
            
            try:
                folder_idx = int(input("请输入文件夹编号: ")) - 1
                if 0 <= folder_idx < len(folders):
                    folder_name = folders[folder_idx]
                    folder_path = os.path.abspath(folder_name)
                    print(f"📂 打开文件夹: {folder_path}")
                    
                    # 尝试打开文件夹
                    try:
                        if os.name == 'nt':  # Windows
                            os.startfile(folder_path)
                        elif os.name == 'posix':  # macOS/Linux
                            os.system(f'open "{folder_path}"')
                        print("✅ 文件夹已打开")
                    except Exception as e:
                        print(f"❌ 无法打开文件夹: {e}")
                        print(f"📁 文件夹路径: {folder_path}")
                else:
                    print("❌ 无效的文件夹编号")
            except ValueError:
                print("❌ 请输入有效的数字")
        
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main() 