# -*- coding: utf-8 -*-
"""
工具函数
"""
import socket
from typing import Optional


def get_local_ip() -> str:
    """
    获取本地IP地址
    
    Returns:
        本地IP地址字符串
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def check_module_available(module_name: str) -> bool:
    """
    检查模块是否可用
    
    Args:
        module_name: 模块名称
        
    Returns:
        模块是否可用
    """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def truncate_text(text: str, max_length: int = 30, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix