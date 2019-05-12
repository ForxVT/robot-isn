# ---------------------------------------------------------------- #
#                                                                  #
#  - main.py                                                       #
#                                                                  #
#  Contient la méthode principale du programme.                    #
#                                                                  #
# ---------------------------------------------------------------- #

# Importe les différents modules standard de Python nécessaire.
import server

# Démarre le programme (méthode main).
if __name__ == "__main__":
    print("===--------------------- SERVEUR ---------------------===")

    print("[MAIN] Démarrage du programme...")
    print("[MAIN] Pour quitter, appuyez sur Ctrl+C.")

    # Crée le serveur.
    server = server.Server()

    # Permet de capturer les interruptions clavier
    # provenant du thread serveur.
    try:
        # Permet de terminer le thread serveur si le processus
        # principal est aussi terminé.
        server.daemon = True

        # Démarre le serveur.
        server.start()

        # Effectue une boucle tant que le serveur est en marche.
        while server.isAlive(): 
            # Attend l'extinction du serveur.
            server.join(1)
    # Signale un SIGINT (interruption clavier)
    # provenant du programme (Ctrl+C).
    except (KeyboardInterrupt, SystemExit):
        # Ne rien faire.
        pass

    # Stop le serveur.
    server.stop()

    print("===---------------------------------------------------===")
