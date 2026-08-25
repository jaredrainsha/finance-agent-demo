"""全剧情批量验证：5 张发票 × 关键 note 变体，跑完整个决策树。

用法：python test_all.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INVOICE_DIR
from pipeline import process_invoice

cases = [
    ("valid_invoice.png", "", "① 合规通过"),
    ("over_budget_invoice.png", "", "② 超标拦截"),
    ("wrong_title_invoice.png", "", "③ 抬头拦截"),
    ("duplicate_invoice.png", "", "④ 重复拦截"),
    ("entertainment_invoice.png", "", "⑤ 招待费缺事由拦截"),
    ("entertainment_invoice.png", "吃饭", "⑥ 事由敷衍→软条款退回"),
    ("entertainment_invoice.png", "接待深圳供应商王总一行3人，洽谈采购合同", "⑦ 事由完整→通过"),
]

reimbursed = set()
for name, note, label in cases:
    img = INVOICE_DIR / name
    r = process_invoice(str(img), note, reimbursed)
    hard_block = [b["rule"] for b in r["blocked"]] or "无"
    soft = r["soft"].get("结论") if r["soft"] else "-"
    print(f"{label:24s} | 硬规则拦截:{hard_block} | 软条款:{soft} | 最终:{'✅通过' if r['passed'] else '❌未通过'}")
