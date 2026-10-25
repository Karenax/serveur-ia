# Deux animations vocales au choix

Dans **Vocal → Affichage → Animation**, l’utilisateur choisit **Orbe** (existant)
ou **Constellation**. Le choix reste mémorisé sur son appareil. L’option **Activer
les mouvements** et la préférence système de réduction des mouvements s’appliquent
aux deux représentations. Le choix peut changer pendant un appel.

Constellation dessine une sphère de particules en volume, des filaments ondulants,
des points internes et quelques lumières en orbite. L’écoute garde un mouvement
calme, la réflexion augmente progressivement la rotation, la parole fait pulser
la sphère selon l’amplitude réelle de la sortie audio. La reconnaissance en cours,
le micro coupé et les erreurs conservent leur état écrit et leurs couleurs.

La scène utilise Canvas 2D, sans bibliothèque, image, modèle ni téléchargement.
Elle garde 800 points principaux sur ordinateur, 560 sur Android, une résolution
plafonnée à deux fois la taille CSS et une cadence d’environ 30 images/s maximum.
Le dessin animé s’arrête hors de la page Vocal. Un dessin figé identique n’est
pas recalculé. Les vitesses changent progressivement et une reprise après pause
ne rattrape pas tout le temps écoulé. En cas d’absence de Canvas, l’orbe reste
disponible et un message explique que Constellation ne peut pas s’afficher.

Le réglage `voice_animation_style` est validé et stocké par les deux clients.
Les réglages existants gardent l’orbe par défaut. Les moteurs Low et Max, leurs
modèles, la dictée et les échanges réseau vocaux ne sont pas modifiés.

## Vérifications

- 76 tests Python du client et validation des valeurs du nouveau réglage.
- 9 suites UI partagées : la nouvelle suite teste Windows et Android avec des
  échanges et du PCM simulés. Choix clavier, une seule scène visible, hauteur
  stable, mémorisation après rechargement, écoute/reconnaissance/réflexion/parole,
  lecture de l’amplitude audio, mouvements arrêtés et réduits, thème, arrêt du
  rendu hors de Vocal, changement pendant l’appel, erreur de sauvegarde et reprise.
- 13 tests de livraison Android, compilation et signature APK.
- Vérification des sources et contrôle UX : les neuf avertissements de longueur
  concernent des textes préexistants de la console serveur, hors de cette tâche.

## Vérification visuelle ciblée

Playwright MCP, fixtures isolées `test_conversation_ui.cjs --preview` et
`--preview --android`, données fictives. Captures lues dans `ui/` : ordinateur
1440×900 clair et sombre, téléphone 390×844 sombre et sélecteur avec focus,
tablette 768×1024 claire/sombre. Pas de débordement horizontal constaté ; le
sélecteur porte un label et un focus visible. Les libellés, composants et réglages
de mouvement sont identiques sur les deux clients. La taille tactile Android
existante de 44 px s’applique au nouveau sélecteur.

La première capture `constellation-first.png` documente un défaut P2 corrigé :
les deux scènes apparaissaient ensemble car `hidden` était affecté comme propriété
sur un SVG. L’attribut est désormais basculé explicitement ; le contrôle de
visibilité et de hauteur des tests passe. Les captures suivantes montrent la
version corrigée.

Cette vérification porte sur la page Vocal et le réglage ajouté. Ce n’est pas un
audit WCAG complet. Le téléphone et la tablette sont simulés dans Chromium avec
les vrais assets Android ; aucune installation sur un appareil physique ni mesure
de fluidité sur un téléphone peu puissant n’a été effectuée.

## Livraison

Windows **3.5.46**, Android **1.0.19/code 20**. Les clés existantes sont conservées.
La publication vérifie une sauvegarde récente, la signature des mises à jour,
les téléchargements authentifiés, les profils et la conservation des processus
Qwen. Le complément Max reste indépendant et n’a pas besoin d’être retéléchargé.

APK publié : `D:\Serveur IA\client-android\dist\Acces-serveur-Kiara-Android.apk`.
Preuves : `publication.json`, `production.json`, `android-publication.json`.
