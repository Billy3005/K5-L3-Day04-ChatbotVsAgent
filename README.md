# Bài tập Ngày 4: Tự viết một ReAct agent từ đầu

Bạn sẽ tự tay làm 2 phần cốt lõi của một agent, không dùng framework:

1. **Tool:** "tay chân" để agent làm việc thật.
2. **Agent loop:** vòng lặp Thought → Action → Observation.

Sau đó chấm agent của mình trên bộ 20 câu hỏi, từ dễ đến khó, và đọc report để tìm chỗ agent sai.

Agent trong bài là trợ lý du lịch: hỏi *"Ngày mai ở Đà Nẵng nên mặc gì?"*, agent tự tra ngày, tra thời tiết, rồi gợi ý trang phục.

## Ý tưởng

Một agent không có gì bí ẩn. Nó chỉ gồm 3 thứ:

```
Agent = LLM (bộ não) + Tools (tay chân) + Loop (vòng lặp nối hai thứ đó lại)
```

- **LLM** quyết định bước tiếp theo: trả lời luôn, hay cần gọi tool nào, với tham số gì.
- **Tool** là code Python bình thường, làm việc thật (tra ngày, tra thời tiết...). LLM không tự chạy được tool, nó chỉ *yêu cầu* gọi.
- **Loop** là phần code của bạn: nhận yêu cầu từ LLM → chạy tool → gửi kết quả lại → hỏi LLM tiếp, cho tới khi LLM trả lời xong.

Framework như LangChain hay LangGraph làm hộ phần **Loop**. Bài này bắt bạn tự viết nó, để hiểu framework đang làm gì bên dưới.

### Kiến trúc tổng thể

Ô viền cam là phần bạn tự viết (TODO).

```mermaid
flowchart LR
    U(["Người dùng"]) -->|"câu hỏi"| L

    subgraph AG["agent.py"]
        P["SYSTEM_PROMPT"]
        L["Agent loop<br/>TODO 3"]
        P -.->|"gửi kèm mỗi lần gọi"| L
    end

    L <-->|"messages + schema TOOLS<br/>trả về: text hoặc tool_use"| M[("Claude API")]
    L -->|"run_tool(name, args)"| R

    subgraph TL["tools.py"]
        S["TOOLS: schema<br/>TODO 2"]
        R["run_tool()"]
        F1["get_current_date"]
        F2["get_weather"]
        F3["recommend_outfit<br/>TODO 1"]
        R --> F1 & F2 & F3
    end

    R -->|"JSON hoặc ERROR: ..."| L
    L -->|"Final Answer"| U

    classDef todo fill:#FFF4E5,stroke:#E8710A,stroke-width:2px,color:#000
    class L,S,F3 todo
```

- **Schema** (TODO 2) là thứ duy nhất LLM nhìn thấy về tool. Thiếu schema, LLM không biết tool tồn tại dù hàm đã viết xong.
- **`run_tool()`** luôn trả về chuỗi. Khi tool lỗi, nó trả `ERROR: ...` thay vì làm sập chương trình, để LLM đọc lỗi và tự sửa tham số.

## Repo có gì

| File | Nội dung |
|---|---|
| `tools.py` | 2 tool mẫu đã viết sẵn (`get_current_date`, `get_weather`) và **TODO 1, TODO 2** |
| `agent.py` | System prompt, hàm gọi model và **TODO 3** |
| `check.py` | Tự kiểm tra 3 TODO, không cần API key |
| `dataset.py` | 20 câu hỏi test, chia 4 mức: easy, medium, hard, edge |
| `evaluate.py` | Chạy agent trên dataset, chấm tự động, xuất `report.md` và `report.json` |
| `run.sh` | Chạy mọi thứ bằng 1 lệnh (Mac, Linux) |

## Bắt đầu

Yêu cầu Python 3.10 trở lên.

```bash
git clone https://github.com/VinUni-AI20k/K5-L3-Day04-ChatbotVsAgent.git
cd K5-L3-Day04-ChatbotVsAgent
./run.sh setup
```

`setup` tạo môi trường `.venv`, cài thư viện và tạo file `.env`. Mở `.env` và điền `ANTHROPIC_API_KEY` của bạn.

