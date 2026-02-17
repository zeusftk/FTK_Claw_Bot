from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
import json


class CommandType(Enum):
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_SCROLL = "mouse_scroll"
    KEYBOARD_TYPE = "keyboard_type"
    KEYBOARD_PRESS = "keyboard_press"
    KEYBOARD_HOTKEY = "keyboard_hotkey"
    SCREENSHOT = "screenshot"
    FIND_WINDOW = "find_window"
    LAUNCH_APP = "launch_app"
    GET_CLIPBOARD = "get_clipboard"
    SET_CLIPBOARD = "set_clipboard"
    GET_SCREEN_SIZE = "get_screen_size"
    GET_MOUSE_POSITION = "get_mouse_position"


@dataclass
class BridgeRequest:
    command: CommandType
    params: Dict[str, Any]
    request_id: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "command": self.command.value,
            "params": self.params,
            "request_id": self.request_id
        })

    @classmethod
    def from_json(cls, json_str: str) -> "BridgeRequest":
        data = json.loads(json_str)
        return cls(
            command=CommandType(data["command"]),
            params=data.get("params", {}),
            request_id=data.get("request_id", "")
        )


@dataclass
class BridgeResponse:
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    request_id: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "request_id": self.request_id
        })

    @classmethod
    def from_json(cls, json_str: str) -> "BridgeResponse":
        data = json.loads(json_str)
        return cls(
            success=data.get("success", False),
            result=data.get("result"),
            error=data.get("error"),
            request_id=data.get("request_id", "")
        )
