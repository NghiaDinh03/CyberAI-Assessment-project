import re
import json
import logging

logger = logging.getLogger(__name__)

def repair_json_string(content: str) -> str:
    """Tự động sửa lỗi cú pháp JSON thường gặp từ các mô hình LLM yếu/chạy CPU.
    
    Các lỗi xử lý:
    1. Trích xuất đúng mảng JSON [...] hoặc đối tượng JSON {...} từ văn bản bao quanh.
    2. Thay thế single quotes (') bằng double quotes (").
    3. Đổi Python values (None, True, False) thành JSON values (null, true, false).
    4. Loại bỏ trailing commas (dấu phẩy thừa ở cuối danh sách/đối tượng).
    5. Vá các dấu ngoặc đóng bị thiếu (}, ]) ở cuối chuỗi do model bị truncate/ngắt nửa chừng.
    6. Xử lý ký tự xuống dòng thừa trong các chuỗi string JSON.
    """
    if not content or not isinstance(content, str):
        return ""
        
    cleaned = content.strip()
    is_originally_array = cleaned.startswith('[') or '[' in cleaned
    
    # 1. Trích xuất phần JSON bằng Regex
    # Thử tìm mảng JSON trước (vì GAP analysis trả về mảng)
    array_match = re.search(r'(\[.*\])', cleaned, re.DOTALL)
    if array_match:
        cleaned = array_match.group(1)
    else:
        # Thử tìm đối tượng JSON
        obj_match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
        if obj_match:
            cleaned = obj_match.group(1)
            
    # 2. Xử lý các dấu ngoặc bị thiếu ở cuối chuỗi do model bị ngắt (Truncated JSON)
    # Đếm số lượng ngoặc để tự động vá
    open_brackets = cleaned.count('[')
    close_brackets = cleaned.count(']')
    open_braces = cleaned.count('{')
    close_braces = cleaned.count('}')
    
    # Vá ngoặc nhọn
    if open_braces > close_braces:
        cleaned += '}' * (open_braces - close_braces)
    # Vá ngoặc vuông
    if open_brackets > close_brackets:
        cleaned += ']' * (open_brackets - close_brackets)
        
    # 3. Sửa single quotes thành double quotes
    cleaned = re.sub(r"\'(\s*[\{\}\[\]\:]\s*)\'", r'"\1"', cleaned)
    cleaned = re.sub(r"(\{|\[|\,)\s*\'", r'\1 "', cleaned)
    cleaned = re.sub(r"\'\s*(\}|\]|\,|\:)", r'"\1', cleaned)
    
    # 4. Thay Python literal bằng JSON literal
    cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
    cleaned = re.sub(r'\bFalse\b', 'false', cleaned)
    cleaned = re.sub(r'\bNone\b', 'null', cleaned)
    
    # 5. Loại bỏ trailing commas (dấu phẩy thừa trước ngoặc đóng)
    cleaned = re.sub(r',\s*\]', ']', cleaned)
    cleaned = re.sub(r',\s*\}', '}', cleaned)
    
    # 6. Sửa lỗi xuống dòng bất hợp lý trong các giá trị chuỗi
    def remove_newlines_in_quotes(match):
        return match.group(0).replace('\n', ' ').replace('\r', '')
    
    cleaned = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', remove_newlines_in_quotes, cleaned)
    
    # Thử parse thử bằng json.loads để kiểm tra
    try:
        parsed = json.loads(cleaned)
        # Nếu ban đầu là array nhưng giờ chỉ parse ra dict đơn lẻ, tự bọc lại thành array
        if is_originally_array and isinstance(parsed, dict):
            cleaned = '[' + cleaned + ']'
        return cleaned
    except Exception as e:
        logger.debug(f"JSON repair failed simple rules: {e}. Trying aggressive repair.")
        
    # Cứu nguy khẩn cấp (Aggressive Repair) nếu vẫn lỗi:
    if is_originally_array or cleaned.startswith('['):
        # Trích xuất tất cả các block nhọn hoàn chỉnh {...}
        matches = re.findall(r'(\{[^\{\}]*\})', cleaned)
        valid_parts = []
        for match_str in matches:
            try:
                json.loads(match_str)
                valid_parts.append(match_str)
            except Exception:
                continue
        if valid_parts:
            cleaned = '[' + ', '.join(valid_parts) + ']'
            return cleaned
            
    return cleaned
