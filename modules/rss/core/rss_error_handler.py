# coding=utf-8
"""
RSS错误处理器

处理RSS模块中的各种错误和异常情况。
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum


class RSSErrorType(Enum):
    """RSS错误类型枚举"""
    FETCH_ERROR = "fetch_error"           # 获取错误
    PARSE_ERROR = "parse_error"           # 解析错误
    VALIDATION_ERROR = "validation_error" # 验证错误
    CACHE_ERROR = "cache_error"           # 缓存错误
    NETWORK_ERROR = "network_error"       # 网络错误
    FORMAT_ERROR = "format_error"         # 格式错误
    TIMEOUT_ERROR = "timeout_error"       # 超时错误
    CONFIG_ERROR = "config_error"         # 配置错误
    UNKNOWN_ERROR = "unknown_error"       # 未知错误


class RSSError(Exception):
    """RSS模块自定义异常"""
    
    def __init__(self, message: str, error_type: RSSErrorType = RSSErrorType.UNKNOWN_ERROR,
                 details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        """
        初始化RSS异常
        
        Args:
            message: 错误消息
            error_type: 错误类型
            details: 错误详情
            original_exception: 原始异常
        """
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'message': str(self),
            'error_type': self.error_type.value,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'original_exception': str(self.original_exception) if self.original_exception else None
        }


class RSSErrorHandler:
    """RSS错误处理器"""
    
    def __init__(self, max_error_history: int = 100):
        """
        初始化RSS错误处理器
        
        Args:
            max_error_history: 最大错误历史记录数
        """
        self.logger = logging.getLogger(__name__)
        self.max_error_history = max_error_history
        
        # 错误历史记录
        self.error_history: List[Dict[str, Any]] = []
        
        # 错误统计
        self.error_stats: Dict[str, int] = {}
        
        # 错误回调函数
        self.error_callbacks: Dict[RSSErrorType, List[Callable]] = {}
        
        # 重试配置
        self.retry_config = {
            RSSErrorType.NETWORK_ERROR: {'max_retries': 3, 'backoff_factor': 2},
            RSSErrorType.TIMEOUT_ERROR: {'max_retries': 2, 'backoff_factor': 1.5},
            RSSErrorType.FETCH_ERROR: {'max_retries': 2, 'backoff_factor': 2},
        }
    
    def handle_fetch_error(self, feed_url: str, error: Exception, 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理RSS获取错误
        
        Args:
            feed_url: RSS源URL
            error: 异常对象
            context: 上下文信息
            
        Returns:
            错误处理结果
        """
        error_type = self._classify_fetch_error(error)
        
        details = {
            'feed_url': feed_url,
            'error_class': error.__class__.__name__,
            'context': context or {}
        }
        
        rss_error = RSSError(
            message=f"RSS源获取失败: {feed_url} - {str(error)}",
            error_type=error_type,
            details=details,
            original_exception=error
        )
        
        return self._process_error(rss_error)
    
    def handle_parse_error(self, xml_content: str, error: Exception,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理RSS解析错误
        
        Args:
            xml_content: XML内容
            error: 异常对象
            context: 上下文信息
            
        Returns:
            错误处理结果
        """
        details = {
            'content_length': len(xml_content) if xml_content else 0,
            'content_preview': xml_content[:200] if xml_content else '',
            'error_class': error.__class__.__name__,
            'context': context or {}
        }
        
        rss_error = RSSError(
            message=f"RSS解析失败: {str(error)}",
            error_type=RSSErrorType.PARSE_ERROR,
            details=details,
            original_exception=error
        )
        
        return self._process_error(rss_error)
    
    def handle_validation_error(self, data: Any, error: Exception,
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理RSS验证错误
        
        Args:
            data: 被验证的数据
            error: 异常对象
            context: 上下文信息
            
        Returns:
            错误处理结果
        """
        details = {
            'data_type': type(data).__name__,
            'error_class': error.__class__.__name__,
            'context': context or {}
        }
        
        rss_error = RSSError(
            message=f"RSS验证失败: {str(error)}",
            error_type=RSSErrorType.VALIDATION_ERROR,
            details=details,
            original_exception=error
        )
        
        return self._process_error(rss_error)
    
    def handle_cache_error(self, operation: str, identifier: str, error: Exception,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理缓存错误
        
        Args:
            operation: 缓存操作类型
            identifier: 缓存标识符
            error: 异常对象
            context: 上下文信息
            
        Returns:
            错误处理结果
        """
        details = {
            'operation': operation,
            'identifier': identifier,
            'error_class': error.__class__.__name__,
            'context': context or {}
        }
        
        rss_error = RSSError(
            message=f"缓存操作失败: {operation} - {str(error)}",
            error_type=RSSErrorType.CACHE_ERROR,
            details=details,
            original_exception=error
        )
        
        return self._process_error(rss_error)
    
    def handle_config_error(self, config_path: str, error: Exception,
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理配置错误
        
        Args:
            config_path: 配置文件路径
            error: 异常对象
            context: 上下文信息
            
        Returns:
            错误处理结果
        """
        details = {
            'config_path': config_path,
            'error_class': error.__class__.__name__,
            'context': context or {}
        }
        
        rss_error = RSSError(
            message=f"配置错误: {config_path} - {str(error)}",
            error_type=RSSErrorType.CONFIG_ERROR,
            details=details,
            original_exception=error
        )
        
        return self._process_error(rss_error)
    
    def handle_general_error(self, error: Exception, error_type: RSSErrorType = RSSErrorType.UNKNOWN_ERROR,
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理一般错误
        
        Args:
            error: 异常对象
            error_type: 错误类型
            context: 上下文信息
            
        Returns:
            错误处理结果
        """
        details = {
            'error_class': error.__class__.__name__,
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        rss_error = RSSError(
            message=f"RSS模块错误: {str(error)}",
            error_type=error_type,
            details=details,
            original_exception=error
        )
        
        return self._process_error(rss_error)
    
    def _classify_fetch_error(self, error: Exception) -> RSSErrorType:
        """分类获取错误"""
        error_name = error.__class__.__name__.lower()
        
        if 'timeout' in error_name:
            return RSSErrorType.TIMEOUT_ERROR
        elif 'connection' in error_name or 'network' in error_name:
            return RSSErrorType.NETWORK_ERROR
        elif 'http' in error_name:
            return RSSErrorType.FETCH_ERROR
        else:
            return RSSErrorType.FETCH_ERROR
    
    def _process_error(self, rss_error: RSSError) -> Dict[str, Any]:
        """处理错误"""
        try:
            # 记录错误
            self._log_error(rss_error)
            
            # 添加到历史记录
            self._add_to_history(rss_error)
            
            # 更新统计
            self._update_stats(rss_error)
            
            # 触发回调
            self._trigger_callbacks(rss_error)
            
            # 准备返回结果
            result = {
                'handled': True,
                'error': rss_error.to_dict(),
                'should_retry': self._should_retry(rss_error),
                'retry_config': self._get_retry_config(rss_error.error_type)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"错误处理过程中发生异常: {str(e)}")
            return {
                'handled': False,
                'error': rss_error.to_dict(),
                'should_retry': False,
                'processing_error': str(e)
            }
    
    def _log_error(self, rss_error: RSSError) -> None:
        """记录错误日志"""
        try:
            log_message = f"[{rss_error.error_type.value}] {rss_error.message}"
            
            if rss_error.error_type in [RSSErrorType.NETWORK_ERROR, RSSErrorType.TIMEOUT_ERROR]:
                self.logger.warning(log_message)
            elif rss_error.error_type in [RSSErrorType.VALIDATION_ERROR, RSSErrorType.FORMAT_ERROR]:
                self.logger.warning(log_message)
            else:
                self.logger.error(log_message)
            
            # 记录详细信息
            if rss_error.details:
                self.logger.debug(f"错误详情: {rss_error.details}")
                
        except Exception as e:
            self.logger.error(f"记录错误日志失败: {str(e)}")
    
    def _add_to_history(self, rss_error: RSSError) -> None:
        """添加到错误历史"""
        try:
            self.error_history.append(rss_error.to_dict())
            
            # 限制历史记录数量
            if len(self.error_history) > self.max_error_history:
                self.error_history = self.error_history[-self.max_error_history:]
                
        except Exception as e:
            self.logger.error(f"添加错误历史失败: {str(e)}")
    
    def _update_stats(self, rss_error: RSSError) -> None:
        """更新错误统计"""
        try:
            error_key = rss_error.error_type.value
            self.error_stats[error_key] = self.error_stats.get(error_key, 0) + 1
        except Exception as e:
            self.logger.error(f"更新错误统计失败: {str(e)}")
    
    def _trigger_callbacks(self, rss_error: RSSError) -> None:
        """触发错误回调"""
        try:
            callbacks = self.error_callbacks.get(rss_error.error_type, [])
            for callback in callbacks:
                try:
                    callback(rss_error)
                except Exception as e:
                    self.logger.error(f"错误回调执行失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"触发错误回调失败: {str(e)}")
    
    def _should_retry(self, rss_error: RSSError) -> bool:
        """判断是否应该重试"""
        retry_config = self.retry_config.get(rss_error.error_type)
        return retry_config is not None and retry_config.get('max_retries', 0) > 0
    
    def _get_retry_config(self, error_type: RSSErrorType) -> Optional[Dict[str, Any]]:
        """获取重试配置"""
        return self.retry_config.get(error_type)
    
    def register_error_callback(self, error_type: RSSErrorType, callback: Callable) -> None:
        """
        注册错误回调函数
        
        Args:
            error_type: 错误类型
            callback: 回调函数
        """
        if error_type not in self.error_callbacks:
            self.error_callbacks[error_type] = []
        self.error_callbacks[error_type].append(callback)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        total_errors = sum(self.error_stats.values())
        
        stats = {
            'total_errors': total_errors,
            'error_types': self.error_stats.copy(),
            'error_history_count': len(self.error_history),
            'most_common_error': None
        }
        
        if self.error_stats:
            most_common = max(self.error_stats.items(), key=lambda x: x[1])
            stats['most_common_error'] = {
                'type': most_common[0],
                'count': most_common[1],
                'percentage': (most_common[1] / total_errors) * 100 if total_errors > 0 else 0
            }
        
        return stats
    
    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的错误记录"""
        return self.error_history[-count:] if self.error_history else []
    
    def clear_error_history(self) -> int:
        """清空错误历史"""
        count = len(self.error_history)
        self.error_history.clear()
        self.error_stats.clear()
        return count
    
    def create_error_report(self) -> Dict[str, Any]:
        """创建错误报告"""
        stats = self.get_error_stats()
        recent_errors = self.get_recent_errors(5)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'recent_errors': recent_errors,
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """生成错误处理建议"""
        recommendations = []
        
        if not self.error_stats:
            return recommendations
        
        total_errors = sum(self.error_stats.values())
        
        # 网络错误建议
        network_errors = self.error_stats.get(RSSErrorType.NETWORK_ERROR.value, 0)
        if network_errors / total_errors > 0.3:
            recommendations.append("网络错误较多，建议检查网络连接或增加重试次数")
        
        # 超时错误建议
        timeout_errors = self.error_stats.get(RSSErrorType.TIMEOUT_ERROR.value, 0)
        if timeout_errors / total_errors > 0.2:
            recommendations.append("超时错误较多，建议增加请求超时时间")
        
        # 解析错误建议
        parse_errors = self.error_stats.get(RSSErrorType.PARSE_ERROR.value, 0)
        if parse_errors / total_errors > 0.15:
            recommendations.append("解析错误较多，建议检查RSS源格式或增加格式兼容性")
        
        # 获取错误建议
        fetch_errors = self.error_stats.get(RSSErrorType.FETCH_ERROR.value, 0)
        if fetch_errors / total_errors > 0.25:
            recommendations.append("获取错误较多，建议检查RSS源URL或服务器状态")
        
        if not recommendations:
            recommendations.append("错误率较低，系统运行正常")
        
        return recommendations