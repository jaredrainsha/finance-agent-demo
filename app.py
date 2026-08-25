"""财务报销审核 Agent Demo — Streamlit 界面。

跑法：
    export DEEPSEEK_API_KEY=sk-xxx
    streamlit run app.py
"""
import re
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from config import COMPANY_NAME, COMPANY_TAX_ID, INVOICE_DIR
from pipeline import process_invoice
from rules import load_policy

st.set_page_config(page_title="财务报销审核 Agent Demo", page_icon="🧾", layout="wide")

st.title("🧾 财务报销审核 Agent")
st.caption("发票识别 → 硬规则拦截 → 制度条款审核 → 凭证生成 · 全程审计留痕")

# ---- 会话状态 ----
if "reimbursed" not in st.session_state:
    st.session_state.reimbursed = set()
for k in ("total_processed", "total_passed", "total_blocked"):
    if k not in st.session_state:
        st.session_state[k] = 0
if "records" not in st.session_state:
    st.session_state.records = []

SAMPLE_LABELS = {
    "valid_invoice.png": "✅ 合规（住宿 480）",
    "over_budget_invoice.png": "🛑 超标（住宿 800）",
    "wrong_title_invoice.png": "🛑 抬头错误",
    "duplicate_invoice.png": "🛑 重复报销",
    "entertainment_invoice.png": "⚠️ 招待费（需事由）",
}

MIN_PER_INVOICE = 3  # 每张发票人工审核约 3 分钟


def _amt(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d+(?:\.\d+)?", str(v))
    return float(m.group(0)) if m else 0.0


def _category(item: str) -> str:
    if "住宿" in item:
        return "差旅住宿"
    if "餐饮" in item or "招待" in item or "宴请" in item:
        return "业务招待"
    if "交通" in item or "打车" in item or "出租" in item:
        return "市内交通"
    return "其他"


def _record_result(result: dict) -> None:
    st.session_state.total_processed += 1
    if result["passed"]:
        st.session_state.total_passed += 1
    else:
        st.session_state.total_blocked += 1
    f = result["fields"]
    item = (f.get("项目名称") or "").strip()
    st.session_state.records.append({
        "类别": _category(item),
        "项目": item or "未知",
        "金额": _amt(f.get("金额")),
        "日期": f.get("开票日期") or "",
        "结果": "通过" if result["passed"] else ("拦截" if result["blocked"] else "退回"),
    })


def _save_upload(uploaded) -> str:
    suffix = Path(uploaded.name).suffix or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded.getvalue())
    tmp.close()
    return tmp.name


def render_audit_result(result: dict) -> None:
    """渲染单个审核结果：识别 → 硬规则 → 软条款 → 凭证 → 结论横幅。"""
    for step in result["audit"]:
        stage = step["阶段"]
        status = step["状态"]
        detail = step["明细"]

        if stage == "① 发票识别":
            with st.expander(f"{stage} — 已识别字段", expanded=True):
                st.json(detail)
        elif stage == "② 硬规则校验":
            with st.expander(f"{stage} — {status}", expanded=True):
                for r in detail:
                    icon = "✅" if r["status"] == "pass" else "🛑"
                    st.markdown(f"{icon} **{r['rule']}** — {r['detail']}")
                    if r["reason"]:
                        st.error(f"拦截原因：{r['reason']}　`依据：{r['reference']}`")
                    else:
                        st.caption(f"依据：{r['reference']}")
        elif stage == "③ 制度条款审核":
            with st.expander(f"{stage} — {status}", expanded=True):
                st.json(detail)
        elif stage == "④ 凭证生成":
            with st.expander(f"{stage} — {status}", expanded=True):
                v = detail
                st.markdown(f"**凭证字号** `{v['凭证字号']}`　**日期** `{v['日期']}`　**摘要** `{v['摘要']}`")
                st.markdown(f"| 方向 | 分录 |\n|---|---|\n| 借 | {v['借方']} |\n| 贷 | {v['贷方']} |")

    if result["passed"]:
        st.success("🎉 审核通过，已自动生成记账凭证")
    elif result["blocked"]:
        st.error(f"🛑 被硬规则拦截，共 {len(result['blocked'])} 条")
    elif result["soft"] and result["soft"].get("结论") in ("退回", "需人工复核"):
        st.warning(f"⚠️ 制度条款审核结论：{result['soft'].get('结论')}")

    st.markdown("---")
    st.caption("📋 全链路审计留痕：每一步判断均带规则依据，可追溯、可审计")


