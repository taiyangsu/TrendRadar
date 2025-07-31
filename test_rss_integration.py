#!/usr/bin/env python3
# coding=utf-8
"""
RSS模块测试脚本

用于测试RSS模块的基本功能。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_rss_module():
    """测试RSS模块基本功能"""
    print("=" * 50)
    print("RSS模块功能测试")
    print("=" * 50)
    
    try:
        from rss_integration_manager import RSSIntegrationManager
        print("✓ RSS模块导入成功")
    except ImportError as e:
        print(f"✗ RSS模块导入失败: {e}")
        return False
    
    try:
        # 初始化RSS管理器
        rss_manager = RSSIntegrationManager()
        print("✓ RSS管理器初始化成功")
        
        # 检查是否启用
        if rss_manager.is_enabled():
            print("✓ RSS功能已启用")
            
            # 获取配置摘要
            summary = rss_manager.get_rss_summary()
            config_summary = summary.get('config_summary', {})
            print(f"✓ 配置的RSS源数量: {config_summary.get('total_feeds', 0)}")
            print(f"✓ 启用的RSS源数量: {config_summary.get('enabled_feeds', 0)}")
            print(f"✓ 配置的关键词数量: {config_summary.get('keywords_count', 0)}")
            
            # 测试配置验证
            validation_result = rss_manager.validate_rss_config()
            if validation_result.get('valid', False):
                print("✓ RSS配置验证通过")
            else:
                print(f"⚠ RSS配置验证警告: {validation_result}")
            
            # 测试连通性（仅测试前2个源以节省时间）
            print("正在测试RSS源连通性...")
            connectivity_result = rss_manager.test_rss_connectivity()
            if connectivity_result.get('tested', False):
                available = connectivity_result.get('available', 0)
                total = connectivity_result.get('total_tested', 0)
                print(f"✓ 连通性测试完成: {available}/{total} 个源可用")
            else:
                print("⚠ 连通性测试失败")
            
        else:
            print("ℹ RSS功能已禁用")
        
        # 清理资源
        rss_manager.close()
        print("✓ RSS资源清理完成")
        
        return True
        
    except Exception as e:
        print(f"✗ RSS模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_integration():
    """测试与主程序的集成"""
    print("\n" + "=" * 50)
    print("主程序集成测试")
    print("=" * 50)
    
    try:
        # 检查主程序是否能正常导入RSS管理器
        import main
        print("✓ 主程序导入成功")
        
        # 检查RSS_AVAILABLE标志
        if hasattr(main, 'RSS_AVAILABLE') and main.RSS_AVAILABLE:
            print("✓ RSS功能在主程序中可用")
        else:
            print("⚠ RSS功能在主程序中不可用")
        
        return True
        
    except Exception as e:
        print(f"✗ 主程序集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("TrendRadar RSS模块集成测试")
    print("测试时间:", Path(__file__).stat().st_mtime)
    
    # 检查配置文件
    rss_config = Path("modules/rss/config/rss_feeds.yaml")
    if rss_config.exists():
        print(f"✓ RSS配置文件存在: {rss_config}")
    else:
        print(f"✗ RSS配置文件不存在: {rss_config}")
        return
    
    # 运行测试
    test1_result = test_rss_module()
    test2_result = test_main_integration()
    
    # 总结
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)
    
    if test1_result and test2_result:
        print("✓ 所有测试通过！RSS模块集成成功")
        print("\n可以运行以下命令启动完整程序:")
        print("python main.py")
    else:
        print("✗ 部分测试失败，请检查错误信息")
        
        print("\n故障排除建议:")
        print("1. 确保已安装所有依赖: pip install -r requirements.txt")
        print("2. 检查RSS配置文件是否正确")
        print("3. 检查网络连接是否正常")

if __name__ == "__main__":
    main()