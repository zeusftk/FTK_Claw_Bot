# -*- coding: utf-8 -*-
import base64
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

from loguru import logger

BUTTON_KEYWORDS = ["确定", "取消", "提交", "登录", "确认", "关闭", 
                   "删除", "保存", "下一步", "上一步", "注册", "退出",
                   "OK", "Cancel", "Submit", "Login", "Confirm", "Close",
                   "Delete", "Save", "Next", "Back", "Register", "Exit"]

INPUT_KEYWORDS = ["用户名", "账号", "密码", "邮箱", "手机", 
                  "电话", "输入", "搜索", "查询",
                  "Username", "Account", "Password", "Email", "Phone",
                  "Input", "Search", "Query"]


@dataclass
class OCRElement:
    text: str
    bbox: List[int]
    confidence: float
    action_type: str
    hint: str


class OCRProvider(ABC):
    """OCR 提供商抽象基类"""
    
    @abstractmethod
    def recognize(self, image_data: bytes) -> List[dict]:
        """
        识别图片中的文字
        
        Args:
            image_data: PNG 格式的图片数据
        
        Returns:
            识别结果列表，每个元素包含:
            - text: 识别的文字
            - bbox: [x1, y1, x2, y2] 边界框
            - confidence: 置信度 (0.0 - 1.0)
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """提供商名称"""
        pass
    
    @property
    def is_available(self) -> bool:
        """检查提供商是否可用"""
        return True


class MockOCRProvider(OCRProvider):
    """Mock OCR 提供商（用于测试）"""
    
    @property
    def name(self) -> str:
        return "mock"
    
    def recognize(self, image_data: bytes) -> List[dict]:
        logger.warning("[MockOCR] OCR not implemented, returning empty result")
        return []


class GLMOCRProvider(OCRProvider):
    """GLM OCR 提供商（预留接口）"""
    
    def __init__(self, api_key: str = None, api_base: str = None):
        self._api_key = api_key
        self._api_base = api_base or "https://open.bigmodel.cn/api/paas/v4"
    
    @property
    def name(self) -> str:
        return "glm_ocr"
    
    @property
    def is_available(self) -> bool:
        return bool(self._api_key)
    
    def recognize(self, image_data: bytes) -> List[dict]:
        if not self.is_available:
            logger.warning("[GLM OCR] API key not configured")
            return []
        
        # TODO: 实现 GLM OCR API 调用
        # 1. 将 image_data 编码为 base64
        # 2. 调用 GLM OCR API
        # 3. 解析返回结果，转换为标准格式
        
        logger.info("[GLM OCR] OCR recognition not yet implemented")
        return []


class DeepSeekOCRProvider(OCRProvider):
    """DeepSeek OCR2 提供商（预留接口）"""
    
    def __init__(self, api_key: str = None, api_base: str = None):
        self._api_key = api_key
        self._api_base = api_base or "https://api.deepseek.com/v1"
    
    @property
    def name(self) -> str:
        return "deepseek_ocr"
    
    @property
    def is_available(self) -> bool:
        return bool(self._api_key)
    
    def recognize(self, image_data: bytes) -> List[dict]:
        if not self.is_available:
            logger.warning("[DeepSeek OCR] API key not configured")
            return []
        
        # TODO: 实现 DeepSeek OCR2 API 调用
        # 1. 将 image_data 编码为 base64
        # 2. 调用 DeepSeek OCR API
        # 3. 解析返回结果，转换为标准格式
        
        logger.info("[DeepSeek OCR] OCR recognition not yet implemented")
        return []


class OCRAutomation:
    """OCR 自动化模块"""
    MIN_CONFIDENCE = 0.7
    
    def __init__(self, provider: str = "mock", config: dict = None):
        self._config = config or {}
        self._provider: OCRProvider = None
        self._init_provider(provider)
    
    def _init_provider(self, provider: str):
        """初始化 OCR 提供商"""
        providers = {
            "mock": MockOCRProvider,
            "glm": GLMOCRProvider,
            "glm_ocr": GLMOCRProvider,
            "deepseek": DeepSeekOCRProvider,
            "deepseek_ocr": DeepSeekOCRProvider,
        }
        
        provider_class = providers.get(provider.lower(), MockOCRProvider)
        
        if provider_class in (GLMOCRProvider, DeepSeekOCRProvider):
            api_key = self._config.get("api_key") or self._config.get(f"{provider}_api_key")
            api_base = self._config.get("api_base") or self._config.get(f"{provider}_api_base")
            self._provider = provider_class(api_key=api_key, api_base=api_base)
        else:
            self._provider = provider_class()
        
        logger.info(f"[OCRAutomation] Initialized with provider: {self._provider.name}")
    
    def set_provider(self, provider: str, config: dict = None):
        """动态切换 OCR 提供商"""
        if config:
            self._config.update(config)
        self._init_provider(provider)
    
    @property
    def is_available(self) -> bool:
        return self._provider is not None and self._provider.is_available
    
    @property
    def provider_name(self) -> str:
        return self._provider.name if self._provider else "none"
    
    def screenshot_ocr(self, image_data: bytes = None, region: Tuple[int, int, int, int] = None) -> dict:
        """
        截图并执行 OCR 识别
        
        Args:
            image_data: 可选的图片数据，如果不提供则自动截图
            region: 截图区域 [x, y, width, height]
        
        Returns:
            {
                "success": bool,
                "elements": List[dict],  # 可交互元素列表
                "summary": dict,         # 统计信息
                "error": str             # 错误信息（如果失败）
            }
        """
        try:
            if image_data is None:
                image_data = self._capture_screenshot(region)
            
            if image_data is None:
                return {"success": False, "error": "screenshot_failed", 
                        "message": "Failed to capture screenshot"}
            
            ocr_results = self._perform_ocr(image_data)
            
            elements = self._process_ocr_results(ocr_results)
            
            return {
                "success": True,
                "elements": [self._element_to_dict(e) for e in elements],
                "summary": {
                    "total": len(elements),
                    "clickable": sum(1 for e in elements if e.action_type == "click"),
                    "inputable": sum(1 for e in elements if e.action_type == "input")
                },
                "provider": self.provider_name
            }
        except Exception as e:
            logger.error(f"[OCRAutomation] OCR failed: {e}")
            return {"success": False, "error": "ocr_failed", "message": str(e)}
    
    def _capture_screenshot(self, region: Tuple[int, int, int, int] = None) -> Optional[bytes]:
        """截取屏幕截图"""
        try:
            import pyautogui
            from PIL import Image
            
            if region:
                img = pyautogui.screenshot(region=region)
            else:
                img = pyautogui.screenshot()
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"[OCRAutomation] Screenshot failed: {e}")
            return None
    
    def _perform_ocr(self, image_data: bytes) -> List[dict]:
        """调用 OCR 提供商进行识别"""
        if self._provider is None:
            logger.warning("[OCRAutomation] No OCR provider configured")
            return []
        
        return self._provider.recognize(image_data)
    
    def _process_ocr_results(self, ocr_results: List[dict]) -> List[OCRElement]:
        """处理 OCR 结果，提取可交互元素"""
        elements = []
        
        for result in ocr_results:
            text = result.get("text", "")
            bbox = result.get("bbox", [0, 0, 0, 0])
            confidence = result.get("confidence", 0.0)
            
            if confidence < self.MIN_CONFIDENCE:
                continue
            
            action_type = self._determine_action_type(text)
            if action_type == "none":
                continue
            
            hint = self._generate_hint(text, action_type)
            
            elements.append(OCRElement(
                text=text,
                bbox=bbox,
                confidence=confidence,
                action_type=action_type,
                hint=hint
            ))
        
        return elements
    
    def _determine_action_type(self, text: str) -> str:
        """根据文字内容判断操作类型"""
        text_lower = text.lower()
        
        for keyword in BUTTON_KEYWORDS:
            if keyword.lower() in text_lower:
                return "click"
        
        for keyword in INPUT_KEYWORDS:
            if keyword.lower() in text_lower:
                return "input"
        
        return "none"
    
    def _generate_hint(self, text: str, action_type: str) -> str:
        """生成操作提示"""
        if action_type == "click":
            return f"点击「{text}」按钮"
        elif action_type == "input":
            return f"在「{text}」输入框输入"
        return ""
    
    def _element_to_dict(self, element: OCRElement) -> dict:
        """将元素转换为字典"""
        return {
            "text": element.text,
            "bbox": element.bbox,
            "confidence": element.confidence,
            "action_type": element.action_type,
            "hint": element.hint
        }
    
    def click_text(self, text: str, screenshot_data: bytes = None) -> dict:
        """根据文字点击屏幕元素"""
        result = self.screenshot_ocr(screenshot_data)
        
        if not result.get("success"):
            return result
        
        for element in result.get("elements", []):
            if text in element.get("text", ""):
                bbox = element.get("bbox", [])
                if len(bbox) == 4:
                    center_x = (bbox[0] + bbox[2]) // 2
                    center_y = (bbox[1] + bbox[3]) // 2
                    
                    try:
                        import pyautogui
                        pyautogui.click(center_x, center_y)
                        return {"success": True, "clicked": text, 
                                "position": [center_x, center_y]}
                    except Exception as e:
                        return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "text_not_found", 
                "message": f"Text '{text}' not found on screen"}
    
    def input_text(self, text: str, value: str, screenshot_data: bytes = None) -> dict:
        """根据文字定位输入框并输入内容"""
        result = self.screenshot_ocr(screenshot_data)
        
        if not result.get("success"):
            return result
        
        for element in result.get("elements", []):
            if text in element.get("text", "") and element.get("action_type") == "input":
                bbox = element.get("bbox", [])
                if len(bbox) == 4:
                    center_x = (bbox[0] + bbox[2]) // 2
                    center_y = (bbox[1] + bbox[3]) // 2
                    
                    try:
                        import pyautogui
                        pyautogui.click(center_x, center_y)
                        pyautogui.write(value)
                        return {"success": True, "input_at": text, "value": value}
                    except Exception as e:
                        return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "input_field_not_found",
                "message": f"Input field '{text}' not found on screen"}
    
    def get_screenshot_base64(self, region: Tuple[int, int, int, int] = None) -> Optional[str]:
        """获取截图的 base64 编码（供外部 OCR 服务使用）"""
        image_data = self._capture_screenshot(region)
        if image_data:
            return base64.b64encode(image_data).decode("utf-8")
        return None
