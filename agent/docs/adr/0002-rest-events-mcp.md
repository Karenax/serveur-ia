# ADR-0002 — REST + Events + MCP

## Décision
- REST : intégration applicative.
- Events/webhooks : notifications et synchronisation.
- MCP : outils destinés aux agents IA.

## Rejeté
Utiliser MCP comme unique bus applicatif.

## Motif
MCP est utile pour l'agentique mais ne remplace pas les contrats transactionnels et la diffusion événementielle.
