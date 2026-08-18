import json
import sys
from utils.json_repair import repair_json_string

def test_repair_perfect_json():
    raw = 'Một số text trước [{"id": "A.5.1", "gap": "Không có"}] text sau'
    repaired = repair_json_string(raw)
    assert json.loads(repaired) == [{"id": "A.5.1", "gap": "Không có"}]

def test_repair_single_quotes():
    raw = "[{'id': 'A.5.1', 'gap': 'Không có'}]"
    repaired = repair_json_string(raw)
    assert json.loads(repaired) == [{"id": "A.5.1", "gap": "Không có"}]

def test_repair_python_literals():
    raw = '[{"id": "A.5.1", "implemented": True, "notes": None}]'
    repaired = repair_json_string(raw)
    assert json.loads(repaired) == [{"id": "A.5.1", "implemented": True, "notes": None}]

def test_repair_trailing_commas():
    raw = '[{"id": "A.5.1", "gap": "Không",},]'
    repaired = repair_json_string(raw)
    assert json.loads(repaired) == [{"id": "A.5.1", "gap": "Không"}]

def test_repair_missing_brackets():
    raw = '[{"id": "A.5.1", "gap": "Không có"'
    repaired = repair_json_string(raw)
    assert json.loads(repaired) == [{"id": "A.5.1", "gap": "Không có"}]

def test_repair_newlines_in_strings():
    raw = '[{"id": "A.5.1", "gap": "Dòng 1\nDòng 2"}]'
    repaired = repair_json_string(raw)
    parsed = json.loads(repaired)
    assert "Dòng 1" in parsed[0]["gap"]
    assert "Dòng 2" in parsed[0]["gap"]

def test_repair_aggressive_cut():
    raw = '[{"id": "A.5.1", "gap": "Đã đạt"}, {"id": "A.5.2", "gap": "Chưa '
    repaired = repair_json_string(raw)
    print(f"DEBUG aggressive_cut output: {repaired}")
    parsed = json.loads(repaired)
    print(f"DEBUG parsed list: {parsed}")
    assert len(parsed) == 1
    assert parsed[0]["id"] == "A.5.1"

if __name__ == "__main__":
    print("Chạy bộ kiểm thử JSON Repair...")
    try:
        test_repair_perfect_json()
        print("  - perfect_json: PASS")
        test_repair_single_quotes()
        print("  - single_quotes: PASS")
        test_repair_python_literals()
        print("  - python_literals: PASS")
        test_repair_trailing_commas()
        print("  - trailing_commas: PASS")
        test_repair_missing_brackets()
        print("  - missing_brackets: PASS")
        test_repair_newlines_in_strings()
        print("  - newlines_in_strings: PASS")
        test_repair_aggressive_cut()
        print("  - aggressive_cut: PASS")
        print("TẤT CẢ TESTS ĐỀU ĐẠT! 🎉")
    except AssertionError as e:
        print(f"TEST THẤT BẠI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"LỖI HỆ THỐNG KHI CHẠY TEST: {e}")
        sys.exit(1)
