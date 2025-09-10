# coding=utf-8

import os
import sys
from pathlib import Path

# Add the modules directory to the Python path
sys.path.append(str(Path(__file__).parent / "modules"))

from modules.config import load_config, VERSION
from modules.analyzer import NewsAnalyzer


print("正在加载配置...")
CONFIG = load_config()
print(f"TrendRadar v{VERSION} 配置加载完成")
print(f"监控平台数量: {len(CONFIG['PLATFORMS'])}")


def main():
    try:
        analyzer = NewsAnalyzer()
        analyzer.run()
    except FileNotFoundError as e:
        print(f"❌ 配置文件错误: {e}")
        print("\n请确保以下文件存在:")
        print("  • config/config.yaml")
        print("  • config/frequency_words.txt")
        print("\n参考项目文档进行正确配置")
    except Exception as e:
        print(f"❌ 程序运行错误: {e}")
        raise


if __name__ == "__main__":
    main()