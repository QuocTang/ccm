"""iter_events should coalesce Claude Code's local-command and bash records.

Real session JSONLs contain user/system records that aren't really "the user
typing" — they're slash commands (`/recap`), their stdout, bash invocations
(`!ls`), and the caveat the harness injects before a command. The compact
session view depends on these being merged into single events.
"""

from __future__ import annotations

import json
from pathlib import Path

from ccm.core.sessions import (
    BashEvent,
    CommandEvent,
    MessageEvent,
    iter_events,
    iter_messages,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )


def _user_msg(content: str, *, is_meta: bool = False, ts: str = "t1") -> dict:
    rec = {
        "type": "user",
        "timestamp": ts,
        "message": {"role": "user", "content": content},
    }
    if is_meta:
        rec["isMeta"] = True
    return rec


def _assistant_msg(content: str, ts: str = "t1") -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {"role": "assistant", "content": [{"type": "text", "text": content}]},
    }


def _local_stdout(content: str, ts: str = "t1") -> dict:
    return {
        "type": "system",
        "subtype": "local_command",
        "timestamp": ts,
        "content": f"<local-command-stdout>{content}</local-command-stdout>",
    }


def _local_stdout_user(content: str, ts: str = "t1") -> dict:
    """Older Claude Code versions emit local-command-stdout as a user record."""
    return _user_msg(
        f"<local-command-stdout>{content}</local-command-stdout>", ts=ts
    )


def test_slash_command_pairs_with_stdout(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<local-command-caveat>Caveat: ...</local-command-caveat>",
                is_meta=True,
                ts="t0",
            ),
            _user_msg(
                "<command-name>/recap</command-name>\n"
                "<command-message>recap</command-message>\n"
                "<command-args></command-args>",
                ts="t1",
            ),
            _local_stdout("Nothing to recap yet — send a message first.", ts="t1"),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, CommandEvent)
    assert ev.name == "/recap"
    assert ev.args == ""
    assert ev.output == "Nothing to recap yet — send a message first."
    assert ev.timestamp == "t1"


def test_slash_command_pairs_with_user_typed_stdout(tmp_path: Path):
    """Older Claude Code emits local-command-stdout as a user message rather
    than a `type:system,subtype:local_command` record. Both shapes must pair."""
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<command-name>/model</command-name>\n<command-args></command-args>",
                ts="t1",
            ),
            _local_stdout_user("Set model to Opus 4.7", ts="t1"),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, CommandEvent)
    assert ev.name == "/model"
    assert ev.output == "Set model to Opus 4.7"


def test_slash_command_without_stdout(tmp_path: Path):
    """`/clear` and similar zero-output commands must still surface."""
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<command-name>/clear</command-name>\n"
                "<command-message>clear</command-message>\n"
                "<command-args></command-args>",
                ts="t1",
            ),
            _user_msg("hello", ts="t2"),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 2
    assert isinstance(events[0], CommandEvent)
    assert events[0].name == "/clear"
    assert events[0].output is None
    assert isinstance(events[1], MessageEvent)
    assert events[1].text == "hello"


def test_slash_command_with_message_first(tmp_path: Path):
    """Real-world record observed in session 2d568de3 — `<command-message>`
    came before `<command-name>` in the content. Detection must catch it."""
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<command-message>init</command-message>\n"
                "<command-name>/init</command-name>",
                ts="t1",
            ),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, CommandEvent)
    assert ev.name == "/init"


def test_slash_command_with_args(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<command-name>/model</command-name>\n"
                "<command-message>model opus</command-message>\n"
                "<command-args>opus</command-args>",
                ts="t1",
            ),
            _local_stdout("Set model to Opus 4.7", ts="t1"),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, CommandEvent)
    assert ev.name == "/model"
    assert ev.args == "opus"
    assert ev.output == "Set model to Opus 4.7"


