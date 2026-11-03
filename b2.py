import json
import sys
import unicodedata
from datetime import date, datetime, timedelta

FICHIER = "data/festival.json"
ECART = timedelta(minutes=30)


# ===== Lire et écrire le fichier =====

def charger_festival():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"{FICHIER} does not exist.") from None
    except json.JSONDecodeError as erreur:
        raise ValueError(f"{FICHIER} is damaged (line {erreur.lineno}).") from None


def sauver_festival(festival):
    with open(FICHIER, "w", encoding="utf-8") as f:
        json.dump(festival, f, ensure_ascii=False, indent=2)


# ===== Transformer le texte tapé en valeurs =====

def fabriquer_code(texte):
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.lower()
    propre = ""
    for caractere in texte:
        if caractere.isalnum():
            propre += caractere
        else:
            propre += " "
    mots = propre.split()
    return "-".join(mots)


def lire_jour(texte):
    try:
        return date.fromisoformat(texte)
    except ValueError:
        raise ValueError(f"'{texte}' is not a day, use YYYY-MM-DD.") from None


def lire_moment(texte):
    try:
        return datetime.fromisoformat(texte)
    except ValueError:
        raise ValueError(f"'{texte}' is not a moment, use YYYY-MM-DDTHH:MM.") from None


def lire_minutes(texte):
    try:
        return int(texte)
    except ValueError:
        raise ValueError(f"'{texte}' is not a number of minutes.") from None


# ===== Machines de calcul (elles rendent un résultat, sans print) =====

def nom_de_salle(festival, code):
    for salle in festival["venues"]:
        if fabriquer_code(salle["name"]) == code:
            return salle["name"]
    return None


def nom_artiste(festival, code):
    for artiste in festival["artists"]:
        if fabriquer_code(artiste["name"]) == code:
            return artiste["name"]
    return None


def debut(spectacle):
    return datetime.fromisoformat(spectacle["start"])


def fin(spectacle):
    return debut(spectacle) + timedelta(minutes=spectacle["duration_minutes"])


# un spectacle à 01:00 le samedi appartient encore au vendredi
def jour_du_festival(spectacle):
    return (debut(spectacle) - timedelta(hours=6)).date()


def jours_du_festival(festival):
    premier = date.fromisoformat(festival["first_day"])
    dernier = date.fromisoformat(festival["last_day"])
    jours = []
    jour = premier
    while jour <= dernier:
        jours.append(jour)
        jour += timedelta(days=1)
    return jours


def identifiant(spectacle):
    return f"{spectacle['venue']}-{debut(spectacle):%Y-%m-%d-%H%M}"


def programme_du_jour(festival, jour):
    spectacles = []
    for spectacle in festival["performances"]:
        if jour_du_festival(spectacle) == jour:
            spectacles.append(spectacle)
    return sorted(spectacles, key=debut)


def role_dans(spectacle, code):
    if spectacle["kind"] == "solo" and spectacle["artist"] == code:
        return "solo"
    if spectacle["kind"] == "lineup":
        if spectacle["host"] == code:
            return "host"
        if code in spectacle["acts"]:
            return "act"
    if spectacle["kind"] == "workshop" and spectacle["teacher"] == code:
        return "teacher"
    return None


def artistes_de(spectacle):
    if spectacle["kind"] == "solo":
        return [spectacle["artist"]]
    if spectacle["kind"] == "lineup":
        return [spectacle["host"]] + spectacle["acts"]
    return [spectacle["teacher"]]


def spectacles_artiste(festival, code):
    resultat = []
    for spectacle in festival["performances"]:
        if role_dans(spectacle, code) is not None:
            resultat.append(spectacle)
    return sorted(resultat, key=debut)


def en_scene(festival, moment):
    resultat = []
    for spectacle in festival["performances"]:
        if debut(spectacle) <= moment < fin(spectacle):
            resultat.append(spectacle)
    return sorted(resultat, key=debut)


def a_venir(festival, moment, combien):
    resultat = []
    for spectacle in festival["performances"]:
        if debut(spectacle) > moment:
            resultat.append(spectacle)
    return sorted(resultat, key=debut)[:combien]


def trouver_spectacle(festival, code):
    for spectacle in festival["performances"]:
        if identifiant(spectacle) == code:
            return spectacle
    raise ValueError(f"No performance '{code}'.")


# ===== Les règles : elles ne font que raise =====

def trop_proches(a, b):
    return debut(a) < fin(b) + ECART and debut(b) < fin(a) + ECART


