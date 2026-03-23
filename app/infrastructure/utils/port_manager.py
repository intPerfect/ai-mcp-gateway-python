# -*- coding: utf-8 -*-
"""
Port Manager - 端口管理工具
"""
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PortManager:
    """端口管理器"""
    
    @staticmethod
    def kill_port(port: int) -> bool:
        """
        终止占用指定端口的进程
        
        Args:
            port: 端口号
            
        Returns:
            是否成功终止
        """
        try:
            # Windows系统
            import platform
            if platform.system() == "Windows":
                # 查找占用端口的进程
                result = subprocess.run(
                    f'netstat -ano | findstr ":{port}"',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid.isdigit():
                                subprocess.run(
                                    f'taskkill /F /PID {pid}',
                                    shell=True,
                                    capture_output=True
                                )
                                logger.info(f"终止进程 PID: {pid}")
                else:
                    logger.info(f"端口 {port} 未被占用")
            else:
                # Linux/Mac系统
                result = subprocess.run(
                    f'lsof -ti:{port}',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            subprocess.run(
                                f'kill -9 {pid}',
                                shell=True,
                                capture_output=True
                            )
                            logger.info(f"终止进程 PID: {pid}")
                else:
                    logger.info(f"端口 {port} 未被占用")
            
            return True
            
        except Exception as e:
            logger.error(f"终止端口 {port} 进程失败: {e}")
            return False
    
    @staticmethod
    def is_port_in_use(port: int) -> bool:
        """
        检查端口是否被占用
        
        Args:
            port: 端口号
            
        Returns:
            端口是否被占用
        """
        import socket
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    @staticmethod
    def find_available_port(start_port: int, max_attempts: int = 100) -> Optional[int]:
        """
        查找可用端口
        
        Args:
            start_port: 起始端口
            max_attempts: 最大尝试次数
            
        Returns:
            可用端口号，如果找不到则返回None
        """
        for port in range(start_port, start_port + max_attempts):
            if not PortManager.is_port_in_use(port):
                return port
        return None
