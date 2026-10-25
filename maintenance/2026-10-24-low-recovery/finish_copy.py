from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=root/'client-qwen/conversation.js';text=path.read_text(encoding='utf-8')
old="status.textContent=allowInterruptions.checked?'Vous pouvez l’interrompre en parlant':'L’écoute reprend après la réponse';};"
assert old in text
text=text.replace(old,"status.textContent=native.quality!=='max'?'Kiara prépare sa réponse':allowInterruptions.checked?'Vous pouvez l’interrompre en parlant':'L’écoute reprend après la réponse';};")
path.write_text(text,encoding='utf-8')
