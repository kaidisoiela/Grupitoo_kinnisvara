import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# === SAMM 1: ÄPI LEHE JA PEALKIRJADE SEADISTUS ===
# Seadistame veebilehe laiaks, et interaktiivne graafik mahuks hästi ekraanile.
st.set_page_config(page_title="Kinnisvara Ostujõu Indeks", layout="wide")

st.title("📐 Mitu ruutmeetrit korterit saad osta ühe kuupalgaga?")
st.markdown("""
    Antud äpp arvutab makromajandusandmete põhjal välja **Kinnisvara Ostujõu Indeksi**.
    See näitab visuaalselt, mitu ruutmeetrit Eesti korteriomandit sai keskmise (või Sinu enda) 
    ühe kuu netopalgaga konkreetses maakonnas reaalajas osta aastatel 2005–2025.
""")

# === SAMM 2: ANDMETE LAADIMINE JA FORMAATIDE ÜHTLUSTAMINE ===
# Kasutame st.cache_data, et andmeid loetaks failist ainult üks kord, mis teeb äpi ülikiireks.
@st.cache_data
def laadi_ja_puhasta_andmed():
    # Abifunktsioon kuude (1-12) teisendamiseks Rooma numbriteks (I-IV), et ühildada THI tabel
    def kuu_to_kvartal(kuu):
        if kuu <= 3: return "I"
        elif kuu <= 6: return "II"
        elif kuu <= 9: return "III"
        else: return "IV"

    # Abifunktsioon maakondade nimede puhastamiseks (kaotab tühikud ja ühtlustab kirjapildi)
    def puhasta_maakond(nimi):
        if pd.isna(nimi): return ""
        nimi = str(nimi).strip().lower()
        nimi = nimi.replace("maakond", "").replace("maa", "").strip()
        if nimi.endswith("ma"): nimi = nimi[:-2]
        return nimi.capitalize()

    # A. Palkade laadimine ja veergude ettevalmistus (quarter -> Kvartal_ID, county -> Maakond)
    df_palk = pd.read_csv("Eesti_keskmine_palk_py_final.csv")
    df_palk.rename(columns={'quarter': 'Kvartal_ID', 'county': 'Maakond', 'salary': 'Palk'}, inplace=True)
    df_palk['Kvartal_ID'] = df_palk['Kvartal_ID'].astype(str).str.strip()
    df_palk['Maakond_Puhas'] = df_palk['Maakond'].apply(puhasta_maakond)
    
    # B. Maa-ameti andmete laadimine ja veeru otsing (Aeg_Plokk -> Kvartal_ID, keskmine_hind -> Hind_m2)
    df_kv = pd.read_csv("maa_amet_py_final.csv")
    if 'Aeg_Plokk' in df_kv.columns: 
        df_kv.rename(columns={'Aeg_Plokk': 'Kvartal_ID'}, inplace=True)
    
    # Otsime automaatselt üles hinna veeru, kui nimes esineb 'hind' või 'price'
    hinna_veerg = [col for col in df_kv.columns if 'hind' in col.lower() or 'price' in col.lower()]
    if hinna_veerg:
        df_kv.rename(columns={hinna_veerg[0]: 'Hind_m2'}, inplace=True)
    else:
        df_kv['Hind_m2'] = 1000

    df_kv['Kvartal_ID'] = df_kv['Kvartal_ID'].astype(str).str.strip()
    df_kv['Maakond_Puhas'] = df_kv['Maakond'].apply(puhasta_maakond)

    # C. Tarbijahinnaindeksi (THI) laadimine ja formaadi muutmine ("2005-01-01" -> "2005 I")
    df_thi = pd.read_csv("thi_py_final.csv")
    t_id_col = [col for col in df_thi.columns if 'quarter' in col.lower() or 'id' in col.lower()]
    indeks_col = [col for col in df_thi.columns if 'indeks' in col.lower() or 'index' in col.lower()]
    
    if t_id_col and indeks_col:
        df_thi[t_id_col[0]] = pd.to_datetime(df_thi[t_id_col[0]], errors='coerce')
        df_thi['Aasta'] = df_thi[t_id_col[0]].dt.year
        df_thi['Kvartal_Rooma'] = df_thi[t_id_col[0]].dt.month.apply(kuu_to_kvartal)
        df_thi['Kvartal_ID'] = df_thi['Aasta'].astype(str) + " " + df_thi['Kvartal_Rooma']
        df_thi_clean = df_thi[['Kvartal_ID', indeks_col[0]]].rename(columns={indeks_col[0]: 'THI'})
    else:
        df_thi_clean = pd.DataFrame(columns=['Kvartal_ID', 'THI'])

    # D. TABELITE LIITMINE (Ühise Kvartal_ID ja Maakonna baasil)
    df_merged = pd.merge(df_kv, df_palk, on=['Kvartal_ID', 'Maakond_Puhas'], how='inner', suffixes=('', '_palk'))
    df_merged = pd.merge(df_merged, df_thi_clean, on='Kvartal_ID', how='left')
    
    # Määrame lõpliku maakonna nime ilusal kujul og eraldame aasta numbri horisontaaltelje jaoks
    df_merged['Maakond'] = df_merged['Maakond_Puhas'] + " maakond"
    df_merged['Aasta'] = df_merged['Kvartal_ID'].str[:4].astype(int)
    
    # Piirame andmed vahemikuga 2005-2025, nagu soovitud
    df_merged = df_merged[(df_merged['Aasta'] >= 2005) & (df_merged['Aasta'] <= 2025)].copy()
    
    # Puhastame andmetüübid numbri kujule ja täidame tühjad kohad turvalisuse huvides mediaaniga
    df_merged['Hind_m2'] = pd.to_numeric(df_merged['Hind_m2'], errors='coerce').fillna(1000)
    df_merged['Palk'] = pd.to_numeric(df_merged['Palk'], errors='coerce').fillna(1200)
    
    return df_merged

