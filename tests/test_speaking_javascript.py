import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which('node') is None,reason='Node is required for Speaking controller checks')
def test_speaking_recording_and_retry_controller():
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run(['node',str(root/'tests/js/speaking-practice.test.cjs')],cwd=root,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
