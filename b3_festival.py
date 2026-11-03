import json
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta

FICHIER = "data/festival.json"
ECART = timedelta(minutes=30)
FIN_DE_NUIT = timedelta(hours=6)


# ===== Transformer du texte en valeurs =====

def fabriquer_code(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii").lower()
    propre = ""
    for caractere in texte:
        if caractere.isalnum():
            propre += caractere
        else:
            propre += " "
    return "-".join(propre.split())


def lire_jour(texte: str) -> date:
    try:
        return date.fromisoformat(texte)
    except ValueError:
        raise ValueError(f"'{texte}' is not a day, use YYYY-MM-DD.") from None


def lire_moment(texte: str) -> datetime:
    try:
        return datetime.fromisoformat(texte)
    except ValueError:
        raise ValueError(f"'{texte}' is not a moment, use YYYY-MM-DDTHH:MM.") from None


def lire_minutes(texte: str) -> int:
    try:
        return int(texte)
    except ValueError:
        raise ValueError(f"'{texte}' is not a number of minutes.") from None


def texte_moment(moment: datetime) -> str:
    return f"{moment:%Y-%m-%dT%H:%M}"


# ===== Les classes =====

@dataclass
class Salle:
    nom: str
    capacite: int
    adresse: str = ""

    def __post_init__(self) -> None:
        if self.capacite < 1:
            raise ValueError(f"{self.nom} needs at least one seat.")

    @property
    def slug(self) -> str:
        return fabriquer_code(self.nom)

    def vue(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.nom,
            "capacity": self.capacite,
            "address": self.adresse,
        }


@dataclass(eq=False)
class Artiste:
    nom: str
    bio: str = ""
    photo_url: str = ""

    @property
    def slug(self) -> str:
        return fabriquer_code(self.nom)

    # deux artistes sont le même s'ils ont le même code
    def __eq__(self, autre: object) -> bool:
        return isinstance(autre, Artiste) and autre.slug == self.slug

    def __hash__(self) -> int:
        return hash(self.slug)

    def vue(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.nom,
            "bio": self.bio,
            "photo_url": self.photo_url,
        }


# Une seule classe pour les trois genres : certains champs restent à None.
# Les "if self.kind == ..." disparaîtront au bloc B4 (step 09).
class Spectacle:
    def __init__(
        self,
        kind: str,
        titre: str,
        salle: Salle,
        debut: datetime,
        duree: int,
        description: str = "",
        artiste: Artiste | None = None,
        age_min: int | None = None,
        hote: Artiste | None = None,
        numeros: list[Artiste] | None = None,
        intervenant: Artiste | None = None,
        max_participants: int | None = None,
        participants: list[str] | None = None,
    ) -> None:
        if not 1 <= duree <= 360:
            raise ValueError(f"{duree} minutes: a performance lasts from 1 to 360 minutes.")
        self.kind = kind
        self.titre = titre
        self.salle = salle
        self.debut = debut
        self.duree = duree
        self.description = description
        self.artiste = artiste
        self.age_min = age_min
        self.hote = hote
        self.numeros = numeros or []
        self.intervenant = intervenant
        self.max_participants = max_participants
        self.participants = participants or []

    @property
    def fin(self) -> datetime:
        return self.debut + timedelta(minutes=self.duree)

    @property
    def jour_festival(self) -> date:
        return (self.debut - FIN_DE_NUIT).date()

    @property
    def id(self) -> str:
        return f"{self.salle.slug}-{self.debut:%Y-%m-%d-%H%M}"

    @property
    def artistes(self) -> list[Artiste]:
        if self.kind == "solo":
            return [self.artiste]
        if self.kind == "lineup":
            return [self.hote] + self.numeros
        return [self.intervenant]

    def role(self, artiste: Artiste) -> str | None:
        if self.kind == "solo" and artiste == self.artiste:
            return "solo"
        if self.kind == "lineup" and artiste == self.hote:
            return "host"
        if self.kind == "lineup" and artiste in self.numeros:
            return "act"
        if self.kind == "workshop" and artiste == self.intervenant:
            return "teacher"
        return None

    def implique(self, artiste: Artiste) -> bool:
        return self.role(artiste) is not None

    def trop_proche(self, autre: "Spectacle") -> bool:
        return self.debut < autre.fin + ECART and autre.debut < self.fin + ECART

    @property
    def places(self) -> int:
        if self.kind == "workshop":
            return min(self.max_participants, self.salle.capacite)
        return self.salle.capacite

    def resume(self) -> str:
        if self.kind == "solo":
            return self.artiste.nom
        if self.kind == "lineup":
            noms = ", ".join(a.nom for a in self.numeros)
            return f"hosted by {self.hote.nom}, with {noms}"
        pris = len(self.participants)
        return f"with {self.intervenant.nom}, {pris}/{self.places} places taken"

    def vers_dict(self) -> dict:
        donnees = {
            "kind": self.kind,
            "title": self.titre,
            "venue": self.salle.slug,
            "start": texte_moment(self.debut),
            "duration_minutes": self.duree,
            "description": self.description,
        }
        if self.kind == "solo":
            donnees["artist"] = self.artiste.slug
            donnees["min_age"] = self.age_min
        if self.kind == "lineup":
            donnees["host"] = self.hote.slug
            donnees["acts"] = [a.slug for a in self.numeros]
        if self.kind == "workshop":
            donnees["teacher"] = self.intervenant.slug
            donnees["max_participants"] = self.max_participants
            donnees["participants"] = list(self.participants)
        return donnees

    def vue(self) -> dict:
        donnees = self.vers_dict()
        donnees["id"] = self.id
        donnees["venue_name"] = self.salle.nom
        donnees["end"] = texte_moment(self.fin)
        donnees["festival_day"] = self.jour_festival.isoformat()
        donnees["summary"] = self.resume()
        donnees["capacity"] = self.places
        donnees["artists"] = [{"slug": a.slug, "name": a.nom} for a in self.artistes]
        if self.kind == "workshop":
            donnees["places_left"] = self.places - len(self.participants)
        return donnees

    # sorted() range par heure de début, puis par nom de salle
    def __lt__(self, autre: "Spectacle") -> bool:
        return (self.debut, self.salle.nom) < (autre.debut, autre.salle.nom)

    def __str__(self) -> str:
        heures = f"{self.debut:%H:%M}-{self.fin:%H:%M}"
        return f"{heures} | {self.salle.nom} | {self.titre} ({self.kind})"


class Festival:
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
        self._artistes = list(artistes)
        self._spectacles: list[Spectacle] = []

    @property
    def jours(self) -> list[date]:
        jours = []
        jour = self.premier_jour
        while jour <= self.dernier_jour:
            jours.append(jour)
            jour += timedelta(days=1)
        return jours

    @property
    def salles(self) -> list[Salle]:
        return list(self._salles)

    @property
    def artistes(self) -> list[Artiste]:
        return sorted(self._artistes, key=lambda artiste: artiste.slug)

    @property
    def spectacles(self) -> list[Spectacle]:
        return sorted(self._spectacles)

    def trouver_salle(self, slug: str) -> Salle | None:
        for salle in self._salles:
            if salle.slug == slug:
                return salle
        return None

    def trouver_artiste(self, slug: str) -> Artiste | None:
        for artiste in self._artistes:
            if artiste.slug == slug:
                return artiste
        return None

    def trouver_spectacle(self, id: str) -> Spectacle | None:
        for spectacle in self._spectacles:
            if spectacle.id == id:
                return spectacle
        return None

    def programme(self, jour: date | None = None, salle: Salle | None = None) -> list[Spectacle]:
        resultat = []
        for spectacle in self.spectacles:
            if jour is not None and spectacle.jour_festival != jour:
                continue
            if salle is not None and spectacle.salle != salle:
                continue
            resultat.append(spectacle)
        return resultat

    def spectacles_de(self, artiste: Artiste) -> list[Spectacle]:
        return [s for s in self.spectacles if s.implique(artiste)]

    def en_scene(self, moment: datetime) -> list[Spectacle]:
        return [s for s in self.spectacles if s.debut <= moment < s.fin]

    def a_venir(self, moment: datetime, combien: int = 3) -> list[Spectacle]:
        return [s for s in self.spectacles if s.debut > moment][:combien]

    # les règles : elles ne font que raise
    def verifier(self, nouveau: Spectacle) -> None:
        if nouveau.salle not in self._salles:
            raise ValueError(f"No venue '{nouveau.salle.slug}'.")
        for artiste in nouveau.artistes:
            if artiste not in self._artistes:
                raise ValueError(f"No artist '{artiste.slug}'.")
        if nouveau.jour_festival not in self.jours:
            raise ValueError(f"{nouveau.jour_festival} is not a day of the festival.")
        for autre in self._spectacles:
            if autre.salle == nouveau.salle and autre.trop_proche(nouveau):
                raise ValueError(
                    f"{autre.salle.nom} is busy with {autre.titre} "
                    f"({autre.debut:%Y-%m-%d %H:%M}-{autre.fin:%H:%M})."
                )
        for autre in self._spectacles:
            for artiste in nouveau.artistes:
                if autre.implique(artiste) and autre.trop_proche(nouveau):
                    raise ValueError(f"{artiste.nom} is on stage in {autre.titre}.")

    # la seule façon d'ajouter un spectacle : les règles passent toujours
    def ajouter(self, spectacle: Spectacle) -> None:
        self.verifier(spectacle)
        self._spectacles.append(spectacle)

    def annuler(self, id: str) -> Spectacle:
        spectacle = self.trouver_spectacle(id)
        if spectacle is None:
            raise ValueError(f"No performance '{id}'.")
        self._spectacles.remove(spectacle)
        return spectacle

    def vue(self) -> dict:
        return {
            "name": self.nom,
            "first_day": self.premier_jour.isoformat(),
            "last_day": self.dernier_jour.isoformat(),
            "days": [jour.isoformat() for jour in self.jours],
        }

    def vers_dict(self) -> dict:
        return {
            "name": self.nom,
            "first_day": self.premier_jour.isoformat(),
            "last_day": self.dernier_jour.isoformat(),
            "venues": [
                {"name": s.nom, "capacity": s.capacite, "address": s.adresse}
                for s in self._salles
            ],
            "artists": [
                {"name": a.nom, "bio": a.bio, "photo_url": a.photo_url}
                for a in self._artistes
            ],
            "performances": [s.vers_dict() for s in self.spectacles],
        }


# ===== Du fichier aux objets, et retour =====

def creer_spectacle(festival: Festival, donnees: dict) -> Spectacle:
    salle = festival.trouver_salle(donnees["venue"])
    if salle is None:
        raise ValueError(f"No venue '{donnees['venue']}'.")

    def artiste(slug: str) -> Artiste:
        trouve = festival.trouver_artiste(slug)
        if trouve is None:
            raise ValueError(f"No artist '{slug}'.")
        return trouve

    kind = donnees["kind"]
    spectacle = Spectacle(
        kind,
        donnees["title"],
        salle,
        lire_moment(donnees["start"]),
        donnees["duration_minutes"],
        donnees.get("description", ""),
    )
    if kind == "solo":
        spectacle.artiste = artiste(donnees["artist"])
        spectacle.age_min = donnees.get("min_age", 0)
    if kind == "lineup":
        spectacle.hote = artiste(donnees["host"])
        spectacle.numeros = [artiste(slug) for slug in donnees["acts"]]
    if kind == "workshop":
        spectacle.intervenant = artiste(donnees["teacher"])
        spectacle.max_participants = donnees["max_participants"]
        spectacle.participants = list(donnees.get("participants", []))
    return spectacle


def charger_festival(chemin: str = FICHIER) -> Festival:
    try:
        with open(chemin, encoding="utf-8") as f:
            donnees = json.load(f)
    except FileNotFoundError:
        raise ValueError(f"{chemin} does not exist.") from None
    except json.JSONDecodeError as erreur:
        raise ValueError(f"{chemin} is damaged (line {erreur.lineno}).") from None

    festival = Festival(
        donnees["name"],
        date.fromisoformat(donnees["first_day"]),
        date.fromisoformat(donnees["last_day"]),
        [Salle(s["name"], s["capacity"], s["address"]) for s in donnees["venues"]],
        [Artiste(a["name"], a["bio"], a["photo_url"]) for a in donnees["artists"]],
    )
    for spectacle in donnees["performances"]:
        festival.ajouter(creer_spectacle(festival, spectacle))
    return festival


def sauver_festival(festival: Festival, chemin: str = FICHIER) -> None:
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(festival.vers_dict(), f, ensure_ascii=False, indent=2)
