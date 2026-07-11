"""Per-chat short-term memory: the last few user/assistant turns, so the bot
doesn't lose context between messages (e.g. follow-up questions, "yang tadi
ubah jadi 50rb", "iya betul").

In-memory only — fine for a single-process personal bot. If this ever needs
to survive restarts or scale horizontally, swap the dict for Redis (same
interface). Keyed by Telegram chat id.
"""
from __future__ import annotations

from collections import deque

# "5 chat terakhir" = the last 5 exchanges, i.e. up to 5 user + 5 assistant
# messages. deque(maxlen) transparently drops the oldest as new turns arrive.
_MAX_TURNS = 5


class ConversationMemory:
    def __init__(self, max_turns: int = _MAX_TURNS) -> None:
        self._store: dict[int, deque[dict[str, str]]] = {}
        self._maxlen = max_turns * 2  # user + assistant per turn

    def _dq(self, chat_id: int) -> deque[dict[str, str]]:
        dq = self._store.get(chat_id)
        if dq is None:
            dq = deque(maxlen=self._maxlen)
            self._store[chat_id] = dq
        return dq

    def record_user(self, chat_id: int, content: str) -> None:
        if content and content.strip():
            self._dq(chat_id).append({"role": "user", "content": content.strip()})

    def record_assistant(self, chat_id: int, content: str) -> None:
        if content and content.strip():
            self._dq(chat_id).append({"role": "assistant", "content": content.strip()})

    def history(self, chat_id: int) -> list[dict[str, str]]:
        """The turns BEFORE the message currently being handled, oldest first.
        Callers pass this straight into an LLM provider's `history` argument."""
        return list(self._store.get(chat_id, ()))

    def clear(self, chat_id: int) -> None:
        self._store.pop(chat_id, None)


conversation_memory = ConversationMemory()
