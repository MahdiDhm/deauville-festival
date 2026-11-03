from datetime import date, datetime, timedelta
from typing import Self

from deauville.erreurs import ConflitError, IntrouvableError, InvalideError
from deauville.modeles import (
    Artiste,
    Atelier,
    Plateau,
    Salle,
    Solo,
    Spectacle,
    lire_entier,
    lire_jour,
    lire_moment,
)

# le seul endroit où le "kind" du fichier choisit la classe
GENRES: dict[str, type[Spectacle]] = {
    "solo": Solo,
    "lineup": Plateau,
    "workshop": Atelier,
}


class Festival:
    """Le festival : lieux, artistes, programme, et les règles pour le changer.

    Les collections ne sortent que sous forme de tuples : on ne les change
    qu'avec les méthodes, qui vérifient toujours les règles.
    """

    def __init__(
        self,
        nom: str,
        premier_jour: date,
        dernier_jour: date,
        salles: list[Salle],
        artistes: list[Artiste],
    ) -> None:
        self.nom = nom
        self.premier_jour = premier_jour
        self.dernier_jour = dernier_jour
        self._salles = list(salles)
        self._artistes: dict[str, Artiste] = {}
        for artiste in artistes:
            self.ajouter_artiste(artiste)
        self._spectacles: list[Spectacle] = []

    @classmethod
    def depuis_dict(cls, donnees: dict) -> Self:
        try:
            festival = cls(
                donnees["name"],
                lire_jour(donnees["first_day"]),
                lire_jour(donnees["last_day"]),
                [
                    Salle(s["name"], s["capacity"], s.get("address", ""))
                    for s in donnees["venues"]
                ],
                [
                    Artiste(a["name"], a.get("bio", ""), a.get("photo_url", ""))
                    for a in donnees["artists"]
                ],
            )
        except (KeyError, TypeError) as erreur:
            raise InvalideError(f"The festival data misses {erreur}.") from None
        for spectacle in donnees.get("performances", []):
            festival.ajouter(festival.creer_spectacle(spectacle))
        return festival

    def vers_dict(self) -> dict:
        return {
            "name": self.nom,
            "first_day": self.premier_jour.isoformat(),
            "last_day": self.dernier_jour.isoformat(),
            "venues": [s.vers_dict() for s in self._salles],
            "artists": [a.vers_dict() for a in self._artistes.values()],
            "performances": [s.vers_dict() for s in self.spectacles],
        }

    def vue(self) -> dict:
        return {
            "name": self.nom,
            "first_day": self.premier_jour.isoformat(),
            "last_day": self.dernier_jour.isoformat(),
            "days": [jour.isoformat() for jour in self.jours],
        }

    @property
    def jours(self) -> list[date]:
        nombre = (self.dernier_jour - self.premier_jour).days + 1
        return [self.premier_jour + timedelta(days=i) for i in range(nombre)]

    @property
    def salles(self) -> tuple[Salle, ...]:
        return tuple(self._salles)

    @property
    def artistes(self) -> tuple[Artiste, ...]:
        return tuple(sorted(self._artistes.values(), key=lambda a: a.slug))

    @property
    def spectacles(self) -> tuple[Spectacle, ...]:
        return tuple(sorted(self._spectacles))

    def salle(self, slug: str) -> Salle:
        for salle in self._salles:
            if salle.slug == slug:
                return salle
        raise IntrouvableError(f"No venue '{slug}'.")

    def artiste(self, slug: str) -> Artiste:
        if slug not in self._artistes:
            raise IntrouvableError(f"No artist '{slug}'.")
        return self._artistes[slug]

    def spectacle(self, id: str) -> Spectacle:
        for spectacle in self._spectacles:
            if spectacle.id == id:
                return spectacle
        raise IntrouvableError(f"No performance '{id}'.")

    def programme(
        self, jour: date | None = None, salle: str | None = None
    ) -> list[Spectacle]:
        lieu = self.salle(salle) if salle else None
        resultat = []
        for spectacle in self.spectacles:
            if jour is not None and spectacle.jour_festival != jour:
                continue
            if lieu is not None and spectacle.salle != lieu:
                continue
            resultat.append(spectacle)
        return resultat

    def spectacles_de(self, artiste: Artiste) -> list[Spectacle]:
        return [s for s in self.spectacles if s.implique(artiste)]

    def en_scene(self, moment: datetime) -> list[Spectacle]:
        return [s for s in self.spectacles if s.debut <= moment < s.fin]

    def a_venir(self, moment: datetime, combien: int = 3) -> list[Spectacle]:
        return [s for s in self.spectacles if s.debut > moment][:combien]

    def creer_spectacle(self, donnees: dict) -> Spectacle:
        """Construit un spectacle depuis le JSON, sans l'ajouter au programme."""
        genre = donnees.get("kind")
        if genre not in GENRES:
            raise InvalideError(f"'{genre}' is not a kind of performance.")
        try:
            communs = {
                "titre": str(donnees["title"]),
                "salle": self.salle(donnees["venue"]),
                "debut": lire_moment(donnees["start"]),
                "duree": lire_entier(
                    donnees["duration_minutes"], "a number of minutes"
                ),
                "description": donnees.get("description") or "",
            }
            return GENRES[genre].depuis_dict(donnees, communs, self.artiste)
        except KeyError as erreur:
            raise InvalideError(f"The field {erreur} is missing.") from None

    def verifier(self, nouveau: Spectacle, ancien: Spectacle | None = None) -> None:
        """Lève une erreur si `nouveau` casse une règle ; `ancien` est ignoré."""
        self.salle(nouveau.salle.slug)
        for artiste in nouveau.artistes:
            self.artiste(artiste.slug)
        if nouveau.jour_festival not in self.jours:
            raise InvalideError(
                f"{nouveau.jour_festival} is not a day of the festival."
            )
        autres = [s for s in self._spectacles if s is not ancien]
        for autre in autres:
            if autre.salle == nouveau.salle and autre.trop_proche(nouveau):
                raise ConflitError(
                    f"{autre.salle.nom} is busy with {autre.titre} "
                    f"({autre.debut:%Y-%m-%d %H:%M}-{autre.fin:%H:%M})."
                )
        for autre in autres:
            for artiste in nouveau.artistes:
                if autre.implique(artiste) and autre.trop_proche(nouveau):
                    raise ConflitError(f"{artiste.nom} is on stage in {autre.titre}.")

    def ajouter(self, spectacle: Spectacle) -> Spectacle:
        self.verifier(spectacle)
        self._spectacles.append(spectacle)
        return spectacle

    # on vérifie d'abord : si c'est refusé, l'ancien reste en place
    def remplacer(self, id: str, nouveau: Spectacle) -> Spectacle:
        ancien = self.spectacle(id)
        self.verifier(nouveau, ancien)
        self._spectacles[self._spectacles.index(ancien)] = nouveau
        return nouveau

    def annuler(self, id: str) -> Spectacle:
        spectacle = self.spectacle(id)
        self._spectacles.remove(spectacle)
        return spectacle

    def inscrire(self, id: str, nom: str) -> Spectacle:
        spectacle = self.spectacle(id)
        spectacle.inscrire(nom)
        return spectacle

    def ajouter_artiste(self, artiste: Artiste) -> Artiste:
        if artiste.slug in self._artistes:
            raise ConflitError(f"{self._artistes[artiste.slug].nom} already exists.")
        self._artistes[artiste.slug] = artiste
        return artiste
