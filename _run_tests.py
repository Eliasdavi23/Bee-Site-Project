import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
result = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=root, capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
raise SystemExit(result.returncode)
