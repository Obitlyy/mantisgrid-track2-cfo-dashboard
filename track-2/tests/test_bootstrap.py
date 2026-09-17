from decision.bootstrap import bootstrap_paths

def test_bootstrap_only_resolves_paths(monkeypatch,tmp_path):
    monkeypatch.setenv('MGAI_DATA_DIR',str(tmp_path)); monkeypatch.setenv('TRACK2_DATA_DIR',str(tmp_path))
    assert bootstrap_paths().data_dir==tmp_path.resolve()
