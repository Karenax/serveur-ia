    if(response.headers.get('content-type')?.includes('text/event-stream')){
      const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',complete=false;
      while(true){const {value,done}=await reader.read();pending+=done?decoder.decode():decoder.decode(value,{stream:true});const frames=pending.split(/\r?\n\r?\n/);pending=frames.pop();for(const frame of frames)complete=delta(frame,correctorAnswer,view)||complete;if(done){if(pending.trim())complete=delta(pending,correctorAnswer,view)||complete;if(!complete)throw Object.assign(new Error('Connexion interrompue pendant la correction. Le résultat partiel est conservé.'),{code:'connection_error'});break;}}
    }else{
      const value=await response.json(),message=value.choices?.[0]?.message;
      if(value.error||!message)throw Object.assign(new Error(value.error?.message||'Réponse de correction invalide.'),{code:value.error?.code});
      correctorAnswer.content=typeof message.content==='string'?message.content:'';
      correctorAnswer.reasoning_content=typeof message.reasoning_content==='string'?message.reasoning_content:'';
      renderMarkdown(view.content,correctorAnswer.content);save();
    }
