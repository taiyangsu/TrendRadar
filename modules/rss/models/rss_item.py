# coding=utf-8
"""
RSS条目数据模型

定义RSS条目的数据结构，提供数据验证和序列化功能。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class RSSItem:
    """RSS条目数据模型"""
    
    title: str                         # 标题
    link: str                          # 链接
    description: str                   # 描述
    pub_date: datetime                # 发布时间
    author: Optional[str] = None      # 作者
    category: Optional[str] = None    # 分类
    guid: Optional[str] = None        # 唯一标识符
    content: Optional[str] = None     # 完整内容
    source: str = ""                  # 来源
    rank: Optional[int] = None        # 排名
    tags: list = field(default_factory=list)  # 标签列表
    
    def __post_init__(self):
        """初始化后的数据验证"""
        if not self.title.strip():
            raise ValueError("标题不能为空")
        if not self.link.strip():
            raise ValueError("链接不能为空")
        if not self.description.strip():
            raise ValueError("描述不能为空")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "author": self.author,
            "category": self.category,
            "guid": self.guid,
            "content": self.content,
            "source": self.source,
            "rank": self.rank,
            "tags": self.tags
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSItem':
        """从字典创建实例"""
        # 处理发布时间
        pub_date = data.get('pub_date')
        if isinstance(pub_date, str):
            pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
        elif pub_date is None:
            pub_date = datetime.now()
            
        return cls(
            title=data.get('title', ''),
            link=data.get('link', ''),
            description=data.get('description', ''),
            pub_date=pub_date,
            author=data.get('author'),
            category=data.get('category'),
            guid=data.get('guid'),
            content=data.get('content'),
            source=data.get('source', ''),
            rank=data.get('rank'),
            tags=data.get('tags', [])
        )
    
    def is_valid(self) -> bool:
        """检查数据是否有效"""
        try:
            return (
                bool(self.title.strip()) and
                bool(self.link.strip()) and
                bool(self.description.strip()) and
                isinstance(self.pub_date, datetime)
            )
        except Exception:
            return False
    
    def get_display_title(self, max_length: int = 50) -> str:
        """获取用于显示的标题（截断处理）"""
        if len(self.title) <= max_length:
            return self.title
        return self.title[:max_length-3] + "..."
    
    def matches_keywords(self, keywords: list) -> bool:
        """检查是否匹配关键词"""
        if not keywords:
            return False
            
        text_content = f"{self.title} {self.description} {self.content or ''}".lower()
        return any(keyword.lower() in text_content for keyword in keywords)