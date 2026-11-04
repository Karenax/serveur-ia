/* The shared voice fixture, with Linux platform capabilities and server PCM. */
'use strict';
const {spawnSync}=require('node:child_process'),path=require('node:path');
const result=spawnSync(process.execPath,[path.join(__dirname,'test_conversation_ui.cjs'),'--linux'],
 {stdio:'inherit',windowsHide:true,timeout:120000});
if(result.error)throw result.error;
process.exitCode=result.status||0;
