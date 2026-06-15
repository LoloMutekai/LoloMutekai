<!-- Post-mortem du chantier "profil GitHub 床の間". Document de référence durable. -->
# 床の間 — profile build post-mortem

> Recit complet du chantier du profil `LoloMutekai/LoloMutekai` : ce qui a ete
> construit, **chaque erreur commise**, et les lecons a retenir. A lire avant de
> retoucher l'image-monde ou le generateur.
>
> Date : 2026-06-14. Toutes les dates sont absolues.

---

## 1. Resultat final

Le profil affiche **une seule image-monde** (`assets/tokonoma.svg`) qui sert a la fois
de header et de tableau de metrics :

- **Kakemono** (掛物, le rouleau suspendu d'un 床の間) : stele verticale neo-Tokyo
  centree — manifeste, les 5 projets Kairo en colophon, sceau access scelle (hanko).
- **Fond flow-field** : ondulations "fleurs" rose/gris d'origine, prolongees vers le bas.
- **Constellation de donnees** : les vraies metrics GitHub eclatees en fragments
  holographiques dans le 間 (vide lateral), reliees a la stele par des fils de donnees.
- **Animation de formation** au chargement (visible sur la vue `/blob`, figee sur le profil).

L'art est un **template fige** ; un script Python n'y **injecte que les chiffres**.
Une Action GitHub rafraichit les donnees (push + cron + manuel) sans jamais pouvoir
casser l'art. `access` reste classified ; aucun nom de repo prive ne fuit.

---

## 2. Architecture (pourquoi c'est fait comme ca)

```
metrics/
  template.svg     <- L'ART, fige. Kakemono + constellation + fond + animations.
                      Contient des marqueurs <!--DATA:cle-->valeur d'exemple<!--/DATA:cle-->.
  generate.py      <- NE DESSINE RIEN. Il : (1) fetch l'API GitHub (leak-safe),
                      (2) injecte les vraies valeurs dans les slots DATA du template (regex),
                      (3) ecrit assets/tokonoma.svg.
  POSTMORTEM.md    <- ce fichier.
.github/workflows/metrics.yml  <- regenere assets/tokonoma.svg (push metrics/** + cron + dispatch).
assets/tokonoma.svg  <- la sortie = l'image-monde live (regeneree, ne pas editer a la main).
```

**Le principe-cle** : separer l'art (fige, fait main / par l'agent) des donnees (volatiles,
injectees). Un refresh automatique remplit des trous, il ne redessine jamais. C'est ce qui
permet d'avoir une image artistique ET des chiffres a jour sans que l'un casse l'autre.

### Slots de donnees injectes
`repos`, `commits`, `private` (blocs ▓░ selon le ratio prive/total), `since`,
`languages_count`, `peak_hour`, `heatmap_spark` (24 caracteres), et pour 3 langages :
`langN_name` + `langN_pct` + la largeur de barre via `data-key="lang_*_w"` (max 55 px).

---

## 3. Securite (PAT + anti-fuite)

- **PAT fine-grained read-only** : permissions `Contents:read` + `Metadata:read`, All
  repositories, expiration 90 jours. Stocke en secret repo `METRICS_TOKEN`.
  **Expire le 2026-09-12** — a regenerer + `gh secret set METRICS_TOKEN` avant.
- **Account/Profile : aucune permission.** Le token ne peut rien ecrire, nulle part.
- **Anti-fuite (invariant absolu)** : `generate.py` agrege le volume des repos prives
  (compte, langages en octets, dates de commit) **sans jamais emettre un nom de repo**.
  Les noms de projets visibles dans le kakemono (sayna, access, maestrale...) viennent du
  **colophon fige** (manifeste voulu), PAS de l'API. Preuve : leur compte est identique
  entre `template.svg` et le SVG genere.
  - Audit : `grep -o '<!--DATA:[a-z0-9_]*-->[^<]*<!--' assets/tokonoma.svg | grep -iE 'access|sayna|maestrale|unicorn|kairo|dotfiles'` doit etre **vide**.
- Le secret n'a jamais transite par le disque ni l'historique shell : pose via
  `gh secret set METRICS_TOKEN` (saisie masquee), jamais en argument de commande.

---

## 4. Les erreurs commises (et la lecon de chacune)

### 4.1 — rsvg-convert ment : il ne joue pas les animations CSS
**Le piege le plus couteux.** Pendant des heures, j'ai juge les rendus avec
`rsvg-convert`. Or rsvg **n'execute pas les @keyframes** (`draw`, `appear`, `glowpulse`).
Resultat : il montrait un fond noir-sur-noir (courbes non tracees = invisibles), un glow
explose (etat initial non anime), un terminal vide. **Tous mes jugements "c'est rate /
c'est beau" sur ces fichiers etaient faux.**

- **Symptome** : le `.bak-classic` (que Lolo savait magnifique sur GitHub) rendait un gros
  halo rose + tache noire + aucune courbe sous rsvg.
