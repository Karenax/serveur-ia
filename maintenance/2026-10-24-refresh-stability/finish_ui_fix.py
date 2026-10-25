from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def edit(name,old,new):
    path=ROOT/name;s=path.read_text(encoding='utf-8');assert old in s,name;path.write_text(s.replace(old,new),encoding='utf-8')
edit('client-qwen/chat.html','modelCatalogLoading=!connected||!modelCatalog.length;', 'modelCatalogLoading=true;')
edit('client-qwen/chat.html',":modelCatalogLoading?'Actualisation des modèles…':typeof displayCapacity", ':typeof displayCapacity')
edit('client-qwen/chat.html','b.onclick=()=>openHistoryRecord(c);', 'b.onclick=()=>openHistoryRecord(library.find(row=>row.id===c.id));')
edit('client-qwen/test_model_selector_ui.cjs','state.holdModels=true;await page.evaluate(()=>{models();});', "const statusBeforeBackgroundPoll=await page.textContent('#model');state.holdModels=true;await page.evaluate(()=>{models();});")
edit('client-qwen/test_model_selector_ui.cjs',"assert((await page.textContent('#model')).includes('Actualisation'));", "assert.equal(await page.textContent('#model'),statusBeforeBackgroundPoll,'Healthy background checks preserve the visible model status');")
edit('client-qwen/workspace.html','function fredInboxDraw(){const rows=', "let fredInboxDrawSignature='';\nfunction fredInboxDraw(){const signature=JSON.stringify([[...fredInbox.items.values()],fredInbox.preferences,fredInbox.dirty]);if(signature===fredInboxDrawSignature)return;fredInboxDrawSignature=signature;const rows=")
edit('client-qwen/workspace.html',"fredInboxNav.textContent='Notifications'+(unread?' · '+unread:'');if(typeof uiDecorateNavigation==='function')uiDecorateNavigation();", "if(typeof uiDecorateNavigation==='function')uiDecorateNavigation();else fredInboxNav.textContent='Notifications'+(unread?' · '+unread:'');")
