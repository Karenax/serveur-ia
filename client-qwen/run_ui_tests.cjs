'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const {root}=require('./test_artifacts.cjs');
console.log('UI artifacts: '+root);
const suites=fs.readdirSync(__dirname).filter(name=>/^test_.*\.cjs$/.test(name)).sort();
for(const name of suites){
  const result=spawnSync(process.execPath,[path.join(__dirname,name)],{cwd:path.dirname(__dirname),stdio:'inherit',timeout:180000});
  if(result.error||result.status!==0){if(result.error)console.error(result.error.message);process.exit(result.status||1);}
}
console.log(suites.length+' shared UI suites passed.');
