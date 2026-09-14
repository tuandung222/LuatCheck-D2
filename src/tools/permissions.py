"""
Permission management and Access Control for LuatCheck Tools (Least Privilege Enforcement)
"""
from enum import Enum
from typing import Dict, Any, Tuple


class PermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"                   # Hoàn toàn tự động
    REVERSIBLE_WRITE = "REVERSIBLE_WRITE"     # Tự động ghi có nhật ký kiểm toán
    IRREVERSIBLE_WRITE = "IRREVERSIBLE_WRITE" # Bắt buộc Human-in-the-loop confirmation


TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
    "search_law": PermissionLevel.READ_ONLY,
    "get_article": PermissionLevel.READ_ONLY,
    "save_case": PermissionLevel.REVERSIBLE_WRITE,
    "send_summary": PermissionLevel.IRREVERSIBLE_WRITE,
}


class PermissionError(Exception):
    pass


class PermissionManager:
    """
    Cơ chế gác cổng phân quyền tối thiểu (Least Privilege Gatekeeper)
    """

    @staticmethod
    def check_permission(tool_name: str, args: Dict[str, Any], user_confirmed: bool = False) -> Tuple[bool, str]:
        level = TOOL_PERMISSIONS.get(tool_name)
        if not level:
            return False, f"Công cụ '{tool_name}' không tồn tại hoặc chưa được cấp phép."

        if level == PermissionLevel.IRREVERSIBLE_WRITE:
            if not user_confirmed:
                return False, (
                    f"CẢNH BÁO BẢO MẬT: Hành động '{tool_name}' là tác vụ ghi không khả hồi (Irreversible Egress). "
                    "Bắt buộc phải có sự xác nhận trực tiếp từ người dùng (Human-In-The-Loop Confirmation) trước khi thực thi!"
                )

        return True, "Authorized"
