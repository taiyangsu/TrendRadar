# coding=utf-8
"""
RSS解析器

负责解析RSS XML内容，支持RSS 2.0和Atom格式，提取标准化的数据结构。
"""

import feedparser
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from xml.etree import ElementTree as ET
import logging
from ..models.rss_item import RSSItem
from ..models.rss_feed import RSSFeed


class RSSParser:
    """RSS解析器"""
    
    def __init__(self):
        """初始化RSS解析器"""
        self.logger = logging.getLogger(__name__)
        
        # feedparser配置
        feedparser.USER_AGENT = "TrendRadar RSS Parser/2.0"
        
        # 常见的HTML标签正则
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        
        # 时间格式映射
        self.time_formats = [
            '%Y-%m-%dT%H:%M:%S%z',      # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%SZ',       # ISO 8601 UTC
            '%Y-%m-%dT%H:%M:%S',        # ISO 8601 without timezone
            '%a, %d %b %Y %H:%M:%S %z', # RFC 2822 with timezone
            '%a, %d %b %Y %H:%M:%S %Z', # RFC 2822 with timezone name
            '%a, %d %b %Y %H:%M:%S',    # RFC 2822 without timezone
            '%Y-%m-%d %H:%M:%S',        # Common format
            '%Y-%m-%d',                 # Date only
        ]
    
    def parse_feed(self, xml_content: str, source_id: str = "", 
                   category: str = "") -> Optional[RSSFeed]:
        """
        解析RSS XML内容
        
        Args:
            xml_content: RSS XML内容
            source_id: 源ID
            category: 分类
            
        Returns:
            解析后的RSSFeed对象，失败时返回None
        """
        try:
            if not xml_content or not xml_content.strip():
                self.logger.error("RSS内容为空")
                return None
            
            # 使用feedparser解析
            parsed = feedparser.parse(xml_content)
            
            if not parsed or not hasattr(parsed, 'feed'):
                self.logger.error("RSS内容解析失败")
                return None
            
            # 检查是否有解析错误
            if hasattr(parsed, 'bozo') and parsed.bozo:
                if hasattr(parsed, 'bozo_exception'):
                    self.logger.warning(f"RSS解析警告: {parsed.bozo_exception}")
            
            # 提取RSS源信息
            feed_data = parsed.feed
            feed_title = self._clean_text(feed_data.get('title', 'Unknown Feed'))
            feed_link = feed_data.get('link', '')
            feed_description = self._clean_text(feed_data.get('description', ''))
            feed_language = feed_data.get('language', 'zh')
            
            # 处理最后更新时间
            last_build_date = self._parse_datetime(
                feed_data.get('updated', feed_data.get('published', ''))
            ) or datetime.now()
            
            # 创建RSS源对象
            rss_feed = RSSFeed(
                title=feed_title,
                link=feed_link,
                description=feed_description,
                language=feed_language,
                last_build_date=last_build_date,
                source_id=source_id,
                category=category,
                image_url=self._extract_image_url(feed_data),
                generator=feed_data.get('generator', ''),
                ttl=self._extract_ttl(feed_data)
            )
            
            # 解析条目
            if hasattr(parsed, 'entries') and parsed.entries:
                items = self._parse_entries(parsed.entries, source_id)
                rss_feed.add_items(items)
                self.logger.info(f"解析完成: {feed_title}, 条目数: {len(items)}")
            else:
                self.logger.warning(f"RSS源没有条目: {feed_title}")
            
            return rss_feed
            
        except Exception as e:
            self.logger.error(f"RSS解析异常: {str(e)}")
            return None
    
    def _parse_entries(self, entries: List[Any], source_id: str) -> List[RSSItem]:
        """解析RSS条目列表"""
        items = []
        
        for i, entry in enumerate(entries, 1):
            try:
                item = self._parse_entry(entry, source_id, i)
                if item and item.is_valid():
                    items.append(item)
            except Exception as e:
                self.logger.warning(f"条目解析失败: {str(e)}")
                continue
        
        return items
    
    def _parse_entry(self, entry: Any, source_id: str, rank: Optional[int] = None) -> Optional[RSSItem]:
        """解析单个RSS条目"""
        try:
            # 提取基本信息
            title = self._clean_text(entry.get('title', ''))
            link = entry.get('link', '')
            description = self._clean_text(entry.get('summary', entry.get('description', '')))
            
            # 检查必须字段
            if not title or not link:
                return None
            
            # 提取发布时间
            pub_date = self._parse_datetime(
                entry.get('published', entry.get('updated', ''))
            ) or datetime.now()
            
            # 提取作者
            author = self._extract_author(entry)
            
            # 提取分类/标签
            category = self._extract_category(entry)
            tags = self._extract_tags(entry)
            
            # 提取GUID
            guid = entry.get('id', entry.get('guid', ''))
            
            # 提取完整内容
            content = self._extract_content(entry)
            
            # 创建RSS条目对象
            rss_item = RSSItem(
                title=title,
                link=link,
                description=description,
                pub_date=pub_date,
                author=author,
                category=category,
                guid=guid,
                content=content,
                source=source_id,
                rank=rank,
                tags=tags
            )
            
            return rss_item
            
        except Exception as e:
            self.logger.warning(f"RSS条目解析失败: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        
        # 移除HTML标签
        text = self.html_tag_pattern.sub('', text)
        
        # 标准化空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除首尾空白
        text = text.strip()
        
        return text
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not date_str:
            return None
        
        # 使用feedparser的时间解析
        try:
            time_struct = feedparser._parse_date(date_str)
            if time_struct:
                # 转换为datetime对象
                dt = datetime(*time_struct[:6])
                # 如果没有时区信息，假定为UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
        except:
            pass
        
        # 备用解析方法
        for fmt in self.time_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        self.logger.warning(f"无法解析日期时间: {date_str}")
        return None
    
    def _extract_author(self, entry: Any) -> Optional[str]:
        """提取作者信息"""
        # 尝试多个可能的字段
        author_fields = ['author', 'author_detail', 'dc_creator']
        
        for field in author_fields:
            author = entry.get(field, '')
            if author:
                if isinstance(author, dict):
                    return author.get('name', str(author))
                return str(author)
        
        return None
    
    def _extract_category(self, entry: Any) -> Optional[str]:
        """提取分类信息"""
        # 尝试多个可能的字段
        if 'tags' in entry and entry.tags:
            return entry.tags[0].get('term', '')
        
        category = entry.get('category', '')
        if category:
            return str(category)
        
        return None
    
    def _extract_tags(self, entry: Any) -> List[str]:
        """提取标签列表"""
        tags = []
        
        if 'tags' in entry and entry.tags:
            for tag in entry.tags:
                if isinstance(tag, dict):
                    term = tag.get('term', '')
                    if term:
                        tags.append(term)
                else:
                    tags.append(str(tag))
        
        return tags
    
    def _extract_content(self, entry: Any) -> Optional[str]:
        """提取完整内容"""
        # 尝试获取完整内容
        if 'content' in entry and entry.content:
            for content in entry.content:
                if isinstance(content, dict):
                    return self._clean_text(content.get('value', ''))
                return self._clean_text(str(content))
        
        # 备用：使用summary
        summary = entry.get('summary', '')
        if summary:
            return self._clean_text(summary)
        
        return None
    
    def _extract_image_url(self, feed_data: Any) -> Optional[str]:
        """提取RSS源图标URL"""
        # 尝试多个可能的字段
        if 'image' in feed_data:
            image = feed_data.image
            if isinstance(image, dict):
                return image.get('href', image.get('url', ''))
            return str(image)
        
        if 'logo' in feed_data:
            return str(feed_data.logo)
        
        return None
    
    def _extract_ttl(self, feed_data: Any) -> Optional[int]:
        """提取TTL（生存时间）"""
        ttl = feed_data.get('ttl', '')
        if ttl:
            try:
                return int(ttl)
            except:
                pass
        
        return None
    
    def validate_xml_format(self, xml_content: str) -> bool:
        """验证XML格式是否有效"""
        try:
            ET.fromstring(xml_content)
            return True
        except ET.ParseError:
            return False
    
    def extract_feed_info(self, xml_content: str) -> Dict[str, Any]:
        """提取RSS源基本信息（不解析条目）"""
        info = {
            'valid': False,
            'format': 'unknown',
            'title': '',
            'link': '',
            'description': '',
            'language': '',
            'item_count': 0,
            'last_build_date': None
        }
        
        try:
            parsed = feedparser.parse(xml_content)
            
            if not parsed or not hasattr(parsed, 'feed'):
                return info
            
            feed_data = parsed.feed
            
            # 检测格式
            if hasattr(parsed, 'version'):
                info['format'] = parsed.version
            
            # 提取基本信息
            info.update({
                'valid': True,
                'title': self._clean_text(feed_data.get('title', '')),
                'link': feed_data.get('link', ''),
                'description': self._clean_text(feed_data.get('description', '')),
                'language': feed_data.get('language', ''),
                'item_count': len(parsed.entries) if hasattr(parsed, 'entries') else 0,
                'last_build_date': self._parse_datetime(
                    feed_data.get('updated', feed_data.get('published', ''))
                )
            })
            
        except Exception as e:
            info['error'] = str(e)
        
        return info
    
    def parse_feed_urls_from_html(self, html_content: str, base_url: str = "") -> List[Dict[str, str]]:
        """从HTML页面中提取RSS/Atom链接"""
        feeds = []
        
        try:
            # 使用正则表达式查找link标签
            link_pattern = r'<link[^>]*(?:type=["\'](?:application/(?:rss|atom)\+xml|text/xml)["\'])[^>]*>'
            links = re.findall(link_pattern, html_content, re.IGNORECASE)
            
            for link in links:
                # 提取href和title
                href_match = re.search(r'href=["\']([^"\']+)["\']', link, re.IGNORECASE)
                title_match = re.search(r'title=["\']([^"\']+)["\']', link, re.IGNORECASE)
                type_match = re.search(r'type=["\']([^"\']+)["\']', link, re.IGNORECASE)
                
                if href_match:
                    href = href_match.group(1)
                    
                    # 处理相对URL
                    if base_url and not href.startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        href = urljoin(base_url, href)
                    
                    feeds.append({
                        'url': href,
                        'title': title_match.group(1) if title_match else '',
                        'type': type_match.group(1) if type_match else ''
                    })
        
        except Exception as e:
            self.logger.warning(f"从HTML提取RSS链接失败: {str(e)}")
        
        return feeds