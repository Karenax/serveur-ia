/** Check the statically loaded portal entry graph emitted by Vite. */
import {readFileSync} from 'node:fs';
import {isAbsolute, relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';

// First split measured 419,860 bytes / 129,610 gzip bytes. A 10% margin
// allows routine changes while requiring review of a substantial regression.
export const LIMITS = {jsBytes:462_000, jsGzipBytes:143_000};

export function measureInitial(manifest, read) {
  const entry = manifest['index.html'];
  if (!entry?.isEntry) throw new Error('Entrée index.html absente du manifeste Vite.');
  const visited = new Set(), files = new Set();
  function visit(key) {
    if (visited.has(key)) return;
    const item = manifest[key];
    if (!item || typeof item.file !== 'string') throw new Error(`Module initial absent : ${key}`);
    visited.add(key);
    if (/\.(?:js|css)$/.test(item.file)) files.add(item.file);
    for (const css of item.css || []) files.add(css);
    for (const dependency of item.imports || []) visit(dependency);
    // dynamicImports are intentionally deferred and excluded.
  }
  visit('index.html');
  const result = {jsBytes:0, jsGzipBytes:0, cssBytes:0, cssGzipBytes:0, files:[]};
  for (const name of [...files].sort()) {
    const bytes = read(name), compressed = gzipSync(bytes, {level:9}).length;
    const isJs = name.endsWith('.js');
    if (!isJs && !name.endsWith('.css')) throw new Error(`Ressource initiale inattendue : ${name}`);
    result[isJs?'jsBytes':'cssBytes'] += bytes.length;
    result[isJs?'jsGzipBytes':'cssGzipBytes'] += compressed;
    result.files.push({name, bytes:bytes.length, gzipBytes:compressed});
  }
  return result;
}

export function withinBudget(measurement) {
  return measurement.jsBytes <= LIMITS.jsBytes && measurement.jsGzipBytes <= LIMITS.jsGzipBytes;
}

function main(directory) {
  if (!directory) throw new Error('Indiquez le dossier Vite compilé avec --manifest.');
  const root = resolve(directory);
  const manifest = JSON.parse(readFileSync(resolve(root,'.vite/manifest.json'),'utf8'));
  const measurement = measureInitial(manifest, name=>{
    const target=resolve(root,name), rel=relative(root,target);
    if (!rel || isAbsolute(name) || isAbsolute(rel) || rel==='..' || rel.startsWith(`..${sep}`)) throw new Error('Chemin de ressource invalide.');
    return readFileSync(target);
  });
  const passed=withinBudget(measurement);
  console.log(JSON.stringify({passed, limits:LIMITS, measurement},null,2));
  if (!passed) process.exitCode=1;
}

if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {main(process.argv[2]);} catch (error) {console.error(error.message);process.exitCode=1;}
}
