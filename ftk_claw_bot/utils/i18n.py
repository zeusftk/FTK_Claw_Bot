import json
from pathlib import Path
from typing import Dict, Optional, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal

from ..constants import Language


class I18nManager(QObject):
    language_changed = pyqtSignal()
    
    _instance: Optional['I18nManager'] = None
    _translations: Dict[str, str] = {}
    _current_locale: str = Language.DEFAULT
    _callbacks: List[Callable] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance
    
    @classmethod
    def initialize(cls, locale: str = None):
        if locale is None:
            locale = Language.DEFAULT
        cls.load_locale(locale)
    
    @classmethod
    def load_locale(cls, locale: str):
        if locale not in Language.SUPPORTED:
            locale = Language.DEFAULT
        
        translations_dir = Path(__file__).parent.parent / "translations"
        lang_file = translations_dir / f"{locale}.json"
        
        if lang_file.exists():
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    cls._translations = json.load(f)
                cls._current_locale = locale
            except (json.JSONDecodeError, IOError):
                cls._translations = {}
                cls._current_locale = Language.DEFAULT
        else:
            cls._translations = {}
            cls._current_locale = Language.DEFAULT
        
        if cls._instance:
            cls._instance.language_changed.emit()
            for callback in cls._callbacks:
                try:
                    callback()
                except Exception:
                    pass
    
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
