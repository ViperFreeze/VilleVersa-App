// Le seul JavaScript de l'appli : les onglets et l'affichage des graphiques.
// Sans JavaScript, tous les thèmes restent affichés les uns sous les autres.

function initialiserOnglets() {
  const onglets = document.querySelectorAll("[data-onglet]");
  if (!onglets.length) return;
  const panneaux = document.querySelectorAll(".panneau");
  document.body.classList.add("avec-onglets");

  function afficher(id) {
    onglets.forEach((o) => o.setAttribute("aria-selected", o.dataset.onglet === id));
    panneaux.forEach((p) => { p.hidden = p.id !== id; });
    // Un graphique tracé dans un onglet caché a une largeur nulle : on le redimensionne.
    document.querySelectorAll(`#${id} .graphique`).forEach((g) => {
      if (window.Plotly && g.data) Plotly.Plots.resize(g);
    });
  }

  onglets.forEach((o) => o.addEventListener("click", (e) => {
    e.preventDefault();
    afficher(o.dataset.onglet);
    history.replaceState(null, "", `#${o.dataset.onglet}`);
  }));

  const demande = location.hash.slice(1);
  const existe = [...onglets].some((o) => o.dataset.onglet === demande);
  afficher(existe ? demande : onglets[0].dataset.onglet);
}

function tracerGraphiques() {
  if (!window.Plotly) return;
  document.querySelectorAll("[data-figure]").forEach((div) => {
    const figure = JSON.parse(document.getElementById(div.dataset.figure).textContent);
    Plotly.newPlot(div, figure.data, figure.layout, { responsive: true, displayModeBar: false });
  });
}

document.addEventListener("DOMContentLoaded", initialiserOnglets);
window.addEventListener("load", tracerGraphiques); // après le chargement de Plotly
