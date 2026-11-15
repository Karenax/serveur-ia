# Thèmes de couleur et fond d'écran (UI MiniPilot)

## Thèmes

Cinq thèmes commutables, mémorisés par navigateur (`mp-theme`) :

| Thème | Ambiance |
|---|---|
| Doré | look historique (Golden Gate), défaut |
| Forêt | aurore verte sur fond profond |
| Océan | aurore bleue sur fond profond |
| Rose | crépuscule rosé |
| Graphite (sombre) | fond nuit + coquille sombre (barre, fenêtres, dock, widgets) |

Sélection : menu **Affichage → Thème …** (bascule rapide) ou app
**Réglages → Apparence** (pastilles d'aperçu). Le choix s'applique
immédiatement, sans rechargement, et sans flash au démarrage (appliqué avant
le premier rendu).

## Fond d'écran

Trois modes, mémorisés par navigateur (`mp-wallpaper`) :

- **Automatique** : le fond suit le thème (défaut).
- **Image personnelle** : fichier PNG/JPEG choisi dans Réglages, stocké en
  local dans IndexedDB (jamais envoyé au serveur) ; limite 4 Mo pour rester
  mémorisable. Prend le dessus sur le fond du thème.
- **Couleur unie** : sélecteur de couleur natif.

Réinitialisation : bouton **Réinitialiser** (thème Doré + fond automatique +
couleurs du thème, image locale effacée).

## Couleurs personnalisées

Dans Réglages → Apparence, sous les thèmes :

- **6 palettes** (Rouge d'origine, Bleu, Vert, Violet, Orange, Turquoise),
  chacune = boutons + accents + danger, en un clic ;
- **3 pipettes** : *Boutons* (remplace le rouge `--button-primary-bg`,
  survol assombri calculé), *Accents* (sélection, badges info) et *Danger*
  (boutons danger, textes d'erreur) ;
- bouton **Couleurs du thème** pour revenir aux couleurs du thème actif.

Mémorisées par navigateur (`mp-colors`, `null` = défaut du thème),
appliquées en variables inline sur `body` — donc prioritaires sur tous les
thèmes, sombre compris. Le bouton rouge historique reste disponible via la
palette « Rouge (origine) ».

Règle d'harmonisation : tout élément d'action (boutons primaires, anciens
`mp-red`, badges de comptage, pastilles de navigation) dérive de
`--button-primary-bg` ; les états d'erreur de `--danger-strong`. Aucun rouge
codé en dur ne subsiste dans les CSS (vérifié par recherche), hors la
définition même de `--red` qui sert de défaut.

## Implémentation

- `web/src/themes.css` : fonds par `body[data-theme]`, coquille sombre par
  `body[data-theme="graphite"]`, fond perso par `body[data-wallpaper]` +
  variables `--wp-image` / `--wp-color` (aucune retouche des 3 rendus du fond).
- `web/src/lib/wallpaper.ts` : persistance IndexedDB (`minipilot/kv`).
- `web/src/App.tsx` : états `theme`/`wallpaper` dans Desktop, appliqués sur
  `document.body` (thème synchrone à l'import, image chargée ensuite) ;
  section Apparence dans `SettingsApp`, bascule rapide dans le menu Affichage.
