from datetime import date, datetime

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from b3_festival import charger_festival, texte_moment

festival = charger_festival()
app = FastAPI(title="Deauville Festival du Rire")


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
    artiste = festival.trouver_artiste(slug)
    if artiste is None:
        raise HTTPException(status_code=404, detail=f"No artist '{slug}'.")
    donnees = artiste.vue()
    donnees["performances"] = [s.vue() for s in festival.spectacles_de(artiste)]
    return donnees


@app.get("/api/programme")
def lire_programme(day: date | None = None, venue: str | None = None) -> list[dict]:
    salle = None
    if venue is not None:
        salle = festival.trouver_salle(venue)
        if salle is None:
            raise HTTPException(status_code=404, detail=f"No venue '{venue}'.")
    return [s.vue() for s in festival.programme(day, salle)]


@app.get("/api/performances/{id}")
def lire_spectacle(id: str) -> dict:
    spectacle = festival.trouver_spectacle(id)
    if spectacle is None:
        raise HTTPException(status_code=404, detail=f"No performance '{id}'.")
    return spectacle.vue()


@app.get("/api/now")
def maintenant(at: datetime | None = None) -> dict:
    if at is None:
        at = datetime.now().replace(second=0, microsecond=0)
    return {
        "at": texte_moment(at),
        "now_playing": [s.vue() for s in festival.en_scene(at)],
        "up_next": [s.vue() for s in festival.a_venir(at)],
    }


app.mount("/", StaticFiles(directory="web/public", html=True), name="site")
