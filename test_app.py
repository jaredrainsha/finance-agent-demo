"""用 Streamlit AppTest 无头验证 app.py 渲染无异常（不触发 API 调用）。

用法：python test_app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=60)
at.run()

if at.exception:
    for e in at.exception:
        print("EXC:", type(e.value).__name__, "-", e.value)
else:
    print("OK：app.py 渲染无异常")
    print("tabs:", [t.label for t in at.tabs])
    print("metrics:", [m.label for m in at.metric])
    print("buttons:", [b.label for b in at.button])
