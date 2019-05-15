// ---------------------------------------------------------------- //
//                                                                  //
//  - index.js                                                      //
//                                                                  //
//  Script JavaScript du site web.                                  //
//                                                                  //
// ---------------------------------------------------------------- //

// Variables globales.
var webSocket = null;
var connected = false;

// Connecte le client au serveur.
function connect(domain) {
    var numberOfErrors = 0;

    var tryToConnect = function(domain) {
        webSocket = new WebSocket(domain);

        webSocket.onerror = function() {
            numberOfErrors++;

            console.log("[CLIENT] En attente du serveur...");

            if (numberOfErrors > 15) {
                console.log("[CLIENT] Impossible de connecter le serveur.");
            } else {
                setTimeout(function() {
                    tryToConnect(domain);
                }, 100);
            }
        };

        webSocket.onopen = function() {
            changeState("connected");
        };

        webSocket.onmessage = function(event)
        {
            console.log("[CLIENT] Réponse reçu: " + event.data);

            if (event.data == "disconnect" || event.data == "shutdown") {
                changeState(event.data);
            } else {
                document.getElementById("text-answer").innerHTML = "Réponse: " + event.data;
            }
        }
    };

    tryToConnect(domain);
}

// Change l'état actuel de connexion du site.
// message: "connected" ou "disconnected" ou "shutdown".
function changeState(message) {
    if (message == "connected") {
        console.log("[CLIENT] Connexion établie.");

        connected = true;
        document.getElementById("text-server-state").innerHTML = "Serveur connecté";
    } else {
        console.log("[CLIENT] Fin de la connexion.");

        webSocket.close();

        connected = false;
        document.getElementById("text-server-state").innerHTML = "Serveur déconnecté";
        document.getElementById("text-answer").innerHTML = "Réponse: " + (message == "disconnect" ? "Déconnexion..." : "Extinction...");
    }
}

// Évènement appelé avant que la page soit déchargé.
window.onbeforeunload = function() {
    if (connected) {
        webSocket.send("disconnect");
        webSocket.close();
    }
};

// Évènement appelé lorsque l'élément "button-send" est cliqué.
function buttonSendOnClick() {
    // Prend la valeur de l'élément "input-message".
    var message = document.getElementById("input-message").value;

    if (connected && message != "") {
        webSocket.send(message);

        if (message == "disconnect" || message == "shutdown") {
            changeState(message);
        }
    }
}

// Évènement appelé lorsqu'une touche est appuyé dans l'élément "input-message".
function inputMessageOnKeyPress(event) {
    // Si c'est la touché entrée (keyCode = 13):
    if (event.keyCode == 13) {
        // On empêche l'évènement par défaut (qui recharge la page).
        event.preventDefault();
        // On envoie le message.
        buttonSendOnClick();
    }
}

// Tente de connecter le client à l'adrese suivante à l'aide du protocole WebSocket.
connect("ws://192.168.1.33:4444");
