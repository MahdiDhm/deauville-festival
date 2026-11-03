import argparse
import sys

from deauville.erreurs import FestivalError, InvalideError
from deauville.festival import Festival
from deauville.modeles import lire_jour, lire_moment
from deauville.stockage import Stockage, StockageJson


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
    if jour not in festival.jours:
        raise InvalideError(f"{jour} is not a day of the festival.")
    print(f"Programme for {jour:%A %d %B}:")
    for spectacle in festival.programme(jour):
        print(spectacle)


def afficher_artiste(festival: Festival, slug: str) -> None:
    artiste = festival.artiste(slug)
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


def ajouter_spectacle(festival: Festival, stockage: Stockage) -> None:
    donnees = {
        "kind": "solo",
        "title": input("Title: "),
        "artist": input("Artist (slug): ").strip(),
        "venue": input("Venue (slug): ").strip(),
        "start": input("Start (YYYY-MM-DDTHH:MM): ").strip(),
        "duration_minutes": input("Duration (minutes): ").strip(),
    }
    spectacle = festival.ajouter(festival.creer_spectacle(donnees))
    stockage.sauver(festival)
    print(f"Added: {spectacle.id}")


def annuler_spectacle(festival: Festival, stockage: Stockage, id: str) -> None:
    spectacle = festival.annuler(id)
    stockage.sauver(festival)
    print(f"Cancelled: {spectacle.titre}")


def servir(stockage: Stockage, port: int) -> None:
    import uvicorn

    from deauville.api import create_app

    uvicorn.run(create_app(stockage), host="127.0.0.1", port=port)


def lire_arguments(arguments: list[str] | None) -> argparse.Namespace:
    parseur = argparse.ArgumentParser(prog="deauville")
    parseur.add_argument("--data", default="data/festival.json", help="data file")
    commandes = parseur.add_subparsers(dest="commande")
    commandes.add_parser("venues", help="venues, slugs and seats")
    commandes.add_parser("programme", help="programme of a day").add_argument("day")
    commandes.add_parser("artist", help="shows of an artist").add_argument("slug")
    commandes.add_parser("now", help="on stage at a moment").add_argument("moment")
    commandes.add_parser("add", help="schedule a solo show")
    commandes.add_parser("cancel", help="cancel a performance").add_argument("id")
    serve = commandes.add_parser("serve", help="start the website and the API")
    serve.add_argument("--port", type=int, default=8000)
    return parseur.parse_args(arguments)


def main(arguments: list[str] | None = None) -> None:
    args = lire_arguments(arguments)
    stockage = StockageJson(args.data)
    try:
        if args.commande == "serve":
            servir(stockage, args.port)
            return
        festival = stockage.charger()
        if args.commande is None:
            afficher_resume(festival)
        elif args.commande == "venues":
            afficher_salles(festival)
        elif args.commande == "programme":
            afficher_programme(festival, args.day)
        elif args.commande == "artist":
            afficher_artiste(festival, args.slug)
        elif args.commande == "now":
            afficher_maintenant(festival, args.moment)
        elif args.commande == "add":
            ajouter_spectacle(festival, stockage)
        elif args.commande == "cancel":
            annuler_spectacle(festival, stockage, args.id)
    except FestivalError as erreur:
        print(f"Error: {erreur}")
        sys.exit(1)


if __name__ == "__main__":
    main()
