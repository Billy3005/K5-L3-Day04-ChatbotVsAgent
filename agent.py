"""ReAct agent viết từ đầu: vòng lặp Thought → Action → Observation (slide 22, 27).

Chạy:
    python agent.py "Ngày mai ở Đà Nẵng nên mặc gì?"
    python agent.py                      # hỏi nhiều câu, gõ exit để thoát
"""
from __future__ import annotations

import json
import os
import sys

import anthropic
from dotenv import load_dotenv

from tools import TOOLS, run_tool

load_dotenv()
MODEL = os.getenv("MODEL", "claude-opus-5-5")
MAX_ITERATIONS = 6          # safeguard: không bao giờ lặp quá số vòng này (slide 30)

# System prompt (slide 28), thêm 1 dòng để model viết "Thought" trước mỗi lần gọi tool
SYSTEM_PROMPT = """You are a Vietnamese travel assistant.

Your job:
- Break the user goal into smaller steps
- Use tools when fresh information is required
- Stop when you have enough evidence to answer

Rules:
- Before each tool call, write ONE short sentence explaining what you need next.
- Never invent tool results.
- If a tool returns an ERROR, read it, fix the arguments and try once more.
- Final answer: short, in Vietnamese.
"""

_client: anthropic.Anthropic | None = None


def call_model(messages: list[dict]):
    """Gọi model 1 lần. Trả về response có .content (danh sách block) và .stop_reason."""
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key or key.endswith("..."):
            sys.exit("Chưa có ANTHROPIC_API_KEY. Mở file .env và điền key của bạn (copy từ .env.example nếu chưa có).")
        _client = anthropic.Anthropic()
    return _client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )


def run_agent(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    # TODO 3: viết vòng lặp agent theo pseudocode slide 27.
    #
    #   for step in range(1, MAX_ITERATIONS + 1):
    #       1. response = call_model(messages)
    #       2. Thêm lượt của model vào lịch sử:
    #              messages.append({"role": "assistant", "content": response.content})
    #       3. Lấy text của model: nối b.text của các block có b.type == "text"
    #       4. Nếu response.stop_reason != "tool_use": model đã trả lời xong -> return text
    #       5. Ngược lại, in "Thought {step}: {text}", rồi với MỖI block có b.type == "tool_use":
    #              - in "Action {step}: {b.name}({b.input})"
    #              - result = run_tool(b.name, b.input)
    #              - in "Observation {step}: {result}"
    #              - gom lại: {"type": "tool_result", "tool_use_id": b.id, "content": result}
    #       6. Gửi TẤT CẢ kết quả tool về cho model trong MỘT lượt:
    #              messages.append({"role": "user", "content": <danh sách tool_result>})
    #
    #   Hết vòng for mà chưa return (chạm MAX_ITERATIONS) -> return 1 câu xin lỗi, báo agent đã dừng.
    raise NotImplementedError("TODO 3")


def main() -> None:
    try:
        if len(sys.argv) > 1:
            print("Final Answer:", run_agent(" ".join(sys.argv[1:])))
            return
        while (q := input("\nBạn> ").strip()).lower() not in {"exit", "quit", ""}:
            print("Final Answer:", run_agent(q))
    except anthropic.AuthenticationError:
        sys.exit("API key không hợp lệ. Kiểm tra lại ANTHROPIC_API_KEY trong file .env.")
    except anthropic.APIError as e:
        sys.exit(f"Lỗi khi gọi API: {e}")


if __name__ == "__main__":
    main()
