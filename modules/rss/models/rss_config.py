# coding=utf-8
"""
RSS配置数据模型

定义RSS配置的数据结构，管理RSS源配置和相关设置。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import yaml
from pathlib import Path


@dataclass
class RSSFeedConfig:
    """单个RSS源配置"""
    
    id: str                          # RSS源唯一标识
    name: str                        # RSS源名称
    url: str                         # RSS源URL
    category: str                    # 分类
    enabled: bool = True             # 是否启用
    priority: int = 1                # 优先级(1最高)
    custom_headers: Dict[str, str] = field(default_factory=dict)  # 自定义请求头
    timeout: Optional[int] = None    # 超时时间(秒)
    retry_count: Optional[int] = None # 重试次数
    
    def __post_init__(self):
        """初始化后的数据验证"""
        if not self.id.strip():
            raise ValueError("RSS源ID不能为空")
        if not self.name.strip():
            raise ValueError("RSS源名称不能为空")
        if not self.url.strip():
            raise ValueError("RSS源URL不能为空")
        if self.priority < 1:
            raise ValueError("优先级不能小于1")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "category": self.category,
            "enabled": self.enabled,
            "priority": self.priority,
            "custom_headers": self.custom_headers,
            "timeout": self.timeout,
            "retry_count": self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSFeedConfig':
        """从字典创建实例"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            url=data.get('url', ''),
            category=data.get('category', 'default'),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 1),
            custom_headers=data.get('custom_headers', {}),
            timeout=data.get('timeout'),
            retry_count=data.get('retry_count')
        )


@dataclass
class RSSConfig:
    """RSS模块配置"""
    
    enable_rss: bool = True                     # 是否启用RSS功能
    request_interval: int = 2000                # 请求间隔(毫秒)
    timeout: int = 30                           # 默认超时时间(秒)
    max_retries: int = 3                        # 默认最大重试次数
    cache_duration: int = 300                   # 缓存时间(秒)
    feeds: List[RSSFeedConfig] = field(default_factory=list)  # RSS源配置列表
    keywords: List[str] = field(default_factory=list)        # 关键词列表
    
    def add_feed(self, feed_config: RSSFeedConfig) -> None:
        """添加RSS源配置"""
        if not isinstance(feed_config, RSSFeedConfig):
            raise TypeError("必须是RSSFeedConfig实例")
        
        # 检查ID是否重复
        if any(feed.id == feed_config.id for feed in self.feeds):
            raise ValueError(f"RSS源ID '{feed_config.id}' 已存在")
        
        self.feeds.append(feed_config)
    
    def remove_feed(self, feed_id: str) -> bool:
        """移除RSS源配置"""
        for i, feed in enumerate(self.feeds):
            if feed.id == feed_id:
                del self.feeds[i]
                return True
        return False
    
    def get_feed(self, feed_id: str) -> Optional[RSSFeedConfig]:
        """获取RSS源配置"""
        for feed in self.feeds:
            if feed.id == feed_id:
                return feed
        return None
    
    def get_enabled_feeds(self) -> List[RSSFeedConfig]:
        """获取启用的RSS源配置"""
        return [feed for feed in self.feeds if feed.enabled]
    
    def get_feeds_by_category(self, category: str) -> List[RSSFeedConfig]:
        """按分类获取RSS源配置"""
        return [feed for feed in self.feeds if feed.category == category]
    
    def get_feeds_by_priority(self, priority: int) -> List[RSSFeedConfig]:
        """按优先级获取RSS源配置"""
        return [feed for feed in self.feeds if feed.priority == priority]
    
    def sort_feeds_by_priority(self) -> None:
        """按优先级排序RSS源配置"""
        self.feeds.sort(key=lambda x: x.priority)
    
    def enable_feed(self, feed_id: str) -> bool:
        """启用RSS源"""
        feed = self.get_feed(feed_id)
        if feed:
            feed.enabled = True
            return True
        return False
    
    def disable_feed(self, feed_id: str) -> bool:
        """禁用RSS源"""
        feed = self.get_feed(feed_id)
        if feed:
            feed.enabled = False
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "rss": {
                "enable_rss": self.enable_rss,
                "request_interval": self.request_interval,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "cache_duration": self.cache_duration,
                "feeds": [feed.to_dict() for feed in self.feeds]
            },
            "rss_keywords": self.keywords
        }
    
    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSConfig':
        """从字典创建实例"""
        rss_data = data.get('rss', {})
        
        config = cls(
            enable_rss=rss_data.get('enable_rss', True),
            request_interval=rss_data.get('request_interval', 2000),
            timeout=rss_data.get('timeout', 30),
            max_retries=rss_data.get('max_retries', 3),
            cache_duration=rss_data.get('cache_duration', 300),
            keywords=data.get('rss_keywords', [])
        )
        
        # 添加RSS源配置
        feeds_data = rss_data.get('feeds', [])
        for feed_data in feeds_data:
            try:
                feed_config = RSSFeedConfig.from_dict(feed_data)
                config.add_feed(feed_config)
            except (ValueError, TypeError):
                continue  # 忽略无效配置
        
        return config
    
    @classmethod
    def from_yaml_file(cls, file_path: str) -> 'RSSConfig':
        """从YAML文件加载配置"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    def save_to_yaml_file(self, file_path: str) -> None:
        """保存配置到YAML文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_yaml())
    
    def get_summary(self) -> Dict[str, Any]:
        """获取配置摘要信息"""
        enabled_feeds = self.get_enabled_feeds()
        categories = list(set(feed.category for feed in self.feeds))
        
        return {
            "rss_enabled": self.enable_rss,
            "total_feeds": len(self.feeds),
            "enabled_feeds": len(enabled_feeds),
            "disabled_feeds": len(self.feeds) - len(enabled_feeds),
            "categories": categories,
            "keywords_count": len(self.keywords),
            "request_interval_seconds": self.request_interval / 1000,
            "timeout_seconds": self.timeout,
            "cache_duration_minutes": self.cache_duration / 60
        }