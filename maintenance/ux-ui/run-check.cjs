'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const candidates = [process.env.PYTHON_EXE, path.join(root, 'toolchain/eg2-python/Scripts/python.exe'), 'python3', 'python'].filter(Boolean);
const python = candidates.find(command => {
  if (path.isAbsolute(command) && !fs.existsSync(command)) return false;
  const result = spawnSync(command, ['-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'], {stdio: 'ignore', timeout: 10000});
  return !result.error && result.status === 0;
});
if (!python) {
  console.warn('UX : Python >= 3.10 indisponible. Définir PYTHON_EXE pour activer le contrôle.');
  process.exit(0);
}
const result = spawnSync(python, ['-X', 'utf8', path.join(root, 'maintenance/ux_check.py'), ...process.argv.slice(2)], {cwd: root, stdio: 'inherit'});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
