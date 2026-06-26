"""日期工具模块"""

from datetime import date, datetime


def format_date(d: date) -> str:
    """格式化 date 为 yyyy-MM-dd 字符串"""
    return d.strftime("%Y-%m-%d")


def parse_date(date_str: str) -> date:
    """将 yyyy-MM-dd 字符串解析为 date"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format (expected yyyy-MM-dd): {date_str}") from e


def days_between(start: date, end: date) -> int:
    """获取两个日期之间的天数"""
    return (end - start).days


def is_weekend(d: date) -> bool:
    """判断日期是否为周末"""
    return d.weekday() >= 5  # 5=Saturday, 6=Sunday
