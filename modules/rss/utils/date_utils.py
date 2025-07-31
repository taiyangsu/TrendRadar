# coding=utf-8
"""
日期处理工具

提供日期时间解析、格式化和处理功能。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import re
import logging
from dateutil import parser as dateutil_parser
from dateutil.tz import tzutc, gettz


class DateUtils:
    """日期处理工具类"""
    
    def __init__(self):
        """初始化日期工具"""
        self.logger = logging.getLogger(__name__)
        
        # 常见的日期时间格式
        self.common_formats = [
            '%Y-%m-%dT%H:%M:%S%z',          # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%SZ',           # ISO 8601 UTC
            '%Y-%m-%dT%H:%M:%S',            # ISO 8601 without timezone
            '%a, %d %b %Y %H:%M:%S %z',     # RFC 2822 with timezone
            '%a, %d %b %Y %H:%M:%S %Z',     # RFC 2822 with timezone name
            '%a, %d %b %Y %H:%M:%S GMT',    # RFC 2822 GMT
            '%a, %d %b %Y %H:%M:%S',        # RFC 2822 without timezone
            '%Y-%m-%d %H:%M:%S',            # Common database format
            '%Y-%m-%d',                     # Date only
            '%d/%m/%Y %H:%M:%S',           # European format
            '%m/%d/%Y %H:%M:%S',           # US format
            '%d-%m-%Y %H:%M:%S',           # Alternative format
        ]
        
        # 时区缩写映射
        self.timezone_abbr = {
            'GMT': 'UTC',
            'EST': 'US/Eastern',
            'PST': 'US/Pacific',
            'CST': 'US/Central',
            'MST': 'US/Mountain',
            'JST': 'Asia/Tokyo',
            'KST': 'Asia/Seoul',
            'CST': 'Asia/Shanghai',  # 中国标准时间
        }
    
    def parse_datetime(self, date_str: str, 
                      default_timezone: Optional[timezone] = None) -> Optional[datetime]:
        """
        解析日期时间字符串
        
        Args:
            date_str: 日期时间字符串
            default_timezone: 默认时区（当日期字符串没有时区信息时使用）
            
        Returns:
            解析后的datetime对象，失败时返回None
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        date_str = date_str.strip()
        if not date_str:
            return None
        
        # 预处理日期字符串
        date_str = self._preprocess_date_string(date_str)
        
        # 尝试使用dateutil解析（最智能的解析方式）
        try:
            dt = dateutil_parser.parse(date_str)
            
            # 如果没有时区信息，应用默认时区
            if dt.tzinfo is None and default_timezone:
                dt = dt.replace(tzinfo=default_timezone)
            elif dt.tzinfo is None:
                # 假定为UTC
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
            
        except Exception:
            pass
        
        # 尝试使用预定义格式解析
        for fmt in self.common_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                
                # 处理没有时区信息的情况
                if dt.tzinfo is None:
                    if default_timezone:
                        dt = dt.replace(tzinfo=default_timezone)
                    else:
                        dt = dt.replace(tzinfo=timezone.utc)
                
                return dt
                
            except ValueError:
                continue
        
        self.logger.warning(f"无法解析日期时间: {date_str}")
        return None
    
    def _preprocess_date_string(self, date_str: str) -> str:
        """预处理日期字符串"""
        # 移除多余的空白字符
        date_str = re.sub(r'\s+', ' ', date_str).strip()
        
        # 处理时区缩写
        for abbr, full_name in self.timezone_abbr.items():
            if date_str.endswith(f' {abbr}'):
                # 简单替换，dateutil会处理
                break
        
        # 处理特殊格式
        # 例如：Mon, 01 Jan 2024 12:00:00 +0000 (UTC)
        date_str = re.sub(r'\s*\([^)]+\)$', '', date_str)
        
        return date_str
    
    def format_datetime(self, dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        """
        格式化日期时间
        
        Args:
            dt: datetime对象
            fmt: 格式字符串
            
        Returns:
            格式化后的字符串
        """
        try:
            return dt.strftime(fmt)
        except Exception as e:
            self.logger.warning(f"日期格式化失败: {str(e)}")
            return str(dt)
    
    def to_iso_format(self, dt: datetime) -> str:
        """
        转换为ISO格式字符串
        
        Args:
            dt: datetime对象
            
        Returns:
            ISO格式字符串
        """
        try:
            return dt.isoformat()
        except Exception as e:
            self.logger.warning(f"ISO格式转换失败: {str(e)}")
            return str(dt)
    
    def to_rfc2822_format(self, dt: datetime) -> str:
        """
        转换为RFC 2822格式字符串
        
        Args:
            dt: datetime对象
            
        Returns:
            RFC 2822格式字符串
        """
        try:
            return dt.strftime('%a, %d %b %Y %H:%M:%S %z')
        except Exception as e:
            self.logger.warning(f"RFC 2822格式转换失败: {str(e)}")
            return str(dt)
    
    def convert_timezone(self, dt: datetime, target_tz: Union[str, timezone]) -> Optional[datetime]:
        """
        转换时区
        
        Args:
            dt: datetime对象
            target_tz: 目标时区
            
        Returns:
            转换后的datetime对象
        """
        try:
            if isinstance(target_tz, str):
                target_tz = gettz(target_tz)
            
            if dt.tzinfo is None:
                # 假定为UTC
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt.astimezone(target_tz)
            
        except Exception as e:
            self.logger.warning(f"时区转换失败: {str(e)}")
            return None
    
    def is_recent(self, dt: datetime, hours: int = 24) -> bool:
        """
        检查日期是否在指定小时内
        
        Args:
            dt: 要检查的datetime对象
            hours: 小时数
            
        Returns:
            True表示在指定时间内
        """
        try:
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            cutoff_time = now - timedelta(hours=hours)
            return dt >= cutoff_time
            
        except Exception:
            return False
    
    def get_age_description(self, dt: datetime) -> str:
        """
        获取时间描述（如："2小时前"）
        
        Args:
            dt: datetime对象
            
        Returns:
            时间描述字符串
        """
        try:
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days}天前"
            elif diff.seconds >= 3600:
                hours = diff.seconds // 3600
                return f"{hours}小时前"
            elif diff.seconds >= 60:
                minutes = diff.seconds // 60
                return f"{minutes}分钟前"
            else:
                return "刚刚"
                
        except Exception:
            return "未知时间"
    
    def normalize_datetime(self, dt: datetime) -> datetime:
        """
        标准化datetime对象（确保有时区信息）
        
        Args:
            dt: datetime对象
            
        Returns:
            标准化后的datetime对象
        """
        if dt.tzinfo is None:
            # 假定为UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def get_start_of_day(self, dt: datetime) -> datetime:
        """
        获取某天的开始时间（00:00:00）
        
        Args:
            dt: datetime对象
            
        Returns:
            当天开始时间
        """
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def get_end_of_day(self, dt: datetime) -> datetime:
        """
        获取某天的结束时间（23:59:59）
        
        Args:
            dt: datetime对象
            
        Returns:
            当天结束时间
        """
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    def is_same_day(self, dt1: datetime, dt2: datetime) -> bool:
        """
        检查两个日期是否是同一天
        
        Args:
            dt1: 第一个datetime对象
            dt2: 第二个datetime对象
            
        Returns:
            True表示是同一天
        """
        try:
            # 转换为UTC进行比较
            if dt1.tzinfo is None:
                dt1 = dt1.replace(tzinfo=timezone.utc)
            if dt2.tzinfo is None:
                dt2 = dt2.replace(tzinfo=timezone.utc)
            
            utc_dt1 = dt1.astimezone(timezone.utc)
            utc_dt2 = dt2.astimezone(timezone.utc)
            
            return (utc_dt1.year == utc_dt2.year and
                    utc_dt1.month == utc_dt2.month and
                    utc_dt1.day == utc_dt2.day)
                    
        except Exception:
            return False