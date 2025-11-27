import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Vakantiewoning Pro Calculator", layout="wide")
st.title("Vakantiewoning Rendementscalculator – De enige die écht klopt")

# ─── DARK MODE ───
def set_dark_mode():
    st.markdown("""
    <style>
        .css-1d391kg {background-color: #0e1117;}
        .css-1v0mbdj {color: white;}
        h1, h2, h3, .stMetric {color: white !important;}
        .stPlotlyChart {background-color: #1e1e1e;}
    </style>
    """, unsafe_allow_html=True)

if st.sidebar.checkbox("Dark Mode", value=True):
    set_dark_mode()

# ─── SIDEBAR: MODE KEUZE ───
st.sidebar.header("Financieringsmode")
mode = st.sidebar.radio("Kies je scenario", ["Met financiering", "Zonder financiering (all-cash)"])

# ─── INPUTS ───
col1, col2 = st.columns(2)

with col1:
    st.subheader("Object & Aankoop")
    koopsom = st.number_input("Koopsom", value=350000, step=5000)
    kosten_koper = st.number_input("Kosten koper + extra's (notaris, taxatie, etc.)", value=15000)
    marktwaarde = st.number_input("Getaxeerde waarde verhuurde staat", value=320000)
    
    st.subheader("Exploitatie")
    bruto_huur_maand = st.number_input("Bruto huur per maand", value=1800)
    bezetting_pct = st.slider("Bezetting %", 50, 95, 78)
    vve_jaar = st.number_input("VVE/parkkosten per jaar", value=2800)
    beheer_pct = st.number_input("Beheer % van omzet", value=20.0) / 100
    onderhoud_pct = st.number_input("Onderhoud % van koopsom", value=1.5) / 100
    energie_maand = st.number_input("Energie + internet per maand", value=160)
    indexatie = st.number_input("Indexatie huur & kosten % per jaar", value=2.5) / 100

with col2:
    if mode == "Met financiering":
        st.subheader("Hypotheek (4 delen)")
        ltv = st.slider("LTV %", 50, 90, 80) / 100
        
        d1_pct = st.slider("Deel 1 – Aflossingsvrij %", 0, 100, 40)
        d1_rente = st.number_input("Rente deel 1 %", value=4.2, step=0.1) / 100
        
        d2_pct = st.slider("Deel 2 – Lineair %", 0, 100, 20)
        d2_rente = st.number_input("Rente deel 2 %", value=4.3, step=0.1) / 100
        d2_jaren = st.number_input("Lineair termijn (jaren)", value=20)
        
        d3_pct = st.slider("Deel 3 – Annuïteit %", 0, 100, 40)
        d3_rente = st.number_input("Rente deel 3 %", value=4.5, step=0.1) / 100
        d3_jaren = st.number_input("Annuïteit termijn (jaren)", value=30)
        
        # Deel 4 optioneel
        d4_pct = st.slider("Deel 4 – Extra annuïteit %", 0, 100, 0)
        d4_rente = st.number_input("Rente deel 4 %", value=4.8, step=0.1) / 100 if d4_pct > 0 else 0
        d4_jaren = st.number_input("Deel 4 termijn (jaren)", value=30) if d4_pct > 0 else 30

