# coding=utf-8
"""
RSS集成管理器

负责RSS模块与主系统的集成，管理RSS数据的获取、处理和格式转换。
"""

import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from modules.rss import (
    RSSFetcher, RSSParser, RSSValidator, RSSCacheManager,
    RSSHubAdapter, DataConverter, RSSConfig, RSSErrorHandler
)


class RSSIntegrationManager:
    """RSS集成管理器"""
    
    def __init__(self, config_path: str = "modules/rss/config/rss_feeds.yaml"):
        """
        初始化RSS集成管理器
        
        Args:
            config_path: RSS配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path
        
        # 检查RSS配置文件是否存在
        if not Path(config_path).exists():
            self.logger.warning(f"RSS配置文件不存在: {config_path}")
            self.rss_config = None
            self.enabled = False
            return
        
        try:
            # 加载RSS配置
            self.rss_config = RSSConfig.from_yaml_file(config_path)
            self.enabled = self.rss_config.enable_rss
            
            if not self.enabled:
                self.logger.info("RSS功能已禁用")
                return
            
            # 初始化RSS组件
            self.rss_fetcher = RSSFetcher(
                timeout=self.rss_config.timeout,
                max_retries=self.rss_config.max_retries,
                request_interval=self.rss_config.request_interval
            )
            
            self.rss_parser = RSSParser()
            self.rss_validator = RSSValidator()
            self.rss_cache = RSSCacheManager(
                cache_duration=self.rss_config.cache_duration
            )
            self.rsshub_adapter = RSSHubAdapter()
            self.data_converter = DataConverter()
            self.error_handler = RSSErrorHandler()
            
            self.logger.info(f"RSS模块初始化成功，配置 {len(self.rss_config.feeds)} 个RSS源")
            
        except Exception as e:
            self.logger.error(f"RSS模块初始化失败: {str(e)}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """检查RSS功能是否启用"""
        return self.enabled
    
    def get_rss_data(self) -> Tuple[Dict[str, Any], List[str]]:
        """
        获取RSS数据（主入口方法）
        
        Returns:
            Tuple[RSS数据字典, 失败的RSS源ID列表]
        """
        if not self.enabled:
            return {}, []
        
        try:
            self.logger.info("开始获取RSS数据")
            
            # 获取启用的RSS源配置
            enabled_feeds = self.rss_config.get_enabled_feeds()
            if not enabled_feeds:
                self.logger.warning("没有启用的RSS源")
                return {}, []
            
            # 按优先级排序
            enabled_feeds.sort(key=lambda x: x.priority)
            
            # 构建请求配置
            feed_configs = []
            for feed_config in enabled_feeds:
                config_dict = {
                    'id': feed_config.id,
                    'url': feed_config.url,
                    'custom_headers': feed_config.custom_headers,
                    'timeout': feed_config.timeout or self.rss_config.timeout
                }
                feed_configs.append(config_dict)
            
            # 并发获取RSS数据
            fetch_results = self.rss_fetcher.fetch_feeds_with_config(
                feed_configs, max_workers=3  # 限制并发数
            )
            
            # 处理获取结果
            rss_feeds = []
            failed_feed_ids = []
            
            for feed_id, (xml_content, config) in fetch_results.items():
                if xml_content:
                    # 尝试从缓存获取
                    cached_feed = self.rss_cache.get_cached_rss_feed(feed_id)
                    
                    if not cached_feed:
                        # 解析RSS数据
                        feed_config = next((f for f in enabled_feeds if f.id == feed_id), None)
                        if feed_config:
                            rss_feed = self.rss_parser.parse_feed(
                                xml_content, 
                                source_id=feed_id,
                                category=feed_config.category
                            )
                            
                            if rss_feed:
                                # 缓存解析结果
                                self.rss_cache.cache_rss_feed(feed_id, rss_feed)
                                self.rss_cache.cache_xml_content(config['url'], xml_content)
                                rss_feeds.append(rss_feed)
                            else:
                                failed_feed_ids.append(feed_id)
                    else:
                        rss_feeds.append(cached_feed)
                else:
                    failed_feed_ids.append(feed_id)
            
            # 转换数据格式
            if rss_feeds:
                unified_data = self.data_converter.convert_multiple_feeds_to_unified_format(rss_feeds)
                self.logger.info(f"RSS数据获取完成: {len(rss_feeds)}个源, {len(failed_feed_ids)}个失败")
                return unified_data, failed_feed_ids
            else:
                self.logger.warning("没有成功获取到任何RSS数据")
                return {}, failed_feed_ids
                
        except Exception as e:
            error_result = self.error_handler.handle_general_error(e)
            self.logger.error(f"RSS数据获取异常: {str(e)}")
            return {}, []
    
    def merge_with_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将RSS数据与API数据合并
        
        Args:
            api_data: 现有的API数据
            
        Returns:
            合并后的数据
        """
        if not self.enabled:
            return api_data
        
        try:
            # 获取RSS数据
            rss_data, failed_feeds = self.get_rss_data()
            
            if not rss_data:
                return api_data
            
            # 合并数据
            merged_data = self.data_converter.merge_rss_with_api_data(api_data, rss_data)
            
            # 记录合并结果
            rss_summary = rss_data.get("_summary", {})
            self.logger.info(
                f"数据合并完成: API源 {len(api_data)}个, RSS源 {rss_summary.get('active_feeds', 0)}个"
            )
            
            return merged_data
            
        except Exception as e:
            self.logger.error(f"RSS数据合并失败: {str(e)}")
            return api_data  # 返回原始API数据
    
    def get_rss_summary(self) -> Dict[str, Any]:
        """获取RSS模块状态摘要"""
        if not self.enabled:
            return {
                'enabled': False,
                'message': 'RSS功能未启用'
            }
        
        try:
            summary = {
                'enabled': True,
                'config_summary': self.rss_config.get_summary(),
                'cache_stats': self.rss_cache.get_cache_stats(),
                'error_stats': self.error_handler.get_error_stats(),
                'recent_errors': self.error_handler.get_recent_errors(3)
            }
            
            return summary
            
        except Exception as e:
            return {
                'enabled': True,
                'error': f'获取摘要失败: {str(e)}'
            }
    
    def clear_rss_cache(self) -> int:
        """清理RSS缓存"""
        if not self.enabled:
            return 0
        
        try:
            return self.rss_cache.clear_cache()
        except Exception as e:
            self.logger.error(f"清理RSS缓存失败: {str(e)}")
            return 0
    
    def validate_rss_config(self) -> Dict[str, Any]:
        """验证RSS配置"""
        if not self.enabled:
            return {'valid': False, 'message': 'RSS功能未启用'}
        
        validation_results = []
        
        try:
            for feed_config in self.rss_config.feeds:
                result = self.rss_validator.validate_feed_url(feed_config.url)
                result['feed_id'] = feed_config.id
                result['feed_name'] = feed_config.name
                validation_results.append(result)
            
            valid_count = sum(1 for r in validation_results if r['valid'])
            
            return {
                'valid': valid_count > 0,
                'total_feeds': len(validation_results),
                'valid_feeds': valid_count,
                'invalid_feeds': len(validation_results) - valid_count,
                'details': validation_results
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'配置验证失败: {str(e)}'
            }
    
    def test_rss_connectivity(self) -> Dict[str, Any]:
        """测试RSS源连通性"""
        if not self.enabled:
            return {'tested': False, 'message': 'RSS功能未启用'}
        
        results = []
        
        try:
            enabled_feeds = self.rss_config.get_enabled_feeds()[:5]  # 限制测试数量
            
            for feed_config in enabled_feeds:
                availability = self.rss_validator.check_feed_availability(
                    feed_config.url, timeout=10
                )
                availability['feed_id'] = feed_config.id
                availability['feed_name'] = feed_config.name
                results.append(availability)
            
            available_count = sum(1 for r in results if r['available'])
            
            return {
                'tested': True,
                'total_tested': len(results),
                'available': available_count,
                'unavailable': len(results) - available_count,
                'results': results
            }
            
        except Exception as e:
            return {
                'tested': False,
                'error': f'连通性测试失败: {str(e)}'
            }
    
    def get_keywords_for_matching(self) -> List[str]:
        """获取用于关键词匹配的关键词列表"""
        if not self.enabled or not self.rss_config:
            return []
        
        return self.rss_config.keywords
    
    def close(self):
        """关闭RSS模块资源"""
        if self.enabled:
            try:
                self.rss_fetcher.close()
                self.logger.info("RSS模块资源已关闭")
            except Exception as e:
                self.logger.error(f"关闭RSS模块资源失败: {str(e)}")