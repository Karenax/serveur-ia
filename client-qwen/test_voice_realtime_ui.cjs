'use strict';
const {spawnSync}=require('node:child_process'),path=require('node:path');
const result=spawnSync(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--realtime-loop'],{stdio:'inherit',windowsHide:true,timeout:120000});
if(result.error)throw result.error;
process.exitCode=result.status||0;
