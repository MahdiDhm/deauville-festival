import json

with open("data/festival.json", encoding="utf-8") as f:
    festival = json.load(f)

print(festival["name"])
print(f"From {festival["first_day"]} to {festival["last_day"]}")
print(f"{len(festival["venues"])} venues, {len(festival["artists"])} artists, {len(festival["performances"])} performances  ")


venues = festival["venues"]
total=0
for venue in venues:
    print(f" -{venue["name"]} qui a une capacite  {venue["capacity"]} siege a l'adresse suivante : {venue["address"]}")
    total+=venue["capacity"]

print(f"le nombre total de sieges est :{total}")


solos = 0
lineups = 0
workshops = 0

for perf in festival["performances"]:
    if perf["kind"] == "solo":
        solos += 1
    if perf["kind"] == "lineup":
        lineups += 1
    if perf["kind"] == "workshop":
        workshops += 1

print(f"nombre de solo : {solos}")
print(f"nombre de lineup : {lineups}")
print(f"nombre de workshop : {workshops}")


for perf in festival["performances"]:
    if perf["venue"] == "le-kiosque":
        print(f"At Le Kiosque: {perf["start"]} {perf["title"]}")


plus_long = festival["performances"][0]

for perf in festival["performances"]:
    if perf["duration_minutes"] > plus_long["duration_minutes"]:
        plus_long=perf


print(f"le plus long : {plus_long['title']} ({plus_long['duration_minutes']} min)")

#Pour chaque workshops , il faut afficher son jour et combien de personnes sont inscrites sur le nombre de places


for perf in festival["performances"]:
    if perf["kind"] == "workshop":
        jour = perf["start"][:10]
        inscrits = len(perf["participants"])
        places = perf["max_participants"]
        print(f"Atelier {perf['title']}, le {jour} : {inscrits}/{places} inscrits")

##E02

# 1 Faire le lien entre l'identifiant d'une salle et son vrai nom

venue_names = {}
for venue in festival["venues"]:
    slug = venue["name"].lower().replace(" ", "-").replace("é", "e").replace("â", "a")
    venue_names[slug] = venue["name"]

# 2 Trouver la liste des jours du festival (sans doublons)
days = []
for perf in festival["performances"]:
    day = perf["start"][:10]
    if day not in days:
        days.append(day)
days.sort()

# 3 Demander un jour, et redemander tant qu'il n'est pas valide
answer = input("Quel jour ? ").strip()
while answer not in days:
    print(f"Ce jour n'est pas dans le festival. Jours possibles : {', '.join(days)}")
    answer = input("Quel jour ? ").strip()

# 4 Afficher les spectacles de ce jour, triés par heure
day_perfs = []
for perf in festival["performances"]:
    if perf["start"][:10] == answer:
        day_perfs.append(perf)


def heure_de_debut(p):
    return p["start"]

day_perfs.sort(key=heure_de_debut)

print(f"Programme du {answer} :")
for perf in day_perfs:
    heure = perf["start"][11:]
    salle = venue_names[perf["venue"]]
    print(f"  {heure}  {salle} - {perf['title']} ({perf['kind']})")