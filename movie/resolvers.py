import json
from pathlib import Path
from threading import Lock
from uuid import uuid4

from graphql import GraphQLError

DATA_DIR = Path(__file__).resolve().parent / "data"
MOVIES_PATH = DATA_DIR / "movies.json"
ACTORS_PATH = DATA_DIR / "actors.json"
moviesLock = Lock()


# ===================================
# # ==== Read & write des movies ====
# ===================================


def load_movies_fichier():
    """Charge les movies depuis le fichier json"""

    with MOVIES_PATH.open("r", encoding="utf-8") as fichier:
        return json.load(fichier)


def save_movies_fichier(moviesData):
    """Remplace le fichier après avoir write le document complet"""

    temporaryPath = MOVIES_PATH.with_suffix(".tmp")

    with temporaryPath.open("w", encoding="utf-8") as fichier:
        json.dump(moviesData, fichier, indent=2, ensure_ascii=False)
        fichier.write("\n")

    temporaryPath.replace(MOVIES_PATH)


def validate_movie_texte(value, fieldName):
    """Vérifie qu'un champ texte contient une valeur utilisable"""

    cleanValue = value.strip()

    if not cleanValue:
        raise GraphQLError(f"Champ {fieldName} ne peut pas être vide")

    return cleanValue


#### Queries Movie ####


def all_movies(_, info):
    """Retourne tous les movies"""

    with moviesLock:
        return load_movies_fichier()["movies"]


def movie_with_id(_, info, _id):
    """Recherche un movie à partir de son id"""

    with moviesLock:
        moviesData = load_movies_fichier()

    for movie in moviesData["movies"]:
        if movie["id"] == _id:
            return movie

    return None


def resolve_actors_in_movie(movie, info):
    """Récupère les actors associés au current movie"""

    with ACTORS_PATH.open("r", encoding="utf-8") as fichier:
        actorsData = json.load(fichier)

    return [actor for actor in actorsData["actors"] if movie["id"] in actor["films"]]


#### Mutations Movie ####


def create_movie(_, info, _title, _director, _rating):
    """Crée un movie et save son nouvel id"""

    newMovie = {"id": str(uuid4()),
                "title": validate_movie_texte(_title, "title"),
                "director": validate_movie_texte(_director, "director"),
                "rating": _rating,
               }

    # On va garder le lock pendant la modif du fichier
    with moviesLock:
        moviesData = load_movies_fichier()
        moviesData["movies"].append(newMovie)
        save_movies_fichier(moviesData)

    return newMovie


def update_movie_rate(_, info, _id, _rate):
    """Modifie la note d'un movie et save le résultat"""

    with moviesLock:
        moviesData = load_movies_fichier()

        for movie in moviesData["movies"]:
            if movie["id"] != _id:
                continue

            movie["rating"] = _rate
            save_movies_fichier(moviesData)
            return movie

    return None


def delete_movie(_, info, _id):
    """Supprime un movie à partir de son id"""

    with moviesLock:
        moviesData = load_movies_fichier()

        for movie in moviesData["movies"]:
            if movie["id"] == _id:
                moviesData["movies"].remove(movie)
                save_movies_fichier(moviesData)
                return True

    return False
