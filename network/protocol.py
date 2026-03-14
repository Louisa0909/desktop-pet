# -*- coding: utf-8 -*-
"""
网络协议和消息构建
"""
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

import config


class MessageType(Enum):
    """消息类型枚举"""
    DISCOVERY = config.MSG_TYPE_DISCOVERY
    HEARTBEAT = config.MSG_TYPE_HEARTBEAT
    EMOTION = config.MSG_TYPE_EMOTION
    MESSAGE = config.MSG_TYPE_MESSAGE
    EXIT = config.MSG_TYPE_EXIT
    STATUS = config.MSG_TYPE_STATUS
    ANIMATION = config.MSG_TYPE_ANIMATION
    FOCUS_STATE = config.MSG_TYPE_FOCUS_STATE

@dataclass
class BaseMessage:
    """基础消息结构"""
    type: str
    sender_id: str
    sender_name: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMessage':
        return cls(**data)


@dataclass
class DiscoveryMessage(BaseMessage):
    """发现消息"""
    ip: str
    tcp_port: int
    character: str = "cat"
    
    @classmethod
    def create(cls, sender_id: str, sender_name: str, ip: str, tcp_port: int, character: str = "cat"):
        return cls(
            type=config.MSG_TYPE_DISCOVERY,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time(),
            ip=ip,
            tcp_port=tcp_port,
            character=character
        )


@dataclass
class HeartbeatMessage(BaseMessage):
    """心跳消息"""
    mood: str = "stand"  # 当前表情
    focus_state: str = "neutral"  # 当前专注状态
    focus_seconds: int = 0
    play_seconds: int = 0
    character: str = "cat"
    
    @classmethod
    def create(cls, sender_id: str, sender_name: str, 
               mood: str = "stand", focus_state: str = "neutral",
               focus_seconds: int = 0, play_seconds: int = 0,
               character: str = "cat"):
        return cls(
            type=config.MSG_TYPE_HEARTBEAT,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time(),
            mood=mood,
            focus_state=focus_state,
            focus_seconds=focus_seconds,
            play_seconds=play_seconds,
            character=character
        )


@dataclass
class EmotionMessage(BaseMessage):
    """表情消息"""
    emotion: str
    target_id: Optional[str] = None
    
    @classmethod
    def create(cls, sender_id: str, sender_name: str, emotion: str, target_id: str = None):
        return cls(
            type=config.MSG_TYPE_EMOTION,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time(),
            emotion=emotion,
            target_id=target_id
        )


@dataclass
class TextMessage(BaseMessage):
    """文本消息"""
    message: str
    target_id: Optional[str] = None
    
    @classmethod
    def create(cls, sender_id: str, sender_name: str, message: str, target_id: str = None):
        return cls(
            type=config.MSG_TYPE_MESSAGE,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time(),
            message=message,
            target_id=target_id
        )


@dataclass
class ExitMessage(BaseMessage):
    """退出消息"""
    @classmethod
    def create(cls, sender_id: str, sender_name: str):
        return cls(
            type=config.MSG_TYPE_EXIT,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time()
        )


@dataclass
class StatusMessage(BaseMessage):
    """状态同步消息"""
    mood: str  # 当前表情状态
    character: str = "cat"
    
    @classmethod
    def create(cls, sender_id: str, sender_name: str, mood: str, character: str = "cat"):
        return cls(
            type=config.MSG_TYPE_STATUS,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time(),
            mood=mood,
            character=character
        )


@dataclass
class AnimationMessage(BaseMessage):
    """动画同步消息"""
    target_mood: str
    stage_count: int
    character: str = "cat"
    
    @classmethod
    def create(cls, sender_id: str, sender_name: str, target_mood: str, stage_count: int, character: str = "cat"):
        return cls(
            type="animation",
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time(),
            target_mood=target_mood,
            stage_count=stage_count,
            character=character
        )


@dataclass
class FocusStateMessage(BaseMessage):
    """专注状态同步消息"""
    state: str  # "study", "entertainment", "neutral"
    focus_seconds: int = 0
    play_seconds: int = 0
    
    @classmethod
    def create(cls, sender_id: str, sender_name: str, state: str, 
               focus_seconds: int = 0, play_seconds: int = 0):
        return cls(
            type="focus_state",
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=time.time(),
            state=state,
            focus_seconds=focus_seconds,
            play_seconds=play_seconds
        )


class MessageBuilder:
    """消息构建器"""
    
    def __init__(self, sender_id: str, sender_name: str, character: str = "cat"):
        self._sender_id = sender_id
        self._sender_name = sender_name
        self._character = character
    
    def set_character(self, character: str):
        self._character = character
    
    def discovery(self, ip: str, tcp_port: int) -> DiscoveryMessage:
        return DiscoveryMessage.create(self._sender_id, self._sender_name, ip, tcp_port, self._character)
    
    def heartbeat(self) -> HeartbeatMessage:
        return HeartbeatMessage.create(self._sender_id, self._sender_name, character=self._character)
    
    def emotion(self, emotion: str, target_id: str = None) -> EmotionMessage:
        return EmotionMessage.create(self._sender_id, self._sender_name, emotion, target_id)
    
    def text(self, message: str, target_id: str = None) -> TextMessage:
        return TextMessage.create(self._sender_id, self._sender_name, message, target_id)
    
    def exit(self) -> ExitMessage:
        return ExitMessage.create(self._sender_id, self._sender_name)
    
    def status(self, mood: str) -> StatusMessage:
        return StatusMessage.create(self._sender_id, self._sender_name, mood, self._character)
    
    def animation(self, target_mood: str, stage_count: int) -> AnimationMessage:
        return AnimationMessage.create(self._sender_id, self._sender_name, target_mood, stage_count, self._character)
    
    def focus_state(self, state: str, focus_seconds: int = 0, play_seconds: int = 0) -> FocusStateMessage:
        return FocusStateMessage.create(
            self._sender_id, self._sender_name, state, focus_seconds, play_seconds
        )


def parse_message(data: bytes) -> Optional[Dict[str, Any]]:
    """解析消息"""
    try:
        return json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None