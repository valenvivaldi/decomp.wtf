"""What a helper does when its agent says it can't go on: stop for good, not start session after session."""

from decompnet.app.agents import no_credit


def test_a_used_up_subscription_quota_stops_the_helper():
    why = no_credit("You've hit your session limit · resets 6pm (America/Cordoba)")
    assert why and "quota" in why and "resets 6pm" in why


def test_an_empty_account_stops_the_helper_and_ordinary_failures_do_not():
    assert "top it up" in no_credit("Error: Insufficient Balance")
    assert no_credit("Error: 429 Too Many Requests") is None  # throttled: waits and tries again
    assert no_credit("exited with code 1: compile failed") is None


def test_opencode_gets_a_log_level_every_version_accepts(tmp_path):
    """OpenCode 2 stops with "Invalid value for flag --log-level" on "ERROR"; it and 1.x both take "error"."""
    from decompnet.app.agents import Manager, Session

    manager = Manager(None, tmp_path, "http://127.0.0.1:0/mcp")
    manager.prompt = lambda s: "prompt"
    session = Session("opencode-1", "opencode", "opencode #1", "game", "opencode-1", {})
    import decompnet.app.agents as agents
    real = agents._which
    agents._which = lambda name: "/usr/bin/opencode"
    try:
        cmd, _, _ = manager._command(session, "token", tmp_path)
    finally:
        agents._which = real
    assert cmd[cmd.index("--log-level") + 1] == "error"


def test_a_silent_agent_session_is_ended_and_reported(tmp_path, monkeypatch):
    """A CLI that hangs (waiting on its provider or a tool) used to hold its session and claim for good."""
    import decompnet.app.agents as agents
    from decompnet.app.agents import Manager, Session

    from decompnet.app.engine import RomNetwork

    monkeypatch.setattr(agents, "IDLE_LIMIT", 1)
    manager = Manager(RomNetwork(tmp_path / "decomp.db", tmp_path), tmp_path, "http://127.0.0.1:0/mcp")
    session = Session("codex-1", "codex", "Codex CLI #1", "game", "codex-1", {})
    # prints one line, then hangs without printing anything
    monkeypatch.setattr(manager, "_command", lambda s, token, workdir: (
        ["sh", "-c", 'echo "{\\"type\\":\\"thread.started\\"}"; sleep 60'], None, ""))
    import time as _time
    t0 = _time.monotonic()
    assert manager._run_cli(session, "token", tmp_path) is False
    assert _time.monotonic() - t0 < 40
    assert "said nothing" in session.error


def test_the_session_after_a_reset_is_told_what_the_stuck_one_was_doing(tmp_path, monkeypatch):
    import json

    import decompnet.app.agents as agents
    from decompnet.app.agents import Manager, Session
    from decompnet.app.engine import RomNetwork

    net = RomNetwork(tmp_path / "decomp.db", tmp_path)
    with net.store.tx() as db:
        db.execute("INSERT INTO projects(id, slug, name, root, config) VALUES(1,'game','game',?,?)", (str(tmp_path), json.dumps({})))
        db.execute("INSERT INTO functions(project_id, name, size, n_insns, best_score) VALUES(1,'sub_1',4,2,120)")
    agent, _ = net.local_agent("codex-1")
    net.claim_row(agent, "game", "sub_1")
    monkeypatch.setattr(agents, "IDLE_LIMIT", 1)
    manager = Manager(net, tmp_path, "http://127.0.0.1:0/mcp")
    session = Session("codex-1", "codex", "Codex CLI #1", "game", "codex-1", {})
    monkeypatch.setattr(manager, "_command", lambda s, token, workdir: (["sh", "-c", "sleep 60"], None, ""))
    assert manager._run_cli(session, "token", tmp_path) is False
    assert "sub_1" in session.error and "sub_1" in session.resume and "120" in session.resume
    monkeypatch.setattr(manager, "_prompt", lambda s: "base prompt")
    monkeypatch.setattr(net, "overview", lambda slug: {"platform": "gba", "compiler": {"toolchain": "agbcc"}})
    first = manager.prompt(session)
    assert "reset while working on sub_1" in first
    assert "reset" not in manager.prompt(session)  # said once
