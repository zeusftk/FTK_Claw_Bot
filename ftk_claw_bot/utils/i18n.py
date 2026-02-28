# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, Optional, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal


def _debug_log(msg: str):
    """调试日志"""
    try:
        print(f"[DEBUG] {msg}")
        from loguru import logger
        logger.info(msg)
    except Exception:
        pass


from ..constants import Language


class I18nSignals(QObject):
    """分离信号类，避免 QObject 初始化问题"""
    language_changed = pyqtSignal()


class I18nManager:
    """国际化管理器 - 不继承 QObject，使用分离的信号对象"""
    
    _signals: Optional[I18nSignals] = None
    _translations: Dict[str, str] = {}
    _current_locale: str = Language.DEFAULT
    _callbacks: List[Callable] = []
    
    @classmethod
    def _get_signals(cls) -> I18nSignals:
        """获取信号对象，延迟初始化"""
        if cls._signals is None:
            _debug_log("[I18nManager._get_signals] 创建信号对象...")
            cls._signals = I18nSignals()
            _debug_log("[I18nManager._get_signals] 信号对象创建完成")
        return cls._signals
    
    @classmethod
    def get_instance(cls) -> 'I18nManager':
        """获取管理器实例（兼容旧代码）"""
        return cls
    
    @classmethod
    def initialize(cls, locale: str = None):
        if locale is None:
            locale = Language.DEFAULT
        cls.load_locale(locale)
    
    @classmethod
    def load_locale(cls, locale: str):
        _debug_log(f"[I18nManager.load_locale] 开始加载语言: {locale}")
        if locale not in Language.SUPPORTED:
            _debug_log(f"[I18nManager.load_locale] 语言不在支持列表中，使用默认语言")
            locale = Language.DEFAULT
        
        translations_dir = Path(__file__).parent.parent / "translations"
        _debug_log(f"[I18nManager.load_locale] 翻译目录路径: {translations_dir}")
        _debug_log(f"[I18nManager.load_locale] 翻译目录存在: {translations_dir.exists()}")
        
        lang_file = translations_dir / f"{locale}.json"
        _debug_log(f"[I18nManager.load_locale] 语言文件路径: {lang_file}")
        _debug_log(f"[I18nManager.load_locale] 语言文件存在: {lang_file.exists()}")
        
        if lang_file.exists():
            try:
                _debug_log(f"[I18nManager.load_locale] 正在读取语言文件...")
                with open(lang_file, "r", encoding="utf-8") as f:
                    cls._translations = json.load(f)
                cls._current_locale = locale
                _debug_log(f"[I18nManager.load_locale] 语言文件加载成功，翻译条目数: {len(cls._translations)}")
            except (json.JSONDecodeError, IOError) as e:
                _debug_log(f"[I18nManager.load_locale] 语言文件加载失败: {e}")
                cls._translations = {}
                cls._current_locale = Language.DEFAULT
        else:
            _debug_log(f"[I18nManager.load_locale] 语言文件不存在，使用空翻译")
            cls._translations = {}
            cls._current_locale = Language.DEFAULT
        
        _debug_log(f"[I18nManager.load_locale] 发送语言变更信号...")
        cls._get_signals().language_changed.emit()
        for callback in cls._callbacks:
            try:
                callback()
            except Exception:
                pass
        _debug_log(f"[I18nManager.load_locale] 完成")
    
    @classmethod
    def tr(cls, key: str, default: str = None) -> str:
        if default is None:
            default = key
        return cls._translations.get(key, default)
    
    @classmethod
    def get_current_locale(cls) -> str:
        return cls._current_locale
    
    @classmethod
    def get_supported_locales(cls) -> Dict[str, str]:
        return Language.SUPPORTED.copy()
    
    @classmethod
    def register_callback(cls, callback: Callable):
        if callback not in cls._callbacks:
            cls._callbacks.append(callback)
    
    @classmethod
    def unregister_callback(cls, callback: Callable):
        if callback in cls._callbacks:
            cls._callbacks.remove(callback)


def tr(key: str, default: str = None) -> str:
    return I18nManager.tr(key, default)
