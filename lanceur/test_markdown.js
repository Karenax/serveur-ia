'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..','client-qwen'),context=vm.createContext({atob});
vm.runInContext(fs.readFileSync(path.join(root,'vendor','markdown-it.min.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'markdown.js'),'utf8'),context);
function render(text){context.text=text;return vm.runInContext('fredMarkdown.render(text)',context);}
const formatted=render('## Préparer ComfyUI\n\nUn **workflow** clair.\n\n1. Charger le modèle\n2. Décrire une image\n\n```bash\npython main.py\n```\n\n| Étape | Résultat |\n| --- | --- |\n| 1 | Image |');
for(const tag of ['<h2>','<strong>workflow</strong>','<ol>','<li>','<pre>','language-bash','<table>','<th>'])assert.ok(formatted.includes(tag),tag);
for(const payload of ['<script>alert(1)</script>','<img src=x onerror=alert(1)>','[danger](javascript:alert(1))','[danger](j&#x61;vascript:alert(1))','[danger](data:text/html,<script>alert(1)</script>)','![pixel](https://example.org/tracking.png)','[local](file:///C:/secret.txt)']){
  const result=render(payload);
  assert.doesNotMatch(result,/<(?:script|img|iframe|object)\b/i,payload);
  assert.doesNotMatch(result,/<a\b[^>]*href=["'][^"']*(?:javascript|data|file):/i,payload);
}
const link=render('[Documentation](https://example.org/)');assert.match(link,/target="_blank"/);assert.match(link,/rel="noopener noreferrer"/);
assert.ok(render('```html\n<img src=x onerror=alert(1)>\n```').includes('&lt;img'));
console.log('Markdown formatting and hostile content checks passed.');
