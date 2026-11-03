import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deauville.api import create_app
from deauville.erreurs import StockageError
from deauville.festival import Festival
from deauville.stockage import StockageJson, StockageMemoire

DONNEES = Path(__file__).parent.parent / "data" / "festival.json"

SOLO = {
    "kind": "solo",
    "title": "Morning Coffee",
    "venue": "le-kiosque",
    "start": "2027-06-13T11:00",
    "duration_minutes": 45,
    "artist": "nora-lebrun",
}


@pytest.fixture
def fichier(tmp_path: Path) -> Path:
    copie = tmp_path / "festival.json"
    shutil.copy(DONNEES, copie)
    return copie


@pytest.fixture
def client(fichier: Path) -> TestClient:
    return TestClient(create_app(StockageJson(fichier)))


# ===== Lectures =====


def test_festival(client):
    assert client.get("/api/festival").json() == {
        "name": "Deauville Festival du Rire 2027",
        "first_day": "2027-06-10",
        "last_day": "2027-06-13",
        "days": ["2027-06-10", "2027-06-11", "2027-06-12", "2027-06-13"],
    }


def test_salles_dans_l_ordre_du_fichier(client):
    salles = client.get("/api/venues").json()
    assert len(salles) == 4
    assert salles[0] == {
        "slug": "grand-casino",
        "name": "Grand Casino",
        "capacity": 650,
        "address": "Seafront, main hall",
    }


def test_artistes_tries_par_slug(client):
    artistes = client.get("/api/artists").json()
    assert len(artistes) == 12
    assert artistes[0]["name"] == "Élodie Marchal"
    assert set(artistes[0]) == {"slug", "name", "bio", "photo_url"}


def test_page_d_un_artiste(client):
    artiste = client.get("/api/artists/max-pellerin").json()
    titres = [s["title"] for s in artiste["performances"]]
    assert titres == [
        "Opening Gala",
        "Late Laughs",
        "Deauville Comedy Club",
        "Closing Gala",
    ]


def test_artiste_inconnu(client):
    reponse = client.get("/api/artists/nobody")
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "No artist 'nobody'."}


def test_programme_complet(client):
    assert len(client.get("/api/programme").json()) == 23


def test_programme_d_un_jour(client):
    vendredi = client.get("/api/programme", params={"day": "2027-06-11"}).json()
    assert len(vendredi) == 7
    assert vendredi[-1]["title"] == "After Hours"


def test_programme_d_une_salle(client):
    kiosque = client.get("/api/programme", params={"venue": "le-kiosque"}).json()
    assert len(kiosque) == 7


def test_programme_jour_et_salle(client):
    params = {"day": "2027-06-11", "venue": "le-kiosque"}
    titres = [s["title"] for s in client.get("/api/programme", params=params).json()]
    assert titres == ["Writing a Punchline", "Late Laughs", "After Hours"]


def test_programme_salle_inconnue(client):
    reponse = client.get("/api/programme", params={"venue": "nowhere"})
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "No venue 'nowhere'."}


def test_programme_jour_mal_ecrit(client):
    assert client.get("/api/programme", params={"day": "June 11"}).status_code == 422


def test_vue_d_un_plateau(client):
    assert client.get("/api/performances/le-kiosque-2027-06-12-0100").json() == {
        "id": "le-kiosque-2027-06-12-0100",
        "kind": "lineup",
        "title": "After Hours",
        "venue": "le-kiosque",
        "venue_name": "Le Kiosque",
        "start": "2027-06-12T01:00",
        "end": "2027-06-12T02:00",
        "duration_minutes": 60,
        "festival_day": "2027-06-11",
        "description": "The last show of Friday night, after midnight.",
        "summary": "hosted by Tom Vasseur, with Hugo Lemaire, Maya Choukri",
        "capacity": 120,
        "host": "tom-vasseur",
        "acts": ["hugo-lemaire", "maya-choukri"],
        "artists": [
            {"slug": "tom-vasseur", "name": "Tom Vasseur"},
            {"slug": "hugo-lemaire", "name": "Hugo Lemaire"},
            {"slug": "maya-choukri", "name": "Maya Choukri"},
        ],
    }


