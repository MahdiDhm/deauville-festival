from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from deauville.erreurs import (
    ConflitError,
    FestivalError,
    IntrouvableError,
    InvalideError,
    StockageError,
)
from deauville.modeles import Artiste, texte_moment
from deauville.stockage import Stockage

WEB = Path(__file__).resolve().parents[2] / "web"

STATUTS: dict[type[FestivalError], int] = {
    IntrouvableError: 404,
    ConflitError: 409,
    InvalideError: 422,
    StockageError: 500,
}


class CorpsSpectacle(BaseModel):
    """Le JSON attendu pour créer ou remplacer un spectacle."""

    kind: Literal["solo", "lineup", "workshop"]
    title: str
    venue: str
    start: str
    duration_minutes: int
    description: str = ""
    artist: str | None = None
    min_age: int | None = None
    host: str | None = None
    acts: list[str] | None = None
    teacher: str | None = None
    max_participants: int | None = None
    participants: list[str] | None = None


class CorpsArtiste(BaseModel):
    """Le JSON attendu pour ajouter un artiste."""

    name: str
    bio: str = ""
    photo_url: str = ""


class CorpsParticipant(BaseModel):
    """Le JSON attendu pour inscrire quelqu'un à un atelier."""

    name: str


def statut(erreur: FestivalError) -> int:
    for classe, code in STATUTS.items():
        if isinstance(erreur, classe):
            return code
    return 400


def create_app(stockage: Stockage) -> FastAPI:
    """L'application, construite autour d'un stockage (vrai fichier ou test)."""
    festival = stockage.charger()
    app = FastAPI(title="Deauville Festival du Rire")

    # le seul endroit qui transforme une erreur du festival en code HTTP
    @app.exception_handler(FestivalError)
    def erreur_du_festival(request: Request, erreur: FestivalError) -> JSONResponse:
        return JSONResponse(status_code=statut(erreur), content={"detail": str(erreur)})

    @app.get("/api/festival")
    def lire_festival() -> dict:
        return festival.vue()

    @app.get("/api/venues")
    def lister_salles() -> list[dict]:
        return [salle.vue() for salle in festival.salles]

    @app.get("/api/artists")
    def lister_artistes() -> list[dict]:
        return [artiste.vue() for artiste in festival.artistes]

    @app.get("/api/artists/{slug}")
    def lire_artiste(slug: str) -> dict:
        artiste = festival.artiste(slug)
        spectacles = [s.vue() for s in festival.spectacles_de(artiste)]
        return {**artiste.vue(), "performances": spectacles}

    @app.post("/api/artists", status_code=201)
    def ajouter_artiste(corps: CorpsArtiste) -> dict:
        artiste = Artiste(corps.name, corps.bio, corps.photo_url)
        festival.ajouter_artiste(artiste)
        stockage.sauver(festival)
        return artiste.vue()

    @app.get("/api/programme")
    def lire_programme(day: date | None = None, venue: str | None = None) -> list[dict]:
        return [s.vue() for s in festival.programme(day, venue)]

    @app.get("/api/now")
    def maintenant(at: datetime | None = None) -> dict:
        if at is None:
            at = datetime.now().replace(second=0, microsecond=0)
        return {
            "at": texte_moment(at),
            "now_playing": [s.vue() for s in festival.en_scene(at)],
            "up_next": [s.vue() for s in festival.a_venir(at)],
        }

    @app.get("/api/performances/{id}")
    def lire_spectacle(id: str) -> dict:
        return festival.spectacle(id).vue()

    @app.post("/api/performances", status_code=201)
    def ajouter_spectacle(corps: CorpsSpectacle) -> dict:
        spectacle = festival.creer_spectacle(corps.model_dump(exclude_none=True))
        festival.ajouter(spectacle)
        stockage.sauver(festival)
        return spectacle.vue()

    @app.put("/api/performances/{id}")
    def remplacer_spectacle(id: str, corps: CorpsSpectacle) -> dict:
        spectacle = festival.creer_spectacle(corps.model_dump(exclude_none=True))
        festival.remplacer(id, spectacle)
        stockage.sauver(festival)
        return spectacle.vue()

    @app.delete("/api/performances/{id}", status_code=204)
    def annuler_spectacle(id: str) -> Response:
        festival.annuler(id)
        stockage.sauver(festival)
        return Response(status_code=204)

    @app.post("/api/performances/{id}/participants", status_code=201)
    def inscrire(id: str, corps: CorpsParticipant) -> dict:
        spectacle = festival.inscrire(id, corps.name)
        stockage.sauver(festival)
        return spectacle.vue()

    app.mount("/admin", StaticFiles(directory=WEB / "admin", html=True), name="admin")
    app.mount("/", StaticFiles(directory=WEB / "public", html=True), name="site")
    return app
