import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, request

SCHEDULE_PATH = Path(__file__).resolve().parent / "data" / "times.json"
PORT = int(os.environ.get("SCHEDULE_PORT", "3002"))
HOST = "0.0.0.0"

app = Flask(__name__)
scheduleLock = Lock()


# ====================================
# ==== Read & write des schedules ====
# ====================================


def load_schedule_fichier():
    """Charge les schedules depuis le json"""

    with SCHEDULE_PATH.open("r", encoding="utf-8") as fichier:
        return json.load(fichier)


def save_schedule_fichier(scheduleData):
    """Remplace le fichier après avoir écrit le document complet"""

    temporaryPath = SCHEDULE_PATH.with_suffix(".tmp")

    with temporaryPath.open("w", encoding="utf-8") as fichier:
        json.dump(scheduleData, fichier, indent=2, ensure_ascii=False)
        fichier.write("\n")

    temporaryPath.replace(SCHEDULE_PATH)


def validate_schedule_date(dateValue):
    """Vérifie le format qu'on a (YYYYMMDD) et l'existence de la date"""

    if len(dateValue) != 8 or not dateValue.isdigit():
        return False

    try:
        datetime.strptime(dateValue, "%Y%m%d")
    except ValueError:
        return False

    return True


#### Routes REST Schedule ####


@app.route("/schedule", methods=["GET"])
def get_all_schedules():
    """Retourne tous les schedules"""

    with scheduleLock:
        scheduleData = load_schedule_fichier()

    return jsonify(scheduleData), 200


@app.route("/schedule/<dateValue>", methods=["GET"])
def get_schedule_par_date(dateValue):
    """Recherche le schedule d'une date"""

    if not validate_schedule_date(dateValue):
        return (
            jsonify(
                {
                    "error": " date doit être valide au format YYYYMMDD.",
                }
            ),
            400,
        )

    with scheduleLock:
        scheduleData = load_schedule_fichier()

    for entry in scheduleData["schedule"]:
        if entry["date"] == dateValue:
            return jsonify(entry), 200

    return (
        jsonify(
            {
                "error": "pas de schedule pour la dante donnée",
            }
        ),
        404,
    )


@app.route("/schedule", methods=["POST"])
def create_schedule():
    """Crée un schedule sans remplacer une date déjà programmée"""

    requestData = request.get_json(silent=True)

    if not isinstance(requestData, dict):
        return (
            jsonify(
                {
                    "error": "body doit être json",
                }
            ),
            400,
        )

    dateValue = requestData.get("date")
    movieIds = requestData.get("movies")

    if not validate_schedule_date(dateValue):
        return (
            jsonify(
                {
                    "error": "date doit être au format YYYYMMDD",
                }
            ),
            400,
        )

    if not isinstance(movieIds, list) or not movieIds:
        return (
            jsonify(
                {
                    "error": "movies doit être une liste non vide",
                }
            ),
            400,
        )

    if any(not isinstance(movieId, str) or not movieId.strip() for movieId in movieIds):
        return (
            jsonify(
                {
                    "error": "Schedule doit contenir au moins un movie id non vide",
                }
            ),
            400,
        )

    if len(movieIds) != len(set(movieIds)):
        return (
            jsonify(
                {
                    "error": "Movie id ne peut PAS être présent plusieurs fois",
                }
            ),
            400,
        )

    with scheduleLock:
        scheduleData = load_schedule_fichier()

        for entry in scheduleData["schedule"]:
            if entry["date"] == dateValue:
                return (
                    jsonify(
                        {
                            "error": "schedule existe déjà pour cette date",
                        }
                    ),
                    409,
                )

        newSchedule = {"date": dateValue,
                       "movies": movieIds,
                      }

        scheduleData["schedule"].append(newSchedule)
        save_schedule_fichier(scheduleData)

    return jsonify(newSchedule), 201


@app.route("/schedule/<dateValue>", methods=["DELETE"])
def delete_schedule(dateValue):
    """Supprime le schedule d'une date"""

    if not validate_schedule_date(dateValue):
        return (
            jsonify(
                {
                    "error": "date doit être au format YYYYMMDD",
                }
            ),
            400,
        )

    with scheduleLock:
        scheduleData = load_schedule_fichier()

        for entry in scheduleData["schedule"]:
            if entry["date"] == dateValue:
                scheduleData["schedule"].remove(entry)
                save_schedule_fichier(scheduleData)
                return "", 204

    return (
        jsonify(
            {
                "error": "pas de schedule pour cette date",
            }
        ),
        404,
    )


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