Các lệnh dùng trong bài:

| Lệnh | Làm gì | Cần API key? |
|---|---|---|
| `./run.sh check` | Kiểm tra 3 TODO | Không |
| `./run.sh ask "Ngày mai ở Đà Nẵng nên mặc gì?"` | Hỏi agent 1 câu, xem trace | Có |
| `./run.sh eval` | Chấm agent trên cả 20 câu, xuất report | Có |
| `./run.sh eval --level edge` | Chỉ chạy 1 mức: `easy`, `medium`, `hard`, `edge` | Có |
| `./run.sh eval --ids E2,M3` | Chỉ chạy vài câu (tiết kiệm token khi đang sửa lỗi) | Có |

**Windows, hoặc không muốn dùng script:** cài thủ công rồi gọi thẳng Python.

```bash
python -m venv .venv
.venv\Scripts\activate          # Mac / Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Mac / Linux: cp .env.example .env, rồi điền ANTHROPIC_API_KEY

python check.py                  # = ./run.sh check
python agent.py "Ngày mai ở Đà Nẵng nên mặc gì?"   # = ./run.sh ask "..."
python evaluate.py --level edge  # = ./run.sh eval --level edge
```

## Bước 1: Làm 3 TODO

Hướng dẫn chi tiết nằm ngay trong code.

| TODO | File | Việc cần làm | Slide |
|---|---|---|---|
| 1 | `tools.py` | Viết hàm `recommend_outfit`: gợi ý trang phục theo nhiệt độ và khả năng mưa | 34 |
| 2 | `tools.py` | Khai báo schema cho `recommend_outfit` để model biết khi nào gọi, gọi thế nào | 29 |
| 3 | `agent.py` | Viết vòng lặp agent: gọi model → chạy tool → gửi kết quả về → lặp | 27, 30 |

Sau mỗi TODO, chạy `./run.sh check`. Làm xong TODO nào thì dòng đó chuyển ✓.

### Vòng lặp bạn sẽ viết ở TODO 3

Đây là pseudocode slide 27 vẽ thành flowchart. Một vòng = **Thought + Action** (model quyết định) rồi **Observation** (kết quả tool gửi về).

```mermaid
flowchart TD
    Q(["Câu hỏi của người dùng"]) --> INIT["messages = [câu hỏi]"]
    INIT --> LIM{"step ≤ MAX_ITERATIONS?"}
    LIM -->|"hết vòng"| STOP(["Dừng an toàn:<br/>báo đã chạm giới hạn"])
    LIM -->|"còn vòng"| CALL["response = call_model(messages)<br/><i>Thought + Action</i>"]
    CALL --> SAVE["messages += lượt assistant<br/>(nguyên response.content)"]
    SAVE --> DEC{"stop_reason == tool_use?"}
    DEC -->|"không"| FIN(["Final Answer:<br/>trả về text của model"])
    DEC -->|"có"| RUN["Với MỖI block tool_use:<br/>result = run_tool(name, input)<br/><i>Observation</i>"]
    RUN --> BACK["messages += 1 lượt user<br/>chứa TẤT CẢ tool_result"]
    BACK --> LIM

    classDef todo fill:#FFF4E5,stroke:#E8710A,stroke-width:2px,color:#000
    class INIT,LIM,CALL,SAVE,DEC,RUN,BACK todo
```

`MAX_ITERATIONS` là safeguard (slide 30): dù model có "kẹt", vòng lặp vẫn chắc chắn dừng.

## Bước 2: Chạy thử agent

```bash
./run.sh ask "Ngày mai ở Đà Nẵng nên mặc gì?"
```

