from pathlib import Path
import pytest
from scripts.reuse_data import reuse_data

def test_reuse_is_idempotent_and_conflict_safe(tmp_path):
    source, dest = tmp_path/'source', tmp_path/'dest'; rel=Path('raw/dcgm.csv')
    (source/rel).parent.mkdir(parents=True); (source/rel).write_text('official')
    reuse_data(source,dest,[rel]); reuse_data(source,dest,[rel]); assert (dest/rel).read_text()=='official'
    (dest/rel).write_text('different')
    with pytest.raises(ValueError): reuse_data(source,dest,[rel])
