"""Short-term per-chat memory + the provider history-merging helper."""
from app.llm.base import merge_history
from app.services.conversation_memory import ConversationMemory


def test_records_and_returns_turns_in_order():
    mem = ConversationMemory()
    mem.record_user(7, "halo")
    mem.record_assistant(7, "hai!")
    mem.record_user(7, "makan 25rb")
    assert mem.history(7) == [
        {"role": "user", "content": "halo"},
        {"role": "assistant", "content": "hai!"},
        {"role": "user", "content": "makan 25rb"},
    ]


def test_keeps_only_last_five_exchanges():
    mem = ConversationMemory(max_turns=5)
    for i in range(8):  # 8 exchanges = 16 messages, cap is 10
        mem.record_user(9, f"u{i}")
        mem.record_assistant(9, f"a{i}")
    hist = mem.history(9)
    assert len(hist) == 10                      # 5 exchanges
    assert hist[0] == {"role": "user", "content": "u3"}   # u0..u2 dropped
    assert hist[-1] == {"role": "assistant", "content": "a7"}


def test_isolated_per_chat():
    mem = ConversationMemory()
    mem.record_user(1, "a")
    mem.record_user(2, "b")
    assert mem.history(1) == [{"role": "user", "content": "a"}]
    assert mem.history(2) == [{"role": "user", "content": "b"}]


def test_merge_history_appends_current_prompt_and_alternates():
    history = [
        {"role": "user", "content": "makan 25rb"},
        {"role": "assistant", "content": "(kartu)"},
    ]
    merged = merge_history(history, "pakai gopay")
    assert merged == [
        {"role": "user", "content": "makan 25rb"},
        {"role": "assistant", "content": "(kartu)"},
        {"role": "user", "content": "pakai gopay"},
    ]


def test_merge_history_coalesces_consecutive_same_role():
    # Two user turns in a row (e.g. no assistant reply recorded between them)
    # must collapse into one so Claude's alternation rule isn't violated.
    history = [
        {"role": "assistant", "content": "leading — should be dropped"},
        {"role": "user", "content": "first"},
    ]
    merged = merge_history(history, "second")
    assert merged == [{"role": "user", "content": "first\nsecond"}]