def test_vue_d_un_atelier(client):
    atelier = client.get("/api/performances/la-cabane-2027-06-11-1030").json()
    assert atelier["teacher"] == "ines-moreau"
    assert atelier["max_participants"] == 12
    assert atelier["participants"] == ["Camille R.", "Yanis B.", "Lou M."]
    assert atelier["places_left"] == 9


def test_vue_d_un_solo(client):
    solo = client.get("/api/performances/le-kiosque-2027-06-11-2330").json()
    assert solo["artist"] == "max-pellerin"
    assert solo["min_age"] == 18
    assert solo["summary"] == "Max Pellerin"


def test_spectacle_inconnu(client):
    assert client.get("/api/performances/nothing").status_code == 404


def test_maintenant_a_21h(client):
    reponse = client.get("/api/now", params={"at": "2027-06-11T21:00"}).json()
    assert [s["title"] for s in reponse["now_playing"]] == ["Tall Tales"]
    suivants = [s["title"] for s in reponse["up_next"]]
    assert suivants == ["Straight Face", "Late Laughs", "After Hours"]


def test_maintenant_apres_minuit(client):
    reponse = client.get("/api/now", params={"at": "2027-06-12T01:30"}).json()
    assert [s["title"] for s in reponse["now_playing"]] == ["After Hours"]
    assert len(reponse["up_next"]) == 3


def test_maintenant_mal_ecrit(client):
    assert client.get("/api/now", params={"at": "ce soir"}).status_code == 422


# ===== Écritures =====


def test_ajouter_un_solo_est_sauve(client, fichier):
    reponse = client.post("/api/performances", json=SOLO)
    assert reponse.status_code == 201
    assert reponse.json()["id"] == "le-kiosque-2027-06-13-1100"
    sauve = json.loads(fichier.read_text(encoding="utf-8"))
    assert len(sauve["performances"]) == 24
    relu = TestClient(create_app(StockageJson(fichier)))
    assert relu.get("/api/performances/le-kiosque-2027-06-13-1100").status_code == 200


def test_ajouter_un_plateau_et_un_atelier(client):
    plateau = {
        **SOLO,
        "kind": "lineup",
        "venue": "la-cabane",
        "start": "2027-06-13T08:00",
        "host": "tom-vasseur",
        "acts": ["hugo-lemaire", "maya-choukri"],
    }
    del plateau["artist"]
    assert client.post("/api/performances", json=plateau).status_code == 201
    atelier = {
        "kind": "workshop",
        "title": "Atelier",
        "venue": "grand-casino",
        "start": "2027-06-13T09:00",
        "duration_minutes": 60,
        "teacher": "jeanne-aubry",
        "max_participants": 999,
    }
    reponse = client.post("/api/performances", json=atelier)
    assert reponse.status_code == 201
    assert reponse.json()["places_left"] == 650


def test_salle_occupee_409(client):
    client.post("/api/performances", json=SOLO)
    reponse = client.post(
        "/api/performances", json={**SOLO, "start": "2027-06-13T11:30"}
    )
    assert reponse.status_code == 409
    assert "Le Kiosque is busy" in reponse.json()["detail"]


def test_artiste_sur_scene_409(client):
    client.post("/api/performances", json=SOLO)
    ailleurs = {**SOLO, "venue": "grand-casino", "start": "2027-06-13T12:00"}
    reponse = client.post("/api/performances", json=ailleurs)
    assert reponse.status_code == 409
    assert "Nora Lebrun is on stage" in reponse.json()["detail"]


def test_plateau_avec_un_seul_numero_422(client):
    plateau = {
        **SOLO,
        "kind": "lineup",
        "start": "2027-06-13T08:00",
        "host": "tom-vasseur",
        "acts": ["hugo-lemaire"],
    }
    reponse = client.post("/api/performances", json=plateau)
    assert reponse.status_code == 422
    assert "at least two acts" in reponse.json()["detail"]


@pytest.mark.parametrize(
    "changement",
    [
        {"duration_minutes": 0},
        {"duration_minutes": 361},
        {"duration_minutes": "half an hour"},
        {"start": "2027-06-20T11:00"},
        {"start": "demain"},
        {"min_age": 19},
        {"kind": "concert"},
    ],
)
def test_valeurs_invalides_422(client, changement):
    reponse = client.post("/api/performances", json={**SOLO, **changement})
    assert reponse.status_code == 422


