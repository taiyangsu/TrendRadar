# coding=utf-8
"""
RSS缓存管理器

负责RSS数据的缓存存储、读取和管理。
"""

import os
import json
import pickle
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, List
import logging
from ..models.rss_feed import RSSFeed
from ..models.rss_item import RSSItem


class RSSCacheManager:
    """RSS缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache/rss", cache_duration: int = 300):
        """
        初始化RSS缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
            cache_duration: 缓存持续时间(秒)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_duration = cache_duration
        self.logger = logging.getLogger(__name__)
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存文件扩展名
        self.cache_extensions = {
            'feed': '.feed_cache',
            'xml': '.xml_cache',
            'meta': '.meta_cache'
        }
        
        # 内存缓存（用于频繁访问的数据）
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._memory_cache_max_size = 50  # 最大内存缓存条目数
    
    def _generate_cache_key(self, identifier: str) -> str:
        """生成缓存键"""
        # 使用MD5哈希生成短且唯一的键
        return hashlib.md5(identifier.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str, cache_type: str) -> Path:
        """获取缓存文件路径"""
        extension = self.cache_extensions.get(cache_type, '.cache')
        return self.cache_dir / f"{cache_key}{extension}"
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """检查缓存文件是否有效"""
        try:
            if not cache_file.exists():
                return False
            
            # 检查文件修改时间
            mtime = cache_file.stat().st_mtime
            current_time = time.time()
            
            return (current_time - mtime) < self.cache_duration
            
        except Exception as e:
            self.logger.warning(f"检查缓存有效性失败: {str(e)}")
            return False
    
    def cache_rss_feed(self, feed_id: str, rss_feed: RSSFeed) -> bool:
        """
        缓存RSS源数据
        
        Args:
            feed_id: RSS源ID
            rss_feed: RSS源对象
            
        Returns:
            True表示缓存成功
        """
        try:
            cache_key = self._generate_cache_key(feed_id)
            cache_file = self._get_cache_file_path(cache_key, 'feed')
            
            # 准备缓存数据
            cache_data = {
                'feed_id': feed_id,
                'cached_at': datetime.now().isoformat(),
                'feed_data': rss_feed.to_dict()
            }
            
            # 写入文件缓存
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # 更新内存缓存
            self._update_memory_cache(cache_key, cache_data)
            
            self.logger.info(f"RSS源缓存成功: {feed_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"RSS源缓存失败: {feed_id}, 错误: {str(e)}")
            return False
    
    def get_cached_rss_feed(self, feed_id: str) -> Optional[RSSFeed]:
        """
        获取缓存的RSS源数据
        
        Args:
            feed_id: RSS源ID
            
        Returns:
            缓存的RSS源对象，不存在或过期时返回None
        """
        try:
            cache_key = self._generate_cache_key(feed_id)
            
            # 先检查内存缓存
            if cache_key in self._memory_cache:
                memory_data = self._memory_cache[cache_key]
                if self._is_memory_cache_valid(memory_data):
                    feed_data = memory_data['data']['feed_data']
                    return RSSFeed.from_dict(feed_data)
            
            # 检查文件缓存
            cache_file = self._get_cache_file_path(cache_key, 'feed')
            
            if not self._is_cache_valid(cache_file):
                return None
            
            # 读取缓存数据
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 更新内存缓存
            self._update_memory_cache(cache_key, cache_data)
            
            # 重建RSS源对象
            feed_data = cache_data['feed_data']
            rss_feed = RSSFeed.from_dict(feed_data)
            
            self.logger.info(f"RSS源缓存命中: {feed_id}")
            return rss_feed
            
        except Exception as e:
            self.logger.warning(f"获取RSS源缓存失败: {feed_id}, 错误: {str(e)}")
            return None
    
    def cache_xml_content(self, url: str, xml_content: str) -> bool:
        """
        缓存原始XML内容
        
        Args:
            url: RSS源URL
            xml_content: XML内容
            
        Returns:
            True表示缓存成功
        """
        try:
            cache_key = self._generate_cache_key(url)
            cache_file = self._get_cache_file_path(cache_key, 'xml')
            
            cache_data = {
                'url': url,
                'cached_at': datetime.now().isoformat(),
                'xml_content': xml_content,
                'content_length': len(xml_content)
            }
            
            # 写入文件缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"XML内容缓存成功: {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"XML内容缓存失败: {url}, 错误: {str(e)}")
            return False
    
    def get_cached_xml_content(self, url: str) -> Optional[str]:
        """
        获取缓存的XML内容
        
        Args:
            url: RSS源URL
            
        Returns:
            缓存的XML内容，不存在或过期时返回None
        """
        try:
            cache_key = self._generate_cache_key(url)
            cache_file = self._get_cache_file_path(cache_key, 'xml')
            
            if not self._is_cache_valid(cache_file):
                return None
            
            # 读取缓存数据
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            xml_content = cache_data.get('xml_content', '')
            
            self.logger.debug(f"XML内容缓存命中: {url}")
            return xml_content
            
        except Exception as e:
            self.logger.warning(f"获取XML内容缓存失败: {url}, 错误: {str(e)}")
            return None
    
    def cache_metadata(self, identifier: str, metadata: Dict[str, Any]) -> bool:
        """
        缓存元数据
        
        Args:
            identifier: 标识符
            metadata: 元数据字典
            
        Returns:
            True表示缓存成功
        """
        try:
            cache_key = self._generate_cache_key(identifier)
            cache_file = self._get_cache_file_path(cache_key, 'meta')
            
            cache_data = {
                'identifier': identifier,
                'cached_at': datetime.now().isoformat(),
                'metadata': metadata
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"元数据缓存失败: {identifier}, 错误: {str(e)}")
            return False
    
    def get_cached_metadata(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的元数据
        
        Args:
            identifier: 标识符
            
        Returns:
            缓存的元数据，不存在或过期时返回None
        """
        try:
            cache_key = self._generate_cache_key(identifier)
            cache_file = self._get_cache_file_path(cache_key, 'meta')
            
            if not self._is_cache_valid(cache_file):
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            return cache_data.get('metadata', {})
            
        except Exception as e:
            self.logger.warning(f"获取元数据缓存失败: {identifier}, 错误: {str(e)}")
            return None
    
    def _update_memory_cache(self, cache_key: str, cache_data: Dict[str, Any]) -> None:
        """更新内存缓存"""
        try:
            # 如果缓存满了，移除最旧的条目
            if len(self._memory_cache) >= self._memory_cache_max_size:
                # 按时间戳排序，移除最旧的
                oldest_key = min(
                    self._memory_cache.keys(),
                    key=lambda k: self._memory_cache[k]['timestamp']
                )
                del self._memory_cache[oldest_key]
            
            # 添加新的缓存条目
            self._memory_cache[cache_key] = {
                'timestamp': time.time(),
                'data': cache_data
            }
            
        except Exception as e:
            self.logger.warning(f"更新内存缓存失败: {str(e)}")
    
    def _is_memory_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查内存缓存是否有效"""
        try:
            timestamp = cache_entry['timestamp']
            current_time = time.time()
            return (current_time - timestamp) < self.cache_duration
        except Exception:
            return False
    
    def clear_cache(self, cache_type: Optional[str] = None) -> int:
        """
        清理缓存
        
        Args:
            cache_type: 缓存类型，None表示清理所有
            
        Returns:
            清理的文件数量
        """
        cleared_count = 0
        
        try:
            if cache_type:
                # 清理特定类型的缓存
                extension = self.cache_extensions.get(cache_type, '.cache')
                pattern = f"*{extension}"
            else:
                # 清理所有缓存
                pattern = "*"
            
            for cache_file in self.cache_dir.glob(pattern):
                try:
                    cache_file.unlink()
                    cleared_count += 1
                except Exception as e:
                    self.logger.warning(f"删除缓存文件失败: {cache_file}, {str(e)}")
            
            # 清理内存缓存
            if not cache_type or cache_type == 'memory':
                self._memory_cache.clear()
            
            self.logger.info(f"清理缓存完成: {cleared_count}个文件")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"清理缓存失败: {str(e)}")
            return cleared_count
    
    def clear_expired_cache(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的文件数量
        """
        cleared_count = 0
        
        try:
            current_time = time.time()
            
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file():
                    try:
                        mtime = cache_file.stat().st_mtime
                        if (current_time - mtime) >= self.cache_duration:
                            cache_file.unlink()
                            cleared_count += 1
                    except Exception as e:
                        self.logger.warning(f"检查缓存文件失败: {cache_file}, {str(e)}")
            
            # 清理过期的内存缓存
            expired_keys = []
            for key, entry in self._memory_cache.items():
                if not self._is_memory_cache_valid(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._memory_cache[key]
            
            self.logger.info(f"清理过期缓存完成: {cleared_count}个文件")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {str(e)}")
            return cleared_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        stats = {
            'cache_dir': str(self.cache_dir),
            'cache_duration': self.cache_duration,
            'total_files': 0,
            'total_size': 0,
            'memory_cache_entries': len(self._memory_cache),
            'cache_types': {}
        }
        
        try:
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file():
                    stats['total_files'] += 1
                    file_size = cache_file.stat().st_size
                    stats['total_size'] += file_size
                    
                    # 按类型统计
                    suffix = cache_file.suffix
                    if suffix not in stats['cache_types']:
                        stats['cache_types'][suffix] = {'count': 0, 'size': 0}
                    
                    stats['cache_types'][suffix]['count'] += 1
                    stats['cache_types'][suffix]['size'] += file_size
            
            # 转换大小为可读格式
            stats['total_size_readable'] = self._format_size(stats['total_size'])
            
            for cache_type in stats['cache_types']:
                size = stats['cache_types'][cache_type]['size']
                stats['cache_types'][cache_type]['size_readable'] = self._format_size(size)
                
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {str(e)}")
        
        return stats
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def invalidate_cache(self, identifier: str, cache_type: str = 'feed') -> bool:
        """
        使特定缓存失效
        
        Args:
            identifier: 标识符
            cache_type: 缓存类型
            
        Returns:
            True表示成功
        """
        try:
            cache_key = self._generate_cache_key(identifier)
            cache_file = self._get_cache_file_path(cache_key, cache_type)
            
            # 删除文件缓存
            if cache_file.exists():
                cache_file.unlink()
            
            # 删除内存缓存
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            
            self.logger.info(f"缓存失效成功: {identifier}")
            return True
            
        except Exception as e:
            self.logger.error(f"缓存失效失败: {identifier}, 错误: {str(e)}")
            return False