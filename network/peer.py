# -*- coding: utf-8 -*-
"""
对等节点类
"""
import time
from dataclasses import dataclass
from typing import Optional
import socket

import config


@dataclass
class Peer:
    """网络对等节点"""
    id: str
    name: str
    ip: str
    port: int
    last_seen: float
    connection: Optional[socket.socket] = None  # 字段名从 socket 改为 connection
    
    @property
    def is_online(self) -> bool:
        """检查是否在线（根据最后活跃时间）"""
        timeout = config.HEARTBEAT_INTERVAL * config.PEER_TIMEOUT_MULTIPLIER
        return time.time() - self.last_seen < timeout
    
    @property
    def address(self) -> tuple:
        """获取地址元组"""
        return (self.ip, self.port)
    
    def update_last_seen(self):
        """更新最后活跃时间"""
        self.last_seen = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "ip": self.ip,
            "last_seen": self.last_seen
        }