def _batch_order(names: list) -> list:
    return sorted(names, key=lambda n: (n != "valid_invoice.png", n))


# ================= 侧边栏：报销设置（改这里全局生效）=================
with st.sidebar.expander("⚙️ 报销设置", expanded=False):
    company_name = st.text_input("公司全称", value=COMPANY_NAME)
    company_tax_id = st.text_input("公司税号", value=COMPANY_TAX_ID)
    hotel_cap = st.number_input("住宿单晚上限（元）", value=500.0, step=50.0, min_value=0.0)
    ent_cap = st.number_input("招待费单笔上限（元）", value=1000.0, step=100.0, min_value=0.0)
    exp_days = st.number_input("报销时限（天）", value=90, step=5, min_value=1)
    policy_text = st.text_area("报销制度", value=load_policy(), height=200)

rules = {
    "hotel_cap": float(hotel_cap),
    "entertainment_cap": float(ent_cap),
    "expense_days": int(exp_days),
}

# ================= 顶部 ROI 看板 =================
st.markdown("### 📊 ROI 看板")
c1, c2, c3, c4 = st.columns(4)
c1.metric("累计处理发票", f"{st.session_state.total_processed} 张")
c2.metric("审核通过", f"{st.session_state.total_passed} 张")
c3.metric("违规拦截", f"{st.session_state.total_blocked} 张")
c4.metric("估算节省工时", f"{st.session_state.total_processed * MIN_PER_INVOICE} 分钟")
st.caption("按每张发票人工审核约 3 分钟估算，AI 秒级完成。")
st.markdown("---")

# ================= 三个 Tab =================
tab_upload, tab_sample, tab_batch, tab_analysis = st.tabs(["📤 上传票据", "🔍 示例演示", "📦 批量报销", "📈 经营分析"])

# ---------- Tab 1：上传票据（核心） ----------
with tab_upload:
    st.subheader("上传一张票据，走完「识别 → 报销」全流程")
    col_u1, col_u2 = st.columns([1, 1.4])

    with col_u1:
        st.markdown("**① 上传票据图片**")
        uploaded = st.file_uploader("选择图片（发票 / 票据）", type=["png", "jpg", "jpeg", "webp"])
        st.markdown("**② 报销说明（招待费必填）**")
        note_u = st.text_area("事由 / 行程说明", height=80,
                              placeholder="例：接待深圳供应商王总一行 3 人，洽谈采购合同")
        run_u = st.button("开始识别并报销", type="primary", width="stretch")

    with col_u2:
        if uploaded is not None:
            tmp_path = _save_upload(uploaded)
            st.image(tmp_path, width="stretch", caption="上传的票据")
            if run_u:
                with st.spinner("正在识别 + 审核 + 入账…"):
                    result = process_invoice(
                        tmp_path, note_u, st.session_state.reimbursed,
                        company_name=company_name.strip(), company_tax_id=company_tax_id.strip(),
                        rules=rules, policy_text=policy_text,
                    )
                _record_result(result)
                render_audit_result(result)
        else:
            st.info("👈 上传一张票据图片，点「开始识别并报销」")

# ---------- Tab 2：示例演示 ----------
with tab_sample:
    col_s1, col_s2 = st.columns([1, 1.4])
    with col_s1:
        st.subheader("选择示例发票")
        samples = sorted(INVOICE_DIR.glob("*.png"))
        choice = st.radio(
            "选一张：",
            options=[p.name for p in samples],
            format_func=lambda n: SAMPLE_LABELS.get(n, n),
        )
        selected = INVOICE_DIR / choice
        if selected.exists():
            st.image(str(selected), width="stretch")
    with col_s2:
        st.subheader("报销说明（招待费必填）")
        note_s = st.text_area("事由 / 行程说明", height=90,
                              placeholder="例：接待深圳供应商王总一行 3 人，洽谈采购合同")
        run_s = st.button("开始审核", type="primary", width="stretch")
        if run_s:
            with st.spinner("正在识别 + 审核…"):
                result = process_invoice(
                    str(selected), note_s, st.session_state.reimbursed,
                    company_name=company_name.strip(), company_tax_id=company_tax_id.strip(),
                    rules=rules, policy_text=policy_text,
                )
            _record_result(result)
            render_audit_result(result)
        else:
            st.info("👈 左侧选一张发票，点「开始审核」演示完整链路")

