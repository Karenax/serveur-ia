/* Protect the Low interruption choice alongside Max and both animations. */
const {spawnSync}=require('node:child_process'),path=require('node:path');
for(const args of [[],['--android'],['--android','--no-aec'],['--max']]){
  const result=spawnSync(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--interruptions',...args],{stdio:'inherit',windowsHide:true,timeout:120000});
  if(result.error)throw result.error;
  if(result.status){process.exitCode=result.status;break;}
}
