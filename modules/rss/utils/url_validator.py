# coding=utf-8
"""
URL验证工具

提供URL验证、标准化和处理功能。
"""

import re
from urllib.parse import urlparse, urljoin, quote, unquote
from typing import Optional, Dict, Any, List
import logging


class URLValidator:
    """URL验证工具类"""
    
    def __init__(self):
        """初始化URL验证器"""
        self.logger = logging.getLogger(__name__)
        
        # URL正则模式
        self.url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
            r'(?::\d+)?'  # 可选端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        # 危险的URL模式
        self.dangerous_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'file://',
        ]
        
        # 常见的RSS路径模式
        self.rss_path_patterns = [
            r'/rss',
            r'/feed',
            r'/feeds',
            r'\.xml$',
            r'\.rss$',
            r'/atom',
        ]
    
    def is_valid_url(self, url: str) -> bool:
        """
        验证URL是否有效
        
        Args:
            url: 要验证的URL
            
        Returns:
            True表示URL有效
        """
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        if not url:
            return False
        
        # 检查危险模式
        if self._is_dangerous_url(url):
            return False
        
        # 使用正则模式验证
        if not self.url_pattern.match(url):
            return False
        
        # 使用urllib.parse验证
        try:
            parsed = urlparse(url)
            return all([
                parsed.scheme in ('http', 'https'),
                parsed.netloc,
                not self._has_invalid_characters(url)
            ])
        except Exception:
            return False
    
    def _is_dangerous_url(self, url: str) -> bool:
        """检查URL是否包含危险模式"""
        url_lower = url.lower()
        return any(re.search(pattern, url_lower) for pattern in self.dangerous_patterns)
    
    def _has_invalid_characters(self, url: str) -> bool:
        """检查URL是否包含无效字符"""
        # 检查是否包含不可打印字符或控制字符
        return any(ord(char) < 32 or ord(char) > 126 for char in url 
                  if char not in 'áéíóúñü')  # 允许一些常见的非ASCII字符
    
    def normalize_url(self, url: str) -> Optional[str]:
        """
        标准化URL
        
        Args:
            url: 原始URL
            
        Returns:
            标准化后的URL，失败时返回None
        """
        if not url:
            return None
        
        try:
            url = url.strip()
            
            # 添加协议前缀（如果缺少）
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # 解析URL
            parsed = urlparse(url)
            
            # 标准化域名（转小写）
            netloc = parsed.netloc.lower()
            
            # 移除默认端口
            if netloc.endswith(':80') and parsed.scheme == 'http':
                netloc = netloc[:-3]
            elif netloc.endswith(':443') and parsed.scheme == 'https':
                netloc = netloc[:-4]
            
            # 标准化路径
            path = parsed.path or '/'
            if not path.startswith('/'):
                path = '/' + path
            
            # 重构URL
            normalized = f"{parsed.scheme}://{netloc}{path}"
            
            # 添加查询参数和片段（如果存在）
            if parsed.query:
                normalized += f"?{parsed.query}"
            if parsed.fragment:
                normalized += f"#{parsed.fragment}"
            
            return normalized
            
        except Exception as e:
            self.logger.warning(f"URL标准化失败: {url}, 错误: {str(e)}")
            return None
    
    def get_domain(self, url: str) -> Optional[str]:
        """
        获取URL的域名
        
        Args:
            url: URL字符串
            
        Returns:
            域名，失败时返回None
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None
    
    def get_base_url(self, url: str) -> Optional[str]:
        """
        获取URL的基础部分（协议+域名）
        
        Args:
            url: URL字符串
            
        Returns:
            基础URL，失败时返回None
        """
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return None
    
    def join_urls(self, base_url: str, relative_url: str) -> Optional[str]:
        """
        连接基础URL和相对URL
        
        Args:
            base_url: 基础URL
            relative_url: 相对URL
            
        Returns:
            完整URL，失败时返回None
        """
        try:
            return urljoin(base_url, relative_url)
        except Exception as e:
            self.logger.warning(f"URL连接失败: {base_url} + {relative_url}, 错误: {str(e)}")
            return None
    
    def encode_url(self, url: str) -> str:
        """
        编码URL中的特殊字符
        
        Args:
            url: 原始URL
            
        Returns:
            编码后的URL
        """
        try:
            parsed = urlparse(url)
            
            # 编码路径
            encoded_path = quote(parsed.path.encode('utf-8'), safe='/')
            
            # 编码查询参数
            encoded_query = quote(parsed.query.encode('utf-8'), safe='=&')
            
            # 重构URL
            encoded_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
            if encoded_query:
                encoded_url += f"?{encoded_query}"
            if parsed.fragment:
                encoded_url += f"#{quote(parsed.fragment.encode('utf-8'))}"
            
            return encoded_url
            
        except Exception as e:
            self.logger.warning(f"URL编码失败: {url}, 错误: {str(e)}")
            return url
    
    def decode_url(self, url: str) -> str:
        """
        解码URL中的编码字符
        
        Args:
            url: 编码的URL
            
        Returns:
            解码后的URL
        """
        try:
            return unquote(url)
        except Exception as e:
            self.logger.warning(f"URL解码失败: {url}, 错误: {str(e)}")
            return url
    
    def is_rss_url(self, url: str) -> bool:
        """
        检查URL是否可能是RSS源
        
        Args:
            url: URL字符串
            
        Returns:
            True表示可能是RSS源
        """
        if not self.is_valid_url(url):
            return False
        
        url_lower = url.lower()
        
        # 检查路径模式
        for pattern in self.rss_path_patterns:
            if re.search(pattern, url_lower):
                return True
        
        return False
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """
        从文本中提取URL
        
        Args:
            text: 文本内容
            
        Returns:
            URL列表
        """
        urls = []
        
        if not text:
            return urls
        
        # URL正则模式（更宽松）
        url_pattern = re.compile(
            r'https?://[^\s<>"\']+',
            re.IGNORECASE
        )
        
        matches = url_pattern.findall(text)
        
        for match in matches:
            # 清理URL（移除尾部标点符号）
            url = match.rstrip('.,;:!?)')
            if self.is_valid_url(url):
                urls.append(url)
        
        return list(set(urls))  # 去重
    
    def get_url_info(self, url: str) -> Dict[str, Any]:
        """
        获取URL的详细信息
        
        Args:
            url: URL字符串
            
        Returns:
            包含URL信息的字典
        """
        info = {
            'url': url,
            'valid': False,
            'scheme': '',
            'domain': '',
            'port': None,
            'path': '',
            'query': '',
            'fragment': '',
            'is_secure': False,
            'is_rss': False
        }
        
        try:
            if not self.is_valid_url(url):
                return info
            
            parsed = urlparse(url)
            
            info.update({
                'valid': True,
                'scheme': parsed.scheme,
                'domain': parsed.netloc.split(':')[0].lower(),
                'port': parsed.port,
                'path': parsed.path,
                'query': parsed.query,
                'fragment': parsed.fragment,
                'is_secure': parsed.scheme == 'https',
                'is_rss': self.is_rss_url(url)
            })
            
        except Exception as e:
            info['error'] = str(e)
        
        return info
    
    def validate_rsshub_url(self, url: str) -> bool:
        """
        验证是否是有效的RSSHub URL
        
        Args:
            url: URL字符串
            
        Returns:
            True表示是有效的RSSHub URL
        """
        if not self.is_valid_url(url):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 检查是否是RSSHub域名
            rsshub_domains = [
                'rsshub.app',
                'rsshub.rssforever.com',
                'rsshub.ktachibana.party',
                'rss.shab.fun'
            ]
            
            return any(domain == rsshub_domain or domain.endswith(f'.{rsshub_domain}') 
                      for rsshub_domain in rsshub_domains)
                      
        except Exception:
            return False