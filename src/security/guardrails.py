"""
Security Guardrails for LuatCheck
Bảo vệ biên an toàn hệ thống, gắn thẻ dữ liệu không tin cậy và phát hiện tấn công Prompt Injection
"""
import re
from typing import Tuple, Dict, Any, Optional


class SecurityGuardrails:
    # Các mẫu tấn công Direct & Indirect Prompt Injection phổ biến
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"bỏ\s+qua\s+(hết\s+)?(mọi\s+)?(quy\s+định|chỉ\s+dẫn|hướng\s+dẫn)\s+trước",
        r"you\s+are\s+now\s+in\s+developer\s+mode",
        r"hãy\s+đóng\s+vai\s+(hacker|công\s+tố\s+viên|luật\s+sư\s+tối\s+thượng)",
        r"(print|reveal|show|dump)\s+(system\s+prompt|hidden\s+instructions)",
        r"(tiết\s+lộ|hiển\s+thị|in\s+ra)\s+(prompt\s+hệ\s+thống|chỉ\s+dẫn\s+gốc)",
        r"(hướng\s+dẫn|chỉ\s+(cho\s+)?|bày\s+(cho\s+)?)?.*(trốn\s+thuế|trốn\s+đóng\s+bảo\s+hiểm|lách\s+luật)",
        r"gửi\s+(toàn\s+bộ\s+)?(dữ\s+liệu|thông\s+tin)\s+ra\s+ngoài"
    ]

    @classmethod
    def check_input_safety(cls, user_query: str, pasted_doc: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Kiểm tra an toàn đầu vào trước khi chuyển vào Agent ReAct Loop
        """
        combined_text = f"{user_query} {pasted_doc or ''}".lower()

        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return False, (
                    "CẢNH BÁO AN NINH: Phát hiện dấu hiệu tấn công Prompt Injection hoặc yêu cầu vi phạm đạo đức / lách luật. "
                    "Hệ thống tự động kích hoạt cơ chế từ chối an toàn (Safety Refusal)."
                )

        return True, None

    @classmethod
    def wrap_untrusted_input(cls, user_query: str, pasted_doc: Optional[str] = None) -> str:
        """
        Bao gói dữ liệu đầu vào trong ranh giới bảo mật nghiêm ngặt
        """
        wrapped = f"[UNTRUSTED_USER_QUERY]\n{user_query.strip()}\n[/UNTRUSTED_USER_QUERY]"
        if pasted_doc and pasted_doc.strip():
            wrapped += f"\n\n[UNTRUSTED_PASTED_DOCUMENT]\n{pasted_doc.strip()}\n[/UNTRUSTED_PASTED_DOCUMENT]"
        return wrapped
