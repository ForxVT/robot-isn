// ---------------------------------------------------------------- //
//                                                                  //
//  - index.js                                                      //
//                                                                  //
//  Script JavaScript du site web.                                  //
//                                                                  //
// ---------------------------------------------------------------- //

console.log("[CLIENT] Client lancé.")

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
                document.getElementById("text-answer").innerHTML = event.data;
            }
        }
    };

    document.getElementById("img-stream").src = "http://" + domain + ":4445/";
    tryToConnect("ws://" + domain + ":4444/");
}

// Change l'état actuel de connexion du site.
// message:
// - "connected": Défini le client comme connecté.
// - "disconnected": Défini le client comme déconnecté.
// - "shutdown": Défini le client comme déconnecté et le serveur comme éteint.
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
        document.getElementById("text-answer").innerHTML = (message == "disconnect" ? "Déconnexion..." : "Extinction...");
    }
}

// Envoi un message au serveur.
function sendMessage(message) {
    if (connected) {
        if (message != "") {
            webSocket.send(message);
            document.getElementById("input-message").placeholder = "";
            document.getElementById("input-message").value = "";

            if (message == "disconnect" || message == "shutdown") {
                changeState(message);
            }
        } else {
            console.log("[CLIENT] Tentative d'envoi d'un message vide.")
        }
    } else {
        console.log("[CLIENT] Tentative d'envoi d'un message alors que le serveur est déconnecté.");
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
    // Envoi la valeur de l'élément "input-message".
    sendMessage(document.getElementById("input-message").value);
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

// Évènement gérant les pressions clavier sur toute la fenêtre.
function documentOnKeyPress(event) {
    // Si le document en focus n'est pas l'input-message (zone d'écriture):
    if (document.activeElement !== document.getElementById("input-message")) {
        // Si la touche est Z ou flèche du haut.
        if (event.keyCode == 90 || event.keyCode ==  38) {
            // Envoi au serveur un message pour dire au robot d'aller en avant.
            sendMessage("movf");
        }
        // Si la touche est S ou flèche du bas.
        else if (event.keyCode == 83 || event.keyCode == 40) {
            // Envoi au serveur un message pour dire au robot d'aller en avant.
            sendMessage("movb");
        }
        // Si la touche est Q ou flèche de gauche.
        else if (event.keyCode ==  81 || event.keyCode == 37) {
            // Envoi au serveur un message pour dire au robot d'aller en avant.
            sendMessage("movl");
        } 
        // Si la touche est D ou flèche de droite.
        else if (event.keyCode == 68 || event.keyCode == 39) {
            // Envoi au serveur un message pour dire au robot d'aller en avant.
            sendMessage("movr");
        }
    }
}

// Ajoute un évènement pour récupérer les pressions clavier sur toute la fenêtre (à l'aide de la fonction précédente).
window.addEventListener("keydown", documentOnKeyPress, false);
// Tente de connecter le client à l'adrese suivante à l'aide du protocole WebSocket.
connect("192.168.1.17");
