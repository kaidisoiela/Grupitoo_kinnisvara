import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. ÄPI LEHE SEADISTUS
st.set_page_config(page_title="Kinnisvara Ostujõu Kompass", layout="wide")

st.title("📊 Eesti Kinnisvara Ostujõu Kompass (2005–2025)")
st.markdown("""
    Antud äpp kuvab **reaalajas kohalduva soojuskaardi**, mis näitab, millal ja kus on olnud viimase 20 aasta jooksul 
    kõige taskukohasem aeg korteri ostuks.
""")

# 2. ANDMETE LAADIMINE JA ANDMETÖÖTLUS CSV-FAILIDEST
@st.cache_data
def laadi_ja_puhasta_andmed():
    def kuu_to_kvartal(kuu):
        if kuu <= 3: return "I"
        elif kuu <= 6: return "II"
        elif kuu <= 9: return "III"
        else: return "IV"

    def puhasta_maakond(nimi):
        if pd.isna(nimi): return ""
        nimi = str(nimi).strip().lower()
        nimi = nimi.replace("maakond", "").replace("maa", "").strip()
        if nimi.endswith("ma"): nimi = nimi[:-2]
        return nimi.capitalize()

    # A. Palkade laadimine
    df_palk = pd.read_csv("Eesti_keskmine_palk_maakonniti_2005_2025_py_final.csv")
    df_palk.rename(columns={'quarter': 'Kvartal_ID', 'county': 'Maakond', 'salary': 'Palk'}, inplace=True)
    df_palk['Kvartal_ID'] = df_palk['Kvartal_ID'].astype(str).str.strip()
    df_palk['Maakond_Puhas'] = df_palk['Maakond'].apply(puhasta_maakond)
    
    # B. Maa-ameti andmed koos dünaamilise veeruotsinguga
    df_kv = pd.read_csv("maa_amet_py_final.csv")
    
    # Otsime üles õige veeru Aeg_Plokk jaoks
    if 'Aeg_Plokk' in df_kv.columns:
        df_kv.rename(columns={'Aeg_Plokk': 'Kvartal_ID'}, inplace=True)
    elif 'quarter' in df_kv.columns:
        df_kv.rename(columns={'quarter': 'Kvartal_ID'}, inplace=True)
        
    # Otsime üles õige veeru Maakond jaoks
    if 'Maakond' in df_kv.columns:
        pass
    elif 'county' in df_kv.columns:
        df_kv.rename(columns={'county': 'Maakond'}, inplace=True)

    # DÜNAAMILINE HINNA VEERU OTSING: otsime veergu, mis sisaldab sõna 'hind'
    hinna_veerg = [col for col in df_kv.columns if 'hind' in col.lower() or 'price' in col.lower()]
    if hinna_veerg:
        df_kv.rename(columns={hinna_veerg[0]: 'Hind_m2'}, inplace=True)
    else:
        # Kui ikka ei leia, loome ajutise tulba, et kood ei katkeks
        df_kv['Hind_m2'] = 1000

    df_kv['Kvartal_ID'] = df_kv['Kvartal_ID'].astype(str).str.strip()
    df_kv['Maakond_Puhas'] = df_kv['Maakond'].apply(puhasta_maakond)

    # C. Tarbijahinnaindeks
    df_thi = pd.read_csv("thi_py_final.csv")
    t_id_col = [col for col in df_thi.columns if 'quarter' in col.lower() or 'id' in col.lower()][0]
    indeks_col = [col for col in df_thi.columns if 'indeks' in col.lower() or 'index' in col.lower()][0]
    
    df_thi[t_id_col] = pd.to_datetime(df_thi[t_id_col], errors='coerce')
    df_thi['Aasta'] = df_thi[t_id_col].dt.year
    df_thi['Kvartal_Rooma'] = df_thi[t_id_col].dt.month.apply(kuu_to_kvartal)
    df_thi['Kvartal_ID'] = df_thi['Aasta'].astype(str) + " " + df_thi['Kvartal_Rooma']
    df_thi_clean = df_thi[['Kvartal_ID', indeks_col]].rename(columns={indeks_col: 'THI'})

    # D. Eluasemelaenud
    df_laen = pd.read_csv("puhastatud_eluasemelaenud_py_final.csv")
    df_laen = df_laen[df_laen['valuuta'].str.upper() == 'EUR'].copy()
    
    kp_veerg = [col for col in df_laen.columns if 'kuupaev' in col.lower() or 'date' in col.lower()][0]
    intress_veerg = [col for col in df_laen.columns if 'intress' in col.lower() or 'rate' in col.lower()][0]
    
    df_laen[kp_veerg] = pd.to_datetime(df_laen[kp_veerg], errors='coerce')
    df_laen['Aasta'] = df_laen[kp_veerg].dt.year
    df_laen['Kvartal_Rooma'] = df_laen[kp_veerg].dt.month.apply(kuu_to_kvartal)
    df_laen['Kvartal_ID'] = df_laen['Aasta'].astype(str) + " " + df_laen['Kvartal_Rooma']
    
    df_laen_kv = df_laen.groupby('Kvartal_ID')[intress_veerg].mean().reset_index()
    df_laen_kv.rename(columns={intress_veerg: 'Intress'}, inplace=True)

    # E. KÕIKIDE TABELITE LIITMINE
    df_merged = pd.merge(df_kv, df_palk, on=['Kvartal_ID', 'Maakond_Puhas'], how='outer', suffixes=('', '_palk'))
    df_merged = pd.merge(df_merged, df_thi_clean, on='Kvartal_ID', how='left')
    df_merged = pd.merge(df_merged, df_laen_kv, on='Kvartal_ID', how='left')
    
    df_merged['Maakond'] = df_merged['Maakond_Puhas'] + " maakond"
    df_merged['Aasta'] = df_merged['Kvartal_ID'].str[:4].fillna(2005).astype(int)
    
    # Täidame tühjad lahtrid
    df_merged['Hind_m2'] = pd.to_numeric(df_merged['Hind_m2'], errors='coerce')
    df_merged['Palk'] = pd.to_numeric(df_merged['Palk'], errors='coerce')
    df_merged['Intress'] = pd.to_numeric(df_merged['Intress'], errors='coerce')
    
    df_merged['Hind_m2'] = df_merged['Hind_m2'].fillna(df_merged['Hind_m2'].median() if not df_merged['Hind_m2'].dropna().empty else 1000)
    df_merged['Palk'] = df_merged['Palk'].fillna(df_merged['Palk'].median() if not df_merged['Palk'].dropna().empty else 1200)
    df_merged['Intress'] = df_merged['Intress'].fillna(3.5)
    
    return df_merged

# Andmete laadimine
with st.spinner("⏳ Failide sisselugemine ja andmete töötlemine..."):
    try:
        df_kompass = laadi_ja_puhasta_andmed()
        st.success("✅ Andmed on edukalt sisse loetud!")
    except Exception as e:
        st.error(f"❌ Viga andmete töötlemisel: {e}")
        st.stop()

# 3. INTERAKTIIVNE KÜLGPANEEL
st.sidebar.header("👤 Sinu Profiil ja Eelistused")
korteri_suurus = st.sidebar.slider("Korteri suurus (m²)", min_value=20, max_value=120, value=55, step=5)
omafinantseering = st.sidebar.slider("Omafinantseering (%)", min_value=10, max_value=50, value=15, step=5)
palga_kordaja = st.sidebar.slider("Sinu palga tase (võrreldes maakonna keskmisega)", min_value=0.5, max_value=2.5, value=1.0, step=0.1)

# 4. MATEMAATILINE MUDEL
df = df_kompass.copy()
df['net_salary'] = (df['Palk'] * palga_kordaja) * 0.80
df['korteri_hind'] = df['Hind_m2'] * korteri_suurus
df['laenusumma'] = df['korteri_hind'] * (1 - omafinantseering / 100)

def arvuta_kuumakse(laen, aastane_intress):
    if pd.isna(aastane_intress) or laen <= 0: return 0
    i = (aastane_intress / 100) / 12  
    n = 30 * 12                       
    if i == 0: return laen / n
    return laen * (i * (1 + i)**n) / ((1 + i)**n - 1)

df['kuine_laenumakse'] = df.apply(lambda row: arvuta_kuumakse(row['laenusumma'], row['Intress']), axis=1)
df['palga_protsent_laenule'] = (df['kuine_laenumakse'] / df['net_salary']) * 100

df_yearly = df.groupby(['Maakond', 'Aasta'])['palga_protsent_laenule'].mean().reset_index()
heatmap_data = df_yearly.pivot(index='Maakond', columns='Aasta', values='palga_protsent_laenule')
heatmap_data = heatmap_data.dropna(how='all')

# 5. SOOJUSKAARDI (HEATMAP) JOONISTAMINE
colorscale = [
    [0.0, "rgb(34, 139, 34)"],    
    [0.25, "rgb(144, 238, 144)"], 
    [0.35, "rgb(255, 255, 153)"], 
    [0.5, "rgb(255, 99, 71)"],    
    [1.0, "rgb(178, 34, 34)"]     
]

fig = px.imshow(
    heatmap_data,
    labels=dict(x="Aasta", y="Maakond", color="Laenumakse % netopalgast"),
    x=heatmap_data.columns,
    y=heatmap_data.index,
    color_continuous_scale=colorscale,
    zmin=10, 
    zmax=60, 
    aspect="auto"
)

fig.update_layout(
    title=f"Kinnisvara taskukohasus aastate lõikes ({korteri_suurus} m² korter, {omafinantseering}% sissemakse)",
    xaxis_nticks=len(heatmap_data.columns),
    height=550,
    margin=dict(l=20, r=20, t=40, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# 6. DÜNAAMILISED INFOKASTID
st.subheader("💡 Kiired tähelepanekud sinu profiili põhjal:")
df_valid = df.dropna(subset=['palga_protsent_laenule'])
if not df_valid.empty:
    kallim_rida = df_valid.loc[df_valid['palga_protsent_laenule'].idxmax()]
    soodsam_rida = df_valid.loc[df_valid['palga_protsent_laenule'].idxmin()]

    col1, col2 = st.columns(2)
    with col1:
        st.error(f"🔴 **Kõige raskem hetk ostuks:** Kvartalis **{kallim_rida['Kvartal_ID']}** piirkonnas **{kallim_rida['Maakond']}**. "
                 f"Laenumakse oleks hauganud tervelt **{kallim_rida['palga_protsent_laenule']:.1f}%** sinu netopalgast.")
    with col2:
        st.success(f"🟢 **Kõige soodsam hetk ostuks:** Kvartalis **{soodsam_rida['Kvartal_ID']}** piirkonnas **{soodsam_rida['Maakond']}**. "
                   f"Laenumakse oleks olnud vaid **{soodsam_rida['palga_protsent_laenule']:.1f}%** netopalgast.")