# ---------------------------------------------------------------- #
#                                                                  #
#  - robotCamera.py                                                #
#                                                                  #
#  Contient la classe faisant fonctionner la caméra du robot.      #
#                                                                  #
# ---------------------------------------------------------------- #

# Importe les différents modules standard de Python nécessaire.
import io
import picamera
import socketserver
import threading
from threading import Condition
from http import server

# Défini l"instance de la classe de sortie vidéo.
# La création d"une variable globale aurait pu être éviter
# mais aurait complexifier le projet d"ISN avec la nécessité
# d"une fabrique (patron de conception).
robotCameraOutput = None

# Classe gérant la sortie vidéo de la caméra du robot.
class RobotCamera_Output(object):
    # Constructeur de la classe.
    def __init__(self):
        # Défini les propriétés de la classe.
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    # Écrit le contenue obtenu par la sortie vidéo à envoyer aux clients.
    def write(self, buf):
        if buf.startswith(b"\xff\xd8"):
            # Défini la taille du buffer avec le nombre de bytes qu'il possède actuellement.
            self.buffer.truncate()

            # Accède à la condition de l'instance:
            with self.condition:
                # Crée la frame avec la valeur du buffer.
                self.frame = self.buffer.getvalue()
                # Notifie les RobotCamera_RequestHandler que la condition est vérifiée.
                self.condition.notify_all()

            # Change la position d'écriture du buffer à la position 0.
            self.buffer.seek(0)

        # Retourne le contenu du buffer.
        return self.buffer.write(buf)

# Classe gérant les requêtes du serveur de la caméra.
class RobotCamera_RequestHandler(server.BaseHTTPRequestHandler):
    # Gère les requêtes GET demandé par le client.
    def do_GET(self):
        # Utilise la variable globale output.
        global robotCameraOutput

        # Envoie une réponse de code 200 (succès).
        self.send_response(200)
        # Défini le type de contenue:
        # - multipart: Indique que c'est fragmenté (car flux vidéo).
        # - x-mixed-replace: Indique que le contenu est mis à jour en direct.
        # - boundary=FRAME: Indique que le contenu est de type vidéo.
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        # Fin de l"écriture du header de la requête.
        self.end_headers()

        # On essaie:
        try:
            # Tant que le client est connecté:
            while True:
                # Avec la condition du robotCameraOutput:
                with robotCameraOutput.condition:
                    # Attendre que la condition soit résolu.
                    robotCameraOutput.condition.wait()
                    # Prendre la frame obtenu par le robotCameraOutput.
                    frame = robotCameraOutput.frame

                # Défini le contenu comme une FRAME (image de vidéo).
                self.wfile.write(b"--FRAME\r\n")

                # Défini le format du contenu.
                self.send_header("Content-Type", "image/jpeg")
                # Défini la longueur du contenu.
                self.send_header("Content-Length", len(frame))
                # Fin de l"écriture du header de la requête.
                self.end_headers()

                # On écrit la frame actuel dans le flux vidéo.
                self.wfile.write(frame)
                # Crée une nouvelle ligne (depuis le début de la ligne).
                self.wfile.write(b"\r\n")
        # Sinon:
        # (la déconnexion d"un client émet une exception).
        except Exception as e:
            # On ne fait rien.
            return
    # Cette méthode est utilisé pour indiquer les messages des requêtes HTTP.
    def log_message(self, format, *args):
        # On ne fait rien (dans la fonction d"origine de la classe mère, elles sont "printer").
        return

# Classe gérant le serveur HTTP de la caméra.
class RobotCamera_Server(socketserver.ThreadingMixIn, server.HTTPServer):
    # Autorise l"utilisation d"une adresse IP et port déjà en cours d"utilisation.
    allow_reuse_address = True
    # Autorise à terminer ce thread si le thread principal (celui-ci) est terminé.
    daemon_threads = True

# Classe gérant la caméra du robot.
class RobotCamera(threading.Thread):
    # Démarre le thread (automatiquement appelé par start()).
    def run(self):
        # Utilise la variable globale output.
        global robotCameraOutput

        # Crée la caméra.
        camera = picamera.PiCamera(resolution="720x576", framerate=24)
        # Crée la variable globale de la sortie vidéo.
        robotCameraOutput = RobotCamera_Output()
        # Commence l"enregistrement vidéo.
        camera.start_recording(robotCameraOutput, format="mjpeg")

        # Tant que le thread est en cours:
        try:
            # Crée le serveur de streaming de la caméra du robot (même IP que le serveur principal, port différent).
            server = RobotCamera_Server(("0.0.0.0", 4445), RobotCamera_RequestHandler)
            # On stream le serveur jusqu"à l"arrêt du thread.
            server.serve_forever()
        # Sinon:
        finally:
            # On arrête l"enregistrement vidéo.
            camera.stop_recording()
