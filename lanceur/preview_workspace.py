"""Isolated browser preview for workspaces; never runs the production model."""
import secrets
import threading
from test_remote import RemoteTests,client
from wireguard_access import Engine
from app import Controller,serve

fixture=RemoteTests();fixture.setUp();engine=None;remote=None;server=None;console=None
try:
    w=fixture.store.workspace;owner=fixture.access['id']
    p=w.action(owner,{'action':'project_create','title':'Préparer notre lancement'})['id']
    w.action(owner,{'action':'document_create','project':p,'title':'Note de cadrage','text':'Objectif : préparer une présentation claire de notre service.\nBudget : 2 500 euros.\nLivrables : synthèse, calendrier et liste des questions ouvertes.'})
    w.action(owner,{'action':'memory_create','project':p,'text':'Utiliser le français et expliquer les termes techniques.'})
    w.action(owner,{'action':'job_create','project':p,'prompt':'Préparer une synthèse de la note de cadrage.','title':'Synthèse du lancement','assistant':'analysis','request_key':secrets.token_hex(16)})
    engine=Engine({'role':'server','wireguard':{'private_key':fixture.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':fixture.gateway.server_port,'peers':fixture.wireguard.peers()})
    remote=client.Remote(fixture.profile,endpoint=f'127.0.0.1:{engine.port}')
    server=client.serve_local(remote,secrets.token_urlsafe(32),8099)
    controller=Controller(fixture.temporary.name,include_legacy=False);controller.remote=fixture.store;controller.wireguard=fixture.wireguard
    console=serve(8875,controller);threading.Thread(target=console.serve_forever,daemon=True).start()
    print('Aperçus isolés : client 8099/chat ; console 8875/#spaces',flush=True)
    server.serve_forever()
finally:
    if server:server.server_close()
    if console:console.shutdown();console.server_close()
    if remote:remote.close()
    if engine:engine.close()
    fixture.tearDown()