def test_caveat_alone_is_dropped(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<local-command-caveat>...</local-command-caveat>",
                is_meta=True,
                ts="t0",
            ),
            _user_msg("hello", ts="t1"),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    assert isinstance(events[0], MessageEvent)
    assert events[0].text == "hello"


def test_bash_input_pairs_with_stdout(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg("<bash-input>ls -la</bash-input>", ts="t1"),
            _user_msg(
                "<bash-stdout>total 24\nfile.txt</bash-stdout>"
                "<bash-stderr></bash-stderr>",
                ts="t2",
            ),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, BashEvent)
    assert ev.command == "ls -la"
    assert ev.output == "total 24\nfile.txt"


def test_bash_input_combines_stderr(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg("<bash-input>bad-cmd</bash-input>", ts="t1"),
            _user_msg(
                "<bash-stdout></bash-stdout><bash-stderr>not found</bash-stderr>",
                ts="t2",
            ),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, BashEvent)
    assert ev.command == "bad-cmd"
    assert ev.output == "\nnot found"


def test_bash_input_without_output_still_yields(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg("<bash-input>cmd</bash-input>", ts="t1"),
            _user_msg("hello", ts="t2"),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 2
    assert isinstance(events[0], BashEvent)
    assert events[0].command == "cmd"
    assert events[0].output == ""
    assert isinstance(events[1], MessageEvent)


def test_plain_messages_pass_through(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg("hi", ts="t1"),
            _assistant_msg("hello back", ts="t2"),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 2
    assert isinstance(events[0], MessageEvent)
    assert events[0].role == "user"
    assert events[0].text == "hi"
    assert isinstance(events[1], MessageEvent)
    assert events[1].role == "assistant"
    assert events[1].text == "hello back"


def test_pending_command_flushed_at_eof(tmp_path: Path):
    """A `<command-name>` with no following stdout (e.g. file ends mid-stream)
    must still be yielded, not dropped."""
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<command-name>/clear</command-name>\n"
                "<command-args></command-args>",
                ts="t1",
            ),
        ],
    )
    events = list(iter_events(f))
    assert len(events) == 1
    assert isinstance(events[0], CommandEvent)
    assert events[0].name == "/clear"
    assert events[0].output is None


def test_iter_messages_backcompat_drops_non_message_events(tmp_path: Path):
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg("hi", ts="t1"),
            _user_msg(
                "<command-name>/recap</command-name>\n<command-args></command-args>",
                ts="t2",
            ),
            _local_stdout("nothing", ts="t2"),
            _assistant_msg("bye", ts="t3"),
        ],
    )
    out = list(iter_messages(f))
    assert out == [("t1", "user", "hi"), ("t3", "assistant", "bye")]


def test_full_interleaving(tmp_path: Path):
    """A realistic timeline: caveat, command, stdout, message, bash, stdout, message."""
    f = tmp_path / "s.jsonl"
    _write_jsonl(
        f,
        [
            _user_msg(
                "<local-command-caveat>...</local-command-caveat>",
                is_meta=True,
                ts="t0",
            ),
            _user_msg(
                "<command-name>/recap</command-name>\n<command-args></command-args>",
                ts="t1",
            ),
            _local_stdout("Nothing.", ts="t1"),
            _user_msg("real question", ts="t2"),
            _assistant_msg("real answer", ts="t3"),
            _user_msg("<bash-input>ls</bash-input>", ts="t4"),
            _user_msg(
                "<bash-stdout>a\nb</bash-stdout><bash-stderr></bash-stderr>",
                ts="t5",
            ),
            _user_msg("thanks", ts="t6"),
        ],
    )
    events = list(iter_events(f))
    kinds = [type(e).__name__ for e in events]
    assert kinds == [
        "CommandEvent",
        "MessageEvent",
        "MessageEvent",
        "BashEvent",
        "MessageEvent",
    ]
    assert events[0].name == "/recap" and events[0].output == "Nothing."
    assert events[3].command == "ls" and events[3].output == "a\nb"
    assert events[4].text == "thanks"
