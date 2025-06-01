import json
import os
import sys

def load_config():
    """加载配置文件"""
    try:
        if not os.path.exists('config.json'):
            config = {
                "download_dir": "downloads",
                "check_interval": 5
            }
            save_config(config)
        else:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        return config
    except Exception as e:
        print(f"加载配置文件出错: {str(e)}")
        return {
            "download_dir": "downloads",
            "check_interval": 5
        }

def save_config(config):
    """保存配置文件"""
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print("配置已保存")
    except Exception as e:
        print(f"保存配置文件出错: {str(e)}")

def main():
    config = load_config()
    
    print("\n当前配置:")
    print(f"下载目录: {config['download_dir']}")
    print(f"检查间隔: {config['check_interval']}秒")
    
    print("\n请输入新的下载目录路径 (直接回车保持不变):")
    new_path = input().strip()
    
    if new_path:
        # 转换为绝对路径
        new_path = os.path.abspath(new_path)
        config['download_dir'] = new_path
        
        # 确保目录存在
        if not os.path.exists(new_path):
            try:
                os.makedirs(new_path)
                print(f"已创建目录: {new_path}")
            except Exception as e:
                print(f"创建目录失败: {str(e)}")
                return
        
        save_config(config)
        print(f"\n下载目录已更新为: {new_path}")
    else:
        print("\n保持原有设置不变")

if __name__ == "__main__":
    main() 