- **Cause** : rsvg fige l'etat **initial** des animations (opacity:0, dashoffset=longueur).
- **Solution** : rendre via **chromium headless** qui joue les animations, puis capturer
  une frame apres `--virtual-time-budget=11000`. Le SVG est **inline dans un HTML**
  (fond #0d1117), PAS reference via `<img src>` (sinon chromium screenshote avant le chargement).
  Script : voir §6.
- **Lecon** : pour tout SVG anime destine a GitHub, **juger via chromium, jamais rsvg**.
  rsvg reste OK pour un SVG 100% statique.

### 4.2 — Le glow radial pris au piege de son animation
Le `#glow` (halo rose central) avait `stop-opacity:1` mais etait **attenue par l'animation
`glowpulse` qui le maintient a 0.05** la plupart du temps. Quand un rendu fige l'etat sans
jouer l'anim, le glow apparait **a fond** et noie toute la scene.
- **Lecon** : un element dont l'opacite depend d'une @keyframes ne doit pas etre juge a
  l'etat initial. Si on veut le figer, le regler explicitement — ne pas forcer `opacity:1`
  aveuglement (ca l'aurait rendu ecrasant ici). Solution retenue plus tard : reduire et
  repositionner le glow.

### 4.3 — J'ai casse le fond "fleurs" en voulant le "reveiller"
Lolo aime des courbes type **petales/fleurs**. Pour rendre le fond plus visible, un agent a
**multiplie les opacites x2.3 et ajoute 8 spirales** — ce qui a transforme les fleurs en
**vilaines spirales**. Lolo (a juste titre) : *"LES ONDULATIONS DE FOND ON LES LAISSE COMME
AVANT !!!"*.
- **Solution** : repartir du `.bak-classic` (fond intact) et n'y greffer QUE les ajouts
  HUD, sans toucher une seule courbe.
- **Lecon** : le fond flow-field d'origine est **sacre**. Ne jamais modifier ses opacites
  ni ajouter de courbes "ameliorantes". Pour etendre, **prolonger** les courbes existantes
  (cf. 4.7), pas en inventer d'autres au milieu.

### 4.4 — Le terminal etait un cliche
La forme "fenetre terminal + 3 ronds macOS + $ prompt" est le reflexe n°1 de toute IA
(remarque d'un ami de Lolo : *"first one any AI will throw at you"*). Mettre des coins HUD
autour ne suffisait pas — *"t'as juste mis des coins a mon terminal"*.
- **Solution** : remplacer la **forme** par un kakemono (la forme dit le concept : l'objet
  expose dans le 床の間). Pas un terminal deguise.
- **Lecon** : quand quelque chose sonne generique, changer la **forme**, pas le decor.

### 4.5 — On ne peut PAS faire d'interactif sur un profil GitHub
Idees de Lolo : pivot a la souris, tablette qui s'ouvre, donnees qui se chargent.
**Impossible sur la page profil** : GitHub strippe le JS, le `:hover`, le `<style>`, et
**Camo rasterise le SVG en une frame figee**. Toute "animation/interaction" est invisible
sur le profil.
- **Solution** : viser **l'etat final fige magnifique**. Les idees d'ouverture/chargement
  deviennent la *composition* (une interface deja affichee), pas une sequence.
- **Lecon** : sur un profil GitHub, tout doit etre beau en **une frame statique**.
  Les @keyframes peuvent rester (elles jouent sur la vue `/blob` + previews) mais ne
  comptent pas pour le profil.

### 4.6 — Le cache Camo fausse les tests visuels
La page profil sert une version **proxifiee/cachee** par Camo qui ne se purge PAS avec
Ctrl+Shift+R (plusieurs minutes a ~1h de retard). On croit que "le push n'a rien fait".
- **Verification fiable** : la vue `/blob/main/assets/tokonoma.svg`, la preview README, ou
  `curl https://raw.githubusercontent.com/.../tokonoma.svg` montrent la vraie version a jour.
- **Lecon** : ne JAMAIS conclure "ca marche pas" depuis la page profil sans verifier via raw/blob.

### 4.7 — "Vagues" vs "fleurs ondulaires" pour le bas
En etendant le fond vers le bas, j'ai d'abord fait des **sinusoides horizontales (vagues)** —
pas le bon langage. Lolo voulait des **fleurs ondulaires** (courbes circulaires/petales),
et surtout : *"prolonge le bas des 2 grosses fleurs laterales qui existent deja"*.
- **Solution finale** : pour chaque courbe `.pN` qui finit ~y543, calculer sa direction de
  fin et la **prolonger** par une courbe de Bezier (en reprenant couleur/opacite/epaisseur
  de sa classe) + ajouter 2 fleurs-spirales aplaties au centre-bas.
- **Lecon** : etendre = continuer l'existant dans sa propre logique, pas plaquer une autre forme.

### 4.8 — Tailles de texte : x1.5 etait trop
En agrandissant les labels de la constellation, j'ai applique x1.5 a TOUT (labels ET
valeurs) → les valeurs a 24px **chevauchaient la stele**. Lolo voulait juste les **labels**
un peu plus grands.
- **Solution** : valeurs revenues a 16px, labels montes de 7/7.5 a 8/8.5px seulement.
- **Lecon** : agrandir avec discernement (labels ≠ valeurs), et verifier les collisions
  avec la stele centrale (qui commence ~x=450).

### 4.9 — La barre de caviardage "redacted" etait moche
Le tell access etait d'abord `▓▓▓▓▓` (blocs pixelises), puis une barre noire laquee — les
deux jugees moches. Lolo voulait *"du texte avec des ? et symboles bizarres"*.
- **Solution** : un faux **cipher** `?▒⟐?◈⟁?▟⊘?` (pensee chiffree, pas censure). Plus
  coherent avec access = entites cognitives.
- **Lecon** : pour suggerer le secret, le cipher (illisible mais "vivant") bat la barre noire.

### 4.10 — Co-author sur un repo solo
Convention figee : le repo profil a **1 seul contributeur (Lolo)**. Ses commits **ne portent
PAS** de `Co-Authored-By`. Les commits de refresh sont faits par `github-actions[bot]` (pas
sous le nom de Lolo) pour garder son historique humain propre. Le message bot porte
`[skip ci]` pour ne pas declencher une boucle de workflow.

### 4.11 — lowlighter/metrics est archive
La 1re intention (decision #7) etait d'utiliser l'Action `lowlighter/metrics`. Elle est
**archivee (read-only) depuis ~2024** — non maintenue, risque si l'API GitHub evolue.
- **Solution** : tout **fait maison** (generateur Python stdlib, zero dependance tierce).
  Plus souverain, palette signature exacte, controle total.
- **Lecon** : verifier l'etat de maintenance d'une Action avant de batir dessus.

### 4.12 — Le hook de commit impose un sujet ≤ 72 caracteres
Plusieurs commits ont ete rejetes (sujet a 74-78 car.). Le `git add` est annule quand le
commit echoue → il faut re-`add` avant de re-committer.
- **Lecon** : garder les sujets de commit ≤ 72 caracteres (corps libre apres une ligne vide).

---

## 5. Comment travailler sur ce profil (procedures)

### Modifier l'ART (kakemono, fond, constellation, couleurs)
On edite `metrics/template.svg`. **Ne jamais editer `assets/tokonoma.svg`** (regenere).
Le fond flow-field (`<g>` de paths `class="pN"`) est **intouchable** — voir 4.3.

### Tester en local SANS le PAT
```bash
GITHUB_TOKEN="$(gh auth token)" GITHUB_USER=LoloMutekai python3 metrics/generate.py
```
(utilise le token gh local, read-only ; produit le meme rendu que le PAT).

### Voir le vrai rendu (avec animations) — voir §6 le script chromium
```bash
/tmp/render_chromium.sh assets/tokonoma.svg /tmp/out.png 11000   # NE PAS utiliser rsvg
```

### Audit anti-fuite (obligatoire avant tout push)
```bash
grep -o '<!--DATA:[a-z0-9_]*-->[^<]*<!--' assets/tokonoma.svg \
  | grep -iE 'access|sayna|maestrale|unicorn|kairo|dotfiles'   # doit etre VIDE
```

### Renouveler le PAT (avant le 2026-09-12)
GitHub Settings -> Developer settings -> Fine-grained tokens -> regenerer (Contents+Metadata
read, All repos), puis `gh secret set METRICS_TOKEN --repo LoloMutekai/LoloMutekai`.

---

## 6. Le script de rendu fidele (chromium)

rsvg ne joue pas les animations -> rendre via chromium, SVG inline dans un HTML :

```bash
#!/usr/bin/env bash
# render_chromium.sh <svg> <out.png> [budget_ms]
set -euo pipefail
SVG="$1"; OUT="$2"; BUDGET="${3:-11000}"
HTML="/tmp/_wrap_$$.html"
{ printf '<!doctype html><meta charset=utf-8><style>html,body{margin:0;background:#0d1117}svg{display:block;width:1000px;height:640px}</style>'; cat "$SVG"; } > "$HTML"
chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=1000,640 \
  --virtual-time-budget="$BUDGET" --screenshot="$OUT" "file://$HTML"
rm -f "$HTML"
```
- `--virtual-time-budget` court (~5500 ms) = frame intermediaire (anim en cours).
- budget long (11000 ms) = etat final (ce que verra la page profil apres rasterisation).

---

## 7. Reste a faire (tiers non livres)

- **Tier 4** — Hub Kairo : cartes silhouettes des 5 projets sous l'image, lien Sayna.
- **Tier 5** — Repo vitrine public (showcase Tokonoma sanitise + manifeste Kairo + galerie SVG).
- **Tier 6** — Finitions : bio GitHub (tell code), epingler les 2 repos publics.

Checklist complete (cote Tokonoma) : `~/Kairo/Tokonoma/docs/GITHUB_PROFILE.md`.
