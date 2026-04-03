import sys
import os
from pathlib import Path

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 切换工作目录
os.chdir(Path(__file__).resolve().parent)

from main import app
import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    # 默认启用热更新，可通过环境变量 RELOAD=false 禁用
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=reload,
        reload_dirs=["app"] if reload else None,
    )
