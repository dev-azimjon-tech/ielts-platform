"""Run browser-controller behavior regressions without third-party JS packages."""
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which('node') is None, reason='Node is required for browser-controller checks')
@pytest.mark.parametrize('controller', ['exam', 'theme', 'guide', 'flashcards'])
def test_frontend_controller_behavior(controller):
    script = Path(__file__).parent / 'js' / 'core_frontend.cjs'
    subprocess.run(['node', str(script), controller], check=True, capture_output=True, text=True)
