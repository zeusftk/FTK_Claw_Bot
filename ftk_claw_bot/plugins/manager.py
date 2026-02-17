import os
import importlib.util
from typing import Dict, List, Optional
from loguru import logger
from ftk_claw_bot.plugins.base import IPlugin


class PluginManager:
    """
    插件管理器
    负责插件的加载、注册和管理
    """
    
    def __init__(self):
        self._plugins: Dict[str, IPlugin] = {}
        self._plugin_paths: List[str] = []
    
    def register(self, plugin: IPlugin) -> bool:
        """
        注册插件
        
        Args:
            plugin: 插件实例
            
        Returns:
            bool: 注册是否成功
        """
        if not isinstance(plugin, IPlugin):
            logger.error(f"插件 {plugin} 不是 IPlugin 的实例")
            return False
        
        if plugin.name in self._plugins:
            logger.warning(f"插件 {plugin.name} 已存在，将被覆盖")
        
        self._plugins[plugin.name] = plugin
        logger.info(f"插件 {plugin.name} v{plugin.version} 注册成功")
        return True
    
    def unregister(self, plugin_name: str) -> bool:
        """
        注销插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 注销是否成功
        """
        if plugin_name not in self._plugins:
            logger.warning(f"插件 {plugin_name} 不存在")
            return False
        
        plugin = self._plugins[plugin_name]
        try:
            plugin.shutdown()
        except Exception as e:
            logger.error(f"关闭插件 {plugin_name} 时出错: {e}")
        
        del self._plugins[plugin_name]
        logger.info(f"插件 {plugin_name} 注销成功")
        return True
    
    def get(self, plugin_name: str) -> Optional[IPlugin]:
        """
        获取插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[IPlugin]: 插件实例，如果不存在返回 None
        """
        return self._plugins.get(plugin_name)
    
    def get_all(self) -> List[IPlugin]:
        """
        获取所有插件实例
        
        Returns:
            List[IPlugin]: 插件实例列表
        """
        return list(self._plugins.values())
    
    def get_plugin_info(self) -> List[Dict[str, str]]:
        """
        获取所有插件信息
        
        Returns:
            List[Dict[str, str]]: 插件信息列表
        """
        info_list = []
        for plugin in self._plugins.values():
            info_list.append({
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description
            })
        return info_list
    
    def add_plugin_path(self, path: str) -> bool:
        """
        添加插件搜索路径
        
        Args:
            path: 插件路径
            
        Returns:
            bool: 添加是否成功
        """
        if not os.path.isdir(path):
            logger.error(f"插件路径 {path} 不存在")
            return False
        
        if path not in self._plugin_paths:
            self._plugin_paths.append(path)
            logger.info(f"添加插件路径 {path} 成功")
        return True
    
    def load_from_dir(self, path: str) -> int:
        """
        从目录加载插件
        
        Args:
            path: 插件目录
            
        Returns:
            int: 加载的插件数量
        """
        if not os.path.isdir(path):
            logger.error(f"插件目录 {path} 不存在")
            return 0
        
        loaded_count = 0
        
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            # 跳过隐藏文件和目录
            if item.startswith('.'):
                continue
            
            # 如果是目录，检查是否包含 __init__.py
            if os.path.isdir(item_path):
                init_file = os.path.join(item_path, "__init__.py")
                if os.path.isfile(init_file):
                    loaded = self._load_plugin_from_file(init_file)
                    if loaded:
                        loaded_count += 1
            
            # 如果是 .py 文件，直接加载
            elif item.endswith('.py'):
                loaded = self._load_plugin_from_file(item_path)
                if loaded:
                    loaded_count += 1
        
        logger.info(f"从目录 {path} 加载了 {loaded_count} 个插件")
        return loaded_count
    
    def _load_plugin_from_file(self, file_path: str) -> bool:
        """
        从文件加载插件
        
        Args:
            file_path: 插件文件路径
            
        Returns:
            bool: 加载是否成功
        """
        try:
            # 获取模块名称
            module_name = os.path.basename(file_path).replace('.py', '')
            
            # 加载模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logger.error(f"无法加载插件文件 {file_path}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, IPlugin) and obj is not IPlugin:
                    # 创建插件实例
                    plugin_instance = obj()
                    # 注册插件
                    return self.register(plugin_instance)
            
            logger.warning(f"插件文件 {file_path} 中未找到 IPlugin 的子类")
            return False
            
        except Exception as e:
            logger.error(f"加载插件文件 {file_path} 时出错: {e}")
            return False
    
    def initialize_all(self, app) -> int:
        """
        初始化所有插件
        
        Args:
            app: 应用程序实例
            
        Returns:
            int: 初始化成功的插件数量
        """
        success_count = 0
        
        for plugin_name, plugin in self._plugins.items():
            try:
                if plugin.initialize(app):
                    success_count += 1
                    logger.info(f"插件 {plugin_name} 初始化成功")
                else:
                    logger.warning(f"插件 {plugin_name} 初始化失败")
            except Exception as e:
                logger.error(f"初始化插件 {plugin_name} 时出错: {e}")
        
        logger.info(f"初始化了 {success_count}/{len(self._plugins)} 个插件")
        return success_count
    
    def shutdown_all(self) -> int:
        """
        关闭所有插件
        
        Returns:
            int: 关闭成功的插件数量
        """
        success_count = 0
        
        for plugin_name, plugin in self._plugins.items():
            try:
                if plugin.shutdown():
                    success_count += 1
                    logger.info(f"插件 {plugin_name} 关闭成功")
                else:
                    logger.warning(f"插件 {plugin_name} 关闭失败")
            except Exception as e:
                logger.error(f"关闭插件 {plugin_name} 时出错: {e}")
        
        logger.info(f"关闭了 {success_count}/{len(self._plugins)} 个插件")
        return success_count
    
    def clear(self):
        """
        清空所有插件
        """
        self.shutdown_all()
        self._plugins.clear()
        logger.info("所有插件已清空")