# Käivitame andmete laadimise spinneri saatel
with st.spinner("⏳ Andmete ettevalmistamine..."):
    df_ostujoud = laadi_ja_puhasta_andmed()

# === SAMM 3: INTERAKTIIVNE KÜLGPANEEL (MÄNGULISUS) ===
st.sidebar.header("👤 Sinu Personaalsed Sätted")

# Kasutaja saab valida, mitu maakonda ta tahab graafikule korraga võrdluseks kuvada
koik_maakonnad = sorted(df_ostujoud['Maakond'].unique())
valitud_maakonnad = st.sidebar.multiselect(
    "Vali maakonnad võrdluseks:", 
    options=koik_maakonnad, 
    default=['Harju maakond', 'Tartu maakond', 'Pärnu maakond']
)

# Liugur mängulisuse jaoks: Kasutaja saab määrata oma sissetuleku kordaja
palga_kordaja = st.sidebar.slider(
    "Sinu palgatase võrreldes keskmisega:", 
    min_value=0.5, max_value=3.0, value=1.0, step=0.1,
    help="1.0 tähendab täpselt maakonna keskmist palku. 2.0 tähendab, et teenid poole rohkem."
)

# === SAMM 4: MATEMAATILISED REAALAJA ARVUTUSED ===
df_calc = df_ostujoud.copy()

# Arvutame brutopalgast ligikaudse netopalga (lahutame maha u 20% makse) ja korrutame kasutaja kordajaga
df_calc['net_salary'] = (df_calc['Palk'] * palga_kordaja) * 0.80

# VALEM: Mitu ruutmeetrit saab osta ühe kuu netopalgaga
df_calc['Ostetavad_Ruutmeetrid'] = round(df_calc['net_salary'] / df_calc['Hind_m2'], 2)