# ---------- Tab 3：批量报销 ----------
with tab_batch:
    st.subheader("📦 批量报销：一次处理整批发票")
    st.caption("演示「月度报销单批量审核」")

    col_b1, col_b2 = st.columns([1, 1.4])
    with col_b1:
        sample_names = sorted(INVOICE_DIR.glob("*.png"))
        default_pick = [n for n in _batch_order([p.name for p in sample_names]) if n != "duplicate_invoice.png"]
        picked = st.multiselect(
            "选择发票",
            options=_batch_order([p.name for p in sample_names]),
            default=default_pick,
            format_func=lambda n: SAMPLE_LABELS.get(n, n),
        )
        st.caption("重复报销（同号发票）建议到「示例演示」体验")
    with col_b2:
        batch_note = st.text_input("统一报销说明（招待费需填事由）", value="")
        batch_run = st.button("批量审核", type="primary", width="stretch")

    if batch_run:
        if not picked:
            st.warning("请至少选择一张发票")
        else:
            rows = []
            with st.spinner(f"正在批量处理 {len(picked)} 张发票…"):
                for name in _batch_order(picked):
                    img = INVOICE_DIR / name
                    r = process_invoice(
                        str(img), batch_note, st.session_state.reimbursed,
                        company_name=company_name.strip(), company_tax_id=company_tax_id.strip(),
                        rules=rules, policy_text=policy_text,
                    )
                    _record_result(r)
                    hard_block = "、".join(b["rule"] for b in r["blocked"]) or "—"
                    soft = r["soft"].get("结论") if r["soft"] else "—"
                    if r["passed"]:
                        status = "✅ 通过"
                    elif r["blocked"]:
                        status = "🛑 拦截"
                    else:
                        status = f"⚠️ {soft}"
                    rows.append({
                        "发票": SAMPLE_LABELS.get(name, name),
                        "金额": r["fields"].get("金额"),
                        "硬规则": hard_block,
                        "软条款": soft,
                        "结果": status,
                    })

            st.table(pd.DataFrame(rows))
            n_pass = sum(1 for r in rows if r["结果"] == "✅ 通过")
            st.success(
                f"批量完成：{len(rows)} 张，其中 {n_pass} 张通过、{len(rows) - n_pass} 张拦截/退回，"
                f"本批节省约 {len(rows) * MIN_PER_INVOICE} 分钟人工审核时间"
            )

# ---------- Tab 4：经营分析 ----------
with tab_analysis:
    st.subheader("📈 经营分析：这个月钱花哪了")
    st.caption("由已识别的报销数据自动聚合，随报销实时更新")

    records = st.session_state.records
    if not records:
        st.info("还没有报销记录。先去「上传票据」或「示例演示」跑几张发票，这里会自动生成费用看板。")
    else:
        df = pd.DataFrame(records)
        total_amt = df["金额"].sum()
        passed_amt = df[df["结果"] == "通过"]["金额"].sum()
        blocked_amt = df[df["结果"] != "通过"]["金额"].sum()
        n_total = len(df)
        n_block = int((df["结果"] != "通过").sum())

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("报销总金额", f"¥{total_amt:,.0f}")
        a2.metric("通过金额", f"¥{passed_amt:,.0f}")
        a3.metric("拦截金额", f"¥{blocked_amt:,.0f}")
        a4.metric("拦截率", f"{n_block / n_total * 100:.0f}%" if n_total else "0%")

        st.markdown("**按费用类别分布**")
        by_cat = df.groupby("类别")["金额"].sum().sort_values(ascending=True)
        if len(by_cat) >= 2:
            st.bar_chart(by_cat, horizontal=True, height=320)
        else:
            st.caption("💡 跑 ≥ 2 张不同类别的发票后，这里会出现分布条形图。当前只有 1 个类别。")

        st.markdown("**报销明细**")
        st.table(df[["日期", "类别", "项目", "金额", "结果"]])

# ---- 侧边栏 ----
st.sidebar.markdown("### 会话状态")
st.sidebar.caption(
    "已报销发票号："
    + ("、".join(sorted(st.session_state.reimbursed)) if st.session_state.reimbursed else "（空）")
)
st.sidebar.markdown("---")
st.sidebar.caption("刷新页面可重置演示状态")
