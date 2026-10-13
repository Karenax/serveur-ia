"""Local UI preview against an isolated fake model, never the production model."""
import secrets
from test_remote import RemoteTests,client
from wireguard_access import Engine
fixture=RemoteTests();fixture.setUp()
engine=None;remote=None;server=None
try:
    engine=Engine({'role':'server','wireguard':{'private_key':fixture.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':fixture.gateway.server_port,'peers':fixture.wireguard.peers()})
    remote=client.Remote(fixture.profile,endpoint=f'127.0.0.1:{engine.port}')
    server=client.serve_local(remote,secrets.token_urlsafe(32),8099)
    print('Aperçu de test isolé : http://127.0.0.1:8099/chat',flush=True)
    server.serve_forever()
finally:
    if server:server.server_close()
    if remote:remote.close()
    if engine:engine.close()
    fixture.tearDown()
