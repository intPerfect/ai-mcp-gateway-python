# -*- coding: utf-8 -*-
"""
Port Manager - 端口管理工具
提供端口清理和进程管理功能
"""

import subprocess
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


class PortManager:
    """端口管理器"""
    
    @staticmethod
    def kill_port(port: int) -> bool:
        """
        终止占用指定端口的进程（Windows）
        
        Args:
            port: 端口号
            
        Returns:
            是否成功终止
        """
        try:
            result = subprocess.run(
                f'powershell -Command "'
                f'Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue '
                f'| ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"',
                shell=True,
                capture_output=True,
                text=True
            )
            logger.info(f"已清理端口 {port}")
            return True
        except Exception as e:
            logger.error(f"清理端口 {port} 失败: {e}")
            return False
    
    @staticmethod
    def kill_ports(ports: List[int]) -> dict:
        """
        终止占用多个端口的进程
        
        Args:
            ports: 端口号列表
            
        Returns:
            {"success": [...], "failed": [...]}
        """
        result = {"success": [], "failed": []}
        for port in ports:
            if PortManager.kill_port(port):
                result["success"].append(port)
            else:
                result["failed"].append(port)
        return result
    
    @staticmethod
    def is_port_in_use(port: int) -> bool:
        """
        检查端口是否被占用
        
        Args:
            port: 端口号
            
        Returns:
            端口是否被占用
        """
        try:
            result = subprocess.run(
                f'powershell -Command "'
                f'Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue"',
                shell=True,
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    @staticmethod
    def wait_for_port_free(port: int, timeout: int = 10) -> bool:
        """
        等待端口释放
        
        Args:
            port: 端口号
            timeout: 超时时间（秒）
            
        Returns:
            端口是否已释放
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not PortManager.is_port_in_use(port):
                return True
            time.sleep(0.5)
        return False
    
    @staticmethod
    def get_port_process(port: int) -> Optional[dict]:
        """
        获取占用端口的进程信息
        
        Args:
            port: 端口号
            
        Returns:
            进程信息字典或 None
        """
        try:
            result = subprocess.run(
                f'powershell -Command "'
                f'Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue '
                f'| Select-Object OwningProcess, State, LocalAddress '
                f'| ConvertTo-Json"',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                import json
                data = json.loads(result.stdout)
                if isinstance(data, list) and data:
                    return data[0]
                elif isinstance(data, dict):
                    return data
        except Exception as e:
            logger.error(f"获取端口 {port} 进程信息失败: {e}")
        return None


def kill_port_and_wait(port: int, wait_seconds: int = 2) -> bool:
    """
    终止端口进程并等待释放
    
    Args:
        port: 端口号
        wait_seconds: 等待时间
        
    Returns:
        是否成功
    """
    PortManager.kill_port(port)
    time.sleep(wait_seconds)
    return not PortManager.is_port_in_use(port)