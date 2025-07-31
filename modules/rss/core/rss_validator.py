# coding=utf-8
"""
RSS验证器

负责验证RSS格式、数据完整性和URL有效性。
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from xml.etree import ElementTree as ET
import logging
from ..models.rss_item import RSSItem
from ..models.rss_feed import RSSFeed
from ..utils.url_validator import URLValidator
from ..utils.xml_parser import XMLParser


class RSSValidator:
    """RSS验证器"""
    
    def __init__(self):
        """初始化RSS验证器"""
        self.logger = logging.getLogger(__name__)
        self.url_validator = URLValidator()
        self.xml_parser = XMLParser()
        
        # RSS格式要求的基本元素
        self.required_rss_elements = ['title', 'link', 'description']
        self.required_item_elements = ['title', 'link']
        
        # Atom格式要求的基本元素
        self.required_atom_elements = ['title', 'id', 'updated']
        self.required_entry_elements = ['title', 'id']
        
        # 支持的RSS/Atom版本
        self.supported_versions = [
            'rss2.0', 'rss0.92', 'rss0.91',
            'atom1.0', 'atom0.3'
        ]
    
    def validate_rss_format(self, xml_content: str) -> Dict[str, Any]:
        """
        验证RSS格式
        
        Args:
            xml_content: RSS XML内容
            
        Returns:
            验证结果字典
        """
        result = {
            'valid': False,
            'format': 'unknown',
            'version': '',
            'errors': [],
            'warnings': [],
            'element_count': 0,
            'item_count': 0
        }
        
        try:
            if not xml_content or not xml_content.strip():
                result['errors'].append('RSS内容为空')
                return result
            
            # 解析XML
            root = self.xml_parser.parse_xml_string(xml_content)
            if not root:
                result['errors'].append('XML格式无效')
                return result
            
            # 检测RSS格式和版本
            format_info = self._detect_format_and_version(root)
            result['format'] = format_info['format']
            result['version'] = format_info['version']
            
            # 根据格式进行相应验证
            if result['format'] == 'rss':
                validation_result = self._validate_rss_structure(root)
            elif result['format'] == 'atom':
                validation_result = self._validate_atom_structure(root)
            else:
                result['errors'].append(f"不支持的RSS格式: {result['format']}")
                return result
            
            # 合并验证结果
            result.update(validation_result)
            
            # 验证内容质量
            quality_result = self._validate_content_quality(root, result['format'])
            result['warnings'].extend(quality_result['warnings'])
            
            # 如果没有严重错误，标记为有效
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f'验证过程异常: {str(e)}')
        
        return result
    
    def _detect_format_and_version(self, root: ET.Element) -> Dict[str, str]:
        """检测RSS格式和版本"""
        format_info = {'format': 'unknown', 'version': ''}
        
        try:
            root_tag = root.tag.lower()
            
            if root_tag == 'rss':
                format_info['format'] = 'rss'
                # 获取版本属性
                version = root.get('version', '')
                if version:
                    format_info['version'] = f'rss{version}'
                else:
                    format_info['version'] = 'rss2.0'  # 默认版本
                    
            elif root_tag == 'feed':
                format_info['format'] = 'atom'
                # 检查命名空间来确定版本
                xmlns = root.get('xmlns', '')
                if 'http://www.w3.org/2005/Atom' in xmlns:
                    format_info['version'] = 'atom1.0'
                elif 'http://purl.org/atom/ns#' in xmlns:
                    format_info['version'] = 'atom0.3'
                else:
                    format_info['version'] = 'atom1.0'  # 默认版本
                    
        except Exception:
            pass
        
        return format_info
    
    def _validate_rss_structure(self, root: ET.Element) -> Dict[str, Any]:
        """验证RSS结构"""
        result = {
            'errors': [],
            'warnings': [],
            'element_count': 0,
            'item_count': 0
        }
        
        try:
            # 查找channel元素
            channel = root.find('channel')
            if channel is None:
                result['errors'].append('缺少必需的channel元素')
                return result
            
            # 验证必需的channel子元素
            for element_name in self.required_rss_elements:
                element = channel.find(element_name)
                if element is None:
                    result['errors'].append(f'channel缺少必需元素: {element_name}')
                elif not element.text or not element.text.strip():
                    result['warnings'].append(f'channel元素内容为空: {element_name}')
            
            # 验证URL格式
            link_element = channel.find('link')
            if link_element is not None and link_element.text:
                if not self.url_validator.is_valid_url(link_element.text.strip()):
                    result['warnings'].append('channel链接格式可能无效')
            
            # 统计和验证item元素
            items = channel.findall('item')
            result['item_count'] = len(items)
            
            for i, item in enumerate(items, 1):
                item_errors = self._validate_rss_item(item)
                if item_errors:
                    result['warnings'].extend([f'第{i}个item: {error}' for error in item_errors])
            
            # 统计所有元素
            result['element_count'] = len(list(channel.iter()))
            
        except Exception as e:
            result['errors'].append(f'RSS结构验证失败: {str(e)}')
        
        return result
    
    def _validate_atom_structure(self, root: ET.Element) -> Dict[str, Any]:
        """验证Atom结构"""
        result = {
            'errors': [],
            'warnings': [],
            'element_count': 0,
            'item_count': 0
        }
        
        try:
            # 验证必需的feed元素
            for element_name in self.required_atom_elements:
                element = root.find(f'.//{element_name}')
                if element is None:
                    result['errors'].append(f'feed缺少必需元素: {element_name}')
                elif not element.text or not element.text.strip():
                    result['warnings'].append(f'feed元素内容为空: {element_name}')
            
            # 统计和验证entry元素
            entries = root.findall('.//entry')
            result['item_count'] = len(entries)
            
            for i, entry in enumerate(entries, 1):
                entry_errors = self._validate_atom_entry(entry)
                if entry_errors:
                    result['warnings'].extend([f'第{i}个entry: {error}' for error in entry_errors])
            
            # 统计所有元素
            result['element_count'] = len(list(root.iter()))
            
        except Exception as e:
            result['errors'].append(f'Atom结构验证失败: {str(e)}')
        
        return result
    
    def _validate_rss_item(self, item: ET.Element) -> List[str]:
        """验证RSS item元素"""
        errors = []
        
        try:
            # 验证必需元素
            has_title = item.find('title') is not None
            has_link = item.find('link') is not None
            has_description = item.find('description') is not None
            
            if not has_title and not has_description:
                errors.append('item必须包含title或description之一')
            
            # 验证链接格式
            link_element = item.find('link')
            if link_element is not None and link_element.text:
                if not self.url_validator.is_valid_url(link_element.text.strip()):
                    errors.append('item链接格式无效')
            
            # 验证GUID
            guid_element = item.find('guid')
            if guid_element is not None and guid_element.text:
                guid_text = guid_element.text.strip()
                is_permalink = guid_element.get('isPermaLink', 'true').lower() == 'true'
                
                if is_permalink and not self.url_validator.is_valid_url(guid_text):
                    errors.append('GUID声明为permalink但格式无效')
            
        except Exception as e:
            errors.append(f'item验证异常: {str(e)}')
        
        return errors
    
    def _validate_atom_entry(self, entry: ET.Element) -> List[str]:
        """验证Atom entry元素"""
        errors = []
        
        try:
            # 验证必需元素
            for element_name in self.required_entry_elements:
                element = entry.find(f'.//{element_name}')
                if element is None:
                    errors.append(f'缺少必需元素: {element_name}')
            
            # 验证链接
            link_elements = entry.findall('.//link')
            for link in link_elements:
                href = link.get('href')
                if href and not self.url_validator.is_valid_url(href):
                    errors.append('链接href格式无效')
            
        except Exception as e:
            errors.append(f'entry验证异常: {str(e)}')
        
        return errors
    
    def _validate_content_quality(self, root: ET.Element, format_type: str) -> Dict[str, Any]:
        """验证内容质量"""
        result = {
            'warnings': []
        }
        
        try:
            if format_type == 'rss':
                channel = root.find('channel')
                if channel is not None:
                    # 检查更新频率信息
                    if channel.find('lastBuildDate') is None and channel.find('pubDate') is None:
                        result['warnings'].append('建议添加lastBuildDate或pubDate元素')
                    
                    # 检查语言信息
                    if channel.find('language') is None:
                        result['warnings'].append('建议添加language元素')
                    
                    # 检查item数量
                    items = channel.findall('item')
                    if len(items) == 0:
                        result['warnings'].append('RSS源没有任何条目')
                    elif len(items) > 100:
                        result['warnings'].append('条目数量过多，可能影响解析性能')
            
            elif format_type == 'atom':
                # 检查更新时间
                if root.find('.//updated') is None:
                    result['warnings'].append('建议添加updated元素')
                
                # 检查条目数量
                entries = root.findall('.//entry')
                if len(entries) == 0:
                    result['warnings'].append('Atom源没有任何条目')
                elif len(entries) > 100:
                    result['warnings'].append('条目数量过多，可能影响解析性能')
        
        except Exception:
            pass
        
        return result
    
    def validate_feed_url(self, url: str) -> Dict[str, Any]:
        """
        验证RSS源URL
        
        Args:
            url: RSS源URL
            
        Returns:
            验证结果字典
        """
        result = {
            'valid': False,
            'url': url,
            'errors': [],
            'warnings': [],
            'url_info': {}
        }
        
        try:
            # 基本URL验证
            if not self.url_validator.is_valid_url(url):
                result['errors'].append('URL格式无效')
                return result
            
            # 获取URL详细信息
            result['url_info'] = self.url_validator.get_url_info(url)
            
            # 检查是否为HTTPS
            if not result['url_info']['is_secure']:
                result['warnings'].append('建议使用HTTPS协议')
            
            # 检查是否看起来像RSS URL
            if not result['url_info']['is_rss']:
                result['warnings'].append('URL路径不像典型的RSS源')
            
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f'URL验证异常: {str(e)}')
        
        return result
    
    def validate_rss_item_data(self, rss_item: RSSItem) -> Dict[str, Any]:
        """
        验证RSS条目数据完整性
        
        Args:
            rss_item: RSS条目对象
            
        Returns:
            验证结果字典
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'completeness_score': 0.0
        }
        
        try:
            score = 0.0
            total_fields = 7  # 总共评估的字段数
            
            # 必需字段验证
            if not rss_item.title or not rss_item.title.strip():
                result['errors'].append('标题为空')
            else:
                score += 1
                
            if not rss_item.link or not rss_item.link.strip():
                result['errors'].append('链接为空')
            elif not self.url_validator.is_valid_url(rss_item.link):
                result['errors'].append('链接格式无效')
            else:
                score += 1
                
            if not rss_item.description or not rss_item.description.strip():
                result['warnings'].append('描述为空')
            else:
                score += 1
            
            # 可选字段评估
            if rss_item.pub_date:
                score += 1
            else:
                result['warnings'].append('缺少发布时间')
                
            if rss_item.author:
                score += 1
            else:
                result['warnings'].append('缺少作者信息')
                
            if rss_item.category:
                score += 1
            else:
                result['warnings'].append('缺少分类信息')
                
            if rss_item.guid:
                score += 1
            else:
                result['warnings'].append('缺少唯一标识符')
                
            # 计算完整性分数
            result['completeness_score'] = score / total_fields
            
            # 内容质量检查
            if rss_item.title and len(rss_item.title) < 5:
                result['warnings'].append('标题过短')
            elif rss_item.title and len(rss_item.title) > 200:
                result['warnings'].append('标题过长')
                
            if rss_item.description and len(rss_item.description) > 1000:
                result['warnings'].append('描述过长')
            
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f'数据验证异常: {str(e)}')
        
        return result
    
    def validate_rss_feed_data(self, rss_feed: RSSFeed) -> Dict[str, Any]:
        """
        验证RSS源数据完整性
        
        Args:
            rss_feed: RSS源对象
            
        Returns:
            验证结果字典
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'item_validation_summary': {
                'total': 0,
                'valid': 0,
                'invalid': 0,
                'warnings': 0
            }
        }
        
        try:
            # 验证RSS源基本信息
            if not rss_feed.title or not rss_feed.title.strip():
                result['errors'].append('RSS源标题为空')
                
            if not rss_feed.link or not rss_feed.link.strip():
                result['errors'].append('RSS源链接为空')
            elif not self.url_validator.is_valid_url(rss_feed.link):
                result['warnings'].append('RSS源链接格式可能无效')
                
            if not rss_feed.description or not rss_feed.description.strip():
                result['warnings'].append('RSS源描述为空')
            
            # 验证条目
            result['item_validation_summary']['total'] = len(rss_feed.items)
            
            for item in rss_feed.items:
                item_result = self.validate_rss_item_data(item)
                
                if item_result['valid']:
                    result['item_validation_summary']['valid'] += 1
                else:
                    result['item_validation_summary']['invalid'] += 1
                    
                if item_result['warnings']:
                    result['item_validation_summary']['warnings'] += 1
            
            # 整体质量检查
            if len(rss_feed.items) == 0:
                result['warnings'].append('RSS源没有任何条目')
            elif len(rss_feed.items) > 200:
                result['warnings'].append('RSS源条目数量过多')
            
            # 检查重复条目
            links = [item.link for item in rss_feed.items if item.link]
            if len(links) != len(set(links)):
                result['warnings'].append('存在重复的条目链接')
            
            result['valid'] = (len(result['errors']) == 0 and 
                             result['item_validation_summary']['invalid'] == 0)
            
        except Exception as e:
            result['errors'].append(f'RSS源验证异常: {str(e)}')
        
        return result
    
    def check_feed_availability(self, feed_url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        检查RSS源可用性
        
        Args:
            feed_url: RSS源URL
            timeout: 超时时间
            
        Returns:
            可用性检查结果
        """
        result = {
            'available': False,
            'url': feed_url,
            'status_code': None,
            'response_time': None,
            'content_type': None,
            'error': None
        }
        
        try:
            import requests
            import time
            
            start_time = time.time()
            
            response = requests.head(
                feed_url,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    'User-Agent': 'TrendRadar RSS Validator/2.0',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*'
                }
            )
            
            response_time = time.time() - start_time
            
            result.update({
                'available': response.status_code == 200,
                'status_code': response.status_code,
                'response_time': round(response_time, 3),
                'content_type': response.headers.get('content-type', '')
            })
            
        except requests.exceptions.Timeout:
            result['error'] = '请求超时'
        except requests.exceptions.ConnectionError:
            result['error'] = '连接失败'
        except requests.exceptions.RequestException as e:
            result['error'] = f'请求异常: {str(e)}'
        except Exception as e:
            result['error'] = f'未知错误: {str(e)}'
        
        return result