/* Reuse the existing synthetic recovery-test fixture, without running its tests. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const root=path.resolve(__dirname,'../../client-qwen');
const input=fs.readFileSync(path.join(root,'test_ux_recovery_ui.cjs'),'utf8');
const prefix=input.slice(0,input.indexOf('async function check(browser,platform){'));
const body=input.slice(input.indexOf('async function check(browser,platform){'),input.indexOf(' const context=await browser.newContext'))
  .replace('async function check(browser,platform){','async function check(platform){');
const source=prefix+body+" console.log(JSON.stringify({platform,url:'http://127.0.0.1:'+server.address().port})); return server;\n}\n(async()=>{await check('windows');await check('android');})();\n";
const fixture=new Module(path.join(root,'audit-fixture.cjs'),module);
fixture.filename=path.join(root,'audit-fixture.cjs');fixture.paths=Module._nodeModulePaths(root);
fixture._compile(source,fixture.filename);
