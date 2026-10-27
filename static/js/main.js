// JavaScript ligero de la tienda. Sin dependencias de CDN.
// HTMX y Alpine.js se cargan desde static/vendor/ (ver base.html).

// Muestra un mensaje de "agregado" breve (se usará en la Fase 1 con el carrito).
window.CiudadBonita = {
  avisar: function (texto) {
    var cont = document.createElement("div");
    cont.className = "mensaje mensaje--exito";
    cont.setAttribute("role", "status");
    cont.textContent = texto;
    cont.style.position = "fixed";
    cont.style.bottom = "80px";
    cont.style.right = "16px";
    cont.style.zIndex = "70";
    cont.style.boxShadow = "0 6px 24px rgba(91,42,134,.14)";
    document.body.appendChild(cont);
    setTimeout(function () { cont.remove(); }, 2500);
  },
};
