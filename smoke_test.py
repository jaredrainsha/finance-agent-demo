"""冒烟测试：跑一张发票验证全链路。

用法：
    python smoke_test.py               # 默认 valid_invoice.png
    python smoke_test.py over_budget_invoice.png
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INVOICE_DIR
from pipeline import process_invoice

name = sys.argv[1] if len(sys.argv) > 1 else "valid_invoice.png"
img = INVOICE_DIR / name
if not img.exists():
    print(f"不存在：{img}")
    sys.exit(1)

r = process_invoice(str(img), "", set())
print("=" * 56)
print("【识别字段】")
print(json.dumps(r["fields"], ensure_ascii=False, indent=2))
print("=" * 56)
print("【硬规则拦截】", [b["rule"] + ":" + b["reason"] for b in r["blocked"]] or "无")
print("【软条款结论】", json.dumps(r["soft"], ensure_ascii=False))
print("【凭证】", json.dumps(r["voucher"], ensure_ascii=False))
print("【最终】", "✅ 通过" if r["passed"] else "❌ 未通过")