# ─── BEREKENING ───
if st.button("Bereken alles", type="primary"):
    totale_investering = koopsom + kosten_koper
    
    if mode == "Zonder financiering (all-cash)":
        hypotheek = 0
        eigen_geld = totale_investering
        rente_jaarlijks = aflossing_jaarlijks = [0] * 30
    else:
        hypotheek = marktwaarde * ltv
        eigen_geld = totale_investering - hypotheek
        
        # Deelbedragen
        d1 = hypotheek * d1_pct / 100
        d2 = hypotheek * d2_pct / 100
        d3 = hypotheek * d3_pct / 100
        d4 = hypotheek * d4_pct / 100

        rente_jaarlijks = []
        aflossing_jaarlijks = []
        restschuld = [hypotheek]

        for jaar in range(30):
            rente = 0
            aflos = 0

            # Deel 1: Aflossingsvrij
            rente += d1 * d1_rente

            # Deel 2: Lineair
            if d2 > 0 and jaar < d2_jaren:
                aflos_d2 = d2 / d2_jaren
                rente += (d2 - aflos_d2 * jaar - aflos_d2/2) * d2_rente
                aflos += aflos_d2

            # Deel 3 & 4: Annuïteit (handmatig berekend)
            for bedrag, rente_pct, termijn in [(d3, d3_rente, d3_jaren), (d4, d4_rente, d4_jaren)]:
                if bedrag > 0:
                    r = rente_pct / 12
                    n = termijn * 12
                    if r == 0:
                        maandbedrag = bedrag / n
                    else:
                        maandbedrag = bedrag * r * (1 + r)**n / ((1 + r)**n - 1)
                    jaarbedrag = maandbedrag * 12
                    # Benadering: eerste jaar bijna alleen rente
                    rente_jaar = bedrag * rente_pct * (1 - jaar / termijn * 0.8)
                    aflos_jaar = jaarbedrag - rente_jaar
                    rente += rente_jaar
                    aflos += aflos_jaar

            rente_jaarlijks.append(rente)
            aflossing_jaarlijks.append(aflos)
            restschuld.append(max(0, restschuld[-1] - aflos))

        restschuld = restschuld[:-1]

    # Jaarlijkse cashflow
    rows = []
    cum_cf = 0
    for jaar in range(1, 31):
        factor = (1 + indexatie) ** (jaar - 1)
        huur = bruto_huur_maand * 12 * factor * (bezetting_pct / 100)
        kosten = (vve_jaar + energie_maand * 12 + koopsom * onderhoud_pct + huur * beheer_pct) * factor
        hypotheek_kosten = rente_jaarlijks[jaar-1] + aflossing_jaarlijks[jaar-1] if mode == "Met financiering" else 0
        cf = huur - kosten - hypotheek_kosten
        cum_cf += cf

        rows.append({
            "Jaar": jaar,
            "Huur": round(huur),
            "Kosten": round(kosten),
            "Hypotheek": round(hypotheek_kosten),
            "Netto Cashflow": round(cf),
            "Cumulatief": round(cum_cf),
            "Restschuld": round(restschuld[jaar-1]) if mode == "Met financiering" else 0
        })

    df = pd.DataFrame(rows)

    # ─── RESULTATEN ───
    st.success("Berekend! Hieronder alles wat je nodig hebt")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BAR", f"{(bruto_huur_maand*12*bezetting_pct/100)/koopsom:.1%}")
    c2.metric("NAR jaar 1", f"{df.iloc[0]['Netto Cashflow']/totale_investering:.1%}")
    c3.metric("ROE jaar 1", f"{df.iloc[0]['Netto Cashflow']/eigen_geld:.1%}")
    c4.metric("Eigen inbreng", f"€{eigen_geld:,.0f}")

    tab1, tab2, tab3 = st.tabs(["30-Jaar Overzicht", "Grafieken", "Download"])

    with tab1:
        st.dataframe(df.style.format("€{:,}"), use_container_width=True)

    with tab2:
        fig1 = px.line(df, x="Jaar", y="Cumulatief", title="Cumulatieve Cashflow")
        fig1.update_layout(template="plotly_dark" if st.sidebar.checkbox("Dark Mode", value=True) else "plotly")
        st.plotly_chart(fig1, use_container_width=True)

        if mode == "Met financiering":
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df["Jaar"], y=df["Restschuld"], name="Restschuld", fill='tozeroy'))
            fig2.update_layout(title="Hypotheek Aflossing")
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button(
            "Download als Excel",
            output.getvalue(),
            "vakantiewoning_resultaat.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.balloons()
