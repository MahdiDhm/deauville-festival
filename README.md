# Deauville Festival du Rire 2027

Programme et administration du festival (10-13 juin 2027). Le projet propose
une ligne de commande, une API FastAPI, le site public et l'administration.
Les règles du brief sont vérifiées à chaque changement, et chaque changement
est sauvegardé dans `data/festival.json`.

## Installer

```bash
uv sync
```

## Lancer

```bash
uv run deauville                                  # résumé
uv run deauville venues                           # lieux, codes et places
uv run deauville programme 2027-06-11             # programme d'un jour
uv run deauville artist max-pellerin              # spectacles d'un artiste et son rôle
uv run deauville now 2027-06-11T21:00             # sur scène, puis les 3 suivants
uv run deauville add                              # programmer un solo
uv run deauville cancel la-cabane-2027-06-13-0800 # annuler un spectacle
uv run deauville serve                            # site, admin et API
uv run deauville --data autre.json serve          # avec un autre fichier
```

- site : <http://127.0.0.1:8000/> (`?at=2027-06-11T21:00` pour simuler l'heure)
- administration : <http://127.0.0.1:8000/admin/>
- documentation de l'API : <http://127.0.0.1:8000/docs>

## Tester et construire

```bash
uv run pytest
uv run ruff format src tests/test_festival.py tests/test_api.py
uv run ruff check src tests/test_festival.py tests/test_api.py
uv build          # dist/deauville-0.1.0-py3-none-any.whl
```

- `tests/test_festival.py` : les règles, directement sur la classe `Festival`
  (au moins un test par règle du brief).
- `tests/test_api.py` : le contrat de l'API, par HTTP avec `TestClient`, sans
  démarrer de serveur. On y trouve chaque route et ses filtres, chaque code
  d'erreur (404, 409, 422, 500), un `PUT` qui change l'id, un `PUT` refusé qui
  ne change rien, un atelier complet et un `DELETE` fait deux fois.
- `tests/test_b3.py` : les tests de la version B3.

Les tests ne touchent jamais `data/festival.json`. `create_app(stockage)`
construit l'application autour d'un stockage, et chaque test lui donne une
copie du fichier dans un dossier temporaire (ou un stockage en mémoire).

## Structure

```
src/deauville/
  erreurs.py    la famille d'erreurs
  modeles.py    Salle, Artiste, Spectacle et ses trois genres
  festival.py   Festival : la collection et les règles
  stockage.py   où le festival est rangé (JSON ou mémoire)
  api.py        les routes, construites autour d'un stockage
  cli.py        la commande deauville
tests/          test_festival.py (les règles), test_api.py (le contrat HTTP)
web/            le site et l'admin fournis
```

Les versions des blocs précédents sont gardées pour voir la progression :

```
b1.py           B1 (steps 00 à 02) : un script qui explore les données
b2.py           B2 (steps 03 à 05) : des fonctions, des dates, des règles
b3_festival.py  B3 (steps 06 à 08) : les premières classes et les règles
b3_main.py      B3 : les commandes du terminal   (uv run b3_main.py ...)
b3_api.py       B3 : le site                     (uv run uvicorn b3_api:app)
tests/test_b3.py
```

### Les classes

- `Salle` et `Artiste` (dataclasses) : les données, et le `slug` calculé depuis
  le nom. Deux salles, ou deux artistes, sont égaux s'ils ont le même slug
  (`__eq__`) : c'est ce qui refuse `zoe tanguy` après `Zoé Tanguy`.
- `Spectacle` (classe abstraite) : ce qui est commun à tous les spectacles.
  Titre, salle, début et durée. `fin`, `jour_festival` (début moins 6 h) et
  `id` sont des propriétés. Il vérifie la durée (1 à 360 min). `__lt__` trie
  par début puis par salle, et `__str__` donne la ligne du terminal.
- `Solo`, `Plateau` et `Atelier` héritent de `Spectacle`. Chacune a ses
  champs, ses règles (`verifier()` appelle d'abord `super()`), son résumé, ses
  artistes et le rôle de chacun. Le code qui les utilise ne demande jamais
  quel genre c'est : c'est le polymorphisme.
- `Festival` : tient les salles, les artistes et le programme. On ne change le
  programme que par ses méthodes (`ajouter`, `remplacer`, `annuler`,
  `inscrire`, `ajouter_artiste`), qui vérifient les règles d'abord. Les
  collections sortent en tuples, on ne peut donc pas faire `append` dessus.
- `Stockage` (abstraite), avec `StockageJson` et `StockageMemoire` : le
  festival ne sait pas où il est rangé.

### Les questions du brief

- **Où vivent les règles ?** Celles d'un seul spectacle sont dans sa classe
  (durée, âge, numéros d'un plateau, places d'un atelier). Celles qui comparent
  plusieurs spectacles sont dans `Festival.verifier()` (jour du festival,
  salle occupée, artiste déjà sur scène). La ligne de commande et l'API
  passent toutes les deux par `Festival`.
- **Comment une erreur dit quelle règle ?** Chaque règle lève une erreur de la
  famille `FestivalError` avec une phrase. Le type dit ce qui ne va pas :
  `IntrouvableError` → 404, `ConflitError` → 409, `InvalideError` → 422,
  `StockageError` → 500. Un seul gestionnaire dans `api.py` fait cette
  traduction. La ligne de commande attrape la famille et affiche
  `Error: ...`.
- **Le mot `kind`** ne sert qu'à un endroit : le dictionnaire `GENRES` de
  `festival.py`, qui choisit la classe à la lecture des données.
- **Avec une base de données ?** Il suffirait d'écrire un nouveau `Stockage`
  avec `charger()` et `sauver()`. `Festival`, les règles, l'API et la ligne de
  commande ne changeraient pas.

## Ce qui est fait

Les steps 00 à 13 : les commandes, les règles, le site, l'admin, le package
et les tests du contrat.

Pas fait (facultatif) : la question 6 de la step 01, et le stockage SQLite
(extension de la step 13).

## Known bugs

- **After Hours apparaissait le mauvais jour (corrigé à la step 04).** Dans
  `b1.py` (step 02), le jour d'un spectacle est pris dans les 10 premiers
  caractères de son début. After Hours, le 12 juin à 01:00, apparaît donc le
  samedi, alors qu'il termine la soirée du vendredi : pour le festival, une
  journée se termine à 06:00. Depuis la step 04, le jour du festival est la
  date du début moins 6 heures.
- `uv run deauville add` ne programme que des solos. Les plateaux et les
  ateliers se programment par l'admin.
- Si l'écriture du fichier échoue, l'API répond 500, mais le changement reste
  en mémoire jusqu'au redémarrage du serveur.
