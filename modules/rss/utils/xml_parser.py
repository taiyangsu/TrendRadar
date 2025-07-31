# coding=utf-8
"""
XML解析工具

提供通用的XML处理功能。
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Optional, Dict, Any, List
import re
import logging


class XMLParser:
    """XML解析工具类"""
    
    def __init__(self):
        """初始化XML解析器"""
        self.logger = logging.getLogger(__name__)
    
    def parse_xml_string(self, xml_content: str) -> Optional[ET.Element]:
        """
        解析XML字符串
        
        Args:
            xml_content: XML内容
            
        Returns:
            解析后的根元素，失败时返回None
        """
        try:
            # 清理XML内容
            xml_content = self._clean_xml_content(xml_content)
            
            # 解析XML
            root = ET.fromstring(xml_content)
            return root
            
        except ET.ParseError as e:
            self.logger.error(f"XML解析错误: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"XML解析异常: {str(e)}")
            return None
    
    def _clean_xml_content(self, xml_content: str) -> str:
        """清理XML内容"""
        if not xml_content:
            return ""
        
        # 移除BOM
        if xml_content.startswith('\ufeff'):
            xml_content = xml_content[1:]
        
        # 移除控制字符（保留制表符、换行符、回车符）
        xml_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_content)
        
        return xml_content.strip()
    
    def get_element_text(self, element: ET.Element, tag_name: str, 
                        default: str = "") -> str:
        """
        获取子元素的文本内容
        
        Args:
            element: 父元素
            tag_name: 子元素标签名
            default: 默认值
            
        Returns:
            子元素的文本内容
        """
        try:
            child = element.find(tag_name)
            if child is not None and child.text:
                return child.text.strip()
            return default
        except Exception:
            return default
    
    def get_element_attribute(self, element: ET.Element, attr_name: str,
                             default: str = "") -> str:
        """
        获取元素属性值
        
        Args:
            element: 元素
            attr_name: 属性名
            default: 默认值
            
        Returns:
            属性值
        """
        try:
            return element.get(attr_name, default)
        except Exception:
            return default
    
    def find_elements_by_tag(self, root: ET.Element, tag_name: str) -> List[ET.Element]:
        """
        查找所有指定标签的元素
        
        Args:
            root: 根元素
            tag_name: 标签名
            
        Returns:
            元素列表
        """
        try:
            return root.findall(f".//{tag_name}")
        except Exception:
            return []
    
    def element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """
        将XML元素转换为字典
        
        Args:
            element: XML元素
            
        Returns:
            字典表示
        """
        result = {}
        
        try:
            # 添加属性
            if element.attrib:
                result['@attributes'] = element.attrib
            
            # 添加文本内容
            if element.text and element.text.strip():
                result['@text'] = element.text.strip()
            
            # 添加子元素
            for child in element:
                child_dict = self.element_to_dict(child)
                
                if child.tag in result:
                    # 如果已存在同名子元素，转换为列表
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_dict)
                else:
                    result[child.tag] = child_dict
            
        except Exception as e:
            self.logger.warning(f"元素转字典失败: {str(e)}")
        
        return result
    
    def pretty_print_xml(self, xml_content: str) -> str:
        """
        格式化XML内容
        
        Args:
            xml_content: XML内容
            
        Returns:
            格式化后的XML内容
        """
        try:
            # 解析XML
            root = ET.fromstring(xml_content)
            
            # 格式化
            rough_string = ET.tostring(root, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            
            return reparsed.toprettyxml(indent="  ")
            
        except Exception as e:
            self.logger.warning(f"XML格式化失败: {str(e)}")
            return xml_content
    
    def validate_xml_structure(self, xml_content: str, 
                              required_elements: List[str]) -> bool:
        """
        验证XML结构是否包含必需元素
        
        Args:
            xml_content: XML内容
            required_elements: 必需元素列表
            
        Returns:
            True表示结构有效
        """
        try:
            root = self.parse_xml_string(xml_content)
            if not root:
                return False
            
            for element_path in required_elements:
                if not root.find(element_path):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def extract_cdata_content(self, xml_content: str) -> str:
        """
        提取CDATA内容
        
        Args:
            xml_content: 包含CDATA的XML内容
            
        Returns:
            CDATA内容
        """
        try:
            # 查找CDATA段
            cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'
            matches = re.findall(cdata_pattern, xml_content, re.DOTALL)
            
            if matches:
                return matches[0]
                
        except Exception as e:
            self.logger.warning(f"提取CDATA失败: {str(e)}")
        
        return ""
    
    def remove_namespaces(self, xml_content: str) -> str:
        """
        移除XML命名空间
        
        Args:
            xml_content: XML内容
            
        Returns:
            移除命名空间后的XML内容
        """
        try:
            # 移除命名空间声明
            xml_content = re.sub(r'\s*xmlns[^=]*="[^"]*"', '', xml_content)
            
            # 移除命名空间前缀
            xml_content = re.sub(r'<(\w+:)', r'<', xml_content)
            xml_content = re.sub(r'</(\w+:)', r'</', xml_content)
            
            return xml_content
            
        except Exception as e:
            self.logger.warning(f"移除命名空间失败: {str(e)}")
            return xml_content