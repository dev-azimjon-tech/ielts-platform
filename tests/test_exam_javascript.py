"""Exercise async browser draft orchestration without a browser dependency."""
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which('node') is None, reason='Node is needed for browser autosave checks')
def test_exam_autosave_waits_for_latest_revision_before_submission():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['node',str(root/'tests/js/exam-session.test.cjs')],cwd=root,capture_output=True,text=True,timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