def verifier_spectacle(festival, nouveau):
    salle = nom_de_salle(festival, nouveau["venue"])
    if salle is None:
        raise ValueError(f"No venue '{nouveau['venue']}'.")
    for code in artistes_de(nouveau):
        if nom_artiste(festival, code) is None:
            raise ValueError(f"No artist '{code}'.")
    if not 1 <= nouveau["duration_minutes"] <= 360:
        raise ValueError("A performance lasts from 1 to 360 minutes.")
    jour = jour_du_festival(nouveau)
    if jour not in jours_du_festival(festival):
        raise ValueError(f"{jour} is not a day of the festival.")

    for autre in festival["performances"]:
        if autre["venue"] == nouveau["venue"] and trop_proches(autre, nouveau):
            raise ValueError(
                f"{salle} is busy with {autre['title']} "
                f"({debut(autre):%Y-%m-%d %H:%M}-{fin(autre):%H:%M})."
            )
    for autre in festival["performances"]:
        for code in artistes_de(nouveau):
            if role_dans(autre, code) is not None and trop_proches(autre, nouveau):
                nom = nom_artiste(festival, code)
                raise ValueError(f"{nom} is on stage in {autre['title']}.")


# ===== Machines d'affichage (ce sont les seules qui font des print) =====

def ligne(festival, spectacle):
    salle = nom_de_salle(festival, spectacle["venue"])
    heures = f"{debut(spectacle):%H:%M}-{fin(spectacle):%H:%M}"
    return f"{heures} | {salle} | {spectacle['title']} ({spectacle['kind']})"


def afficher_resume(festival):
    print(festival["name"])
    print(f"From {festival['first_day']} to {festival['last_day']}")
    print(
        f"{len(festival['venues'])} venues, {len(festival['artists'])} artists, "
        f"{len(festival['performances'])} performances"
    )


def afficher_salles(festival):
    total = 0
    for salle in festival["venues"]:
        code = fabriquer_code(salle["name"])
        print(f"{code}: {salle['name']}, {salle['capacity']} seats")
        total += salle["capacity"]
    print(f"Total: {total} seats")


def afficher_programme(festival, jour):
    print(f"Programme for {jour:%A %d %B}:")
    for spectacle in programme_du_jour(festival, jour):
        print(ligne(festival, spectacle))


def afficher_artiste(festival, code):
    nom = nom_artiste(festival, code)
    if nom is None:
        raise ValueError(f"No artist '{code}'.")
    print(nom)
    for spectacle in spectacles_artiste(festival, code):
        jour = jour_du_festival(spectacle)
        heures = f"{debut(spectacle):%H:%M}-{fin(spectacle):%H:%M}"
        salle = nom_de_salle(festival, spectacle["venue"])
        role = role_dans(spectacle, code)
        print(f"{jour:%a %d} {heures} | {salle} | {spectacle['title']} ({role})")


def afficher_maintenant(festival, moment):
    print(f"On stage at {moment:%Y-%m-%d %H:%M}:")
    for spectacle in en_scene(festival, moment):
        salle = nom_de_salle(festival, spectacle["venue"])
        print(f"- {spectacle['title']} at {salle}, until {fin(spectacle):%H:%M}")
    print("Up next:")
    for spectacle in a_venir(festival, moment, 3):
        print(f"- {ligne(festival, spectacle)}")


def ajouter_spectacle(festival):
    titre = input("Title: ").strip()
    artiste = input("Artist (slug): ").strip()
    salle = input("Venue (slug): ").strip()
    moment = lire_moment(input("Start (YYYY-MM-DDTHH:MM): ").strip())
    duree = lire_minutes(input("Duration (minutes): ").strip())
    nouveau = {
        "kind": "solo",
        "title": titre,
        "venue": salle,
        "start": f"{moment:%Y-%m-%dT%H:%M}",
        "duration_minutes": duree,
        "description": "",
        "artist": artiste,
        "min_age": 0,
    }
    verifier_spectacle(festival, nouveau)
    festival["performances"].append(nouveau)
    sauver_festival(festival)
    print(f"Added: {identifiant(nouveau)}")


def annuler_spectacle(festival, code):
    spectacle = trouver_spectacle(festival, code)
    festival["performances"].remove(spectacle)
    sauver_festival(festival)
    print(f"Cancelled: {spectacle['title']}")


def afficher_utilisation():
    print("Utilisation :")
    print("  uv run b2.py")
    print("  uv run b2.py venues")
    print("  uv run b2.py programme AAAA-MM-JJ")
    print("  uv run b2.py artist CODE-ARTISTE")
    print("  uv run b2.py now AAAA-MM-JJTHH:MM")
    print("  uv run b2.py add")
    print("  uv run b2.py cancel ID")


# ===== Le programme : on regarde la commande tapée =====

def main():
    festival = charger_festival()
    mots = sys.argv

    if len(mots) == 1:
        afficher_resume(festival)
    elif mots[1] == "venues":
        afficher_salles(festival)
    elif mots[1] == "programme" and len(mots) == 3:
        afficher_programme(festival, lire_jour(mots[2]))
    elif mots[1] == "artist" and len(mots) == 3:
        afficher_artiste(festival, mots[2])
    elif mots[1] == "now" and len(mots) == 3:
        afficher_maintenant(festival, lire_moment(mots[2]))
    elif mots[1] == "add":
        ajouter_spectacle(festival)
    elif mots[1] == "cancel" and len(mots) == 3:
        annuler_spectacle(festival, mots[2])
    else:
        afficher_utilisation()


if __name__ == "__main__":
    try:
        main()
    except ValueError as erreur:
        print(f"Error: {erreur}")
        sys.exit(1)
