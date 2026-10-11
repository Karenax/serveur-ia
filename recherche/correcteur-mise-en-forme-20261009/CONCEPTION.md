# Correcteur avec conservation de la mise en forme

Prototype du 9 octobre 2026, isolé du client distribué et du serveur IA.

Le correcteur actuel utilise un `textarea` et du Markdown : les polices et les couleurs sont perdues dès le collage. Le prototype utilise un éditeur enrichi, conserve un exemplaire du document d’origine, et remplace uniquement les fragments de texte dans une copie de ce document. Les styles et les liens ne sont jamais générés par le modèle.

## Comportement proposé

1. Coller le texte depuis un logiciel qui fournit du HTML dans le presse-papiers, par exemple un traitement de texte ou un courriel. Le correcteur récupère ses polices, tailles, couleurs, gras, italique, soulignement, listes, liens et paragraphes. Des styles de classe locaux de type Word/Outlook sont aussi repris.
2. Choisir la correction, le ton professionnel ou le ton amical. Le texte d’origine reste visible à gauche. Les styles sont conservés séparément ; le modèle reçoit le texte et des identifiants de fragments, regroupés par paragraphe.
3. Vérifier le résultat à droite. Le client valide tous les identifiants avant de remplacer le texte dans la copie du document. Une réponse invalide ou incomplète ne remplace pas le dernier résultat valable. L’utilisateur peut arrêter la correction.
4. Copier le résultat avec **deux représentations** : `text/html` avec la mise en forme, et `text/plain` pour les logiciels qui attendent du texte simple. Le bouton, Ctrl+C et la copie d’une sélection conservent les styles. « Reprendre ce texte » conserve aussi la mise en forme.
5. Le dernier brouillon enrichi et le dernier résultat sont conservés dans les préférences locales chiffrées du client. Un ancien brouillon en texte simple reste lisible.

L’aperçu du prototype fonctionne sur [127.0.0.1:8098/chat#corrector](http://127.0.0.1:8098/chat#corrector). **Ses corrections sont simulées**, afin de tester l’interface sans solliciter le moteur. Pour le relancer :

```powershell
& 'D:\Serveur IA\Strata-src\.venv\Scripts\python.exe' 'D:\Serveur IA\recherche\correcteur-mise-en-forme-20261009\Apercu.py'
```

## Contrat de correction

Les fragments gardent leur ordre et leur emplacement dans le document. Un mot coupé entre plusieurs fragments peut être corrigé à partir du contexte du paragraphe.

```json
{"fragments":[
  {"id":"f0","paragraph":0,"text":"Bonjours,"},
  {"id":"f1","paragraph":1,"text":"Je vous envoi les "},
  {"id":"f2","paragraph":1,"text":"documents demmandés"}
]}
```

La réponse doit contenir exactement les mêmes identifiants, sans style ni HTML :

```json
{"fragments":[
  {"id":"f0","text":"Bonjour,"},
  {"id":"f1","text":"Je vous envoie les "},
  {"id":"f2","text":"documents demandés"}
]}
```

Les espaces aux limites des fragments sont conservés par le client, même si le modèle les omet. Les réponses avec un identifiant absent, dupliqué ou inconnu, un passage supprimé, ou une structure incorrecte sont rejetées. Une chaîne ressemblant à une balise HTML reste du texte. Les numéros de paragraphes donnent le contexte ; ils ne permettent pas au modèle de modifier le document.

## Validation réalisée

- Navigateur Chromium, sous la politique de sécurité réelle du client : collage, correction simulée, comparaison des styles calculés, lien conservé, bordures de tableau, copie enrichie, copie d’un mot coloré et gras, réutilisation et rechargement des préférences.
- Onze contrôles de traitement du contenu, dont les identifiants manquants/dupliqués, les fragments vides, les espaces aux frontières, l’indentation du HTML entre paragraphes et les balises qui doivent rester du texte.
- Réponse tronquée et réponse structurellement incorrecte : l’original et le dernier résultat sont conservés.
- Préférences chiffrées : aller-retour vérifié et sept mises à jour invalides refusées sans écraser le fichier précédent.
- **Moteur actuel réellement sollicité, sans redémarrage** : correction, professionnel et amical réussissent le contrat sur un exemple de cinq fragments. Les fautes « Bonjours », « envoi », « demmandés » et « reçeption » sont corrigées ; le mode amical passe au tutoiement. Cela valide cet exemple, pas l’ensemble des documents possibles.

Preuves : `validation-navigateur.json`, `validation-moteur.json`, `tests-preferences.stderr.log` et `correcteur-enrichi.png`. Le serveur actuel reste en 0.1.35 sur 8080. Aucun EXE ni manifeste de mise à jour n’a été publié.

## Limites et intégration à prévoir

- La conservation porte sur les styles du **texte HTML collé**. Une application qui ne fournit que du texte simple ne permet pas de récupérer ses couleurs ou sa police. Le prototype n’importe pas les fichiers DOCX ni le RTF seul.
- Les tableaux simples, listes et liens sont conservés. Les images, objets Office, commentaires, suivi des modifications, pagination, largeurs exactes des colonnes et mises en page complexes demandent un traitement de document distinct.
- Une reformulation reste répartie dans les fragments d’origine. Cela conserve les styles physiques, mais ne garantit pas que chaque couleur garde exactement la même signification après une réécriture importante. Une correction légère se prête mieux à cette conservation. Une sélection mot par mot dans Word peut aussi produire un grand nombre de fragments : limite actuelle de 1 500 fragments et 100 000 caractères.
- Une police doit être installée sur le poste pour s’afficher exactement. Le logiciel de destination peut imposer ses propres règles de collage ; le prototype n’a pas encore été validé dans Word, Outlook et LibreOffice réels. Les essais de navigateur utilisent un contenu HTML représentatif de ces collages.
- Le dernier brouillon et résultat enrichis sont conservés localement. L’historique synchronisé actuel conserve le texte simple : il faudra définir un stockage de documents enrichis associé aux conversations pour retrouver **tous** les anciens résultats avec leurs styles, sur tous les postes. L’export d’historique actuel reste également en texte simple.
- Avant distribution : intégrer les modules au client et à son empaquetage, valider les collages/copiers réels dans les applications cibles, tester de plus gros documents sur le modèle, et définir le stockage de l’historique enrichi. La vérification de structure évite une perte silencieuse, mais une correction peut devoir être relancée si le modèle ne respecte pas le contrat.

Les sources modifiées se trouvent uniquement dans `client/` de ce dossier. `richtext.js` traite les styles et le presse-papiers ; `corrector-rich.js` gère la correction. Les copies de `client.py`, `ui.js`, `ui.css` et `selection.js` assurent l’intégration du prototype.
