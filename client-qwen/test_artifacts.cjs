'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=process.env.UI_PROOF_DIRECTORY||path.resolve(__dirname,'../toolchain/test-results/ui',new Date().toISOString().replace(/[:.]/g,'-')+'-'+crypto.randomBytes(3).toString('hex'));
process.env.UI_PROOF_DIRECTORY=root;
function directory(group){
  if(!/^[a-z0-9-]+$/.test(group))throw new Error('Invalid test artifact group');
  const target=path.join(root,group);fs.mkdirSync(target,{recursive:true});return target;
}
module.exports={root,directory};
