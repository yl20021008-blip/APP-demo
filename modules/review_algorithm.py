from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

VALID_RESULTS = {"忘记", "模糊", "正确", "熟练"}

REVIEW_INTERVALS_DAYS = {
    1: 1,
    2: 3,
    3: 7,
    4: 14,
    5: 30,
    6: 60,
}


@dataclass(frozen=True)
class ReviewDecision:
    new_level: int
    next_review_at: datetime
    status: str
    consecutive_correct_change: str


def calculate_review(
    current_level: int,
    result: str,
    now: datetime | None = None,
) -> ReviewDecision:
    if result not in VALID_RESULTS:
        raise ValueError(f"未知复习结果：{result}")

    now = now or datetime.now()
    current_level = max(0, min(int(current_level), 6))

    if result == "忘记":
        return ReviewDecision(
            new_level=0,
            next_review_at=now + timedelta(minutes=10),
            status="learning",
            consecutive_correct_change="reset",
        )

    if result == "模糊":
        new_level = max(1, current_level)
        return ReviewDecision(
            new_level=new_level,
            next_review_at=now + timedelta(days=1),
            status="reviewing",
            consecutive_correct_change="reset",
        )

    if result == "正确":
        new_level = min(current_level + 1, 6)
    else:
        new_level = min(current_level + 2, 6)

    days = REVIEW_INTERVALS_DAYS[new_level]
    status = "mastered" if new_level >= 5 else "reviewing"

    return ReviewDecision(
        new_level=new_level,
        next_review_at=now + timedelta(days=days),
        status=status,
        consecutive_correct_change="increase",
    )
