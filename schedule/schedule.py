import json
import os
from concurrent import futures
from datetime import datetime
from pathlib import Path
from threading import Lock

import grpc

import schedule_pb2
import schedule_pb2_grpc

SCHEDULE_PATH = Path(__file__).resolve().parent / "data" / "times.json"
PORT = int(os.environ.get("SCHEDULE_PORT", "3002"))


def validate_schedule_date(dateValue, context):
    """Vérifie le format qu'on a (YYYYMMDD) et l'existence de la date"""

    if len(dateValue) != 8 or not dateValue.isdigit():
        context.abort(
            grpc.StatusCode.INVALID_ARGUMENT,
            "La date doit respecter le format YYYYMMDD",
        )

    try:
        datetime.strptime(dateValue, "%Y%m%d")
    except ValueError:
        context.abort(
            grpc.StatusCode.INVALID_ARGUMENT,
            "Date n'existe pas",
        )


class ScheduleServicer(schedule_pb2_grpc.ScheduleServicer):
    """Implémente le truc le contrat défini dans schedule.proto"""

    def __init__(self):
        """Initialise le lock qui protège les accès au fichier json"""

        self.dataLock = Lock()

    def load_schedule_fichier(self):
        """Charge les schedules depuis le json"""

        with SCHEDULE_PATH.open("r", encoding="utf-8") as fichier:
            return json.load(fichier)

    def save_schedule_fichier(self, scheduleData):
        """Remplace le fichier après avoir écrit le document complet"""

        temporaryPath = SCHEDULE_PATH.with_suffix(".tmp")

        with temporaryPath.open("w", encoding="utf-8") as fichier:
            json.dump(scheduleData, fichier, indent=2, ensure_ascii=False)
            fichier.write("\n")

        temporaryPath.replace(SCHEDULE_PATH)

    def GetSchedules(self, request, context):
        """Retourne tous les schedules"""

        with self.dataLock:
            scheduleData = self.load_schedule_fichier()

        return schedule_pb2.SchedulesResponse(
            schedules=[
                schedule_pb2.ScheduleEntry(
                    date=entry["date"],
                    movies=entry["movies"],
                )
                for entry in scheduleData["schedule"]
            ],
        )

    def GetScheduleByDate(self, request, context):
        """Recherche le schedule d'une date"""

        validate_schedule_date(request.date, context)

        with self.dataLock:
            scheduleData = self.load_schedule_fichier()

        for entry in scheduleData["schedule"]:
            if entry["date"] == request.date:
                return schedule_pb2.ScheduleEntry(
                    date=entry["date"],
                    movies=entry["movies"],
                )

        context.abort(
            grpc.StatusCode.NOT_FOUND,
            "Aucun schedule pour la date donnée",
        )

    def CreateSchedule(self, request, context):
        """Crée un schedule sans remplacer une date déjà programmée"""

        validate_schedule_date(request.date, context)
        movieIds = list(request.movies)

        if not movieIds or any(not movieId.strip() for movieId in movieIds):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Schedule doit contenir au moins un movie id non vide",
            )

        if len(movieIds) != len(set(movieIds)):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Movie id ne peut PAS être présent plusieurs fois",
            )

        with self.dataLock:
            scheduleData = self.load_schedule_fichier()

            for entry in scheduleData["schedule"]:
                if entry["date"] == request.date:
                    context.abort(
                        grpc.StatusCode.ALREADY_EXISTS,
                        "schedule existe déjà pour cette date",
                    )

            newSchedule = {
                "date": request.date,
                "movies": movieIds,
            }

            scheduleData["schedule"].append(newSchedule)
            self.save_schedule_fichier(scheduleData)

        return schedule_pb2.ScheduleEntry(
            date=newSchedule["date"],
            movies=newSchedule["movies"],
        )

    def DeleteSchedule(self, request, context):
        """Supprime le schedule d'une date"""

        validate_schedule_date(request.date, context)

        with self.dataLock:
            scheduleData = self.load_schedule_fichier()

            for entry in scheduleData["schedule"]:
                if entry["date"] == request.date:
                    scheduleData["schedule"].remove(entry)
                    self.save_schedule_fichier(scheduleData)
                    return schedule_pb2.DeleteScheduleResponse(deleted=True)

        return schedule_pb2.DeleteScheduleResponse(deleted=False)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    schedule_pb2_grpc.add_ScheduleServicer_to_server(
        ScheduleServicer(),
        server,
    )

    boundPort = server.add_insecure_port(f"0.0.0.0:{PORT}")

    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=5).wait()


if __name__ == "__main__":
    serve()
