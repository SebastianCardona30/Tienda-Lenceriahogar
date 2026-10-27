// JavaScript ligero de la tienda. Sin dependencias de CDN.
// HTMX y Alpine.js se cargan desde static/vendor/ (ver base.html).

// Componente Alpine: cuenta regresiva (ofertas de la semana / venta relámpago)
document.addEventListener("alpine:init", function () {
  if (typeof Alpine === "undefined") return;
  Alpine.data("cuentaRegresiva", function (fechaISO) {
    return {
      reloj: "--:--:--",
      init: function () {
        var destino = new Date(fechaISO).getTime();
        var self = this;
        var actualizar = function () {
          var diff = destino - Date.now();
          if (diff <= 0) {
            self.reloj = "¡Terminaron!";
            clearInterval(self._timer);
            return;
          }
          var dias = Math.floor(diff / 86400000);
          var h = String(Math.floor((diff % 86400000) / 3600000)).padStart(2, "0");
          var m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, "0");
          var s = String(Math.floor((diff % 60000) / 1000)).padStart(2, "0");
          self.reloj = (dias > 0 ? dias + " días " : "") + h + ":" + m + ":" + s;
        };
        actualizar();
        self._timer = setInterval(actualizar, 1000);
      },
    };
  });
});

// Muestra un mensaje breve (usado por el carrito y formularios).
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
