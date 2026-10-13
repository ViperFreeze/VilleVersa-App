"""Graphiques Plotly construits en Python, envoyés au navigateur en JSON.

Une couleur par ville, la même dans tous les graphiques : la ville A en bleu,
la ville B en orange (paire lisible par les daltoniens).
"""
import plotly.graph_objects as go

COULEURS_VILLES = ("#2a78d6", "#eb6834")
MOIS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin",
        "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]


def _mise_en_page(fig: go.Figure, titre_axe_y: str) -> str:
    fig.update_layout(
        margin=dict(l=48, r=16, t=8, b=40),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, sans-serif", size=13, color="#52514e"),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12, x=0),
        yaxis=dict(title=titre_axe_y, gridcolor="#e6e5e1", zeroline=False),
        xaxis=dict(showgrid=False),
    )
    return fig.to_json()


def previsions(fiches) -> str | None:
    """Températures maximales (trait plein) et minimales (pointillé) des prochains jours."""
    fig = go.Figure()
    for fiche, couleur in zip(fiches, COULEURS_VILLES):
        prev = fiche.previsions
        if not prev:
            continue
        nom = fiche.ville.nom
        fig.add_scatter(x=prev["dates"], y=prev["tmax"], name=f"{nom}, max",
                        mode="lines+markers", line=dict(color=couleur, width=2),
                        marker=dict(size=8))
        fig.add_scatter(x=prev["dates"], y=prev["tmin"], name=f"{nom}, min",
                        mode="lines+markers", line=dict(color=couleur, width=2, dash="dot"),
                        marker=dict(size=8, symbol="circle-open"))
    if not fig.data:
        return None
    fig.update_xaxes(tickformat="%d/%m", dtick=86_400_000)  # un repère par jour
    return _mise_en_page(fig, "°C")


def climat(fiches) -> str | None:
    """Température moyenne de chaque mois, une courbe par ville."""
    fig = go.Figure()
    for fiche, couleur in zip(fiches, COULEURS_VILLES):
        if fiche.climat is None:
            continue
        fig.add_scatter(x=MOIS, y=fiche.climat["temp_moy"].round(1).tolist(),
                        name=fiche.ville.nom, mode="lines+markers",
                        line=dict(color=couleur, width=2), marker=dict(size=8))
    if not fig.data:
        return None
    return _mise_en_page(fig, "°C")
