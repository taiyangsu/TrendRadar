# coding=utf-8
"""
数据转换器

将RSS数据转换为与TrendRadar现有系统兼容的格式。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from ..models.rss_item import RSSItem
from ..models.rss_feed import RSSFeed


class DataConverter:
    """数据格式转换器"""
    
    def __init__(self):
        """初始化数据转换器"""
        self.logger = logging.getLogger(__name__)
    
    def convert_rss_item_to_news_format(self, rss_item: RSSItem) -> Dict[str, Any]:
        """
        将RSS条目转换为新闻格式（与现有API数据格式兼容）
        
        Args:
            rss_item: RSS条目对象
            
        Returns:
            新闻格式的字典
        """
        try:
            # 基础格式转换
            news_item = {
                "title": rss_item.title,
                "url": rss_item.link,
                "mobileUrl": rss_item.link,  # RSS通常移动端和桌面端URL相同
                "source": rss_item.source or "RSS",
                "category": rss_item.category or "general",
                "pub_date": rss_item.pub_date.isoformat() if rss_item.pub_date else None,
                "rank": rss_item.rank
            }
            
            # 添加额外的RSS特有信息
            news_item.update({
                "description": rss_item.description,
                "author": rss_item.author,
                "guid": rss_item.guid,
                "content": rss_item.content,
                "tags": rss_item.tags,
                "data_type": "rss"  # 标识数据来源类型
            })
            
            return news_item
            
        except Exception as e:
            self.logger.error(f"RSS条目转换失败: {str(e)}")
            return {}
    
    def convert_rss_feed_to_platform_format(self, rss_feed: RSSFeed) -> Dict[str, Any]:
        """
        将RSS源转换为平台格式（类似现有平台数据结构）
        
        Args:
            rss_feed: RSS源对象
            
        Returns:
            平台格式的字典
        """
        try:
            # 转换所有条目
            items = []
            for rss_item in rss_feed.items:
                converted_item = self.convert_rss_item_to_news_format(rss_item)
                if converted_item:
                    items.append(converted_item)
            
            # 构建平台格式数据
            platform_data = {
                "platform_id": f"rss_{rss_feed.source_id}",
                "platform_name": rss_feed.title,
                "category": rss_feed.category,
                "total_items": len(items),
                "last_update": rss_feed.last_build_date.isoformat(),
                "items": items,
                "metadata": {
                    "feed_url": rss_feed.link,
                    "description": rss_feed.description,
                    "language": rss_feed.language,
                    "image_url": rss_feed.image_url,
                    "generator": rss_feed.generator,
                    "ttl": rss_feed.ttl,
                    "data_type": "rss"
                }
            }
            
            return platform_data
            
        except Exception as e:
            self.logger.error(f"RSS源转换失败: {str(e)}")
            return {}
    
    def convert_multiple_feeds_to_unified_format(self, rss_feeds: List[RSSFeed]) -> Dict[str, Any]:
        """
        将多个RSS源转换为统一格式（类似现有的多平台数据结构）
        
        Args:
            rss_feeds: RSS源列表
            
        Returns:
            统一格式的数据字典
        """
        try:
            unified_data = {}
            total_items = 0
            
            for rss_feed in rss_feeds:
                platform_data = self.convert_rss_feed_to_platform_format(rss_feed)
                if platform_data:
                    platform_id = platform_data["platform_id"]
                    unified_data[platform_id] = platform_data
                    total_items += platform_data["total_items"]
            
            # 添加汇总信息
            unified_data["_summary"] = {
                "total_feeds": len(rss_feeds),
                "active_feeds": len([f for f in unified_data.keys() if not f.startswith("_")]),
                "total_items": total_items,
                "last_update": datetime.now().isoformat(),
                "data_source": "rss"
            }
            
            return unified_data
            
        except Exception as e:
            self.logger.error(f"多RSS源转换失败: {str(e)}")
            return {}
    
    def merge_rss_with_api_data(self, api_data: Dict[str, Any], 
                               rss_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并RSS数据和API数据
        
        Args:
            api_data: 现有的API数据
            rss_data: RSS数据
            
        Returns:
            合并后的数据
        """
        try:
            merged_data = api_data.copy()
            
            # 添加RSS数据
            for platform_id, platform_data in rss_data.items():
                if not platform_id.startswith("_"):  # 跳过元数据
                    merged_data[platform_id] = platform_data
            
            # 更新汇总信息
            if "_summary" in merged_data:
                merged_data["_summary"]["rss_feeds"] = rss_data.get("_summary", {}).get("active_feeds", 0)
                merged_data["_summary"]["rss_items"] = rss_data.get("_summary", {}).get("total_items", 0)
            
            return merged_data
            
        except Exception as e:
            self.logger.error(f"数据合并失败: {str(e)}")
            return api_data  # 返回原始API数据
    
    def convert_for_keyword_matching(self, rss_items: List[RSSItem]) -> List[Dict[str, Any]]:
        """
        为关键词匹配转换RSS条目格式
        
        Args:
            rss_items: RSS条目列表
            
        Returns:
            适合关键词匹配的数据列表
        """
        converted_items = []
        
        for item in rss_items:
            try:
                # 构建用于关键词匹配的文本内容
                searchable_text = f"{item.title} {item.description}"
                if item.content:
                    searchable_text += f" {item.content}"
                if item.tags:
                    searchable_text += f" {' '.join(item.tags)}"
                
                match_item = {
                    "title": item.title,
                    "url": item.link,
                    "source": item.source,
                    "searchable_text": searchable_text.lower(),
                    "pub_date": item.pub_date,
                    "rank": item.rank,
                    "category": item.category,
                    "data_type": "rss",
                    "original_item": item  # 保留原始对象引用
                }
                
                converted_items.append(match_item)
                
            except Exception as e:
                self.logger.warning(f"条目转换失败: {str(e)}")
                continue
        
        return converted_items
    
    def convert_for_notification(self, rss_items: List[RSSItem],
                                source_name: str = "") -> List[Dict[str, Any]]:
        """
        为通知推送转换RSS条目格式
        
        Args:
            rss_items: RSS条目列表
            source_name: 数据源名称
            
        Returns:
            适合通知推送的数据列表
        """
        notification_items = []
        
        for item in rss_items:
            try:
                # 计算权重（基于排名和时间）
                weight = self._calculate_item_weight(item)
                
                notification_item = {
                    "title": item.title,
                    "url": item.link,
                    "source": source_name or item.source or "RSS",
                    "rank": item.rank,
                    "weight": weight,
                    "pub_date": item.pub_date.isoformat() if item.pub_date else None,
                    "category": item.category,
                    "author": item.author,
                    "description": self._truncate_text(item.description, 100),
                    "data_type": "rss"
                }
                
                notification_items.append(notification_item)
                
            except Exception as e:
                self.logger.warning(f"通知条目转换失败: {str(e)}")
                continue
        
        return notification_items
    
    def _calculate_item_weight(self, rss_item: RSSItem) -> float:
        """
        计算RSS条目权重
        
        Args:
            rss_item: RSS条目
            
        Returns:
            权重值
        """
        try:
            weight = 0.0
            
            # 排名权重（排名越靠前权重越高）
            if rss_item.rank is not None:
                # 排名权重：1-10名权重较高，之后递减
                if rss_item.rank <= 10:
                    weight += 0.6 * (11 - rss_item.rank) / 10
                else:
                    weight += 0.1
            else:
                weight += 0.3  # 没有排名的条目给予中等权重
            
            # 时间权重（越新权重越高）
            if rss_item.pub_date:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                
                # 确保时间有时区信息
                pub_date = rss_item.pub_date
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                
                hours_ago = (now - pub_date).total_seconds() / 3600
                
                if hours_ago <= 1:
                    weight += 0.3  # 1小时内
                elif hours_ago <= 6:
                    weight += 0.2  # 6小时内
                elif hours_ago <= 24:
                    weight += 0.1  # 24小时内
                # 超过24小时不加权重
            
            # 内容质量权重（基于标题和描述长度）
            title_length = len(rss_item.title) if rss_item.title else 0
            desc_length = len(rss_item.description) if rss_item.description else 0
            
            if title_length > 10 and desc_length > 20:
                weight += 0.1  # 内容相对完整
            
            return min(weight, 1.0)  # 权重最大为1.0
            
        except Exception:
            return 0.5  # 默认权重
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        截断文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            截断后的文本
        """
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length-3] + "..."
    
    def create_rss_summary(self, rss_feeds: List[RSSFeed]) -> Dict[str, Any]:
        """
        创建RSS数据汇总
        
        Args:
            rss_feeds: RSS源列表
            
        Returns:
            汇总信息字典
        """
        try:
            total_items = sum(len(feed.items) for feed in rss_feeds)
            categories = list(set(feed.category for feed in rss_feeds if feed.category))
            
            # 按分类统计
            category_stats = {}
            for category in categories:
                category_feeds = [f for f in rss_feeds if f.category == category]
                category_items = sum(len(f.items) for f in category_feeds)
                category_stats[category] = {
                    "feeds": len(category_feeds),
                    "items": category_items
                }
            
            # 获取最新条目
            all_items = []
            for feed in rss_feeds:
                all_items.extend(feed.items)
            
            # 按发布时间排序
            all_items.sort(key=lambda x: x.pub_date, reverse=True)
            recent_items = all_items[:10]  # 最新10条
            
            summary = {
                "total_feeds": len(rss_feeds),
                "total_items": total_items,
                "categories": categories,
                "category_stats": category_stats,
                "recent_items": [
                    {
                        "title": item.title,
                        "source": item.source,
                        "pub_date": item.pub_date.isoformat(),
                        "url": item.link
                    }
                    for item in recent_items
                ],
                "last_update": datetime.now().isoformat(),
                "data_source": "rss"
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"RSS汇总创建失败: {str(e)}")
            return {}