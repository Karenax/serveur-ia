/* Shared pure helpers; no mailbox data leaves this extension. */
(function(root){
'use strict';
const origin='https://mail.infomaniak.com';
function detail(value){
 try{const u=new URL(value);const m=u.pathname.match(/^\/api\/mail\/([a-f0-9-]{36})\/folder\/([A-Za-z0-9_%=-]+)\/message\/(\d+)$/i);
 if(u.origin!==origin||u.username||u.password||!m||!u.searchParams.has('prefered_format'))return null;
 return {url:u.href,mailbox:m[1],folder:m[2],id:m[3],resource:u.pathname};
 }catch{return null;}
}
function message(d,data){
 if(!d||!data||data.is_draft||typeof data.msg_id!=='string'||!data.msg_id.trim())throw Error('Message sans identifiant ou brouillon');
 const download=new URL(data.download_resource,origin);
 if(download.href!==origin+d.resource+'/download')throw Error('URL originale non conforme');
 return {key:d.mailbox+':'+data.msg_id,download:download.href,subject:String(data.subject||'Sans objet')};
}
function filename(subject,hash,date){
 const safe=String(subject).normalize('NFKC').replace(/[\\/:*?"<>|\x00-\x1f\x7f]/g,' ').replace(/\s+/g,' ').replace(/^[. ]+|[. ]+$/g,'').slice(0,90)||'Sans objet';
 return 'Infomaniak-IA/'+date+'-'+safe+'-'+hash+'.eml';
}
function eml(text,type=''){
 if(/html|json/i.test(type)||/^\s*[<{]/.test(text))return false;
 const end=text.search(/\r?\n\r?\n/);if(end<0)return false;
 const header=text.slice(0,end);return /^From:\s*\S/im.test(header)&&/^(Date|Subject|Message-ID|To):/im.test(header);
}
const api={detail,message,filename,eml};root.MailAutoCore=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
