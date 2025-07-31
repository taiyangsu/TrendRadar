# coding=utf-8
"""
RSS数据获取器

负责从RSS源获取数据，支持HTTP请求、重试机制、并发获取等功能。
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging


class RSSFetcher:
    """RSS数据获取器"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, request_interval: int = 1000):
        """
        初始化RSS获取器
        
        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            request_interval: 请求间隔(毫秒)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_interval = request_interval / 1000.0  # 转换为秒
        self.session = self._create_session()
        self.logger = logging.getLogger(__name__)
        
        # 用户代理
        self.user_agent = "TrendRadar RSS Fetcher/2.0 (https://github.com/sansan0/TrendRadar)"
        
        # 最后请求时间记录（用于请求间隔控制）
        self._last_request_times: Dict[str, float] = {}
    
    def _create_session(self) -> requests.Session:
        """创建带重试策略的requests会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,  # 退避因子
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # 允许重试的HTTP方法
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        return {
            'User-Agent': self.user_agent,
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    
    def _wait_for_interval(self, url: str) -> None:
        """等待请求间隔"""
        if url in self._last_request_times:
            elapsed = time.time() - self._last_request_times[url]
            if elapsed < self.request_interval:
                sleep_time = self.request_interval - elapsed
                time.sleep(sleep_time)
        
        self._last_request_times[url] = time.time()
    
    def fetch_feed(self, feed_url: str, custom_headers: Optional[Dict[str, str]] = None,
                   custom_timeout: Optional[int] = None) -> Optional[str]:
        """
        获取单个RSS源数据
        
        Args:
            feed_url: RSS源URL
            custom_headers: 自定义请求头
            custom_timeout: 自定义超时时间
            
        Returns:
            RSS源的XML内容，失败时返回None
        """
        try:
            # 控制请求间隔
            self._wait_for_interval(feed_url)
            
            # 准备请求头
            headers = self._get_default_headers()
            if custom_headers:
                headers.update(custom_headers)
            
            # 确定超时时间
            timeout = custom_timeout or self.timeout
            
            self.logger.info(f"开始获取RSS源: {feed_url}")
            
            # 发送请求
            response = self.session.get(
                feed_url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if not any(ct in content_type for ct in ['xml', 'rss', 'atom']):
                self.logger.warning(f"RSS源可能不是XML格式: {feed_url}, Content-Type: {content_type}")
            
            # 获取响应内容
            content = response.text
            
            if not content.strip():
                self.logger.error(f"RSS源返回空内容: {feed_url}")
                return None
            
            self.logger.info(f"成功获取RSS源: {feed_url}, 内容长度: {len(content)}")
            return content
            
        except requests.exceptions.Timeout:
            self.logger.error(f"RSS源请求超时: {feed_url}")
        except requests.exceptions.ConnectionError:
            self.logger.error(f"RSS源连接失败: {feed_url}")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"RSS源HTTP错误: {feed_url}, 状态码: {e.response.status_code if e.response else 'Unknown'}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"RSS源请求异常: {feed_url}, 错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"RSS源获取未知错误: {feed_url}, 错误: {str(e)}")
        
        return None
    
    def fetch_multiple_feeds(self, feed_urls: List[str], 
                           custom_headers: Optional[Dict[str, str]] = None,
                           max_workers: int = 5) -> Dict[str, Optional[str]]:
        """
        并发获取多个RSS源数据
        
        Args:
            feed_urls: RSS源URL列表
            custom_headers: 自定义请求头
            max_workers: 最大并发数
            
        Returns:
            字典，键为URL，值为XML内容(失败时为None)
        """
        results = {}
        
        if not feed_urls:
            return results
        
        self.logger.info(f"开始并发获取 {len(feed_urls)} 个RSS源")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_url = {
                executor.submit(self.fetch_feed, url, custom_headers): url
                for url in feed_urls
            }
            
            # 收集结果
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results[url] = result
                except Exception as e:
                    self.logger.error(f"并发获取RSS源异常: {url}, 错误: {str(e)}")
                    results[url] = None
        
        successful_count = sum(1 for v in results.values() if v is not None)
        self.logger.info(f"并发获取完成: 成功 {successful_count}/{len(feed_urls)} 个RSS源")
        
        return results
    
    def fetch_feeds_with_config(self, feed_configs: List[Dict[str, Any]],
                               max_workers: int = 5) -> Dict[str, Tuple[Optional[str], Dict[str, Any]]]:
        """
        根据配置获取RSS源数据
        
        Args:
            feed_configs: RSS源配置列表，每个配置包含id、url、custom_headers、timeout等
            max_workers: 最大并发数
            
        Returns:
            字典，键为feed_id，值为(XML内容, 配置信息)的元组
        """
        results = {}
        
        if not feed_configs:
            return results
        
        self.logger.info(f"开始根据配置获取 {len(feed_configs)} 个RSS源")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_config = {}
            for config in feed_configs:
                feed_id = config.get('id', '')
                feed_url = config.get('url', '')
                custom_headers = config.get('custom_headers', {})
                custom_timeout = config.get('timeout')
                
                if not feed_id or not feed_url:
                    self.logger.warning(f"RSS源配置无效: {config}")
                    results[feed_id] = (None, config)
                    continue
                
                future = executor.submit(
                    self.fetch_feed, 
                    feed_url, 
                    custom_headers, 
                    custom_timeout
                )
                future_to_config[future] = config
            
            # 收集结果
            for future in as_completed(future_to_config):
                config = future_to_config[future]
                feed_id = config.get('id', '')
                
                try:
                    xml_content = future.result()
                    results[feed_id] = (xml_content, config)
                except Exception as e:
                    self.logger.error(f"根据配置获取RSS源异常: {feed_id}, 错误: {str(e)}")
                    results[feed_id] = (None, config)
        
        successful_count = sum(1 for v, _ in results.values() if v is not None)
        self.logger.info(f"根据配置获取完成: 成功 {successful_count}/{len(feed_configs)} 个RSS源")
        
        return results
    
    def test_feed_availability(self, feed_url: str, 
                              custom_headers: Optional[Dict[str, str]] = None) -> bool:
        """
        测试RSS源可用性
        
        Args:
            feed_url: RSS源URL
            custom_headers: 自定义请求头
            
        Returns:
            True表示可用，False表示不可用
        """
        try:
            # 使用HEAD请求测试可用性
            headers = self._get_default_headers()
            if custom_headers:
                headers.update(custom_headers)
            
            response = self.session.head(
                feed_url,
                headers=headers,
                timeout=10,  # 测试时使用较短的超时时间
                allow_redirects=True
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_feed_info(self, feed_url: str, 
                      custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取RSS源基本信息
        
        Args:
            feed_url: RSS源URL
            custom_headers: 自定义请求头
            
        Returns:
            包含RSS源信息的字典
        """
        info = {
            'url': feed_url,
            'available': False,
            'status_code': None,
            'content_type': None,
            'content_length': None,
            'last_modified': None,
            'server': None,
            'response_time': None
        }
        
        try:
            start_time = time.time()
            
            headers = self._get_default_headers()
            if custom_headers:
                headers.update(custom_headers)
            
            response = self.session.head(
                feed_url,
                headers=headers,
                timeout=10,
                allow_redirects=True
            )
            
            response_time = time.time() - start_time
            
            info.update({
                'available': True,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type'),
                'content_length': response.headers.get('content-length'),
                'last_modified': response.headers.get('last-modified'),
                'server': response.headers.get('server'),
                'response_time': round(response_time, 3)
            })
            
        except Exception as e:
            info['error'] = str(e)
        
        return info
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()