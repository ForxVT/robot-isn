// ---------------------------------------------------------------- //
//                                                                  //
//  - index.js                                                      //
//                                                                  //
//  Script JavaScript du site web.                                  //
//                                                                  //
// ---------------------------------------------------------------- //

console.log("[CLIENT] Client lancé.")

var webSocket = null;
var connected = false;

// Fonction effectué avant que la page soit déchargé.
window.onbeforeunload = function()
{
    if (connected)
    {
        webSocket.send("disconnect");
        webSocket.close();
    }
};

// Connecte le client au serveur.
function connect(domain)
{
    var numberOfErrors = 0;

    var TryConnecting = function(domain)
    {
        webSocket = new WebSocket(domain);

        webSocket.onerror = function()
        {
            numberOfErrors++;

            console.log("[CLIENT] En attente du serveur...");

            if (numberOfErrors > 10)
            {
                console.log("[CLIENT] Impossible de connecter le serveur.");
            }
            else
            {
                setTimeout(function()
                {
                    TryConnecting(domain);
                }, 100);
            }
        };

        webSocket.onopen = function()
        {
            console.log("[CLIENT] Connexion établie.");

            connected = true;

            document.getElementById("text-server-state").innerHTML = "Serveur connecté"
        };

        webSocket.onmessage = function(event)
        {
            console.log("[CLIENT] Réponse reçu: " + event.data);
            document.getElementById("answer").innerHTML = "Réponse: " + event.data;

            if (event.data == "disconnect" || event.data == "shutdown")
            {
                console.log("[CLIENT] Fin de la connexion.");

                webSocket.close();

                connected = false;

                document.getElementById("text-server-state").innerHTML = "Serveur déconnecté";

                var answer = "Extinction...";

                if (message == "disconnect")
                    answer = "Déconnexion..."

                document.getElementById("answer").innerHTML = "Réponse: " + answer;
            }
        }
    };

    TryConnecting(domain);
}

// Déconnecte le client du serveur (en envoyant un mesage de déconnexion au serveur).
function disconnect()
{
    console.log("[CLIENT] Fin de la connexion.");

    webSocket.close();

    connected = false;

    document.getElementById("text-server-state").innerHTML = "Serveur déconnecté";

    var answer = "Extinction...";

    if (message == "disconnect")
        answer = "Déconnexion..."

    document.getElementById("answer").innerHTML = "Réponse: " + answer;
}

// Envoi un message au serveur.
function sendMessage()
{
    var message = document.getElementById("message").value;

    if (connected && message != "")
    {
        webSocket.send(message);

        if (message == "disconnect" || message == "shutdown")
            disconnect();
    }
}

connect("ws://localhost:4444");