def test_champ_manquant_422(client):
    sans_artiste = {k: v for k, v in SOLO.items() if k != "artist"}
    assert client.post("/api/performances", json=sans_artiste).status_code == 422


def test_salle_ou_artiste_inconnus_404(client):
    salle = client.post("/api/performances", json={**SOLO, "venue": "nowhere"})
    assert salle.status_code == 404
    artiste = client.post("/api/performances", json={**SOLO, "artist": "nobody"})
    assert artiste.status_code == 404


def test_put_change_l_id(client):
    client.post("/api/performances", json=SOLO)
    reponse = client.put(
        "/api/performances/le-kiosque-2027-06-13-1100",
        json={**SOLO, "start": "2027-06-13T12:00"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["id"] == "le-kiosque-2027-06-13-1200"
    assert client.get("/api/performances/le-kiosque-2027-06-13-1100").status_code == 404


def test_put_refuse_ne_change_rien(client, fichier):
    client.post("/api/performances", json=SOLO)
    avant = fichier.read_text(encoding="utf-8")
    reponse = client.put(
        "/api/performances/le-kiosque-2027-06-13-1100",
        json={**SOLO, "start": "2027-06-13T15:00"},
    )
    assert reponse.status_code == 409
    assert client.get("/api/performances/le-kiosque-2027-06-13-1100").status_code == 200
    assert fichier.read_text(encoding="utf-8") == avant


def test_put_spectacle_inconnu_404(client):
    assert client.put("/api/performances/nothing", json=SOLO).status_code == 404


def test_delete_deux_fois(client):
    url = "/api/performances/le-kiosque-2027-06-12-0100"
    premier = client.delete(url)
    assert premier.status_code == 204
    assert premier.content == b""
    assert client.delete(url).status_code == 404


def test_inscrire_un_participant(client):
    url = "/api/performances/la-cabane-2027-06-12-1030/participants"
    reponse = client.post(url, json={"name": "Zoé"})
    assert reponse.status_code == 201
    assert "Zoé" in reponse.json()["participants"]


def test_inscrire_deux_fois_le_meme_409(client):
    url = "/api/performances/la-cabane-2027-06-12-1030/participants"
    client.post(url, json={"name": "Zoé"})
    assert client.post(url, json={"name": "zoé"}).status_code == 409


def test_atelier_complet_409(client):
    url = "/api/performances/la-cabane-2027-06-12-1030/participants"
    for i in range(6):
        assert client.post(url, json={"name": f"Personne {i}"}).status_code == 201
    reponse = client.post(url, json={"name": "En trop"})
    assert reponse.status_code == 409
    assert "full" in reponse.json()["detail"]


def test_inscrire_a_un_plateau_422(client):
    url = "/api/performances/le-kiosque-2027-06-12-0100/participants"
    assert client.post(url, json={"name": "Lou"}).status_code == 422


def test_ajouter_un_artiste(client):
    reponse = client.post(
        "/api/artists", json={"name": "Zoé Tanguy", "bio": "Nouvelle"}
    )
    assert reponse.status_code == 201
    assert reponse.json()["slug"] == "zoe-tanguy"
    assert client.get("/api/artists/zoe-tanguy").json()["bio"] == "Nouvelle"


def test_artiste_en_double_409(client):
    client.post("/api/artists", json={"name": "Zoé Tanguy"})
    assert client.post("/api/artists", json={"name": "zoe tanguy"}).status_code == 409


# ===== Erreur d'écriture et site =====


class StockageCasse(StockageMemoire):
    def sauver(self, festival: Festival) -> None:
        raise StockageError("the disk is full.")


def test_erreur_d_ecriture_500():
    donnees = json.loads(DONNEES.read_text(encoding="utf-8"))
    client = TestClient(create_app(StockageCasse(donnees)))
    reponse = client.post("/api/performances", json=SOLO)
    assert reponse.status_code == 500
    assert reponse.json() == {"detail": "the disk is full."}


def test_le_site_et_l_admin_sont_servis(client):
    assert client.get("/").status_code == 200
    assert client.get("/artist.html").status_code == 200
    assert client.get("/admin/").status_code == 200
