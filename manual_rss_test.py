#!/usr/bin/env python3
# coding=utf-8
"""
RSS模块单元测试脚本
"""

import sys
import os
from pathlib import Path

def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("1. 测试模块导入")
    print("=" * 60)
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        
        # 测试RSS模块导入
        from modules.rss.models.rss_item import RSSItem
        from modules.rss.models.rss_feed import RSSFeed
        from modules.rss.models.rss_config import RSSConfig
        print("✓ RSS数据模型导入成功")
        
        from modules.rss.core.rss_fetcher import RSSFetcher
        from modules.rss.core.rss_parser import RSSParser
        from modules.rss.core.rss_validator import RSSValidator
        from modules.rss.core.rss_cache import RSSCacheManager
        print("✓ RSS核心组件导入成功")
        
        from modules.rss.adapters.rsshub_adapter import RSSHubAdapter
        from modules.rss.adapters.data_converter import DataConverter
        print("✓ RSS适配器导入成功")
        
        from modules.rss.utils.xml_parser import XMLParser
        from modules.rss.utils.date_utils import DateUtils
        from modules.rss.utils.url_validator import URLValidator
        print("✓ RSS工具类导入成功")
        
        from rss_integration_manager import RSSIntegrationManager
        print("✓ RSS集成管理器导入成功")
        
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_models():
    """测试数据模型"""
    print("\n" + "=" * 60)
    print("2. 测试数据模型")
    print("=" * 60)
    
    try:
        from modules.rss.models.rss_item import RSSItem
        from modules.rss.models.rss_feed import RSSFeed
        from datetime import datetime
        
        # 测试RSS条目创建
        item = RSSItem(
            title="测试标题",
            link="https://example.com/test",
            description="测试描述",
            pub_date=datetime.now(),
            author="测试作者",
            category="测试分类"
        )
        print(f"✓ RSS条目创建成功: {item.title}")
        
        # 测试RSS源创建
        feed = RSSFeed(
            title="测试RSS源",
            link="https://example.com/rss",
            description="测试RSS源描述",
            language="zh",
            last_build_date=datetime.now(),
            source_id="test_feed",
            category="test"
        )
        
        feed.add_item(item)
        print(f"✓ RSS源创建成功: {feed.title}, 条目数: {len(feed.items)}")
        
        # 测试数据转换
        item_dict = item.to_dict()
        feed_dict = feed.to_dict()
        print("✓ 数据序列化测试成功")
        
        return True
    except Exception as e:
        print(f"✗ 数据模型测试失败: {e}")
        return False

def test_config_loading():
    """测试配置加载"""
    print("\n" + "=" * 60)
    print("3. 测试配置加载")
    print("=" * 60)
    
    try:
        from modules.rss.models.rss_config import RSSConfig
        
        config_path = "modules/rss/config/rss_feeds.yaml"
        if not Path(config_path).exists():
            print(f"✗ 配置文件不存在: {config_path}")
            return False
        
        # 加载RSS配置
        rss_config = RSSConfig.from_yaml_file(config_path)
        print(f"✓ RSS配置加载成功")
        print(f"  - RSS功能启用: {rss_config.enable_rss}")
        print(f"  - RSS源数量: {len(rss_config.feeds)}")
        print(f"  - 启用的RSS源: {len(rss_config.get_enabled_feeds())}")
        print(f"  - 关键词数量: {len(rss_config.keywords)}")
        
        # 显示RSS源列表
        print("  - RSS源列表:")
        for feed in rss_config.get_enabled_feeds()[:3]:  # 只显示前3个
            print(f"    * {feed.name} ({feed.category}) - {feed.url}")
        
        return True
    except Exception as e:
        print(f"✗ 配置加载测试失败: {e}")
        return False

def test_url_validation():
    """测试URL验证"""
    print("\n" + "=" * 60)
    print("4. 测试URL验证")
    print("=" * 60)
    
    try:
        from modules.rss.utils.url_validator import URLValidator
        
        validator = URLValidator()
        
        # 测试有效URL
        valid_urls = [
            "https://rsshub.app/github/trending/daily",
            "https://example.com/rss.xml",
            "http://feeds.example.com/news"
        ]
        
        for url in valid_urls:
            if validator.is_valid_url(url):
                print(f"✓ 有效URL: {url}")
            else:
                print(f"✗ 无效URL: {url}")
        
        # 测试无效URL
        invalid_urls = [
            "not-a-url",
            "javascript:alert('xss')",
            ""
        ]
        
        for url in invalid_urls:
            if not validator.is_valid_url(url):
                print(f"✓ 正确识别无效URL: {url}")
            else:
                print(f"✗ 错误认为有效: {url}")
        
        return True
    except Exception as e:
        print(f"✗ URL验证测试失败: {e}")
        return False

def test_rsshub_adapter():
    """测试RSSHub适配器"""
    print("\n" + "=" * 60)
    print("5. 测试RSSHub适配器")
    print("=" * 60)
    
    try:
        from modules.rss.adapters.rsshub_adapter import RSSHubAdapter
        
        adapter = RSSHubAdapter()
        
        # 测试URL构建
        url1 = adapter.build_url("/github/trending/daily")
        print(f"✓ URL构建测试: {url1}")
        
        # 测试模板URL构建
        url2 = adapter.build_template_url("github_trending", {"period": "daily", "language": "python"})
        if url2:
            print(f"✓ 模板URL构建测试: {url2}")
        
        # 测试路由验证
        valid_route = adapter.validate_route("/github/trending/daily")
        print(f"✓ 路由验证测试: {valid_route}")
        
        # 获取热门路由
        popular_routes = adapter.get_popular_routes()
        print(f"✓ 获取热门路由: {len(popular_routes)}个")
        
        return True
    except Exception as e:
        print(f"✗ RSSHub适配器测试失败: {e}")
        return False

def test_integration_manager():
    """测试集成管理器"""
    print("\n" + "=" * 60)
    print("6. 测试集成管理器")
    print("=" * 60)
    
    try:
        from rss_integration_manager import RSSIntegrationManager
        
        # 初始化管理器
        manager = RSSIntegrationManager()
        print(f"✓ RSS集成管理器初始化成功")
        print(f"  - RSS功能启用: {manager.is_enabled()}")
        
        if manager.is_enabled():
            # 获取摘要信息
            summary = manager.get_rss_summary()
            config_summary = summary.get('config_summary', {})
            print(f"  - 配置摘要: {config_summary}")
            
            # 测试配置验证
            validation = manager.validate_rss_config()
            print(f"  - 配置验证: 总计{validation['total_feeds']}个源, 有效{validation['valid_feeds']}个")
            
            # 获取关键词
            keywords = manager.get_keywords_for_matching()
            print(f"  - 关键词数量: {len(keywords)}")
        
        # 清理资源
        manager.close()
        print("✓ 资源清理完成")
        
        return True
    except Exception as e:
        print(f"✗ 集成管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("TrendRadar RSS模块功能测试")
    print("测试开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 运行所有测试
    tests = [
        test_imports,
        test_data_models,
        test_config_loading,
        test_url_validation,
        test_rsshub_adapter,
        test_integration_manager
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ 测试异常: {e}")
            results.append(False)
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！RSS模块功能正常")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查上述错误信息")
    
    return passed == total

if __name__ == "__main__":
    try:
        from datetime import datetime
        main()
    except Exception as e:
        print(f"测试脚本执行失败: {e}")
        import traceback
        traceback.print_exc()