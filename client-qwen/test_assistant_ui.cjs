'use strict';
const {spawnSync}=require('node:child_process'),path=require('node:path');
for(const args of [[],['--android']]){
  const r=spawnSync(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--assistant-integration',...args],{stdio:'inherit',windowsHide:true,timeout:120000});
  if(r.error)throw r.error;if(r.status){process.exitCode=r.status;break;}
}
