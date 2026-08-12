import pathlib
import py_compile

files = [str(p) for p in pathlib.Path('.').rglob('*.py') if '.git' not in p.parts]
for path in files:
    py_compile.compile(path, doraise=True)
print('ok')
