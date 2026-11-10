"""Tự kiểm tra bài làm, KHÔNG cần API key (dùng model giả).

    python check.py

Mỗi dòng ✓ / ✗ ứng với 1 TODO. Làm xong TODO nào thì dòng đó chuyển ✓.
"""
from __future__ import annotations

import json
import traceback
from types import SimpleNamespace

import agent
import tools


def check_todo1_tool():
    out = tools.recommend_outfit(temp_high_c=33, rain_probability=0.8)
    assert isinstance(out, dict) and isinstance(out.get("items"), list), "phải trả về dict có key 'items' là list"
    text = " ".join(out["items"]).lower()
    assert "ô" in text or "mưa" in text, "mưa 80% thì phải gợi ý mang ô / áo mưa"
    dry = " ".join(tools.recommend_outfit(temp_high_c=25, rain_probability=0.1)["items"]).lower()
    assert "ô" not in dry.split() and "mưa" not in dry, "trời khô (10%) thì không cần gợi ý ô / áo mưa"
    assert tools.run_tool("recommend_outfit", {"temp_high_c": 33, "rain_probability": 70}).startswith("ERROR"), \
        "rain_probability = 70 (sai đơn vị) phải báo lỗi để agent biết truyền 0.7"


def check_todo2_schema():
    spec = next((t for t in tools.TOOLS if t["name"] == "recommend_outfit"), None)
    assert spec, "chưa khai báo recommend_outfit trong TOOLS"
    assert "TODO" not in spec["description"] and len(spec["description"]) > 40, "description quá ngắn hoặc còn TODO"
    props = spec["input_schema"].get("properties", {})
    assert set(props) == {"temp_high_c", "rain_probability"}, "input_schema phải có đúng 2 tham số"
    assert set(spec["input_schema"].get("required", [])) == {"temp_high_c", "rain_probability"}, "thiếu 'required'"
    assert all(p.get("description") for p in props.values()), "mỗi tham số cần có description (đơn vị, khoảng giá trị)"


def _response(blocks, stop_reason):
    return SimpleNamespace(content=blocks, stop_reason=stop_reason)


def _text(t):
    return SimpleNamespace(type="text", text=t)


def _tool(i, name, args):
    return SimpleNamespace(type="tool_use", id=f"toolu_{i}", name=name, input=args)


def check_todo3_loop():
    sent = []

    def run(script):
        replies = iter(script)

        def fake(messages):
            sent.append([dict(m) for m in messages])
            return next(replies)
        original = agent.call_model
        agent.call_model = fake
        try:
            return agent.run_agent("Ngày mai Đà Nẵng nên mặc gì?")
        finally:
            agent.call_model = original

    # 1) model trả lời ngay -> trả về câu trả lời, không gọi tool
    sent.clear()
    assert run([_response([_text("Xin chào!")], "end_turn")]) == "Xin chào!", \
        "khi stop_reason != 'tool_use' phải trả về text của model"

    # 2) model gọi 2 tool rồi trả lời
    sent.clear()
    answer = run([
        _response([_text("Cần biết ngày mai."), _tool(1, "get_current_date", {})], "tool_use"),
        _response([_tool(2, "get_weather", {"city": "Đà Nẵng", "date": "2026-06-02"})], "tool_use"),
        _response([_text("Mai Đà Nẵng nóng, mặc áo mỏng.")], "end_turn"),
    ])
    assert answer == "Mai Đà Nẵng nóng, mặc áo mỏng.", "chưa trả về câu trả lời cuối của model"
    assert len(sent) == 3, f"phải gọi model 3 lần, bạn gọi {len(sent)} lần"
    second = sent[1]
    assert second[-2]["role"] == "assistant", "phải thêm lượt 'assistant' (response.content) vào messages"
    last = second[-1]
    assert last["role"] == "user" and isinstance(last["content"], list), \
        "kết quả tool phải gửi trong message role 'user', content là list"
    block = last["content"][0]
    assert block.get("type") == "tool_result" and block.get("tool_use_id") == "toolu_1", \
        "mỗi kết quả phải là {'type': 'tool_result', 'tool_use_id': <id của tool_use>, 'content': ...}"
    assert "today" in block.get("content", ""), "content của tool_result phải là kết quả của run_tool()"

    # 3) model gọi tool mãi không dừng -> phải dừng ở MAX_ITERATIONS
    sent.clear()
    loop = [_response([_tool(i, "get_current_date", {})], "tool_use") for i in range(50)]
    out = run(loop)
    assert len(sent) == agent.MAX_ITERATIONS, \
        f"phải dừng sau MAX_ITERATIONS={agent.MAX_ITERATIONS} lần gọi model, bạn gọi {len(sent)} lần"
    assert isinstance(out, str) and out, "khi dừng vì safeguard vẫn phải trả về 1 câu thông báo"


CHECKS = [
    ("TODO 1 — build tool recommend_outfit", check_todo1_tool),
    ("TODO 2 — khai báo schema cho tool", check_todo2_schema),
    ("TODO 3 — agent loop", check_todo3_loop),
]

if __name__ == "__main__":
    import contextlib
    import io

    done = 0
    for title, fn in CHECKS:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                fn()
            print(f"✓ {title}")
            done += 1
        except NotImplementedError:
            print(f"✗ {title}: chưa làm")
        except AssertionError as e:
            line = traceback.extract_tb(e.__traceback__)[-1].line
            print(f"✗ {title}: {e or line}")
        except Exception as e:  # noqa: BLE001
            print(f"✗ {title}: lỗi {type(e).__name__}: {e}")
    print(f"\n{done}/{len(CHECKS)} TODO đã xong." + ("  Giờ chạy agent thật: python agent.py, rồi chấm cả bộ dataset: python evaluate.py" if done == len(CHECKS) else ""))
