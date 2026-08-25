"""验证配置化：自定义阈值透传是否生效。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INVOICE_DIR
from pipeline import process_invoice

img = str(INVOICE_DIR / "valid_invoice.png")  # 住宿 480

# ① 默认阈值（住宿 500）：480 应通过
r1 = process_invoice(img, "", set())
b1 = [b["rule"] for b in r1["blocked"]]
print("① 默认阈值(500):", "✅ 无拦截(480≤500)" if not b1 else f"❌ {b1}")

# ② 自定义阈值（住宿 300）：480 应超标拦截
r2 = process_invoice(img, "", set(), rules={"hotel_cap": 300.0, "entertainment_cap": 1000.0, "expense_days": 90})
b2 = [b for b in r2["blocked"] if b["rule"] == "金额标准校验"]
print("② 自定义阈值(300):", "✅ 正确拦截(480>300)" if b2 else "❌ 未拦截")
