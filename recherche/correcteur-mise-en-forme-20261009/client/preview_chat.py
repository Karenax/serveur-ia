"""Local UI fixture. No network forwarding, model loading or inference."""
import io
import json
from pathlib import Path
from client import serve_local

class MockRemote:
    model = 'Vérification du chat · modèle simulé'
    connected = True
    def open(self, path, data=None):
        if data is None:
            content = json.dumps({'data':[{'id':self.model}]}).encode()
        else:
            request = json.loads(data)
            Path(__file__).with_name('preview-request.json').write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')
            frames = []
            if request.get('chat_template_kwargs', {}).get('enable_thinking'):
                frames.append({'reasoning_content':'Vérification de la réponse progressive et du réglage Réflexion.'})
            frames.extend({'content':text} for text in ('Le chat est prêt. ', 'Il partage l’accès du client Windows avec l’API locale.\n\n', 'Cette réponse est simulée : aucun modèle n’a été sollicité.'))
            content = ''.join('data: ' + json.dumps({'choices':[{'delta':frame}]}, ensure_ascii=False) + '\n\n' for frame in frames).encode() + b'data: [DONE]\n\n'
        response = io.BytesIO(content)
        response.status = 200
        return response

if __name__ == '__main__':
    server = serve_local(MockRemote(), 'local_visual_test_only', 8090)
    print('Aperçu simulé : http://127.0.0.1:8090/chat', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
