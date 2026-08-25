"""验证上传路径：自定义公司名/税号透传是否生效。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INVOICE_DIR
from pipeline import process_invoice

img = str(INVOICE_DIR / "valid_invoice.png")

# ① 默认公司名（匹配发票抬头）→ 抬头应通过
r1 = process_invoice(img, "", set())
b1 = [b["rule"] for b in r1["blocked"] if b["rule"] == "发票抬头校验"]
print("① 默认公司名（匹配）:", "✅ 抬头通过" if not b1 else "❌ 误拦")

# ② 老板填了别的公司名 → 抬头应拦截
r2 = process_invoice(img, "", set(), company_name="深圳市某某贸易有限公司", company_tax_id="91440300XXXXXXX")
b2 = [b for b in r2["blocked"] if b["rule"] == "发票抬头校验"]
print("② 自定义公司名（不匹配）:", "✅ 正确拦截" if b2 else "❌ 漏拦")

# ③ 老板填了匹配的公司名 → 抬头应通过
r3 = process_invoice(img, "", set(), company_name="深圳市智造未来科技有限公司", company_tax_id="91440300MA5K8X2Q1C")
b3 = [b["rule"] for b in r3["blocked"] if b["rule"] == "发票抬头校验"]
print("③ 自定义公司名（匹配）:", "✅ 抬头通过" if not b3 else "❌ 误拦")
