---
name: professional-ui-design
description: Composer ou améliorer significativement les écrans métier Kiara avec une hiérarchie claire, des composants réutilisables et une finition sobre adaptée aux données réelles.
---

# Design professionnel de Kiara

Lire les styles et composants de la surface modifiée avant de créer une variante.
Kiara utilise HTML/CSS/JavaScript sans framework UI ; le client Windows et le WebView
Android partagent des sources. Conserver les variables clair/sombre de
`client-qwen/ui.css`, Segoe UI/system-ui, et les adaptations de
`client-android/mobile-ui/android.css`. La console possède ses propres conventions
dans `lanceur/web/`. Ne pas ajouter de framework ou de police distante par défaut.

Pour une composition nouvelle, consulter `../frontend-design/SKILL.md` ; pour
l'audit des bonnes pratiques, `../web-design-guidelines/SKILL.md`. Adapter leurs
conseils au produit existant : le brief et les conventions de Kiara priment sur un
hero, une identité marketing, une nouvelle typographie ou la casse anglaise des titres.

- Hiérarchie lisible, action principale repérable, navigation stable et raccourcis
  cohérents ; employer les composants existants plutôt qu'une variante voisine.
- Échelle typographique et espacements réguliers, alignements cohérents, icônes
  connues avec noms accessibles. Les cartes doivent grouper un contenu utile.
- Tables et formulaires adaptés à la densité réelle, textes longs et listes remplies,
  ordinateur, téléphone et tablette. Vérifier clair/sombre et zoom.
- Soigner chargement, succès, vide et erreur, sans empêcher une action en cours ni
  perdre un brouillon. Prévoir la récupération des erreurs et le retour utilisateur.
- Viser les critères WCAG 2.2 AA pertinents : clavier et focus visible/non masqué,
  noms et rôles, erreurs associées aux champs, contraste texte 4,5:1 (grand texte 3:1),
  composants 3:1, redimensionnement/reflow et cibles de 24 CSS px ou exception valide.
  Les contrastes et gestes exigent une vérification réelle, pas une lecture de regex.
- Ajouter dégradés, badges, ombres, animations ou illustrations uniquement pour un
  besoin établi ; respecter la préférence de réduction du mouvement.

Utiliser `ux-writing-cleaner` pour les textes touchés, `ux-consistency-review` pour
les changements communs et `ux-visual-audit` pour une modification importante.
Présenter les limites des vérifications ; un contrôle automatique ne prouve pas AA.

Référence : [WCAG 2.2 du W3C](https://www.w3.org/TR/WCAG22/), en particulier
[taille des cibles 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