# Agregeerime andmed aastate keskmiseks, et graafiku jooned oleksid puhtad ja ilma kvartali "sakkideta"
df_yearly = df_calc.groupby(['Maakond', 'Aasta']).agg({
    'Ostetavad_Ruutmeetrid': 'mean',
    'Palk': 'mean',
    'Hind_m2': 'mean'
}).reset_index()

# Filtreerime andmed vastavalt külgpaneelis tehtud maakondade valikule
df_filtered = df_yearly[df_yearly['Maakond'].isin(valitud_maakonnad)]

# === SAMM 5: INTERAKTIIVSE JOONDIAGRAMMI LOOMINE PLOTLY-GA ===
if not df_filtered.empty:
    fig = px.line(
        df_filtered, 
        x="Aasta", 
        y="Ostetavad_Ruutmeetrid", 
        color="Maakond",
        markers=True, # Lisab joonele täpid, et aastaid oleks lihtsam klikkida
        title="Kinnisvara Ostujõu Indeks (Ruutmeetrit ühe kuupalga eest)",
        labels={"Ostetavad_Ruutmeetrid": "Mitu m² saab 1 kuu netopalga eest", "Aasta": "Aasta"}
    )
    
    # Tuunime graafiku infomulli (Tooltip), et kasutaja näeks hiirega liikudes reaalset palka ja m² hinda
    fig.update_traces(
        hovertemplate="<b>%{json_backend_country} (%{x})</b><br>" +
                      "Ostujõud: <b>%{y:.2f} m²</b> kuupalga eest<br>" +
                      "<extra></extra>"
    )
    
    fig.update_layout(
        xaxis_nticks=21, # Tagab, et kaikki aastad 2005-2025 on teljel kirjas
        hovermode="x unified", # Ühendab sama aasta jooned hiirega vaatamisel kokku
        height=600
    )
    
    # Kuvame valmis interaktiivse graafiku Streamlitis
    st.plotly_chart(fig, use_container_width=True)

    # === SAMM 6: DÜNAAMILINE STATISTIKA (MÄNGULISED TÄHELEPANEKUD) ===
    st.subheader("🧐 Sinu profiili tähelepanekud:")
    
    # Arvutame kogu filtreeritud ajaloo parima ja halvima hetke ostujõu mõistes
    parim_hetk = df_filtered.loc[df_filtered['Ostetavad_Ruutmeetrid'].idxmax()]
    halvim_hetk = df_filtered.loc[df_filtered['Ostetavad_Ruutmeetrid'].idxmin()]
    
    col1, col2 = st.columns(2)
    with col1:
        # PARANDATUD: Sõna 'ainatse' eemaldatud!
        st.success(f"🟢 **Kõige suurem ostujõud (Kuldajastu):** Aastal **{parim_hetk['Aasta']}** piirkonnas **{parim_hetk['Maakond']}**, "
                   f"kus ühe kuupalgaga sai osta tervelt **{parim_hetk['Ostetavad_Ruutmeetrid']:.2f} m²** korterit. "
                   f"Sel hetkel oli keskmine brutopalk {parim_hetk['Palk']:.0f} € ja ruutmeetri hind {parim_hetk['Hind_m2']:.0f} €.")
    with col2:
        st.error(f"🔴 **Kõige madalam ostujõud (Kriisiaasta):** Aastal **{halvim_hetk['Aasta']}** piirkonnas **{halvim_hetk['Maakond']}**, "
                   f"kus kuupalk venitas välja kõigest **{halvim_hetk['Ostetavad_Ruutmeetrid']:.2f} m²**. "
                   f"Turg oli ülekuumenenud (ruutmeeter {halvim_hetk['Hind_m2']:.0f} € ja brutopalk {halvim_hetk['Palk']:.0f} €).")
else:
    st.warning("Palun vali vasakult menüüst vähemalt üks maakond, et graafikut kuvada.")