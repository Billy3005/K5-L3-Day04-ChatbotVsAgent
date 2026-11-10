"""Chạy agent trên dataset, chấm tự động, xuất report.md (để đọc) và report.json (để so sánh các lần chạy).

    python evaluate.py                    # chạy cả 20 câu
    python evaluate.py --level edge       # chỉ 1 mức: easy | medium | hard | edge
    python evaluate.py --ids E1,M2,X4     # chỉ vài câu (tiết kiệm token khi đang sửa lỗi)

Cần làm xong 3 TODO và có API key. Mỗi câu tốn khoảng 1–6 lượt gọi model.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
import time
from datetime import datetime

import agent
from dataset import build_cases

LEVELS = ["easy", "medium", "hard", "edge"]


def _has(answer: str, phrase: str) -> bool:
    """So khớp nguyên từ, không phân biệt hoa thường."""
    return re.search(rf"(?<!\w){re.escape(phrase.lower())}(?!\w)", answer.lower()) is not None


def check(kind: str, value, answer: str, calls: list[tuple[str, dict]]) -> bool:
    names = [n for n, _ in calls]
    if kind == "no_tools":
        return not calls
    if kind == "calls":
        return all(t in names for t in value)
    if kind == "contains":
        return any(_has(answer, p) for p in value)
    if kind == "not_contains":
        return not any(_has(answer, p) for p in value)
    if kind == "arg":
        tool, key, test = value
        for n, a in calls:
            try:
                if n == tool and key in a and test(a[key]):
                    return True
            except (TypeError, ValueError):
                continue
        return False
    if kind == "arg_all":
        tool, key, wanted = value
        return wanted <= {a.get(key) for n, a in calls if n == tool}
    raise ValueError(f"Loại check không hợp lệ: {kind}")


def run_case(case: dict) -> dict:
    """Chạy agent trên 1 câu hỏi, ghi lại mọi lần gọi tool / model, rồi chấm."""
    calls: list[tuple[str, dict]] = []
    stats = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "tool_errors": 0}
    real_run_tool, real_call_model = agent.run_tool, agent.call_model

    def spy_tool(name, args):
        calls.append((name, dict(args)))
        out = real_run_tool(name, args)
        stats["tool_errors"] += str(out).startswith("ERROR")
        return out

    def spy_model(messages):
        stats["model_calls"] += 1
        resp = real_call_model(messages)
        usage = getattr(resp, "usage", None)
        stats["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
        stats["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
        return resp

    agent.run_tool, agent.call_model = spy_tool, spy_model
    log, error = io.StringIO(), ""
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(log):
            answer = agent.run_agent(case["question"]) or ""
    except (Exception, SystemExit) as e:  # noqa: BLE001  (SystemExit: agent báo thiếu API key)
        answer, error = "", f"{type(e).__name__}: {e}"
    finally:
        agent.run_tool, agent.call_model = real_run_tool, real_call_model

    results = [(desc, check(kind, value, answer, calls)) for desc, kind, value in case["checks"]]
    passed = sum(ok for _, ok in results)
    verdict = "PASS" if passed == len(results) and not error else ("PARTIAL" if passed and not error else "FAIL")
    return {"id": case["id"], "level": case["level"], "question": case["question"], "verdict": verdict,
            "checks": [{"check": d, "ok": ok} for d, ok in results], "answer": answer, "error": error,
            "tools": [n for n, _ in calls], "tool_calls": calls, "latency_s": round(time.perf_counter() - t0, 2),
            **stats, "trace": log.getvalue()}


# ---------------------------------------------------------------- report
def summarize(rows: list[dict]) -> dict:
    def agg(rs):
        n = len(rs) or 1
        return {"cases": len(rs), "pass": sum(r["verdict"] == "PASS" for r in rs),
                "partial": sum(r["verdict"] == "PARTIAL" for r in rs), "fail": sum(r["verdict"] == "FAIL" for r in rs),
                "avg_model_calls": round(sum(r["model_calls"] for r in rs) / n, 1),
                "avg_tool_calls": round(sum(len(r["tools"]) for r in rs) / n, 1),
                "avg_tokens": round(sum(r["input_tokens"] + r["output_tokens"] for r in rs) / n),
                "avg_latency_s": round(sum(r["latency_s"] for r in rs) / n, 1)}
    return {"overall": agg(rows), **{lv: agg([r for r in rows if r["level"] == lv]) for lv in LEVELS
                                     if any(r["level"] == lv for r in rows)}}


def write_reports(rows: list[dict], summary: dict) -> None:
    meta = {"run_at": f"{datetime.now():%Y-%m-%d %H:%M}", "model": agent.MODEL, "max_iterations": agent.MAX_ITERATIONS}
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump({**meta, "summary": summary, "cases": rows}, f, ensure_ascii=False, indent=2, default=str)

    o = summary["overall"]
    L = ["# Report: ReAct agent trên dataset", "",
         f"_Chạy lúc {meta['run_at']} · model `{meta['model']}` · MAX_ITERATIONS = {meta['max_iterations']}_", "",
         f"**Kết quả: {o['pass']}/{o['cases']} PASS** ({o['partial']} PARTIAL, {o['fail']} FAIL)", "",
         "## 1. Tổng hợp theo mức độ", "",
         "| Mức | PASS | PARTIAL | FAIL | Lượt gọi model TB | Lượt gọi tool TB | Token TB | Thời gian TB |",
         "|---|---|---|---|---|---|---|---|"]
    for lv, s in summary.items():
        L.append(f"| {'**tổng**' if lv == 'overall' else lv} | {s['pass']}/{s['cases']} | {s['partial']} | {s['fail']} "
                 f"| {s['avg_model_calls']} | {s['avg_tool_calls']} | {s['avg_tokens']} | {s['avg_latency_s']}s |")
    L += ["", "## 2. Từng câu hỏi", "",
          "| ID | Mức | Câu hỏi | Kết quả | Tool đã gọi | Lượt model | Token | Thời gian |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['id']} | {r['level']} | {r['question']} | {r['verdict']} | {', '.join(r['tools']) or '—'} "
                 f"| {r['model_calls']} | {r['input_tokens'] + r['output_tokens']} | {r['latency_s']}s |")
    L += ["", "## 3. Chi tiết và trace", ""]
    for r in rows:
        L += [f"### {r['id']} ({r['level']}): {r['verdict']}", "", f"**Câu hỏi:** {r['question']}", ""]
        L += [f"- {'✅' if c['ok'] else '❌'} {c['check']}" for c in r["checks"]]
        if r["error"]:
            L.append(f"- ⚠️ Lỗi khi chạy: `{r['error']}`")
        L += ["", "**Câu trả lời:**", "", "> " + (r["answer"] or "(trống)").replace("\n", "\n> "), "",
              "<details><summary>Trace</summary>", "", "```", r["trace"].strip() or "(không có)", "```", "",
              "</details>", ""]
    L += ["## 4. Nhận xét (bạn tự viết)", "",
          "- Agent làm tốt ở mức nào, kém ở mức nào? Vì sao?",
          "- Chọn 1 case FAIL hoặc PARTIAL, đọc trace: agent sai ở bước nào (Thought, Action hay Observation)?",
          "- Bạn sửa gì (system prompt, description của tool, hay code) để case đó PASS? Chạy lại để kiểm chứng.", ""]
    with open("report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def main() -> None:
    ap = argparse.ArgumentParser(description="Chạy agent trên dataset và xuất report.md + report.json")
    ap.add_argument("--level", choices=LEVELS, help="Chỉ chạy 1 mức độ")
    ap.add_argument("--ids", default="", help="Chỉ chạy vài câu, vd. E1,M2,X4")
    args = ap.parse_args()

    ids = {i.strip().upper() for i in args.ids.split(",") if i.strip()}
    cases = [c for c in build_cases() if (not args.level or c["level"] == args.level) and (not ids or c["id"] in ids)]
    if not cases:
        sys.exit("Không có câu hỏi nào khớp bộ lọc.")

    rows = []
    for c in cases:
        print(f"{c['id']:<3} [{c['level']:<6}] {c['question'][:58]:<58} ", end="", flush=True)
        r = run_case(c)
        if r["error"].startswith("NotImplementedError"):
            sys.exit(f"\n{r['error']} chưa làm. Làm xong 3 TODO (kiểm tra bằng python check.py) rồi chạy lại.")
        if r["error"].startswith(("AuthenticationError", "SystemExit")):
            sys.exit(f"\nKhông gọi được model: {r['error'].split(': ', 1)[-1]}")
        print(f"{r['verdict']:<7} ({r['model_calls']} lượt, {r['latency_s']}s)")
        rows.append(r)

    summary = summarize(rows)
    write_reports(rows, summary)
    o = summary["overall"]
    print(f"\n{o['pass']}/{o['cases']} PASS · {o['partial']} PARTIAL · {o['fail']} FAIL")
    for lv in LEVELS:
        if lv in summary:
            print(f"  {lv:<7} {summary[lv]['pass']}/{summary[lv]['cases']}")
    print("Chi tiết: report.md (đọc) · report.json (dữ liệu thô)")


if __name__ == "__main__":
    main()
