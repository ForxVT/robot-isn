// ---------------------------------------------------------------- //
//                                                                  //
//  - index.js                                                      //
//                                                                  //
//  Script JavaScript du site web.                                  //
//                                                                  //
// ---------------------------------------------------------------- //

// Évènement gérant les pressions clavier sur toute la fenêtre.
function documentOnKeyPress(event) {
    // Si la touche est Q ou flèche de gauche.
    if (event.keyCode ==  81 || event.keyCode == 37) {
        // On navigue vers la page précédente du dossier-projet.
        if (document.getElementById("footer-previous") != null) {
            window.location.href = document.getElementById("footer-previous").href;
        }
    } 
    // Si la touche est D ou flèche de droite.
    else if (event.keyCode == 68 || event.keyCode == 39) {
        // On navigue vers la page suivante du dossier-projet.
        if (document.getElementById("footer-next") != null) {
            window.location.href = document.getElementById("footer-next").href;
        }
    }
}

// Ajoute un évènement pour récupérer les pressions clavier sur toute la fenêtre (à l'aide de la fonction précédente).
window.addEventListener("keydown", documentOnKeyPress, false);
