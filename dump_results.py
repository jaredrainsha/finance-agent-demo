"""把演示场景的真实运行结果导出为 results.json，供静态 HTML 演示版使用。

用法：python dump_results.py  →  生成 results.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import INVOICE_DIR
from pipeline import process_invoice

reimbursed = set()

# 先让 valid 通过，后续 duplicate 才能触发查重
valid = process_invoice(str(INVOICE_DIR / "valid_invoice.png"), "", reimbursed)

scenes = [
    {"id": "valid", "file": "valid_invoice.png", "label": "✅ 合规（住宿 480）", "note": "", "result": valid},
    {"id": "over", "file": "over_budget_invoice.png", "label": "🛑 超标（住宿 800）", "note": "",
     "result": process_invoice(str(INVOICE_DIR / "over_budget_invoice.png"), "", reimbursed)},
    {"id": "wrong", "file": "wrong_title_invoice.png", "label": "🛑 抬头错误", "note": "",
     "result": process_invoice(str(INVOICE_DIR / "wrong_title_invoice.png"), "", reimbursed)},
    {"id": "dup", "file": "duplicate_invoice.png", "label": "🛑 重复报销", "note": "",
     "result": process_invoice(str(INVOICE_DIR / "duplicate_invoice.png"), "", reimbursed)},
    {
        "id": "entertainment", "file": "entertainment_invoice.png", "label": "⚠️ 招待费（需事由）",
        "variants": [
            {"note_label": "事由留空", "result": process_invoice(str(INVOICE_DIR / "entertainment_invoice.png"), "", reimbursed)},
            {"note_label": "事由敷衍「吃饭」", "result": process_invoice(str(INVOICE_DIR / "entertainment_invoice.png"), "吃饭", reimbursed)},
            {"note_label": "事由完整", "result": process_invoice(str(INVOICE_DIR / "entertainment_invoice.png"), "接待深圳供应商王总一行3人，洽谈采购合同", reimbursed)},
        ],
    },
]

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(scenes, f, ensure_ascii=False, indent=2)

print("已导出", len(scenes), "个场景到 results.json")
