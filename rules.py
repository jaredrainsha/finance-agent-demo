"""硬规则（确定性校验）+ 制度加载。

财务场景铁律：确定性的事交给规则（不容错、可解释、可审计），
模糊条款才交给 LLM（见 pipeline.py 的软条款环节）。
"""
import re
from datetime import datetime

from config import COMPANY_NAME, COMPANY_TAX_ID, POLICY_FILE

# 硬规则阈值（与 data/policy.md 保持一致）
POLICY_RULES = {
    "hotel_cap": 500.0,           # 一线城市住宿单晚上限
    "entertainment_cap": 1000.0,  # 招待费单笔上限
    "expense_days": 90,           # 报销时限（天）
}


def load_policy() -> str:
    return POLICY_FILE.read_text(encoding="utf-8") if POLICY_FILE.exists() else ""


def _to_float(v) -> float:
    """把模型可能返回的各种金额格式转成 float。"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d+(?:\.\d+)?", str(v))
    return float(m.group(0)) if m else 0.0


def _item_cap(item: str, rules: dict):
    """按项目返回金额上限；无上限返回 None。"""
    if "住宿" in item:
        return rules["hotel_cap"]
    if "餐饮" in item or "招待" in item or "宴请" in item:
        return rules["entertainment_cap"]
    return None


def _within_days(date_str: str, days: int) -> bool:
    """判断日期是否在 days 天内；识别不清时放行（交人工）。"""
    try:
        d = datetime.strptime((date_str or "").strip()[:10], "%Y-%m-%d")
    except ValueError:
        return True
    return (datetime.now() - d).days <= days


def check_hard_rules(
    fields: dict,
    reimbursed_nos: set,
    note: str = "",
    company_name: str = COMPANY_NAME,
    company_tax_id: str = COMPANY_TAX_ID,
    rules: dict = None,
) -> list:
    """逐条硬规则校验，返回结果列表。每项含 rule/status/detail/reason/reference。"""
    rules = rules or POLICY_RULES
    results = []

    # 1. 抬头校验
    buyer = (fields.get("购买方名称") or "").strip()
    ok = buyer == company_name
    results.append({
        "rule": "发票抬头校验",
        "status": "pass" if ok else "block",
        "detail": f"购买方名称「{buyer or '（未识别）'}」",
        "reason": "" if ok else f"抬头与公司全称不符（应为「{company_name}」）",
        "reference": "《费用报销管理制度》第五条",
    })

    # 2. 税号校验
    tax_id = (fields.get("购买方税号") or "").strip()
    ok = tax_id == company_tax_id
    results.append({
        "rule": "税号校验",
        "status": "pass" if ok else "block",
        "detail": f"购买方税号「{tax_id or '（未识别）'}」",
        "reason": "" if ok else f"税号与公司税号不符（应为「{company_tax_id}」）",
        "reference": "《费用报销管理制度》第五条",
    })

    # 3. 金额超标校验
    item = (fields.get("项目名称") or "").strip()
    amount = _to_float(fields.get("金额"))
    cap = _item_cap(item, rules)
    if cap is not None:
        ok = amount <= cap
        results.append({
            "rule": "金额标准校验",
            "status": "pass" if ok else "block",
            "detail": f"项目「{item}」金额 ¥{amount:.2f}（上限 ¥{cap:.2f}）",
            "reason": "" if ok else f"超出标准 ¥{amount - cap:.2f}",
            "reference": "《费用报销管理制度》第一条/第二条",
        })

    # 4. 重复报销校验
    invoice_no = (fields.get("发票号码") or "").strip()
    ok = invoice_no not in reimbursed_nos
    results.append({
        "rule": "重复报销校验",
        "status": "pass" if ok else "block",
        "detail": f"发票号码「{invoice_no or '（未识别）'}」",
        "reason": "" if ok else "该发票已报销过，禁止重复报销",
        "reference": "《费用报销管理制度》第五条",
    })

    # 5. 报销时限校验
    date_str = fields.get("开票日期") or ""
    ok = _within_days(date_str, rules["expense_days"])
    results.append({
        "rule": "报销时限校验",
        "status": "pass" if ok else "block",
        "detail": f"开票日期「{date_str or '（未识别）'}」",
        "reason": "" if ok else f"超过 {rules['expense_days']} 天报销时限",
        "reference": "《费用报销管理制度》第四条",
    })

    # 6. 招待费事由校验（确定性：招待费且未填事由 → 拦截）
    item = (fields.get("项目名称") or "").strip()
    is_entertainment = any(k in item for k in ("餐饮", "招待", "宴请"))
    note_ok = bool((note or "").strip())
    if is_entertainment:
        ok = note_ok
        results.append({
            "rule": "招待费事由校验",
            "status": "pass" if ok else "block",
            "detail": f"项目「{item}」属业务招待费，事由{'已填写' if note_ok else '未填写'}",
            "reason": "" if ok else "招待费必须注明事由（接待对象、人数、目的），未注明不予报销",
            "reference": "《费用报销管理制度》第二条",
        })

    return results
