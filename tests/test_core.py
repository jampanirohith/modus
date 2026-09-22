import tempfile
from pathlib import Path
from src.lyrics import tcr, detect_kind, clean_plain, parse_sync, Candidate, select_candidates
from src.utils import format_ts, parse_timestamp

def test_tcr_and_clean():
    assert tcr('నువ్వు నవ్వితే') == 1.0
    assert tcr('Samajavaragamana') == 0.0
    assert clean_plain('[00:01.00]నువ్వు <00:01.20>నవ్వితే') == 'నువ్వు నవ్వితే'

def test_kind_and_sync():
    s='[00:01.00]నువ్వు <00:01.20>నవ్వితే\n[00:03.00]చాలా'
    assert detect_kind(s)=='enhanced'
    rows=parse_sync(s)
    assert rows[0][0]==1.0 and rows[0][1]=='నువ్వు నవ్వితే'

def test_tiers():
    a=Candidate('a','[00:00.00]నువ్వు నవ్వితే <00:01.00>చాలా','enhanced'); a.tcr=tcr(a.text)
    b=Candidate('b','[00:00.00]నువ్వు నవ్వితే చాలా ఎక్కువ పదాలు','line'); b.tcr=tcr(b.text)
    ranked,champ=select_candidates([b,a]); assert champ is a

def test_timestamp_roundtrip():
    assert abs(parse_timestamp(format_ts(42.1))-42.1)<0.01


def test_downloader_uses_active_python():
    import sys
    from src.downloader import _spotdl_command
    assert _spotdl_command() == [sys.executable, "-m", "spotdl"]
