"""Native SDDM theme preflight using the mock authentication backend."""
import os
from pathlib import Path
import subprocess
import tempfile


def validate_theme(files):
    """Load the complete theme in SDDM test mode before changing system files."""
    with tempfile.TemporaryDirectory(prefix='rdp-sddm-preflight-') as temp:
        theme=Path(temp)
        for name,data in files.items():
            (theme/name).write_bytes(data)
        environment=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',
                         QT_FORCE_STDERR_LOGGING='1',QT_LOGGING_TO_CONSOLE='1')
        process=subprocess.Popen(['sddm-greeter-qt6','--test-mode','--theme',str(theme)],
                                 env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:
            output,_=process.communicate(timeout=2.5)
            raise RuntimeError('SDDM theme preflight exited unexpectedly: '+output.decode(errors='replace')[-2000:])
        except subprocess.TimeoutExpired:
            process.terminate()
            try:output,_=process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.communicate();raise RuntimeError('SDDM preflight did not stop')
        finally:
            if process.poll() is None:
                process.kill();process.communicate()
        log=output.decode(errors='replace')
        errors=('Unexpected token','Expected token','ReferenceError','TypeError','is not a type',
                'Cannot assign','is not installed','Failed to load','Error loading')
        if 'Adding view' not in log or any(error in log for error in errors):
            raise RuntimeError('SDDM theme preflight failed; system files unchanged: '+log[-2000:])


