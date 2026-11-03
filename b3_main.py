import sys

from b3_festival import (
    Festival,
    charger_festival,
    creer_spectacle,
    lire_jour,
    lire_minutes,
    lire_moment,
    sauver_festival,
    texte_moment,
)


def afficher_resume(festival: Festival) -> None:
    print(festival.nom)
    print(f"From {festival.premier_jour} to {festival.dernier_jour}")
    print(
        f"{len(festival.salles)} venues, {len(festival.artistes)} artists, "
        f"{len(festival.spectacles)} performances"
    )


def afficher_salles(festival: Festival) -> None:
    total = 0
    for salle in festival.salles:
        print(f"{salle.slug}: {salle.nom}, {salle.capacite} seats")
        total += salle.capacite
    print(f"Total: {total} seats")


def afficher_programme(festival: Festival, texte: str) -> None:
    jour = lire_jour(texte)
    print(f"Programme for {jour:%A %d %B}:")
    for spectacle in festival.programme(jour):
        print(spectacle)


def afficher_artiste(festival: Festival, slug: str) -> None:
    artiste = festival.trouver_artiste(slug)
    if artiste is None:
        raise ValueError(f"No artist '{slug}'.")
    print(artiste.nom)
    for s in festival.spectacles_de(artiste):
        heures = f"{s.debut:%H:%M}-{s.fin:%H:%M}"
        role = s.role(artiste)
        print(f"{s.jour_festival:%a %d} {heures} | {s.salle.nom} | {s.titre} ({role})")


def afficher_maintenant(festival: Festival, texte: str) -> None:
    moment = lire_moment(texte)
    print(f"On stage at {moment:%Y-%m-%d %H:%M}:")
    for s in festival.en_scene(moment):
        print(f"- {s.titre} at {s.salle.nom}, until {s.fin:%H:%M}")
    print("Up next:")
    for s in festival.a_venir(moment):
        print(f"- {s}")


def ajouter_spectacle(festival: Festival) -> None:
    titre = input("Title: ").strip()
    artiste = input("Artist (slug): ").strip()
    salle = input("Venue (slug): ").strip()
    moment = lire_moment(input("Start (YYYY-MM-DDTHH:MM): ").strip())
    duree = lire_minutes(input("Duration (minutes): ").strip())
    donnees = {
        "kind": "solo",
        "title": titre,
        "venue": salle,
        "start": texte_moment(moment),
        "duration_minutes": duree,
        "artist": artiste,
    }
    spectacle = creer_spectacle(festival, donnees)
    festival.ajouter(spectacle)
    sauver_festival(festival)
    print(f"Added: {spectacle.id}")


def annuler_spectacle(festival: Festival, id: str) -> None:
    spectacle = festival.annuler(id)
    sauver_festival(festival)
    print(f"Cancelled: {spectacle.titre}")


def afficher_utilisation() -> None:
    print("Utilisation :")
    print("  uv run b3_main.py")
    print("  uv run b3_main.py venues")
    print("  uv run b3_main.py programme AAAA-MM-JJ")
    print("  uv run b3_main.py artist CODE-ARTISTE")
    print("  uv run b3_main.py now AAAA-MM-JJTHH:MM")
    print("  uv run b3_main.py add")
    print("  uv run b3_main.py cancel ID")


def main() -> None:
    festival = charger_festival()
    mots = sys.argv

    if len(mots) == 1:
        afficher_resume(festival)
    elif mots[1] == "venues":
        afficher_salles(festival)
    elif mots[1] == "programme" and len(mots) == 3:
        afficher_programme(festival, mots[2])
    elif mots[1] == "artist" and len(mots) == 3:
        afficher_artiste(festival, mots[2])
    elif mots[1] == "now" and len(mots) == 3:
        afficher_maintenant(festival, mots[2])
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
