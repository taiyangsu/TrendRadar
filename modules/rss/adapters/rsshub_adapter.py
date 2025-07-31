# coding=utf-8
"""
RSSHub适配器

专门处理RSSHub服务的URL构建、路由验证和参数处理。
"""

from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlencode
import logging
from ..utils.url_validator import URLValidator


class RSSHubAdapter:
    """RSSHub专用适配器"""
    
    def __init__(self, base_url: str = "https://rsshub.app"):
        """
        初始化RSSHub适配器
        
        Args:
            base_url: RSSHub服务的基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logging.getLogger(__name__)
        self.url_validator = URLValidator()
        
        # 用户代理
        self.user_agent = "TrendRadar RSSHub Adapter/2.0"
        
        # 常用的RSSHub路由模板
        self.route_templates = {
            # 社交媒体
            'weibo_hot': '/weibo/search/hot',
            'weibo_user': '/weibo/user/{uid}',
            'zhihu_hotlist': '/zhihu/hotlist',
            'zhihu_daily': '/zhihu/daily',
            'zhihu_user': '/zhihu/people/activities/{id}',
            'douyin_hot': '/douyin/hot',
            'bilibili_hot': '/bilibili/hot-search',
            'bilibili_user': '/bilibili/user/dynamic/{uid}',
            
            # 新闻媒体
            'techcrunch': '/techcrunch/cn',
            '36kr': '/36kr/news',
            'ithome': '/ithome/news',
            'cnbeta': '/cnbeta',
            'pingwest': '/pingwest',
            
            # 技术平台
            'github_trending': '/github/trending/{period}/{language}',
            'github_user': '/github/user/followers/{user}',
            'stackoverflow': '/stackoverflow/top/{period}',
            'juejin': '/juejin/trending/{category}/{type}',
            'v2ex': '/v2ex/topics/{type}',
            
            # 财经
            'wallstreetcn': '/wallstreetcn/news/global',
            'cls': '/cls/telegraph',
            'xueqiu': '/xueqiu/user/{id}',
            
            # 其他
            'youtube': '/youtube/user/{id}',
            'twitter': '/twitter/user/{id}',
            'instagram': '/instagram/user/{id}',
        }
        
        # 默认参数
        self.default_params = {
            'limit': 20,  # 默认条目数量限制
        }
    
    def build_url(self, route: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        构建RSSHub URL
        
        Args:
            route: RSS路由路径
            params: 查询参数
            
        Returns:
            完整的RSSHub URL
        """
        try:
            # 确保路由以/开头
            if not route.startswith('/'):
                route = '/' + route
            
            # 构建基础URL
            url = urljoin(self.base_url, route)
            
            # 添加查询参数
            if params:
                # 合并默认参数
                merged_params = {**self.default_params, **params}
                # 过滤None值
                filtered_params = {k: v for k, v in merged_params.items() if v is not None}
                
                if filtered_params:
                    query_string = urlencode(filtered_params)
                    url += f"?{query_string}"
            
            return url
            
        except Exception as e:
            self.logger.error(f"构建RSSHub URL失败: {route}, 错误: {str(e)}")
            return f"{self.base_url}{route}"
    
    def build_template_url(self, template_name: str, 
                          template_vars: Optional[Dict[str, str]] = None,
                          params: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        使用模板构建RSSHub URL
        
        Args:
            template_name: 模板名称
            template_vars: 模板变量
            params: 查询参数
            
        Returns:
            构建的URL，失败时返回None
        """
        try:
            if template_name not in self.route_templates:
                self.logger.error(f"未知的路由模板: {template_name}")
                return None
            
            route_template = self.route_templates[template_name]
            
            # 替换模板变量
            if template_vars:
                route = route_template.format(**template_vars)
            else:
                route = route_template
            
            return self.build_url(route, params)
            
        except KeyError as e:
            self.logger.error(f"模板变量缺失: {template_name}, 缺失变量: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"模板URL构建失败: {template_name}, 错误: {str(e)}")
            return None
    
    def validate_route(self, route: str) -> bool:
        """
        验证RSSHub路由是否有效
        
        Args:
            route: 路由路径
            
        Returns:
            True表示路由格式有效
        """
        try:
            if not route:
                return False
            
            # 确保以/开头
            if not route.startswith('/'):
                route = '/' + route
            
            # 基本格式检查
            if '//' in route or route.endswith('/'):
                return False
            
            # 构建完整URL并验证
            full_url = urljoin(self.base_url, route)
            return self.url_validator.is_valid_url(full_url)
            
        except Exception:
            return False
    
    def get_popular_routes(self) -> Dict[str, Dict[str, Any]]:
        """
        获取热门路由配置
        
        Returns:
            热门路由配置字典
        """
        return {
            # 热搜类
            'weibo_hot': {
                'name': '微博热搜',
                'route': '/weibo/search/hot',
                'category': 'social',
                'description': '微博实时热搜榜'
            },
            'zhihu_hotlist': {
                'name': '知乎热榜',
                'route': '/zhihu/hotlist',
                'category': 'social',
                'description': '知乎热门内容排行榜'
            },
            'douyin_hot': {
                'name': '抖音热点',
                'route': '/douyin/hot',
                'category': 'social',
                'description': '抖音热门视频'
            },
            'bilibili_hot': {
                'name': 'B站热搜',
                'route': '/bilibili/hot-search',
                'category': 'social',
                'description': 'B站实时热搜'
            },
            
            # 科技新闻
            'github_trending': {
                'name': 'GitHub趋势',
                'route': '/github/trending/daily',
                'category': 'technology',
                'description': 'GitHub每日趋势项目'
            },
            'techcrunch_cn': {
                'name': 'TechCrunch中文',
                'route': '/techcrunch/cn',
                'category': 'technology',
                'description': 'TechCrunch中文版新闻'
            },
            '36kr': {
                'name': '36氪',
                'route': '/36kr/news',
                'category': 'technology',
                'description': '36氪科技新闻'
            },
            'ithome': {
                'name': 'IT之家',
                'route': '/ithome/news',
                'category': 'technology',
                'description': 'IT之家科技资讯'
            },
            
            # 财经
            'wallstreetcn': {
                'name': '华尔街见闻',
                'route': '/wallstreetcn/news/global',
                'category': 'finance',
                'description': '华尔街见闻全球资讯'
            },
            'cls': {
                'name': '财联社',
                'route': '/cls/telegraph',
                'category': 'finance',
                'description': '财联社快讯'
            }
        }
    
    def create_feed_configs(self, routes: List[str]) -> List[Dict[str, Any]]:
        """
        根据路由列表创建RSS源配置
        
        Args:
            routes: 路由列表
            
        Returns:
            RSS源配置列表
        """
        configs = []
        popular_routes = self.get_popular_routes()
        
        for i, route in enumerate(routes, 1):
            # 查找匹配的热门路由
            route_info = None
            for route_key, info in popular_routes.items():
                if info['route'] == route:
                    route_info = info
                    break
            
            # 生成配置
            if route_info:
                config = {
                    'id': f"rsshub_{route_key}",
                    'name': route_info['name'],
                    'url': self.build_url(route),
                    'category': route_info['category'],
                    'enabled': True,
                    'priority': i,
                    'description': route_info['description']
                }
            else:
                # 通用配置
                route_name = route.strip('/').replace('/', '_')
                config = {
                    'id': f"rsshub_{route_name}",
                    'name': f"RSSHub {route_name}",
                    'url': self.build_url(route),
                    'category': 'general',
                    'enabled': True,
                    'priority': i,
                    'description': f"RSSHub路由: {route}"
                }
            
            configs.append(config)
        
        return configs
    
    def get_custom_headers(self) -> Dict[str, str]:
        """
        获取RSSHub请求的自定义请求头
        
        Returns:
            自定义请求头字典
        """
        return {
            'User-Agent': self.user_agent,
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache'
        }
    
    def parse_rsshub_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        解析RSSHub URL，提取路由和参数信息
        
        Args:
            url: RSSHub URL
            
        Returns:
            包含路由信息的字典，失败时返回None
        """
        try:
            if not self.url_validator.validate_rsshub_url(url):
                return None
            
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(url)
            
            # 提取路由路径
            route = parsed.path
            if not route or route == '/':
                return None
            
            # 解析查询参数
            params = {}
            if parsed.query:
                params = {k: v[0] if len(v) == 1 else v 
                         for k, v in parse_qs(parsed.query).items()}
            
            return {
                'base_url': f"{parsed.scheme}://{parsed.netloc}",
                'route': route,
                'params': params,
                'full_url': url
            }
            
        except Exception as e:
            self.logger.error(f"解析RSSHub URL失败: {url}, 错误: {str(e)}")
            return None
    
    def suggest_routes_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        根据关键词推荐相关路由
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            推荐的路由列表
        """
        suggestions = []
        popular_routes = self.get_popular_routes()
        
        keyword_lower = keyword.lower()
        
        for route_key, info in popular_routes.items():
            # 检查名称、描述和路由是否包含关键词
            searchable_text = f"{info['name']} {info['description']} {info['route']}".lower()
            
            if keyword_lower in searchable_text:
                suggestion = {
                    'route_key': route_key,
                    'name': info['name'],
                    'route': info['route'],
                    'url': self.build_url(info['route']),
                    'category': info['category'],
                    'description': info['description']
                }
                suggestions.append(suggestion)
        
        # 按相关性排序（简单的字符串匹配计分）
        def relevance_score(item):
            name_score = 2 if keyword_lower in item['name'].lower() else 0
            desc_score = 1 if keyword_lower in item['description'].lower() else 0
            return name_score + desc_score
        
        suggestions.sort(key=relevance_score, reverse=True)
        
        return suggestions
    
    def test_route_availability(self, route: str) -> Dict[str, Any]:
        """
        测试路由可用性
        
        Args:
            route: 路由路径
            
        Returns:
            测试结果字典
        """
        result = {
            'route': route,
            'valid': False,
            'url': '',
            'error': None
        }
        
        try:
            if not self.validate_route(route):
                result['error'] = '路由格式无效'
                return result
            
            url = self.build_url(route)
            result['url'] = url
            
            # 这里可以添加实际的HTTP请求测试
            # 为了避免在初始化时发起网络请求，暂时只做格式验证
            result['valid'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result