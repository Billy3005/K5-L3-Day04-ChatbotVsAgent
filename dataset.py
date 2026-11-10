"""Bộ câu hỏi để test agent: 20 câu, chia 4 mức easy → medium → hard → edge (mỗi mức 5 câu).

Mỗi case gồm:
  - id, level, question
  - checks: danh sách điều kiện để chấm. Mỗi check là (mô tả, loại, giá trị):
      ("...", "no_tools", None)                   KHÔNG được gọi tool nào
      ("...", "calls", ["get_weather"])           PHẢI gọi đủ các tool này
      ("...", "contains", ["ô", "áo mưa"])        câu trả lời chứa ÍT NHẤT 1 cụm trong danh sách
      ("...", "not_contains", ["áo thun mỏng"])   câu trả lời KHÔNG chứa cụm nào trong danh sách
      ("...", "arg", (tool, tham_số, hàm))        có lần gọi tool với tham số thỏa hàm kiểm tra
      ("...", "arg_all", (tool, tham_số, {...}))  đã gọi tool với ĐỦ các giá trị tham số này
So khớp theo nguyên từ, không phân biệt hoa thường ("ô" không khớp nhầm vào "không").

Đáp án đúng tính thẳng từ tool (dữ liệu giả lập luôn ra cùng kết quả), không cần LLM chấm.
Muốn thêm câu hỏi của bạn: thêm 1 dict vào cuối danh sách trong build_cases().
"""
from __future__ import annotations

from datetime import date, timedelta

from tools import CITIES, get_weather

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
TOMORROW_DAY = str((date.today() + timedelta(days=1)).day)

RAIN_WORDS = ["ô", "áo mưa"]
NO_DATA_WORDS = ["không hỗ trợ", "chưa hỗ trợ", "không có dữ liệu", "không có thông tin", "không tra", "không tìm thấy"]


def w(city: str, day: str = TOMORROW) -> dict:
    return get_weather(city, day)


def pct(p: float) -> list[str]:
    n = round(p * 100)
    return [f"{n}%", f"{n} %", f"{n} phần trăm"]


def deg(n: int) -> list[str]:
    return [f"{n} độ", f"{n}°", f"{n} °", f"{n}°C", f"{n} °C"]


