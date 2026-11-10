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

    for step in range(1, MAX_ITERATIONS + 1):
        response = call_model(messages)
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        text = "\n".join(
            block.text
            for block in response.content
            if block.type == "text"
        )

        if response.stop_reason != "tool_use":
            return text
        print(f"Thought {step}: {text}")

        tool_results = []

        for block in response.content:
            if block.type == "tool_use":

                print(f"Action {step}: {block.name}({block.input})")

                result = run_tool(block.name, block.input)

                print(f"Observation {step}: {result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
        messages.append({
            "role": "user",
            "content": tool_results
        })
    return "Xin lỗi, tôi đã dừng lại vì đạt giới hạn số vòng lặp xử lý."


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
