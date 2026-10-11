import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/karen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../../..');
const output=path.join(root,'preuves/eg2-20261011');await fs.mkdir(output,{recursive:true});
const fixture=spawn(path.join(root,'Strata-src/.venv/Scripts/python.exe'),['-u',path.join(here,'knowledge_fixture.py')],{cwd:root,windowsHide:true,env:{...process.env,PYTHONUTF8:'1'},stdio:['pipe','pipe','pipe']});
let stderr='';fixture.stderr.on('data',s=>stderr+=s.toString());
const lines=readline.createInterface({input:fixture.stdout})[Symbol.asyncIterator]();const first=await lines.next();assert(!first.done,stderr);const instance=JSON.parse(first.value);assert(instance.fixture);
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu','--no-first-run']});
const page=await browser.newPage({viewport:{width:1440,height:1000},locale:'fr-FR'}),errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(8000);
try{
 await page.goto(instance.url+'/#knowledge');await page.locator('#knowledge-engine').filter({hasText:'Arrêté'}).waitFor();assert(await page.locator('#knowledge').isVisible());checks.push('direct_navigation');
 await page.click('#knowledge-start');await page.locator('#knowledge-engine').filter({hasText:'Prêt'}).waitFor();checks.push('independent_engine_start');
 await page.fill('#knowledge-memory-text','Je souhaite des réponses courtes.');await page.locator('#knowledge-memory-form button').click();await page.locator('#knowledge-memories').filter({hasText:'réponses courtes'}).waitFor();checks.push('personal_memory_create');
 await page.waitForTimeout(1500);await page.fill('#knowledge-query','réponses courtes');await page.locator('#knowledge-search-form button').click();await page.locator('#knowledge-results').filter({hasText:'réponses courtes'}).waitFor();assert(!(await page.locator('#knowledge-results').innerText()).includes('42500'));checks.push('personal_search_isolation');
 const options=await page.locator('#knowledge-scope option').evaluateAll(rows=>rows.map(r=>r.value));await page.selectOption('#knowledge-scope',options[1]);await page.fill('#knowledge-query','budget');await page.locator('#knowledge-search-form button').click();await page.locator('#knowledge-results').filter({hasText:'42500'}).waitFor();assert(!(await page.locator('#knowledge-results').innerText()).includes('végétariens'));checks.push('project_search_isolation');
 await page.locator('#knowledge-index').filter({hasText:'3 passages indexés sur 3'}).waitFor();await page.screenshot({path:path.join(output,'console-memoire.png'),fullPage:true});
 await page.click('#knowledge-stop');await page.locator('#knowledge-engine').filter({hasText:'Arrêté'}).waitFor();await page.locator('#knowledge-search-form button').click();await page.locator('#knowledge-results').filter({hasText:'42500'}).waitFor();checks.push('engine_stop_and_lexical_fallback');
 await page.click('#tab-overview');assert(!(await page.locator('#knowledge').isVisible()));await page.click('#tab-knowledge');assert(await page.locator('#knowledge').isVisible());checks.push('navigation_between_views');
 const denied=await page.request.post(instance.url+'/api/knowledge',{data:{action:'start'}});assert.equal(denied.status(),403);checks.push('admin_token_required');
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(output,'console-validation.json'),JSON.stringify({passed:true,checks,errors,synthetic_only:true},null,2));console.log(JSON.stringify({passed:true,checks,errors}));
}catch(error){console.error(JSON.stringify({errors,html:await page.locator('body').innerText()}));await page.screenshot({path:path.join(output,'console-erreur.png'),fullPage:true});throw error;}finally{await browser.close();fixture.stdin.write('\n');await new Promise(resolve=>fixture.on('exit',resolve));}