Bên dưới, một câu hỏi chạy qua hệ thống như sau. Mỗi lần model trả `tool_use` là thêm một vòng lặp:

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant A as agent.py (loop)
    participant M as Claude
    participant T as tools.py

    U->>A: Ngày mai ở Đà Nẵng nên mặc gì?
    Note over A,T: Vòng 1
    A->>M: messages + TOOLS
    M-->>A: Thought: cần biết ngày mai + tool_use get_current_date
    A->>T: run_tool("get_current_date")
    T-->>A: tomorrow = 2026-11-11
    Note over A,T: Vòng 2
    A->>M: tool_result
    M-->>A: tool_use get_weather(Đà Nẵng, 2026-11-11)
    A->>T: run_tool("get_weather")
    T-->>A: temp_high_c = 33, rain_probability = 0.3
    Note over A,T: Vòng 3
    A->>M: tool_result
    M-->>A: tool_use recommend_outfit(33, 0.3)
    A->>T: run_tool("recommend_outfit")
    T-->>A: items = [áo thun mỏng, vải cotton]
    Note over A,T: Vòng 4
    A->>M: tool_result
    M-->>A: stop_reason = end_turn, câu trả lời
    A-->>U: Final Answer
```

Trên terminal, bạn sẽ thấy trace dạng:

```
Thought 1: Cần biết ngày mai là ngày nào.
Action 1: get_current_date({})
Observation 1: {"today": "...", "tomorrow": "..."}
Thought 2: ...
Action 2: get_weather({"city": "Đà Nẵng", "date": "..."})
...
Final Answer: ...
```

## Bước 3: Chấm trên dataset và đọc report

```bash
./run.sh eval
```

| Mức | Số câu | Ví dụ | Kiểm tra gì |
|---|---|---|---|
| easy | 5 | "Xin chào", "Hôm nay là ngày bao nhiêu?" | Không gọi tool thừa; gọi đúng 1 tool |
| medium | 5 | "Ngày mai ở Hà Nội nên mặc gì?" | Gọi đủ chuỗi tool, đúng ngày, đúng số liệu |
| hard | 5 | "Trong 4 thành phố, ngày mai nơi nào nóng nhất?" | Tra nhiều nơi hoặc nhiều ngày, rồi so sánh |
| edge | 5 | Thành phố không có dữ liệu, ngày sai, user đưa "70%", user bảo "cứ đoán đại" | Không bịa, đổi đúng đơn vị, xử lý lỗi |

Luồng chấm điểm:

```mermaid
flowchart LR
    D["dataset.py<br/>20 câu + điều kiện chấm<br/>đáp án tính từ tools"] --> E["evaluate.py"]
    E -->|"chạy từng câu"| A["agent.run_agent()"]
    A -.->|"ghi lại: tool đã gọi,<br/>số lượt model, token, trace"| E
    E --> G{"Chấm từng điều kiện<br/>gọi đúng tool? đúng số liệu?<br/>không bịa?"}
    G --> R1["report.md<br/>bảng tổng hợp + trace"]
    G --> R2["report.json<br/>dữ liệu thô"]
    R1 --> FIX["Đọc trace, sửa<br/>prompt / tool / loop"]
    FIX -->|"chạy lại: --ids"| E
```

Đáp án đúng được tính thẳng từ dữ liệu của tool, nên không cần LLM chấm. Mỗi câu nhận 1 trong 3 kết quả: **PASS** (đúng hết), **PARTIAL** (đúng một phần), **FAIL**.

Kết quả ghi ra 2 file:

- **`report.md`:** bảng tổng hợp theo mức độ (PASS, lượt gọi model, số tool, token, thời gian), kết quả từng câu kèm câu trả lời và trace, và 3 câu hỏi để bạn tự nhận xét.
- **`report.json`:** cùng dữ liệu dạng thô, để so sánh giữa các lần chạy (vd. trước và sau khi sửa prompt).

Muốn thêm câu hỏi của riêng bạn: thêm 1 dict vào cuối danh sách trong `dataset.py`, theo đúng mẫu các câu có sẵn.

## Câu hỏi suy nghĩ

1. Chọn 1 câu FAIL hoặc PARTIAL trong report. Đọc trace: agent sai ở Thought, Action hay Observation? Sửa system prompt hoặc description của tool rồi chạy lại câu đó (`./run.sh eval --ids <ID>`).
2. Xóa `get_current_date` khỏi `TOOLS` rồi chạy `./run.sh eval --level medium`. Điểm thay đổi thế nào? Vì sao?
3. Đặt `MAX_ITERATIONS = 2` trong `agent.py` rồi chạy `./run.sh eval --level hard`. Chuyện gì xảy ra? Vì sao agent cần giới hạn này?
