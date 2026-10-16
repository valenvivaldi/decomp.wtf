"""An agent sets aside a function no C can match as it stands, for a person: no agent gets it until it's cleared."""

import json

import pytest

from decompnet.app.engine import RomNetwork
from decompnet.app.permute import Permuter
from decompnet.network import NetworkError


@pytest.fixture
def net(tmp_path):
    net = RomNetwork(tmp_path / "decomp.db", tmp_path)
    with net.store.tx() as db:
        db.execute("INSERT INTO projects(id, slug, name, root, config) VALUES(1,'game','game',?,?)",
                   (str(tmp_path), json.dumps({"priority": ["fragment"]})))
        db.execute("INSERT INTO functions(project_id, name, size, n_insns, best_score, best_source) "
                   "VALUES(1,'fragment',4,2,10,'int fragment(void){return 0;}')")  # first in every order
        db.execute("INSERT INTO functions(project_id, name, size, n_insns) VALUES(1,'real',40,20)")
    return net


def test_a_flagged_function_is_set_aside_until_a_person_clears_it(net):
    agent, _ = net.local_agent("codex-1")
    assert net.claim_row(agent, "game")["name"] == "fragment"
    net.flag_for_review(agent, "fragment", "starts in the middle of sub_0800C000: live-in r4", "game")
    assert not net.store.one("SELECT 1 FROM claims")  # released

    other, _ = net.local_agent("codex-2")
    assert net.claim_row(other, "game")["name"] == "real"  # not the star, not the easiest: it's set aside
    with pytest.raises(NetworkError, match="waiting for a person"):
        net.claim_row(net.local_agent("codex-3")[0], "game", "fragment")
    assert Permuter(net).candidates(net.project_row("game")) == []
    assert next(f for f in net.function_map("game") if f["name"] == "fragment")["review"].startswith("starts in")

    net.clear_review("fragment", "game")
    assert net.claim_row(net.local_agent("codex-4")[0], "game")["name"] == "fragment"


def test_flagging_needs_a_reason(net):
    with pytest.raises(NetworkError, match="what's wrong"):
        net.flag_for_review(net.local_agent("codex-1")[0], "fragment", "  ", "game")
