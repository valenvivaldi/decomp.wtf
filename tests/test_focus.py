"""Helpers launched with a priority: near misses first (a strong model) or never tried first (a cheap one)."""

import json

import pytest

from decompnet.app.engine import RomNetwork


@pytest.fixture
def net(tmp_path):
    net = RomNetwork(tmp_path / "decomp.db", tmp_path)
    with net.store.tx() as db:
        db.execute("INSERT INTO projects(id, slug, name, root, config) VALUES(1,'game','game',?,?)",
                   (str(tmp_path), json.dumps({})))
        db.execute("INSERT INTO context_versions(project_id, version, header, unit) VALUES(1, 1, '', '')")
        # name, instructions, best score, attempts, abandons
        for row in (("tiny_new", 3, None, 0, 0),        # what the usual order takes first
                    ("far", 40, 3000, 4, 0),            # tried, 25% off
                    ("almost", 50, 40, 9, 3),           # 99.2%: given up on three times
                    ("big_new", 80, None, 0, 0)):
            db.execute("INSERT INTO functions(project_id, name, size, n_insns, best_score, attempts, abandons) "
                       "VALUES(1,?,?,?,?,?,?)", (row[0], row[1] * 2, *row[1:]))
    return net


def pick(net, name, focus=None):
    agent, _ = net.local_agent(name)
    if focus:
        net.focus[agent.id] = focus
    fn = net.claim_row(agent, "game", None, "easiest")  # what the agent asks for doesn't change a focused helper
    with net.store.tx() as db:
        db.execute("DELETE FROM claims")
    return fn["name"]


def test_each_focus_takes_its_functions_first(net):
    assert pick(net, "usual") == "tiny_new"
    assert pick(net, "strong", "nearest") == "almost"  # the closest to 100%, even after others gave up on it
    assert pick(net, "cheap", "untried") == "tiny_new"
    with net.store.tx() as db:
        db.execute("UPDATE functions SET attempts=1 WHERE name='tiny_new'")
    assert pick(net, "cheap2", "untried") == "big_new"  # never tried beats small


def test_a_near_miss_finisher_gets_one_function_at_a_time(net):
    agent, _ = net.local_agent("strong")
    net.focus[agent.id] = "nearest"
    text = net.claim_many(agent, "game", 4)
    assert text.startswith("## CLAIMED: game/almost")
    assert net.store.one("SELECT COUNT(*) AS n FROM claims WHERE agent_id=?", agent.id)["n"] == 1


def test_stars_still_come_first_for_a_focused_helper(net):
    net._update_cfg("game", lambda cfg: cfg.__setitem__("priority", ["big_new"]))
    assert pick(net, "strong", "nearest") == "big_new"
