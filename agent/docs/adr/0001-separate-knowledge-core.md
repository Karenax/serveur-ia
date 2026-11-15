# ADR-0001 — Cœur de connaissance séparé d'XPilot2

## Décision
Créer un service autonome avec sa propre base et ses propres API.

## Raisons
- réutilisation par plusieurs agents ;
- découplage ;
- évolution indépendante ;
- possibilité de remplacer XPilot2 ou d'ajouter d'autres consommateurs ;
- sécurité et gouvernance plus claires.

## Conséquences
- nécessité d'un mapping projet ;
- APIs versionnées ;
- events ;
- synchronisation explicite.
