'use strict';
const {spawnSync}=require('node:child_process'),path=require('node:path');
for(const platform of [[],['--android']]){
  const result=spawnSync(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--voice-workspace',...platform],{stdio:'inherit',windowsHide:true,timeout:120000});
  if(result.error||result.status!==0)process.exit(result.status||1);
}
