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
import os
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
        # Défini les propriétés du client.
        self.connection = connection
        self.isConnected = True
        self.address = address

# Classe du serveur.
class Server(threading.Thread):

    # Constructeur de la classe.
    def __init__(self):
        # Constructeur de la classe parente de Server.
        threading.Thread.__init__(self)

        # Défini les propriétés du serveur.
        self.isRunning = False
        self.isConnected = False
        self.currentClients = []

    # Démarre le serveur.
    def run(self):
        print("[SERVER] Démarrage du serveur...")

        # Défini le serveur comme en cours de fonctionnement.
        self.isRunning = True
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

                    # Ajoute la connexion à la liste des connexions.
                    connectionList.append(connection)

                    print("[SERVER] Demande de connexion reçu:", connectionAddress)

                    # Connecte le client.
                    client = self.connect(connection, connectionAddress)
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

    # Connecte un client à l'aide du protocole WebSocket.
    # Voir: https://tools.ietf.org/html/rfc6455#section-4
    def connect(self, connection, connectionAddress):
        print("[SERVER] Connexion d'un client...");

        # Attend de recevoir les données de la demande
        # de connexion ("handshake" du protocole WebSocket).
        connectionData = connection.recv(1024).decode("utf-8")
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
        #  Envoie la réponse.
        connection.sendto(response.encode("utf-8"), connectionAddress)

        # Ajoute un nouveau client avec les valeurs obtenus
        # durant la connexion à la liste des clients.
        self.currentClients.append(Client(connection, connectionAddress))
        # Défini le serveur comme connecté à un client.
        self.isConnected = True

        # Retourne le dernier client.
        return self.currentClients[-1]

    # Décode un message (selon l'encodage du protocole WebSocket).
    # Voir: https://tools.ietf.org/html/rfc6455#section-5
    # TODO: À documenter.
    def decodeMessage(self, message):
        # Effectue une opération bitwise AND
        # entre le 1er byte du message et 127.
        # Ce qui retourne la taille du paquet.
        payload_length = message[1] & 127
        # Défini les bytes du mask du message
        # (ce qui est avant le message, 2 bytes par défaut).
        index_mask = 2

        # Si la taille du paquet est 126:
        if payload_length == 126:
            # Le mask est de 2 bytes en plus.
            index_mask = 4
        # Si la taille du paquet est 127:
        elif payload_length == 127:
            # Le mask est de 8 bytes en plus.
            index_mask = 10

        masks = [m for m in message[index_mask: index_mask + 4]]
        indexFirstDataByte = index_mask + 4
        decodedChars = []
        un = []
        i = indexFirstDataByte
        j = 0

        # Tant qu'il reste un caractère à décoder:
        while i < len(message):
            # Décode un caractère et l'ajoute à la liste des caractères.
            decodedChars.append(chr((message[i] ^ masks[j % 4])))

            # Incrémente les variable itéré.
            i += 1
            j += 1

        # Crée le message décodé en joignant tout
        # les caractères décodés.
        decodedMessage = ''.join(decodedChars)

        return decodedMessage

    # Encode un message (selon l'encodage du protocole WebSocket).
    # Voir: https://tools.ietf.org/html/rfc6455#section-5
    # TODO: À documenter.
    def encodeMessage(self, message):
        # Crée la variable du message encodé.
        encodedMessage = ""
        # Le premier byte 0x81 permet d'indiquer
        # que le message sera un texte.
        byte1 = 0x81
        # Le second byte sera la taille du paquet.
        byte2 = 0
        l = b""
        # Prend la taille du message
        # (pour trouver la taille du paquet).
        payload_length = len(message.encode("utf-8"))

        encodedMessage += chr(byte1)

        # La taille du paquet est plus petit que 126:
        if payload_length < 126:
            byte2 |= payload_length
            encodedMessage += chr(byte2)
        # La taille du paquet est de 126:
        elif payload_length < (2 ** 16) - 1:
            byte2 |= 126
            encodedMessage += chr(byte2)
            l = struct.pack(">H", payload_length)
        # La taille du paquet est supérieur (127):
        else:
            l = struct.pack(">Q", payload_length)
            byte2 |= 127
            encodedMessage += chr(byte2)

        # Ajoute le message initial à la fin du paquet.
        encodedMessage += message
        # Encode le message en binaire.
        encodedMessageInByte = bytearray(encodedMessage, 'utf-8')
        #encodedMessageInByte += l
        # Enlève le premier byte rajouté par la conversion
        # qui est illisible par le client.
        del encodedMessageInByte[0:1]

        return encodedMessageInByte

    # Fonction permettant de traiter un message et retourner une réponse.
    def readMessageFromClient(self, message, client):
        # Crée une variable de réponse pour le message du client.
        answer = u"Requête inconnue.Requête inconnue.Requête inconnue.Requête inconnue.Requête inconnue.Requête inconnue.Requête inconnue.Requête inconnue.Requête inconnue.Requête inconnue."

        # Message qui déconnecte le client du serveur.
        # (Pourquoi startwith et non == ?
        # Car il est possible de recevoir un message illisible si un client
        # est déconnecté abruptement, mais nous envoyons déjà le message
        # "disconnect" lorsque la page d'un client se ferme alors il peut
        # arriver que les deux soit concaténer.
        if message.startswith("disconnect"):
            # Déconnecte le client.
            client.isConnected = False
        # Message qui déconnecte le client et stop le serveur.
        elif message == "shutdown":
            # Déconnecte le client.
            client.isConnected = False
            # Défini le serveur comme en cours d'extinction.
            self.isRunning = False

        # Retourne la réponse.
        return answer

    # Fonction permettant d'envoyer un message à un client.
    def sendToClient(self, messageToSend, client):
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
