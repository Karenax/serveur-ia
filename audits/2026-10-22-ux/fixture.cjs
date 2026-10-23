'use strict';
// Audit-only coordinator. All application writes go to the existing disposable fixture.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {spawn,execFileSync}=require('node:child_process'),readline=require('node:readline');
const root=path.resolve(__dirname,'../..');
const python=path.join(root,'Strata-src/.venv/Scripts/python.exe');
const child=spawn(python,['-u',path.join(root,'lanceur/web/tests/lots6_8_fixture.py')],{cwd:root,windowsHide:true,stdio:['pipe','pipe','pipe'],env:{...process.env,PYTHONUTF8:'1'}});
child.stderr.on('data',d=>process.stderr.write(d));
const lines=readline.createInterface({input:child.stdout});
let instance,proxy;
const android=execFileSync(python,['-c',"import importlib.util,sys; from pathlib import Path; s=importlib.util.spec_from_file_location('assets',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.prepare(Path(sys.argv[2])),end='')",path.join(root,'client-android/scripts/Prepare-Assets.py'),path.join(root,'client-qwen')],{encoding:'utf8',maxBuffer:6e6,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
lines.on('line',async line=>{
 if(instance){console.log(line);return;}
 try{instance=JSON.parse(line);}catch{return;}
 proxy=http.createServer(async(req,res)=>{try{
  const fixtureHeaders=Object.fromEntries(Object.entries(req.headers).filter(([k])=>!['host','connection','content-length','origin'].includes(k)));
  if(req.headers.origin)fixtureHeaders.origin=instance.url;
  const upstream=await fetch(instance.url+(req.url==='/'?'/chat':req.url),{method:req.method,headers:fixtureHeaders,...(['GET','HEAD'].includes(req.method)?{}:{body:await new Promise(r=>{let b='';req.on('data',d=>b+=d);req.on('end',()=>r(b));})})});
  let data=Buffer.from(await upstream.arrayBuffer());
  if(req.url==='/'||req.url==='/chat'){
   const source=data.toString();const match=source.match(/const config=(.*?), \$=id=>/);
   if(!match)throw Error('Config de fixture absente');
   const config=JSON.parse(match[1]);config.platform='android';
   data=Buffer.from(android.replace('__CONFIG__',JSON.stringify(config)).replaceAll('__NONCE__','audit'));
  }else if(req.url==='/client/state'){
   const state=JSON.parse(data);state.profile_required=false;state.profile={name:'Accès fictif UX'};data=Buffer.from(JSON.stringify(state));
  }
  res.writeHead(upstream.status,{'Content-Type':upstream.headers.get('content-type')||'application/json'});res.end(data);
 }catch(e){res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:{message:e.message}}));}});
 proxy.listen(0,'127.0.0.1',()=>{const result={...instance,android_url:'http://127.0.0.1:'+proxy.address().port};fs.writeFileSync(path.join(__dirname,'instance.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));});
});
process.stdin.on('data',d=>child.stdin.write(d));
child.on('exit',code=>{proxy?.close();process.exit(code||0);});
