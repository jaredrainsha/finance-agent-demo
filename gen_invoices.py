"""用 PIL 生成 5 张演示用电子发票图（增值税普通发票样式）。

生成目的：字段清晰可控，精确覆盖五种剧情——
① 合规通过 ② 超标拦截 ③ 抬头错误拦截 ④ 重复报销拦截 ⑤ 招待费缺事由（软条款退回）。

这是演示票据，非真实发票。
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "invoices"

# macOS 中文字体候选
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

_font_cache = {}


def _find_font() -> str | None:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def _font(size: int) -> ImageFont.FreeTypeFont:
    if size in _font_cache:
        return _font_cache[size]
    path = _find_font()
    font = None
    if path:
        for index in (0, 1, 2):
            try:
                font = ImageFont.truetype(path, size, index=index)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()
    _font_cache[size] = font
    return font


def _money(n: float) -> str:
    return f"{n:.2f}"


def draw_invoice(
    filename: str,
    invoice_no: str,
    date: str,
    buyer_name: str,
    buyer_tax_id: str,
    item_name: str,
    amount: float,
    tax_rate: float,
    seller_name: str,
) -> None:
    tax_amount = round(amount * tax_rate, 2)
    total = round(amount + tax_amount, 2)
    W, H = 1400, 900
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    f_title = _font(54)
    f_head = _font(36)
    f_body = _font(38)
    f_small = _font(28)

    # 标题
    d.text((W // 2, 60), "增值税普通发票", font=f_title, fill="black", anchor="ma")
    d.text((W // 2, 130), "（演示票据）", font=f_small, fill=(120, 120, 120), anchor="ma")

    # 发票号码 + 开票日期
    d.text((120, 210), f"发票号码：{invoice_no}", font=f_head, fill="black")
    d.text((120, 275), f"开票日期：{date}", font=f_head, fill="black")

    # 购买方
    d.text((120, 370), f"购买方名称：{buyer_name}", font=f_body, fill="black")
    d.text((120, 435), f"购买方税号：{buyer_tax_id}", font=f_body, fill="black")

    # 明细表头
    d.line([(120, 515), (W - 120, 515)], fill="black", width=3)
    d.text((120, 535), "项目名称", font=f_head, fill="black")
    d.text((560, 535), "金额(不含税)", font=f_head, fill="black")
    d.text((880, 535), "税率", font=f_head, fill="black")
    d.text((1080, 535), "税额", font=f_head, fill="black")

    # 明细行
    d.text((120, 605), item_name, font=f_body, fill="black")
    d.text((560, 605), _money(amount), font=f_body, fill="black")
    d.text((880, 605), f"{int(tax_rate * 100)}%", font=f_body, fill="black")
    d.text((1080, 605), _money(tax_amount), font=f_body, fill="black")

    # 价税合计 + 销售方
    d.line([(120, 690), (W - 120, 690)], fill="black", width=3)
    d.text((120, 715), f"价税合计（小写）：¥ {_money(total)}", font=f_head, fill="black")
    d.text((120, 790), f"销售方名称：{seller_name}", font=f_body, fill="black")

    img.save(OUT_DIR / filename)
    print(f"已生成 {filename}：{item_name} 金额={_money(amount)} 税率={int(tax_rate*100)}% "
          f"抬头={buyer_name} 发票号={invoice_no}")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    COMPANY = "深圳市智造未来科技有限公司"
    TAX_ID = "91440300MA5K8X2Q1C"

    # ① 合规：住宿 480（一线城市标准 500 内）
    draw_invoice(
        "valid_invoice.png", "044001900111", "2026-08-10",
        COMPANY, TAX_ID, "住宿服务", 480.0, 0.06, "深圳云端国际酒店有限公司",
    )
    # ② 超标：住宿 800（超 500 标准）
    draw_invoice(
        "over_budget_invoice.png", "044001900222", "2026-08-12",
        COMPANY, TAX_ID, "住宿服务", 800.0, 0.06, "深圳湾区大酒店有限公司",
    )
    # ③ 抬头错：购买方名称少了"有限"（住宿类，只触发抬头拦截）
    draw_invoice(
        "wrong_title_invoice.png", "044001900333", "2026-08-15",
        "深圳市智造未来科技公司", TAX_ID, "住宿服务", 300.0, 0.06, "深圳湘江商务酒店有限公司",
    )
    # ④ 重复：与 valid 同发票号（模拟重复报销）
    draw_invoice(
        "duplicate_invoice.png", "044001900111", "2026-08-10",
        COMPANY, TAX_ID, "住宿服务", 480.0, 0.06, "深圳云端国际酒店有限公司",
    )
    # ⑤ 招待费：金额合规（800 ≤ 1000），但缺事由 → 软条款退回
    draw_invoice(
        "entertainment_invoice.png", "044001900555", "2026-08-16",
        COMPANY, TAX_ID, "餐饮服务", 800.0, 0.06, "深圳市海景轩餐饮有限公司",
    )


if __name__ == "__main__":
    main()
