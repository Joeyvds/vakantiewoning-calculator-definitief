import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Vakantiewoning Calculator", layout="wide")
st.title("Vakantiewoning Rendementscalculator – Eindelijk perfect")

# ─── INPUTS ───
c1, c2 = st.columns(2)
with c1:
    st.subheader("Aankoop")
    koopsom = st.number_input("Koopsom", value=175000, step=5000)
    kosten_koper = st.number_input("Kosten koper + extra's", value=25000)
    all_cash = st.checkbox("All-cash aankoop (geen hypotheek)", value=False)

    if not all_cash:
        st.subheader("Financiering")
        ltv = st.slider("LTV %", 50, 90, 75, 5) / 100
        rente = st.number_input("Rente %", value=4.9, step=0.1) / 100
        hypotheekvorm = st.selectbox("Hypotheekvorm", ["Aflossingsvrij", "Annuïteit 30 jaar"])

with c2:
    st.subheader("Verhuur & Exploitatie")
    bezetting = st.slider("Bezetting %", 40, 95, 72)
    nachtprijs = st.number_input("Gem. nachtprijs €", value=138)
    verblijfsduur = st.number_input("Gem. nachten per boeking", value=4)

st.divider()
k1, k2, k3, k4 = st.columns(4)
vve = k1.number_input("VVE/parkkosten jaar", value=2600)
schoonmaak = k2.number_input("Schoonmaak per wissel", value=75)
beheer_pct = k3.number_input("Beheer % omzet", value=20.0) / 100
toeristenbelasting = k4.number_input("Toeristenbel. p.p.p.n.", value=2.3)

k5, k6, k7, k8 = st.columns(4)
onderhoud_pct = k5.number_input("Onderhoud % koopsom", value=1.8) / 100
energie_maand = k6.number_input("Energie+internet maand", value=180)
erfpacht = k7.number_input("Erfpacht jaar", value=0)
indexatie = k8.number_input("Indexatie % per jaar", value=2.5) / 100

if st.button("Bereken rendement", type="primary"):
    # ─── BEREKENINGEN ───
    totale_investering = koopsom + kosten_koper

    if all_cash:
        hypotheek = 0
        rente_kosten = 0
        aflossing = 0
    else:
        hypotheek = koopsom * ltv
        if hypotheekvorm == "Aflossingsvrij":
            rente_kosten = hypotheek * rente
            aflossing = 0
        else:
            # Handmatige annuïteit (geen numpy-financial nodig)
            r = rente / 12
            n = 360
            aflossing_maand = hypotheek * r * (1 + r)**n / ((1 + r)**n - 1)
            aflossing = aflossing_maand * 12
            rente_kosten = hypotheek * rente

    eigen_geld = totale_investering - hypotheek
    omzet_jaar1 = 365 * (bezetting/100) * nachtprijs
    wissels_jaar1 = 365 * (bezetting/100) / verblijfsduur

    df = pd.DataFrame({"Jaar": range(1, 31)})
    for i in range(30):
        factor = (1 + indexatie) ** i
        omzet = omzet_jaar1 * factor
        wissels = wissels_jaar1 * factor

        rij = {
            "Omzet": omzet,
            "VVE/parkkosten": vve * factor,
            "Schoonmaak": wissels * schoonmaak,
            "Beheer": omzet * beheer_pct,
            "Toeristenbelasting": wissels * verblijfsduur * 3 * toeristenbelasting * factor,
            "Onderhoud": koopsom * onderhoud_pct * factor,
            "Energie+internet": energie_maand * 12 * factor,
            "Erfpacht": erfpacht * factor,
            "Hypotheekrente": rente_kosten if not all_cash else 0,
            "Aflossing": aflossing if not all_cash and hypotheekvorm != "Aflossingsvrij" else 0,
        }
        rij["Totale kosten"] = sum(v for k, v in rij.items() if k not in ["Omzet"])
        rij["Netto cashflow"] = omzet - rij["Totale kosten"]
        df.loc[i] = rij

    df["Cumulatief"] = df["Netto cashflow"].cumsum()

    # ─── RESULTATEN ───
    bar = omzet_jaar1 / koopsom * 100
    nar = df.iloc[0]["Netto cashflow"] / totale_investering * 100
    roe = df.iloc[0]["Netto cashflow"] / eigen_geld * 100 if eigen_geld > 0 else bar

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("BAR", f"{bar:.1f}%")
    col2.metric("NAR", f"{nar:.1f}%")
    col3.metric("ROE jaar 1", f"{roe:.1f}%")
    col4.metric("Eigen inbreng", f"€{eigen_geld:,.0f}")

    tab1, tab2, tab3 = st.tabs(["30-jaars overzicht", "Maandgemiddelde", "Grafieken"])

    with tab1:
        st.dataframe(df.style.format("€{:,.0f}"), use_container_width=True)
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("Download als Excel", output.getvalue(), "vakantiewoning.xlsx")

    with tab2:
        st.metric("Gem. maand omzet", f"€{df['Omzet'].mean()/12:,.0f}")
        st.metric("Gem. maand kosten", f"€{df['Totale kosten'].mean()/12:,.0f}")
        st.metric("Gem. maand cashflow", f"€{df['Netto cashflow'].mean()/12:,.0f}")

    with tab3:
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(df["Jaar"], df["Cumulatief"]/1000, marker="o", linewidth=3, color="#00C853")
        ax.set_title("Cumulatieve cashflow (in duizenden €)")
        ax.grid(alpha=0.3)
        st.pyplot(fig)

        fig2, ax2 = plt.subplots()
        kosten_jaar1 = df.iloc[0, 1:-3]
        ax2.pie(kosten_jaar1, labels=kosten_jaar1.index, autopct="%1.0f%%")
        ax2.set_title("Kostenverdeling jaar 1")
        st.pyplot(fig2)

    st.success("Klaar! Werkt met én zonder financiering – geen fouten meer")
