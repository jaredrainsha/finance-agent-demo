"""多模态发票识别：用 DeepSeek 视觉模型读发票图，抽取结构化字段。"""
import base64
import json
import re
from pathlib import Path

from openai import OpenAI

from config import VISION_CONFIG

EXTRACT_PROMPT = """你是财务发票审核助手。请从这张发票图片中提取关键字段，严格只输出一个 JSON 对象，不要输出任何其他文字、解释或代码块标记。

JSON 字段如下：
{
  "发票号码": "字符串",
  "开票日期": "YYYY-MM-DD",
  "购买方名称": "字符串",
  "购买方税号": "字符串",
  "项目名称": "字符串",
  "金额": 数字,
  "税率": "字符串，如 6%",
  "税额": 数字,
  "价税合计": 数字,
  "销售方名称": "字符串"
}

要求：
1. 金额、税额、价税合计只输出数字（不带 ¥、逗号、单位），保留两位小数。
2. 识别不清的字段填空字符串 ""，数字填 0。
3. 只输出 JSON 本身。"""


def parse_json_obj(content: str) -> dict:
    """从模型输出中稳健提取 JSON 对象。"""
    if not content:
        return {}
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def extract_fields(image_path: str) -> dict:
    """识别发票字段，返回 dict。"""
    client = OpenAI(base_url=VISION_CONFIG["base_url"], api_key=VISION_CONFIG["api_key"])
    b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    resp = client.chat.completions.create(
        model=VISION_CONFIG["model"],
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACT_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }
        ],
        temperature=0.1,
    )
    content = resp.choices[0].message.content
    return parse_json_obj(content)
