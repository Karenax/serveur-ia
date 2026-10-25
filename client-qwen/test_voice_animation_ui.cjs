/* Shared animation choice and lifecycle, using the isolated voice fixture. */
const {spawnSync}=require('node:child_process'),path=require('node:path');
for(const platform of [[],['--android']]){
  const result=spawnSync(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--animation',...platform],{stdio:'inherit',windowsHide:true,timeout:120000});
  if(result.error)throw result.error;
  if(result.status){process.exitCode=result.status;break;}
}
