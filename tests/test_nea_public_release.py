"""Regression checks for publication parity and unsafe input boundaries."""
import json,shutil
from pathlib import Path
import pytest
from public_offline import validate,public_url,assert_public_text
ROOT=Path(__file__).resolve().parents[1]
def test_complete_snapshot():
    r=validate(ROOT/'data/public')
    assert r['counts']==dict(fully_resolved_awards=493,identified_subjects=584,inventoried_awards=502,named_fellows=473,official_awards=502,open_collective_boundaries=8,resolved_including_conditional_screen=494,unresolved_identified_ages=0)
@pytest.mark.parametrize('url',['file:///evidence','https://user:password@example.org','https://127.0.0.1/test','https://familysearch.org/record','https://example.org/?token=secret','https://example.org/#access_token=secret','https://archive.internal/test'])
def test_unsafe_sources(url):
    with pytest.raises(ValueError):public_url(url)
def test_csv_cell_tamper(tmp_path):
    shutil.copytree(ROOT/'data/public',tmp_path/'data')
    p=tmp_path/'data/nea-longevity-comparison.csv';p.write_bytes(p.read_bytes().replace(b'Elder Roma Wilson',b'Changed artist',1))
    with pytest.raises(ValueError,match='parity'):validate(tmp_path/'data')
def test_nonexact_lifespan_tamper(tmp_path):
    shutil.copytree(ROOT/'data/public',tmp_path/'data')
    p=tmp_path/'data/nea-public-projection.json';d=json.loads(p.read_text(encoding='utf-8'));next(r for r in d['people'] if r['exact_lifespan_days'] is None)['exact_lifespan_days']=1;p.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError):validate(tmp_path/'data')
def test_credentials_rejected():
    with pytest.raises(ValueError):assert_public_text('github_pat_'+'a'*40)
