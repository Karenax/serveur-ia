from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'client-qwen/test_conversation_ui.cjs';text=path.read_text(encoding='utf-8')
start=text.index("    if(android){\n      assert(await page.isVisible('#voice-start')")
end=text.index('    if(maxStreaming)',start)
block='''    if(!maxVoice&&!maxInstall&&!maxStreaming&&!baseline){
      assert(await page.isVisible('#voice-start'),'Dictation stays in chat');
      assert(!(await page.isVisible('#conversation-start')),'Vocal has its own page');
      if(android)await page.click('#ui-sidebar-toggle');
      await page.click('[data-view-button="voice"]');
      assert.equal(await page.inputValue('#voice-quality'),'low');
      assert.equal(await page.isVisible('#conversation-options'),false,'Low keeps its classic continuous conversation');
      await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      const nativeTrace=process.argv.find(v=>v.startsWith('--native-trace='));
      const recognized=nativeTrace?JSON.parse(fs.readFileSync(nativeTrace.slice(15),'utf8')).final.turns[0].text:'Quand aura lieu la livraison du projet Orion ?';
      state.native.speech_id=1;state.native.partial_speech_id=1;state.native.partial=recognized;
      await page.waitForFunction(()=>document.getElementById('conversation-status').textContent.startsWith('Vous :'));
      state.native.partial='';state.native.turns=[{id:1,speech_id:1,text:recognized}];
      await until(()=>state.chats.length===1,'Classic Low submits recognized text');
      await until(()=>state.speech.length>0,'Phonon speech requested');
      await page.waitForFunction(()=>window.__audio.started>0);
      // Low accepts an immediate short reply, including during preceding playback.
      state.native.speech_id=2;state.native.partial_speech_id=2;state.native.turns=[{id:2,speech_id:2,text:'Oui'}];
      await until(()=>state.chats.length===2,'Classic Low accepts immediate one-word reply');
      assert.equal(state.acks.filter(id=>id===2).length,1);
      await until(()=>state.speech.length>=2,'Second Phonon reply');
      if(webEvents){assert.equal(await page.evaluate(()=>ws.lastSources?.[0]?.url),'https://example.org/source');await page.waitForSelector('#voice-sources');}
      await page.click('#conversation-mute');await page.waitForFunction(()=>document.getElementById('conversation-mute').getAttribute('aria-pressed')==='true');
      assert.equal(state.native.microphone_closed,true);
      await page.click('#conversation-mute');await page.waitForFunction(()=>document.getElementById('conversation-mute').getAttribute('aria-pressed')==='false');
      await page.waitForFunction(()=>!busy&&!historySyncPending);
      assert.equal(state.chats[0].voice_conversation,true);assert.equal(state.chats[0].reasoning_effort,'none');
      assert.equal(state.chats[0].messages.at(-1).content,recognized);
      assert(state.calls.some(call=>call.path==='/v1/voice/speech'));
      assert(!state.calls.some(call=>call.path==='/client/voice/max/speech'));
      await page.evaluate(()=>window.conversationSuspend());await page.waitForFunction(()=>!window.conversationBusy);
      assert.equal(state.native.phase,'stopped');assert(state.native.microphone_closed);
      state.native.phase='error';state.native.message='Microphone refusé. Autorisez-le dans les paramètres puis réessayez.';
      await page.waitForFunction(()=>document.getElementById('conversation-status').textContent.includes('Microphone refusé'));
      await page.click('#conversation-start');await page.waitForFunction(()=>window.conversationBusy);
      await page.click('#conversation-start');await page.waitForFunction(()=>!window.conversationBusy);
      assert.deepEqual(errors,[]);
      console.log(JSON.stringify({passed:true,platform:android?'android':'windows',engine:'classic Low / Phonon',realAsrTrace:!!nativeTrace,checks:['dictation remains separate','3.5.39 recognized-turn loop','first recognized phrase','immediate one-word reply retained','Phonon PCM playback','mute/unmute','oral Qwen and history','background hangup','microphone error and retry',...(webEvents?['web sources and Phonon coexist']:[])]},null,2));return;
    }
'''
path.write_text(text[:start]+block+text[end:],encoding='utf-8')
