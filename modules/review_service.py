from __future__ import annotations

from datetime import datetime

from modules.database import get_connection
from modules.review_algorithm import calculate_review


def get_today_queue(
    daily_new_limit: int,
    daily_review_limit: int = 200,
) -> list[dict]:
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as connection:
        due_rows = connection.execute(
            """
            SELECT
                w.*,
                ls.status,
                ls.mastery_level,
                ls.total_reviews,
                ls.next_review_at,
                'review' AS task_type
            FROM learning_status ls
            JOIN words w ON w.id = ls.word_id
            WHERE ls.status != 'new'
              AND ls.next_review_at IS NOT NULL
              AND ls.next_review_at <= ?
            ORDER BY ls.next_review_at ASC
            LIMIT ?
            """,
            (now, int(daily_review_limit)),
        ).fetchall()

        new_rows = connection.execute(
            """
            SELECT
                w.*,
                ls.status,
                ls.mastery_level,
                ls.total_reviews,
                ls.next_review_at,
                'new' AS task_type
            FROM learning_status ls
            JOIN words w ON w.id = ls.word_id
            WHERE ls.status = 'new'
            ORDER BY
                w.chapter ASC,
                COALESCE(w.original_number, 999999) ASC,
                w.id ASC
            LIMIT ?
            """,
            (int(daily_new_limit),),
        ).fetchall()

    return [dict(row) for row in due_rows] + [dict(row) for row in new_rows]


def submit_review(
    word_id: int,
    result: str,
    question_type: str = "english_to_chinese",
) -> None:
    now = datetime.now()
    now_text = now.isoformat(timespec="seconds")

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM learning_status
            WHERE word_id = ?
            """,
            (int(word_id),),
        ).fetchone()

        if row is None:
            raise ValueError("找不到该单词的学习状态。")

        old_level = int(row["mastery_level"])
        decision = calculate_review(old_level, result, now)

        first_learned_at = row["first_learned_at"] or now_text

        correct_delta = 1 if result in {"正确", "熟练"} else 0
        wrong_delta = 1 if result == "忘记" else 0
        fuzzy_delta = 1 if result == "模糊" else 0

        if decision.consecutive_correct_change == "increase":
            consecutive_correct = int(row["consecutive_correct"]) + 1
        else:
            consecutive_correct = 0

        difficult_flag = int(row["difficult_flag"])
        updated_wrong_count = int(row["wrong_count"]) + wrong_delta
        updated_fuzzy_count = int(row["fuzzy_count"]) + fuzzy_delta

        if updated_wrong_count >= 3 or updated_fuzzy_count >= 3:
            difficult_flag = 1

        connection.execute(
            """
            UPDATE learning_status
            SET
                status = ?,
                mastery_level = ?,
                first_learned_at = ?,
                last_review_at = ?,
                next_review_at = ?,
                total_reviews = total_reviews + 1,
                correct_count = correct_count + ?,
                wrong_count = wrong_count + ?,
                fuzzy_count = fuzzy_count + ?,
                consecutive_correct = ?,
                difficult_flag = ?
            WHERE word_id = ?
            """,
            (
                decision.status,
                decision.new_level,
                first_learned_at,
                now_text,
                decision.next_review_at.isoformat(timespec="seconds"),
                correct_delta,
                wrong_delta,
                fuzzy_delta,
                consecutive_correct,
                difficult_flag,
                int(word_id),
            ),
        )

        connection.execute(
            """
            INSERT INTO review_logs(
                word_id,
                reviewed_at,
                result,
                question_type,
                old_level,
                new_level,
                next_review_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(word_id),
                now_text,
                result,
                question_type,
                old_level,
                decision.new_level,
                decision.next_review_at.isoformat(timespec="seconds"),
            ),
        )
