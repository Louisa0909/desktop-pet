# -*- coding: utf-8 -*-
"""
网络管理器 - 修复版
"""
import socket
import threading
import time
from typing import Dict, Set, Optional
from PyQt5.QtCore import QObject, pyqtSignal

from .peer import Peer
from .protocol import MessageBuilder, parse_message
from utils.helpers import get_local_ip
import config


class NetworkManager(QObject):
    """网络管理器"""
    
    peer_discovered = pyqtSignal(dict)
    peer_lost = pyqtSignal(dict)
    emotion_received = pyqtSignal(dict)
    message_received = pyqtSignal(dict)
    status_received = pyqtSignal(dict)
    animation_received = pyqtSignal(dict)
    focus_state_received = pyqtSignal(dict)
    connection_established = pyqtSignal(str)  # peer_id
    
    def __init__(self, pet_name: str, pet_id: str, character: str = "cat"):
        super().__init__()
        
        self._pet_name = pet_name
        self._pet_id = pet_id
        self._local_ip = get_local_ip()
        
        self._udp_port = config.DISCOVERY_PORT
        self._tcp_port = config.NETWORK_PORT
        
        self._message_builder = MessageBuilder(pet_id, pet_name, character)
        
        self._peers: Dict[str, Peer] = {}
        self._connections: Dict[str, socket.socket] = {}  # 独立管理连接
        self._lock = threading.RLock()
        
        self._running = False
        self._threads = []
        
        # 记录已建立连接的节点，避免重复连接
        self._connecting_peers: Set[str] = set()
    
    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._connections)
    
    def set_character(self, character: str):
        """更新当前角色类型"""
        self._message_builder.set_character(character)
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        
        # UDP 发现服务
        udp_thread = threading.Thread(target=self._udp_discovery_service, daemon=True)
        udp_thread.start()
        self._threads.append(udp_thread)
        
        # TCP 服务器
        tcp_thread = threading.Thread(target=self._tcp_server, daemon=True)
        tcp_thread.start()
        self._threads.append(tcp_thread)
        
        # 心跳服务
        heartbeat_thread = threading.Thread(target=self._heartbeat_service, daemon=True)
        heartbeat_thread.start()
        self._threads.append(heartbeat_thread)
        
        print(f"[网络] 已启动 - ID: {self._pet_id}, IP: {self._local_ip}")
    
    def stop(self):
        if not self._running:
            return
        
        self._running = False
        
        # 发送退出广播（UDP）
        self._send_exit_broadcast()
        
        time.sleep(0.2)
        
        # 关闭所有连接
        with self._lock:
            for conn in self._connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
            self._peers.clear()
            self._connecting_peers.clear()
        
        print("[网络] 已停止")
    
    def send_emotion(self, emotion: str, target_id: str = None):
        msg = self._message_builder.emotion(emotion, target_id)
        if target_id:
            self._send_to_peer(target_id, msg.to_json())
        else:
            self._broadcast_message(msg.to_json())
        print(f"[网络] 发送表情: {emotion} -> {target_id or '所有人'}")
    
    def send_message(self, text: str, target_id: str = None):
        msg = self._message_builder.text(text, target_id)
        if target_id:
            self._send_to_peer(target_id, msg.to_json())
        else:
            self._broadcast_message(msg.to_json())
        print(f"[网络] 发送消息: {text[:20]}... -> {target_id or '所有人'}")
    
    def broadcast_status(self, mood: str):
        msg = self._message_builder.status(mood)
        self._broadcast_message(msg.to_json())
    
    def broadcast_animation(self, target_mood: str, stage_count: int):
        """广播动画状态"""
        msg = self._message_builder.animation(target_mood, stage_count)
        self._broadcast_message(msg.to_json())
    
    def broadcast_focus_state(self, state: str, focus_seconds: int = 0, play_seconds: int = 0):
        """广播专注状态"""
        msg = self._message_builder.focus_state(state, focus_seconds, play_seconds)
        self._broadcast_message(msg.to_json())
    
    # ==================== UDP 发现服务 ====================
    
    def _udp_discovery_service(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('', self._udp_port))
        udp_socket.settimeout(1.0)
        
        while self._running:
            try:
                try:
                    data, addr = udp_socket.recvfrom(1024)
                    self._handle_udp_data(data, addr[0])
                except socket.timeout:
                    pass
                
                # 只有在运行时才发送广播
                if self._running:
                    self._send_discovery_broadcast(udp_socket)
                    time.sleep(config.DISCOVERY_INTERVAL)
                
            except Exception as e:
                if self._running:
                    print(f"[UDP错误] {e}")
        
        udp_socket.close()
    
    def _send_discovery_broadcast(self, udp_socket: socket.socket):
        msg = self._message_builder.discovery(self._local_ip, self._tcp_port)
        try:
            udp_socket.sendto(
                msg.to_json().encode('utf-8'),
                ('<broadcast>', self._udp_port)
            )
        except Exception as e:
            print(f"[广播失败] {e}")
    
    def _send_exit_broadcast(self):
        """发送退出广播"""
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = self._message_builder.exit()
            udp_socket.sendto(
                msg.to_json().encode('utf-8'),
                ('<broadcast>', self._udp_port)
            )
            udp_socket.close()
            print("[网络] 已发送退出广播")
        except Exception as e:
            print(f"[退出广播失败] {e}")
    
    def _handle_udp_data(self, data: bytes, ip: str):
        msg = parse_message(data)
        if not msg:
            return
        
        sender_id = msg.get("sender_id")
        if sender_id == self._pet_id:
            return
        
        msg_type = msg.get("type")
        
        # 处理退出消息
        if msg_type == config.MSG_TYPE_EXIT:
            self._handle_peer_exit_udp(msg)
            return
        
        # 处理发现消息
        if msg_type == config.MSG_TYPE_DISCOVERY:
            self._handle_discovery(msg, ip)
    
    def _handle_peer_exit_udp(self, msg: dict):
        """通过 UDP 收到退出消息"""
        peer_id = msg.get("sender_id")
        peer_name = msg.get("sender_name", "未知用户")
        
        print(f"[网络] UDP收到退出消息: {peer_name}")
        
        with self._lock:
            # 关闭连接
            conn = self._connections.pop(peer_id, None)
            if conn:
                try:
                    conn.close()
                except:
                    pass
            
            # 移除 peer
            self._peers.pop(peer_id, None)
            self._connecting_peers.discard(peer_id)
        
        self.peer_lost.emit({
            "id": peer_id,
            "name": peer_name
        })
    
    def _handle_discovery(self, msg: dict, ip: str):
        """处理发现消息"""
        peer_id = msg["sender_id"]
        peer_name = msg.get("sender_name", "未知用户")
        peer_port = msg.get("tcp_port", config.NETWORK_PORT)
        
        with self._lock:
            # 检查是否已经有连接
            if peer_id in self._connections:
                # 更新最后活跃时间
                if peer_id in self._peers:
                    self._peers[peer_id].update_last_seen()
                return
            
            # 检查是否正在连接中
            if peer_id in self._connecting_peers:
                return
            
            # 检查是否已知但未连接的 peer
            if peer_id in self._peers:
                self._peers[peer_id].update_last_seen()
                return
            
            # 创建新节点
            peer = Peer(
                id=peer_id,
                name=peer_name,
                ip=ip,
                port=peer_port,
                last_seen=time.time()
            )
            self._peers[peer_id] = peer
        
        print(f"[网络] 发现新用户: {peer_name} ({peer_id})")
        
        self.peer_discovered.emit({
            "id": peer_id,
            "name": peer_name,
            "ip": ip,
            "character": msg.get("character", "cat")
        })
        
        # 核心修复：单向连接策略
        # 比较 IP 地址，只有 IP 较大的一方发起连接
        # 这样避免了双向连接的竞争问题
        if self._should_connect_to(ip, peer_port):
            self._start_connection(peer)
    
    def _should_connect_to(self, peer_ip: str, peer_port: int) -> bool:
        """
        判断是否应该主动连接对方
        使用单向连接策略避免双向连接竞争
        """
        # 比较 (IP, Port) 元组，只有"大"的一方发起连接
        my_addr = (self._local_ip, self._tcp_port)
        peer_addr = (peer_ip, peer_port)
        
        # 字符串/数字比较确保只有一方发起连接
        return my_addr > peer_addr
    
    def _start_connection(self, peer: Peer):
        """启动连接线程"""
        with self._lock:
            if peer.id in self._connecting_peers:
                return
            self._connecting_peers.add(peer.id)
        
        threading.Thread(
            target=self._connect_to_peer,
            args=(peer,),
            daemon=True
        ).start()
    
    # ==================== TCP 服务 ====================
    
    def _tcp_server(self):
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.bind(('0.0.0.0', self._tcp_port))
        tcp_socket.listen(5)
        tcp_socket.settimeout(1.0)
        
        while self._running:
            try:
                client_socket, addr = tcp_socket.accept()
                threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_socket, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"[TCP错误] {e}")
        
        tcp_socket.close()
    
    def _handle_tcp_client(self, client_socket: socket.socket, addr: tuple):
        """处理 TCP 客户端连接（被连接方）"""
        peer_id = None
        
        try:
            client_socket.settimeout(10.0)
            
            data = client_socket.recv(4096)
            
            if not data:
                client_socket.close()
                return
            
            # 初始数据可能包含多条消息，取第一条用于握手
            text = data.decode('utf-8')
            remaining = ""
            first_line = text
            if '\n' in text:
                first_line, remaining = text.split('\n', 1)
            first_line = first_line.strip()
            
            msg = parse_message(first_line.encode('utf-8'))
            if not msg:
                client_socket.close()
                return
            
            peer_id = msg.get("sender_id")
            msg_type = msg.get("type")
            
            if msg_type == config.MSG_TYPE_EXIT:
                print(f"[网络] 客户端发送退出: {msg.get('sender_name')}")
                client_socket.close()
                return
            
            if peer_id and peer_id != self._pet_id:
                self._handle_tcp_message(msg, peer_id)
                
                # 处理初始数据中的剩余消息
                while '\n' in remaining:
                    line, remaining = remaining.split('\n', 1)
                    line = line.strip()
                    if line:
                        extra_msg = parse_message(line.encode('utf-8'))
                        if extra_msg:
                            self._handle_tcp_message(extra_msg, peer_id)
                
                with self._lock:
                    old_conn = self._connections.get(peer_id)
                    if old_conn:
                        try:
                            old_conn.close()
                        except:
                            pass
                    
                    self._connections[peer_id] = client_socket
                    self._connecting_peers.discard(peer_id)
                    
                    if peer_id in self._peers:
                        self._peers[peer_id].update_last_seen()
                
                print(f"[网络] TCP连接建立（被动）: {msg.get('sender_name', peer_id)}")
                self.connection_established.emit(peer_id)
                self._receive_loop(client_socket, peer_id)
            else:
                client_socket.close()
                
        except socket.timeout:
            if peer_id and peer_id in self._peers:
                with self._lock:
                    self._connections[peer_id] = client_socket
                    self._connecting_peers.discard(peer_id)
                print(f"[网络] TCP连接超时但保留: {peer_id}")
                self._receive_loop(client_socket, peer_id)
            else:
                print(f"[网络] TCP连接超时，未知客户端")
                try:
                    client_socket.close()
                except:
                    pass
        except Exception as e:
            print(f"[客户端处理错误] {e}")
            try:
                client_socket.close()
            except:
                pass
    
    def _connect_to_peer(self, peer: Peer):
        """
        主动连接到 peer（连接方）
        核心修复：连接成功后立即发送心跳消息
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries and self._running:
            # 检查是否已经有连接
            with self._lock:
                if peer.id in self._connections:
                    self._connecting_peers.discard(peer.id)
                    return
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect(peer.address)
                
                # 连接成功后立即发送心跳消息（带换行分隔符）
                heartbeat = self._message_builder.heartbeat()
                sock.sendall((heartbeat.to_json() + '\n').encode('utf-8'))
                
                with self._lock:
                    # 再次检查是否已有连接
                    if peer.id in self._connections:
                        sock.close()
                        self._connecting_peers.discard(peer.id)
                        return
                    
                    self._connections[peer.id] = sock
                    self._connecting_peers.discard(peer.id)
                    
                    if peer.id in self._peers:
                        self._peers[peer.id].update_last_seen()
                
                print(f"[连接] 主动连接成功: {peer.name}")
                
                # 通知上层连接已建立，可以广播状态
                self.connection_established.emit(peer.id)
                
                # 进入接收循环
                self._receive_loop(sock, peer.id)
                return
                
            except socket.timeout:
                retry_count += 1
                print(f"[连接超时] {peer.name}, 重试 {retry_count}/{max_retries}")
                if retry_count < max_retries:
                    time.sleep(1)
            except ConnectionRefusedError:
                print(f"[连接被拒绝] {peer.name} 可能还未启动")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2)
            except Exception as e:
                print(f"[连接失败] {peer.name}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(1)
        
        # 连接失败，清理状态
        with self._lock:
            self._connecting_peers.discard(peer.id)
            # 不删除 peer 信息，允许将来重试
    
    def _receive_loop(self, sock: socket.socket, peer_id: str):
        """接收循环（带缓冲区处理粘包）"""
        sock.settimeout(1.0)
        buf = ""
        
        while self._running:
            with self._lock:
                if peer_id not in self._connections:
                    break
            
            try:
                data = sock.recv(4096)
                if not data:
                    break
                
                buf += data.decode('utf-8')
                
                # 按换行符拆分完整消息
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    msg = parse_message(line.encode('utf-8'))
                    if msg:
                        msg_type = msg.get("type")
                        if msg_type == config.MSG_TYPE_EXIT:
                            print(f"[网络] 收到退出消息: {msg.get('sender_name')}")
                            self._handle_peer_disconnect(peer_id, sock)
                            return
                        self._handle_tcp_message(msg, peer_id)
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[接收错误] {peer_id}: {e}")
                break
        
        self._handle_peer_disconnect(peer_id, sock)
    
    def _handle_tcp_message(self, msg: dict, sender_id: str):
        msg_type = msg.get("type")
        
        with self._lock:
            if sender_id in self._peers:
                self._peers[sender_id].update_last_seen()
        
        if msg_type == config.MSG_TYPE_HEARTBEAT:
            pass  # 心跳已更新 last_seen
        
        elif msg_type == config.MSG_TYPE_EXIT:
            print(f"[网络] TCP收到退出消息: {msg.get('sender_name')}")
        
        elif msg_type == config.MSG_TYPE_EMOTION:
            print(f"[网络] 收到表情: {msg.get('sender_name')} -> {msg.get('emotion')}")
            self.emotion_received.emit({
                "sender_id": sender_id,
                "sender_name": msg.get("sender_name", "未知"),
                "emotion": msg.get("emotion", "happy"),
                "timestamp": msg.get("timestamp")
            })
        
        elif msg_type == config.MSG_TYPE_MESSAGE:
            print(f"[网络] 收到消息: {msg.get('sender_name')} -> {msg.get('message', '')[:30]}")
            self.message_received.emit({
                "sender_id": sender_id,
                "sender_name": msg.get("sender_name", "未知"),
                "message": msg.get("message", ""),
                "timestamp": msg.get("timestamp")
            })
        
        elif msg_type == config.MSG_TYPE_STATUS:
            print(f"[网络] 收到状态: {msg.get('sender_name')} -> {msg.get('mood')}")
            self.status_received.emit({
                "sender_id": sender_id,
                "sender_name": msg.get("sender_name", "未知"),
                "mood": msg.get("mood", "stand"),
                "character": msg.get("character", "cat"),
                "timestamp": msg.get("timestamp")
            })
        
        elif msg_type == "animation":
            print(f"[网络] 收到动画: {msg.get('sender_name')} -> {msg.get('target_mood')}")
            self.animation_received.emit({
                "sender_id": sender_id,
                "sender_name": msg.get("sender_name", "未知"),
                "target_mood": msg.get("target_mood", "stand"),
                "stage_count": msg.get("stage_count", 0),
                "character": msg.get("character", "cat"),
                "timestamp": msg.get("timestamp")
            })
        
        elif msg_type == "focus_state":
            self.focus_state_received.emit({
                "sender_id": sender_id,
                "sender_name": msg.get("sender_name", "未知"),
                "state": msg.get("state", "neutral"),
                "focus_seconds": msg.get("focus_seconds", 0),
                "play_seconds": msg.get("play_seconds", 0),
                "timestamp": msg.get("timestamp")
            })
    
    def _handle_peer_disconnect(self, peer_id: str, sock: socket.socket = None):
        """处理对等节点断开"""
        with self._lock:
            # 从连接列表移除
            self._connections.pop(peer_id, None)
            self._connecting_peers.discard(peer_id)
            
            # 获取 peer 信息
            peer = self._peers.get(peer_id)
            
            # 保留 peer 信息以便将来重连
            # 但如果长时间没有活动，才移除
        
        # 关闭 socket
        if sock:
            try:
                sock.close()
            except:
                pass
        
        if peer:
            print(f"[断开] {peer.name} 已断开")
            
            self.peer_lost.emit({
                "id": peer_id,
                "name": peer.name
            })
            
            # 从已知节点移除
            with self._lock:
                self._peers.pop(peer_id, None)
    
    # ==================== 消息发送 ====================
    
    def _send_to_peer(self, peer_id: str, message: str) -> bool:
        with self._lock:
            sock = self._connections.get(peer_id)
            if sock:
                try:
                    sock.sendall((message + '\n').encode('utf-8'))
                    return True
                except Exception as e:
                    print(f"[发送失败] {peer_id}: {e}")
                    return False
            else:
                print(f"[发送失败] {peer_id}: 连接不存在")
                return False
    
    def _broadcast_message(self, message: str):
        data = (message + '\n').encode('utf-8')
        
        with self._lock:
            for peer_id, sock in self._connections.items():
                try:
                    sock.sendall(data)
                except Exception as e:
                    print(f"[广播失败] {peer_id}: {e}")
    
    # ==================== 心跳服务 ====================
    
    def _heartbeat_service(self):
        while self._running:
            time.sleep(config.HEARTBEAT_INTERVAL)
            
            if not self._running:
                break
            
            # 发送心跳
            heartbeat = self._message_builder.heartbeat()
            self._broadcast_message(heartbeat.to_json())
            
            # 清理超时节点
            self._cleanup_stale_peers()
    
    def _cleanup_stale_peers(self):
        """清理超时的节点"""
        current_time = time.time()
        timeout = config.HEARTBEAT_INTERVAL * config.PEER_TIMEOUT_MULTIPLIER
        
        to_remove = []
        
        with self._lock:
            for peer_id, peer in self._peers.items():
                if current_time - peer.last_seen > timeout:
                    to_remove.append((peer_id, peer.name))
        
        for peer_id, peer_name in to_remove:
            print(f"[清理] 超时节点: {peer_name} ({peer_id})")
            
            with self._lock:
                sock = self._connections.pop(peer_id, None)
                self._peers.pop(peer_id, None)
                self._connecting_peers.discard(peer_id)
            
            if sock:
                try:
                    sock.close()
                except:
                    pass
            
            self.peer_lost.emit({
                "id": peer_id,
                "name": peer_name
            })