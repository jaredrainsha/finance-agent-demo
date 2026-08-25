"""财务报销审核 Agent Demo 配置：DeepSeek 一 key 通吃（文本合规 + 视觉发票识别）。

key 三种填法（优先级从高到低）：
1. 环境变量：export DEEPSEEK_API_KEY=sk-xxx
2. 本目录 .env 文件：DEEPSEEK_API_KEY=sk-xxx
3. 直接改下面的 _DEFAULT_KEY

注意：.env 不要提交 git。
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_env() -> None:
    """加载密钥：.env 文件 + 托管平台 secrets，环境变量优先。"""
    # 1) 本地 .env 文件
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    # 2) Streamlit Cloud / 支持 st.secrets 的平台
    try:
        import streamlit as st
        for k, v in st.secrets.items():
            if isinstance(v, str):
                os.environ.setdefault(k, v)
    except Exception:
        pass


_load_env()

# 直接填这里也可以（不推荐提交 git）
_DEFAULT_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# ---- 文本模型（软条款审核 / 制度理解）----
LLM_CONFIG = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
    "api_key": _DEFAULT_KEY or os.getenv("LLM_API_KEY", ""),
    "model": os.getenv("LLM_MODEL", "deepseek-chat"),
}

# ---- 视觉模型（发票识别）----
VISION_CONFIG = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
    "api_key": _DEFAULT_KEY or os.getenv("LLM_API_KEY", ""),
    "model": os.getenv("VISION_MODEL", "deepseek-v4-flash-vision-exp"),
}

# ---- 公司信息（抬头/税号校验的基准）----
COMPANY_NAME = os.getenv("COMPANY_NAME", "深圳市智造未来科技有限公司")
COMPANY_TAX_ID = os.getenv("COMPANY_TAX_ID", "91440300MA5K8X2Q1C")

# ---- 路径 ----
DATA_DIR = BASE_DIR / "data"
INVOICE_DIR = BASE_DIR / "invoices"
POLICY_FILE = DATA_DIR / "policy.md"
