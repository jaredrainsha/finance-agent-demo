"""核心流水线：识别 → 硬规则 → 软条款(LLM) → 凭证生成 → 审计留痕。

固定 pipeline 编排：LLM 只在两个点介入（发票识别、软条款判断），
其余用确定性规则，保证 demo 稳定、可解释、可审计。
"""
import json

from openai import OpenAI

from config import LLM_CONFIG, COMPANY_NAME, COMPANY_TAX_ID
from invoice_vl import extract_fields, parse_json_obj
from rules import check_hard_rules, load_policy

SOFT_REVIEW_PROMPT = """你是资深财务审核员。请对这笔报销做一次通盘合规体检。

《费用报销管理制度》：
{policy}

本笔报销信息（已通过硬规则校验）：
{fields}

报销说明（员工填写，可能为空）：
{note}

判断规则（务必遵守）：
1. 「注明事由」仅对业务招待费（餐饮/招待/宴请）要求；住宿费、市内交通费无需事由，报销说明为空不影响其合规性。
2. 业务招待费：事由完整（含接待对象、人数、目的）→ "通过"；事由敷衍（如仅"吃饭"两字）→ "退回"。
3. 其他情况默认"通过"，不要过度谨慎；仅当存在明确异常时才"需人工复核"。

请严格只输出一个 JSON 对象：

{{
  "结论": "通过" 或 "退回" 或 "需人工复核",
  "依据条款": "相关制度条款原文（无则写 无）",
  "说明": "一句话说明判断理由"
}}
"""


def _soft_review(fields: dict, note: str, policy_text: str = None) -> dict:
    client = OpenAI(base_url=LLM_CONFIG["base_url"], api_key=LLM_CONFIG["api_key"])
    prompt = SOFT_REVIEW_PROMPT.format(
        policy=policy_text or load_policy(),
        fields=json.dumps(fields, ensure_ascii=False, indent=2),
        note=note.strip() or "（未填写）",
    )
    resp = client.chat.completions.create(
        model=LLM_CONFIG["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return parse_json_obj(resp.choices[0].message.content)


def generate_voucher(fields: dict) -> dict:
    """确定性凭证生成：按项目写借贷分录。"""
    item = (fields.get("项目名称") or "").strip()
    amount = fields.get("金额") or 0
    if "住宿" in item:
        debit = "管理费用—差旅费"
    elif "餐饮" in item or "招待" in item or "宴请" in item:
        debit = "管理费用—业务招待费"
    else:
        debit = "管理费用—其他"
    return {
        "凭证字号": "记-001",
        "日期": fields.get("开票日期") or "",
        "摘要": item,
        "借方": f"{debit}  ¥{amount:.2f}",
        "贷方": f"银行存款  ¥{amount:.2f}",
    }


def process_invoice(
    image_path: str,
    note: str,
    reimbursed_nos: set,
    company_name: str = COMPANY_NAME,
    company_tax_id: str = COMPANY_TAX_ID,
    rules: dict = None,
    policy_text: str = None,
) -> dict:
    """主流程：返回 {fields, audit, blocked, soft, voucher, passed}。"""
    audit = []

    # ① 发票识别
    fields = extract_fields(image_path)
    audit.append({"阶段": "① 发票识别", "状态": "完成", "明细": fields})

    # ② 硬规则校验
    hard = check_hard_rules(fields, reimbursed_nos, note, company_name, company_tax_id, rules)
    blocked = [r for r in hard if r["status"] == "block"]
    audit.append({
        "阶段": "② 硬规则校验",
        "状态": "通过" if not blocked else "拦截",
        "明细": hard,
    })

    # ③ 软条款审核（硬规则通过才做）
    soft = None
    if not blocked:
        soft = _soft_review(fields, note, policy_text)
        audit.append({"阶段": "③ 制度条款审核", "状态": soft.get("结论", "未知"), "明细": soft})

    # ④ 凭证生成
    voucher = None
    passed = False
    if not blocked and soft and soft.get("结论") == "通过":
        voucher = generate_voucher(fields)
        reimbursed_nos.add((fields.get("发票号码") or "").strip())
        passed = True
        audit.append({"阶段": "④ 凭证生成", "状态": "完成", "明细": voucher})

    return {
        "fields": fields,
        "audit": audit,
        "blocked": blocked,
        "soft": soft,
        "voucher": voucher,
        "passed": passed,
    }
