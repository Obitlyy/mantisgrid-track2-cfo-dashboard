from decision.config import resolve_paths

def test_data_paths_resolve_to_one_directory(monkeypatch,tmp_path):
    monkeypatch.setenv('MGAI_DATA_DIR',str(tmp_path)); monkeypatch.setenv('TRACK2_DATA_DIR',str(tmp_path/'.'))
    assert resolve_paths().data_dir==tmp_path.resolve()
