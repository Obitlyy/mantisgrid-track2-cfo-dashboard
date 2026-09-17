import os, subprocess, sys

def test_official_loader_honors_environment(tmp_path):
    env={**os.environ,'MGAI_DATA_DIR':str(tmp_path),'PYTHONPATH':'track-2'}
    out=subprocess.check_output([sys.executable,'-c','from api.data_loader import PREP; print(PREP)'],env=env,text=True)
    assert out.strip()==str((tmp_path/'prepped').resolve())