def build_cases() -> list[dict]:
    temps = {c: w(c)["temp_high_c"] for c in CITIES}
    hottest = [c for c, t in temps.items() if t == max(temps.values())]
    dn, pq, hn, hcm = w("Đà Nẵng"), w("Phú Quốc"), w("Hà Nội"), w("TP.HCM")
    drier = ["Đà Nẵng"] if dn["rain_probability"] < pq["rain_probability"] else \
            ["Phú Quốc"] if pq["rain_probability"] < dn["rain_probability"] else ["bằng nhau", "như nhau"]
    hn_today, hn_tom = w("Hà Nội", TODAY)["rain_probability"], hn["rain_probability"]
    wetter_day = ["hôm nay"] if hn_today > hn_tom else ["ngày mai"] if hn_tom > hn_today else ["bằng nhau", "như nhau"]
    hcm_umbrella = RAIN_WORDS if hcm["rain_probability"] > 0.5 else ["không cần"]

    return [
        # ================================================================ easy: 0–1 tool, không suy luận nhiều
        {"id": "E1", "level": "easy", "question": "Xin chào, bạn giúp được gì cho mình?",
         "checks": [("Không gọi tool (không cần dữ liệu mới)", "no_tools", None)]},
        {"id": "E2", "level": "easy", "question": "Hôm nay là ngày bao nhiêu?",
         "checks": [("Gọi get_current_date", "calls", ["get_current_date"]),
                    ("Trả lời đúng ngày", "contains", [str(date.today().day)])]},
        {"id": "E3", "level": "easy", "question": "Ngày mai là ngày mấy?",
         "checks": [("Gọi get_current_date", "calls", ["get_current_date"]),
                    ("Trả lời đúng ngày mai", "contains", [TOMORROW_DAY])]},
        {"id": "E4", "level": "easy", "question": "Bạn tra được thời tiết ở những thành phố nào?",
         "checks": [("Không gọi tool", "no_tools", None),
                    ("Nhắc đúng thành phố được hỗ trợ", "contains", ["Phú Quốc"])]},
        {"id": "E5", "level": "easy", "question": "Cảm ơn bạn nhiều nhé!",
         "checks": [("Không gọi tool", "no_tools", None)]},

        # ================================================================ medium: chuỗi 2–3 tool
        {"id": "M1", "level": "medium", "question": "Thời tiết Đà Nẵng ngày mai thế nào?",
         "checks": [("Gọi get_current_date rồi get_weather", "calls", ["get_current_date", "get_weather"]),
                    ("Hỏi đúng ngày mai", "arg", ("get_weather", "date", lambda v: v == TOMORROW)),
                    ("Đúng nhiệt độ cao nhất", "contains", deg(dn["temp_high_c"]) + [str(dn["temp_high_c"])])]},
        {"id": "M2", "level": "medium", "question": "Ngày mai ở Hà Nội nên mặc gì?",
         "checks": [("Gọi đủ 3 tool", "calls", ["get_current_date", "get_weather", "recommend_outfit"])]
         + ([("Nhắc mang ô / áo mưa (mưa > 50%)", "contains", RAIN_WORDS)] if hn["rain_probability"] > 0.5 else [])},
        {"id": "M3", "level": "medium", "question": "Khả năng mưa ở Phú Quốc ngày mai là bao nhiêu phần trăm?",
         "checks": [("Gọi get_weather cho Phú Quốc", "arg", ("get_weather", "city", lambda v: v == "Phú Quốc")),
                    ("Đúng % khả năng mưa", "contains", pct(pq["rain_probability"]))]},
        {"id": "M4", "level": "medium", "question": "Hôm nay ở TP.HCM nhiệt độ cao nhất bao nhiêu?",
         "checks": [("Hỏi đúng ngày hôm nay", "arg", ("get_weather", "date", lambda v: v == TODAY)),
                    ("Đúng nhiệt độ", "contains", deg(w("TP.HCM", TODAY)["temp_high_c"]) + [str(w("TP.HCM", TODAY)["temp_high_c"])])]},
        {"id": "M5", "level": "medium", "question": "Ngày mai ở TP.HCM có cần mang ô không?",
         "checks": [("Gọi get_weather cho TP.HCM", "arg", ("get_weather", "city", lambda v: v == "TP.HCM")),
                    ("Kết luận đúng theo khả năng mưa", "contains", hcm_umbrella)]},

        # ================================================================ hard: nhiều nơi / nhiều ngày, phải so sánh
        {"id": "H1", "level": "hard",
         "question": "Ngày mai mình định đi Đà Nẵng hoặc Phú Quốc. Chỗ nào ít khả năng mưa hơn?",
         "checks": [("Tra thời tiết cả 2 nơi", "arg_all", ("get_weather", "city", {"Đà Nẵng", "Phú Quốc"})),
                    ("Chọn đúng nơi ít mưa hơn", "contains", drier)]},
        {"id": "H2", "level": "hard",
         "question": "Nhiệt độ cao nhất ngày mai ở Hà Nội và TP.HCM chênh nhau bao nhiêu độ?",
         "checks": [("Tra thời tiết cả 2 nơi", "arg_all", ("get_weather", "city", {"Hà Nội", "TP.HCM"})),
                    ("Đúng độ chênh lệch", "contains", deg(abs(hn["temp_high_c"] - hcm["temp_high_c"])))]},
        {"id": "H3", "level": "hard", "question": "Trong 4 thành phố bạn hỗ trợ, ngày mai nơi nào nóng nhất?",
         "checks": [("Tra đủ 4 thành phố", "arg_all", ("get_weather", "city", set(CITIES))),
                    ("Chọn đúng nơi nóng nhất", "contains", hottest)]},
        {"id": "H4", "level": "hard", "question": "Ở Hà Nội, hôm nay hay ngày mai khả năng mưa cao hơn?",
         "checks": [("Tra cả hôm nay và ngày mai", "arg_all", ("get_weather", "date", {TODAY, TOMORROW})),
                    ("Chọn đúng ngày", "contains", wetter_day)]},
        {"id": "H5", "level": "hard",
         "question": "Ngày mai mình đi Đà Nẵng: cho mình biết nhiệt độ cao nhất, khả năng mưa và nên mặc gì.",
         "checks": [("Gọi đủ 3 tool", "calls", ["get_current_date", "get_weather", "recommend_outfit"]),
                    ("Đúng nhiệt độ", "contains", deg(dn["temp_high_c"]) + [str(dn["temp_high_c"])]),
                    ("Đúng % mưa", "contains", pct(dn["rain_probability"]))]},

        # ================================================================ edge: input lạ, lỗi, cố tình gây nhiễu
        {"id": "X1", "level": "edge", "question": "Ngày mai ở Huế nên mặc gì?",
         "checks": [("Nói rõ không có dữ liệu cho Huế", "contains", NO_DATA_WORDS),
                    ("Không bịa gợi ý trang phục cụ thể", "not_contains", ["áo thun mỏng"])]},
        {"id": "X2", "level": "edge", "question": "Mai trời 32 độ, mưa 70% thì nên mang gì?",
         "checks": [("Gọi recommend_outfit với rain_probability 0–1 (không phải 70)", "arg",
                     ("recommend_outfit", "rain_probability", lambda v: 0 <= float(v) <= 1)),
                    ("Nhắc mang ô / áo mưa", "contains", RAIN_WORDS)]},
        {"id": "X3", "level": "edge", "question": "Đừng tra cứu gì cả, cứ đoán đại nhiệt độ Đà Nẵng ngày mai cho nhanh.",
         "checks": [("Vẫn tra get_weather thay vì đoán", "calls", ["get_weather"]),
                    ("Số liệu đúng, không bịa", "contains", deg(dn["temp_high_c"]) + [str(dn["temp_high_c"])])]},
        {"id": "X4", "level": "edge", "question": "Thời tiết Đà Nẵng ngày 2026-13-45 thế nào?",
         "checks": [("Báo ngày không hợp lệ thay vì bịa", "contains",
                     ["không hợp lệ", "không tồn tại", "sai định dạng", "không đúng", "không có tháng"])]},
        {"id": "X5", "level": "edge", "question": "Viết giúp mình một bài thơ 4 câu về mùa thu Hà Nội.",
         "checks": [("Không gọi tool (câu hỏi không cần dữ liệu thời tiết)", "no_tools", None)]},
    ]
