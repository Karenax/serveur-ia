import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/karen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../../..'),output=path.join(root,'preuves/dossiers-clients-20261011');
await fs.mkdir(output,{recursive:true});
const fixture=spawn(path.join(root,'Strata-src/.venv/Scripts/python.exe'),['-u',path.join(here,'client_storage_fixture.py')],{cwd:root,windowsHide:true,env:{...process.env,PYTHONUTF8:'1'},stdio:['pipe','pipe','pipe']});
let stderr='';fixture.stderr.on('data',s=>stderr+=s.toString());
const lines=readline.createInterface({input:fixture.stdout})[Symbol.asyncIterator](),first=await lines.next();assert(!first.done,stderr);const instance=JSON.parse(first.value);
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu','--no-first-run']});
const context=await browser.newContext({viewport:{width:1440,height:1100},locale:'fr-FR',permissions:['clipboard-read','clipboard-write']}),page=await context.newPage(),errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(10000);
try{
 await page.goto(instance.url+'/#clients');await page.locator('#remote-clients').filter({hasText:instance.alice}).waitFor();checks.push('clients_show_distinct_server_paths');
 const card=page.locator('#remote-clients .client-card').filter({hasText:'Alice synthétique'});assert((await card.locator('.client-storage-path').innerText()).endsWith(instance.alice));await card.getByRole('button',{name:'Copier le chemin'}).click();assert((await page.evaluate(()=>navigator.clipboard.readText())).endsWith(instance.alice));checks.push('copy_exact_client_path');
 await page.click('#tab-devices');await page.locator('#devices-list').filter({hasText:instance.alice}).waitFor();checks.push('devices_show_client_path');
 await page.click('#tab-spaces');await page.locator('#workspace-storage-root').filter({hasText:'donnees-clients'}).waitFor();await page.selectOption('#workspace-owner',instance.bob);await page.locator('#workspace-client-location').filter({hasText:instance.bob}).waitFor();assert(!(await page.locator('#workspace-client-location').innerText()).includes(instance.alice));checks.push('selected_client_location');
 await page.click('#workspace-storage-sync');await page.locator('#workspace-storage-sync').waitFor({state:'visible'});await page.waitForTimeout(500);await page.locator('.shell>main').evaluate(el=>el.scrollTop=0);await page.screenshot({path:path.join(output,'console-dossiers.png'),fullPage:true});checks.push('manual_sync');
 await page.setViewportSize({width:390,height:844});await page.locator('.shell>main').evaluate(el=>el.scrollTop=0);assert(await page.locator('#workspace-client-storage').isVisible());assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));checks.push('mobile_path_wrapping');
 const denied=await page.request.post(instance.url+'/api/client-storage',{data:{action:'sync'}});assert.equal(denied.status(),403);checks.push('admin_token_required');assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(output,'console-validation.json'),JSON.stringify({passed:true,checks,errors,synthetic_only:true},null,2));console.log(JSON.stringify({passed:true,checks,errors}));
}catch(error){console.error(JSON.stringify({error:error.message,errors,body:await page.locator('body').innerText()}));throw error;}finally{await browser.close();fixture.stdin.write('\n');await new Promise(resolve=>fixture.on('exit',resolve));}
