"""The permuter's turns on a function survive an app restart: it doesn't come back to the same hopeless near misses."""

import json

from decompnet.app.engine import RomNetwork
from decompnet.app.permute import MAX_TURNS, Permuter


def test_turns_are_kept_in_the_project(tmp_path):
    db = tmp_path / "decomp.db"
    net = RomNetwork(db, tmp_path)
    with net.store.tx() as d:
        d.execute("INSERT INTO projects(id, slug, name, root, config) VALUES(1,'game','game',?,?)", (str(tmp_path), json.dumps({})))
        d.execute("INSERT INTO functions(project_id, name, size, n_insns, best_score, best_source) "
                  "VALUES(1,'near',40,20,10,'int near(void){return 1;}')")
    proj = net.project_row("game")
    assert [f["name"] for f in Permuter(net).candidates(proj)] == ["near"]
    for _ in range(MAX_TURNS):
        Permuter(net)._spend_turn(proj, "near")

    again = RomNetwork(db, tmp_path)  # the app started again
    assert Permuter(again).candidates(again.project_row("game")) == []
