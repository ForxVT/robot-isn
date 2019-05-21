# ---------------------------------------------------------------- #
#                                                                  #
#  - server.py                                                     #
#                                                                  #
#  Contient la classe faisant fonctionner le serveur.              #
#                                                                  #
# ---------------------------------------------------------------- #

# Importe les différents modules standard de Python nécessaire.
import socket
import struct
import uuid
import sys
import threading
import re
import select
import platform
import io
import itertools
from hashlib import sha1
from base64 import b64encode

# Classe du client.
class Client:
    # Socket de connexion du client.
    connection = None
    # Adresse du client.
    address = None
    # État de la connexion du client.
    isConnected = False

    # Constructeur de la classe.
    def __init__(self, connection, address):
        # Défini les propriétés de la classe.
        self.connection = connection
        self.address = address
        self.isConnected = True

# Classe du serveur.
class Server(threading.Thread):
    # État du serveur (en fonctionnement ou en extinction).
    isRunning = False
    # État de la connexion du serveur (possède au moins un client ou non).
    isConnected = False
    # Liste des clients actuellement connectés.
    currentClients = []
    # Gestion des moteurs du robot.
    robotEngine = None
    # Gestion de la caméra du robot.
    robotCamera = None

    # Démarre le serveur.
    def run(self):
        print("[SERVER] Démarrage du serveur...")

        # Défini le serveur comme en cours de fonctionnement.
        self.isRunning = True

        if "raspberrypi" in platform.uname():
            # Importe le module moteur.
            import robotEngine, robotCamera
            # Crée l'instance de la classe gérant les moteurs du robot.
            self.robotEngine = robotEngine.RobotEngine()
            # Crée l'instance de la classe gérant la caméra du robot.
            self.robotCamera = robotCamera.RobotCamera()
            # Démarre l'instance de robotEngine (un thread).
            self.robotEngine.start()
            # Démarre l'instance de robotCamera (un thread).
            self.robotCamera.start()
        # Crée le socket.
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Indique au socket de réutiliser la connection si elle est déjà utilisé.
        # (ce peut arriver si la connexion est fermée abruptement.)
        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1);
        # Écoute l'adresse l'ipv4 actuel du réseau sur le port 4444
        self.connection.bind(("0.0.0.0", 4444))
        # Autorise jusqu'à 5 échecs de connexions.
        self.connection.listen(5)

        print("[SERVER] En attente de connexions...")

        # Défini une liste des connexions actives
        # (seulement utile pour le fonctionnement de
        # la boucle suivante).
        connectionList = [self.connection]

        # Continue tant que le serveur est en marche.
        while self.isRunning:
            # Crée des listes pour les différents élements
            readable, writable, errored = select.select(connectionList, [], [])
            for s in readable:
                if s is self.connection:
                    # Attend la réception d'une demande de connexion d'un nouveau client.
                    connection, connectionAddress = self.connection.accept()

                    print("[SERVER] Demande de connexion reçu:", connectionAddress)

                    # Connecte le client.
                    client = self.connect(connection, connectionAddress)

                    # Si le client n'est pas nul:
                    if client != None:
                        # Ajoute la connexion à la liste des connexions.
                        connectionList.append(connection)

                        # Crée un thread pour écouter le client
                        # (l'intérêt des threads est d'avoir un nombres
                        # indéterminé de clients possible).
                        threading.Thread(target=self.listenToClient, args=[client]).start()

    # Écoute un client.
    def listenToClient(self, client):
        # Bloque le thread pour éviter les pertes de données.
        lock = threading.Lock()
        lock.acquire()

        print("[CLIENT " + str(self.currentClients.index(client)) + "] " + "Client connecté.")

        # Continue tant que le client est connecté
        while client.isConnected:
            # Attend la réception d'un message du client.
            data = client.connection.recv(1024)
            
            # Vérifie que le message reçu n'est pas vide.
            if data != b"":
                # Décode le mssage (selon l'encodage du protocole WebSocket).
                message = self.decodeMessage(data)

                # Vérifie que le message décodé n'est pas vide.
                if message != "":
                    print("[CLIENT " + str(self.currentClients.index(client)) + "] " + "Message reçu:", message)

                    # Lit le message reçu pour obtenir une réponse.
                    answer = self.readMessageFromClient(message, client)
                    # Envoyer la réponse au client ayant envoyé le message.
                    self.sendToClient(answer, client)

        if self.isRunning:
            print("[CLIENT " + str(self.currentClients.index(client)) + "] " + "Fin de la connexion.")

        # Le client est déconnecté, alors on le supprime
        # de la liste des clients.
        self.currentClients.remove(client)

        # Libère le thread.
        lock.release()

    # Stop le serveur.
    def stop(self):
        print("[SERVER] Extinction du serveur...")

        # Défini le serveur comme en cours d'extinction.
        self.isRunning = False
        # Envoi un message d'extinction à chaque clients.
        self.sendToAllClients("shutdown")
        # Ferme le socket du serveur.
        self.connection.close()
        # Si il y a des moteurs:
        if self.robotEngine != None:
            # Dit aux moteurs de s'arrêter.
            self.robotEngine.stop()

    # Connecte un client à l'aide du protocole WebSocket.
    # Voir: https://tools.ietf.org/html/rfc6455#section-4
    def connect(self, connection, connectionAddress):
        # Attend de recevoir les données de la demande
        # de connexion ("handshake" du protocole WebSocket).
        connectionData = connection.recv(1024).decode("utf-8")

        # Si les données ne sont pas nul:
        if connectionData != "":
            print("[SERVER] Connexion d'un client...");

            # Récupère la clé sécurisé envoyé.
            receivedKey = (re.search("Sec-WebSocket-Key:\s+(.*?)[\n\r]+", connectionData).groups()[0].strip())
            # Converti la clé et un identifiant universelle nécessaire par le protocole au format sécurisé SHA-1.
            receivedKeySHA1 = sha1((receivedKey + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8")).digest()
            # Encode la clé en base64.
            responseKey = b64encode(receivedKeySHA1)
            # Crée la chaîne de caractère de réponse.
            response = "\r\n".join((
                    'HTTP/1.1 101 Switching Protocols',
                    'Upgrade: websocket','Connection: Upgrade',
                    'Sec-WebSocket-Accept: {key}\r\n\r\n'
                )).format(key = responseKey).replace("b'", "").replace("'", "")
            # Envoie la réponse.
            connection.sendto(response.encode("utf-8"), connectionAddress)

            # Ajoute un nouveau client avec les valeurs obtenus
            # durant la connexion à la liste des clients.
            self.currentClients.append(Client(connection, connectionAddress))
            # Défini le serveur comme connecté à un client.
            self.isConnected = True

            # Retourne le dernier client.
            return self.currentClients[-1]

        print("[SERVER] La connexion ne provient pas d'un client valide.");

        return None

    # Décode un message (selon l'encodage du protocole WebSocket).
    # Voir: https://tools.ietf.org/html/rfc6455#section-5
    def decodeMessage(self, message):
        # Crée un stream de lecture du message.
        buffer = io.BytesIO(message)
        # Lis le header du message (dont on ne s'intéresse pas ici).
        # (contenu sur le premier byte)
        data = buffer.read1(1)
        # Lis la longueur du message.
        # (contenu sur le second byte)
        data = buffer.read1(1)
        # Obtient le nombre de byte à lire pour le message (par conversion de type).
        length, = struct.unpack("!B", data)
        # Effectue une opération AND sur la longueur.
        length = length & 127

        # Si la longueur est égal à 126:
        if length == 126:
            # Lis les deux prochains bytes.
            data = buffer.read1(2)
            # Obtient le nombre de byte à lire pour le message (par conversion de type).
            length, = struct.unpack("!H", data)
        # Si la longueur est égal à 127:
        elif length == 127:
            # Lis les 8 prochains bytes.
            data = buffer.read1(8)
            # Obtient le nombre de byte à lire pour le message (par conversion de type).
            length, = struct.unpack("!Q", data)

        # Lis le mask des données.
        mask = buffer.read1(4)
        # Lis le message.
        data = buffer.read1(length)
        # Obtient les données en appliquant le mask dessus.
        data = bytes(b ^ m for b, m in zip(data, itertools.cycle(mask)))

        # Retourne le message décodé.
        return data.decode("utf-8")

    # Encode un message (selon l'encodage du protocole WebSocket).
    # Voir: https://tools.ietf.org/html/rfc6455#section-5
    def encodeMessage(self, message):
        # Contient le message encodé en binaire (au format utf-8).
        data = message.encode("utf-8")
        # Contient la taille du message encodé.
        length = len(data)
        # Content un stream d'écriture en binaire.
        encodedMessage = io.BytesIO()

        # Ajoute 81 en binaire (= 1010001) en tant que premier octet du stream.
        # Ce "81" permet d'indiquer au protocole que le message sera du texte.
        encodedMessage.write(b"\x81")

        # Si le message est plus petit que 126:
        if length < 126:
            # Ajoute la taille du message en second byte, formaté
            # à la bonne taille en byte (selon les structures en C):
            # !: L'ordre des bytes est en big-endian.
            # B: Le byte est au format "unsigned char" (entre 0 - 2^8 en C) donc prend 1 byte.
            encodedMessage.write(struct.pack("!B", length))
        # Sinon, si le message est plus petit que 65536 (= 2^16): 
        elif length < 65536:
            # Ajoute la taille du payload en second byte puis la taille du
            # message en troisième, formaté à la bonne taille de chaque byte:
            # !: L'ordre des bytes est en big-endian.
            # B: Le byte est au format "unsigned char" (entre 0 - 2^8 en C) donc prend 1 byte.
            # H: Le byte est au format "unsigned long long" (entre 0 - 2^16 en C) donc prend 2 byte.
            encodedMessage.write(struct.pack("!BH", 126, length))
        # Sinon, il est plus grand:
        else:
            # Ajoute la taille du payload en second byte puis la taille du
            # message en troisième, formaté à la bonne taille de chaque byte:
            # !: L'ordre des bytes est en big-endian.
            # B: Le byte est au format "unsigned char" (entre 0 - 2^8 en C) donc prend 1 byte.
            # Q: Le byte est au format "unsigned long long" (entre 0 - 2^64 en C) donc prend 8 byte.
            encodedMessage.write(struct.pack("!BQ", 127, length))

        # Ajoute le message dans le stream d'écriture.
        encodedMessage.write(data)

        # Retourne la valeur contenue dans le stream d'écriture.
        return encodedMessage.getvalue()

    # Fonction permettant de traiter un message et retourner une réponse.
    def readMessageFromClient(self, message, client):
        # Crée une variable de réponse pour le message du client.
        answer = u"Requête inconnue."
        # Sépare le message pour chaque espace.
        # (de manière à pouvoir ajouter des arguments après une instruction).
        toks = message.split(" ")

        # Déconnecte le client du serveur.
        # (Pourquoi startwith et non == ?
        # Car il est possible de recevoir un message illisible si un client
        # est déconnecté abruptement, mais nous envoyons déjà le message
        # "disconnect" lorsque la page d'un client se ferme alors il peut
        # arriver que les deux soit concaténer.
        if toks[0].startswith("disconnect"):
            # Déconnecte le client.
            client.isConnected = False
        # Déconnecte le client et stop le serveur.
        elif toks[0] == "shutdown":
            # Déconnecte le client.
            client.isConnected = False
            # Défini le serveur comme en cours d'extinction.
            self.isRunning = False
        # Si le serveur tourne sur un robot:
        elif self.robotEngine != None:
            # Change la vitesse des moteurs.
            if toks[0] == "set":
                self.robotEngine.setSpeeds(int(toks[1]), int(toks[2]))
                answer = "Vitesse actuelle du robot: (" + str(self.robotEngine.speeds[0]) + ", " + str(self.robotEngine.speeds[1]) + ")"
            # Change la vitesse du côté gauche des moteurs.
            elif toks[0] == "setl":
                self.robotEngine.setSpeedLeft(int(toks[1]))
                answer = "Vitesse actuelle du robot: (" + str(self.robotEngine.speeds[0]) + ", " + str(self.robotEngine.speeds[1]) + ")"
            elif toks[0] == "setr":
                self.robotEngine.setSpeedRight(int(toks[1]))
                answer = "Vitesse actuelle du robot: (" + str(self.robotEngine.speeds[0]) + ", " + str(self.robotEngine.speeds[1]) + ")"

        # Retourne la réponse.
        return answer

    # Fonction permettant d'envoyer un message à un client.
    def sendToClient(self, messageToSend, client):
        # Condition pour éviter d'envoyer ce log lors de l'extinction du serveur.
        if self.isRunning and client.isConnected:
            print("[CLIENT " + str(self.currentClients.index(client)) + "] " + "Réponse envoyée:", messageToSend)
        
        # Encode la réponse.
        encodedMessageToSend = self.encodeMessage(messageToSend)
        # Envoi le message au client.
        client.connection.send(encodedMessageToSend)

    # Fonction permettant d'envoyer un message à tout les clients.
    def sendToAllClients(self, messageToSend):
        # Boucle pour obtenir chaque clients.
        for client in self.currentClients:
            # Envoi le message au client.
            self.sendToClient(messageToSend, client)
