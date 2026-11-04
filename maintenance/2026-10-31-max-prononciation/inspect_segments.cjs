'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../..');
const source=fs.readFileSync(path.join(root,'client-qwen/conversation.js'),'utf8');
const plain=source.match(/  function plain\(text\)\{[^\n]+/)[0];
const splitter=source.slice(source.indexOf('  function splitSpeech(final=false){'),source.indexOf('  async function pcm('));
const cases=[
  ['lea','Léa posa le plateau sur la table. Les dés colorés attendaient patiemment. Elle lança les dés, espérant un six. Son pion avança d’une case, puis d’une autre.'],
  ['courant','Bonjour, je vous écoute. Vous pouvez enregistrer les fichiers dans le dossier de votre choix.'],
  ['noms','Le client Kiara utilise Windows et une carte AMD Radeon RX 7800 XT.'],
  ['date','Le rendez-vous avec M. Dupont est prévu le 31 octobre 2026 à 14 h 30.'],
  ['homographes','Les poules du couvent couvent. Les fils du tailleur coupent les fils.'],
  ['markdown','L’**assistant** vous permet d’**enregistrer** vos fichiers.'],
  ['nombres','Le montant à payer est de 12,50 €, soit une remise de 5 %.'],
  ['lettres','Le cœur du problème concerne les œufs, les écureuils et les géraniums.'],
];
const rows=cases.map(([id,text])=>{
  const context={native:{quality:'max'},speechBuffer:'',firstSpeechQueued:false,parts:[]};
  vm.createContext(context);
  vm.runInContext(plain+'\nfunction enqueue(text){text=plain(text);if(text)parts.push(text);}\n'+splitter,context);
  for(const char of text){context.speechBuffer+=char;vm.runInContext('splitSpeech()',context);}
  vm.runInContext('splitSpeech(true)',context);
  const whole=vm.runInContext('plain('+JSON.stringify(text)+')',context);
  return {id,text,whole,parts:context.parts};
});
fs.writeFileSync(path.join(__dirname,'segments.json'),JSON.stringify(rows,null,2)+'\n');
console.log(JSON.stringify(rows,null,2));
