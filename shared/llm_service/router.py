from typing import Optional


class LLMRouter:
    """Placeholder LLM router per ADR-0014.
    Exposes `complete` with task_type and prompt. Not wired for Block 0a.
    """

    def __init__(self):
        pass

    def complete(self, task_type: str, prompt: str, user_id: Optional[int] = None) -> str:
        return f"[LLM stub] task={task_type} user={user_id}: {prompt[:80]}..."

