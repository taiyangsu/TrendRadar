# coding=utf-8
"""
RSS源数据模型

定义RSS源的数据结构，管理RSS源的元数据和条目列表。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from .rss_item import RSSItem


@dataclass
class RSSFeed:
    """RSS源数据模型"""
    
    title: str                        # 源标题
    link: str                         # 源链接
    description: str                  # 源描述
    language: str                     # 语言
    last_build_date: datetime        # 最后更新时间
    items: List[RSSItem] = field(default_factory=list)  # 条目列表
    source_id: str = ""              # 源ID
    category: str = ""               # 分类
    image_url: Optional[str] = None  # 图标URL
    generator: Optional[str] = None  # 生成器
    ttl: Optional[int] = None        # 缓存生存时间(分钟)
    
    def __post_init__(self):
        """初始化后的数据验证"""
        if not self.title.strip():
            raise ValueError("RSS源标题不能为空")
        if not self.link.strip():
            raise ValueError("RSS源链接不能为空")
    
    def add_item(self, item: RSSItem) -> None:
        """添加RSS条目"""
        if not isinstance(item, RSSItem):
            raise TypeError("必须是RSSItem实例")
        if item.is_valid():
            self.items.append(item)
        else:
            raise ValueError("RSS条目数据无效")
    
    def add_items(self, items: List[RSSItem]) -> int:
        """批量添加RSS条目，返回成功添加的数量"""
        added_count = 0
        for item in items:
            try:
                self.add_item(item)
                added_count += 1
            except (ValueError, TypeError):
                continue  # 忽略无效条目
        return added_count
    
    def get_items_by_category(self, category: str) -> List[RSSItem]:
        """按分类获取条目"""
        return [item for item in self.items if item.category == category]
    
    def get_items_by_keywords(self, keywords: List[str]) -> List[RSSItem]:
        """按关键词筛选条目"""
        return [item for item in self.items if item.matches_keywords(keywords)]
    
    def get_top_items(self, count: int = 10) -> List[RSSItem]:
        """获取排名靠前的条目"""
        # 优先按rank排序，如果没有rank则按发布时间排序
        sorted_items = sorted(
            self.items,
            key=lambda x: (x.rank if x.rank is not None else float('inf'), -x.pub_date.timestamp())
        )
        return sorted_items[:count]
    
    def get_recent_items(self, hours: int = 24) -> List[RSSItem]:
        """获取最近指定小时内的条目"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [item for item in self.items if item.pub_date >= cutoff_time]
    
    def sort_items_by_date(self, reverse: bool = True) -> None:
        """按日期排序条目"""
        self.items.sort(key=lambda x: x.pub_date, reverse=reverse)
    
    def sort_items_by_rank(self) -> None:
        """按排名排序条目"""
        self.items.sort(key=lambda x: x.rank if x.rank is not None else float('inf'))
    
    def remove_duplicates_by_link(self) -> int:
        """按链接去重，返回移除的重复条目数量"""
        seen_links = set()
        unique_items = []
        removed_count = 0
        
        for item in self.items:
            if item.link not in seen_links:
                seen_links.add(item.link)
                unique_items.append(item)
            else:
                removed_count += 1
        
        self.items = unique_items
        return removed_count
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "language": self.language,
            "last_build_date": self.last_build_date.isoformat(),
            "source_id": self.source_id,
            "category": self.category,
            "image_url": self.image_url,
            "generator": self.generator,
            "ttl": self.ttl,
            "items": [item.to_dict() for item in self.items],
            "item_count": len(self.items)
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSFeed':
        """从字典创建实例"""
        # 处理最后更新时间
        last_build_date = data.get('last_build_date')
        if isinstance(last_build_date, str):
            last_build_date = datetime.fromisoformat(last_build_date.replace('Z', '+00:00'))
        elif last_build_date is None:
            last_build_date = datetime.now()
        
        # 创建RSS源实例
        feed = cls(
            title=data.get('title', ''),
            link=data.get('link', ''),
            description=data.get('description', ''),
            language=data.get('language', 'zh'),
            last_build_date=last_build_date,
            source_id=data.get('source_id', ''),
            category=data.get('category', ''),
            image_url=data.get('image_url'),
            generator=data.get('generator'),
            ttl=data.get('ttl')
        )
        
        # 添加条目
        items_data = data.get('items', [])
        for item_data in items_data:
            try:
                item = RSSItem.from_dict(item_data)
                feed.add_item(item)
            except (ValueError, TypeError):
                continue  # 忽略无效条目
        
        return feed
    
    def get_summary(self) -> Dict[str, Any]:
        """获取RSS源摘要信息"""
        return {
            "source_id": self.source_id,
            "title": self.title,
            "category": self.category,
            "total_items": len(self.items),
            "last_update": self.last_build_date.isoformat(),
            "recent_items_24h": len(self.get_recent_items(24)),
            "has_ranked_items": any(item.rank is not None for item in self.items)
        }