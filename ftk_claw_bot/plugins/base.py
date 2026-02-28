# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class IPlugin(ABC):
    """
    插件接口
    所有插件必须实现此接口
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        插件名称
        """
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """
        插件版本
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        插件描述
        """
        pass
    
    @abstractmethod
    def initialize(self, app: "Application") -> bool:
        """
        初始化插件
        
        Args:
            app: 应用程序实例
            
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        关闭插件
        
        Returns:
            bool: 关闭是否成功
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取插件配置
        
        Returns:
            Dict[str, Any]: 插件配置
        """
        return {}
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        设置插件配置
        
        Args:
            config: 插件配置
            
        Returns:
            bool: 设置是否成功
        """
        return True
    
    def on_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        处理事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        pass