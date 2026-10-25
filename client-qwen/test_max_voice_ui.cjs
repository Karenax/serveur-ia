/* Max keeps the advanced interruption, buffering and recovery behavior. */
const {spawnSync}=require('node:child_process'),path=require('node:path');
for(const mode of ['--max','--max-install']){
  const result=spawnSync(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),mode],{stdio:'inherit',windowsHide:true,timeout:180000});
  if(result.error)throw result.error;
  if(result.status){process.exitCode=result.status;break;}
}
