import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. ÄPI LEHE SEADISTUS
st.set_page_config(page_title="Kinnisvara Ostujõu Kompass", layout="wide")

st.title("📊 Eesti Kinnisvara Ostujõu Kompass (2005–2025)")
st.markdown("""
    Nihuta vasakul olevaid slidereid vastavalt oma profiilile. Kaardi värvimuutus näitab reaalajas, 
    millised maakonnad ja aastad muutuvad sinu eelarve jaoks **taskukohaseks (roheline)** või **kättesaamatuks (punane)**.
    Andmed põhinevad reaalsetel statistilistel näitajatel aastatest 2005–2025.
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
    df_palk = pd.read_csv("Eesti_keskmine_palk_py_final.csv")
    df_palk.rename(columns={'quarter': 'Kvartal_ID', 'county': 'Maakond', 'salary': 'Palk'}, inplace=True)
    df_palk['Kvartal_ID'] = df_palk['Kvartal_ID'].astype(str).str.strip()
    df_palk['Maakond_Puhas'] = df_palk['Maakond'].apply(puhasta_maakond)
    
    # B. Maa-ameti andmed
    df_kv = pd.read_csv("maa_amet_py_final.csv")
    if 'Aeg_Plokk' in df_kv.columns: 
        df_kv.rename(columns={'Aeg_Plokk': 'Kvartal_ID'}, inplace=True)
    
    # PARANDUS: Võtame listist esimese elemendi [0]
    hinna_veerg = [col for col in df_kv.columns if 'hind' in col.lower() or 'price' in col.lower()]
    if hinna_veerg:
        df_kv.rename(columns={hinna_veerg[0]: 'Hind_m2'}, inplace=True)
    else:
        df_kv['Hind_m2'] = 1000

    df_kv['Kvartal_ID'] = df_kv['Kvartal_ID'].astype(str).str.strip()
    df_kv['Maakond_Puhas'] = df_kv['Maakond'].apply(puhasta_maakond)

    # C. Tarbijahinnaindeks
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

    # D. Eluasemelaenud
    df_laen = pd.read_csv("puhastatud_eluasemelaenud_py_final.csv")
    df_laen = df_laen[df_laen['valuuta'].str.upper() == 'EUR'].copy()
    
    kp_veerg = [col for col in df_laen.columns if 'kuupaev' in col.lower() or 'date' in col.lower()]
    intress_veerg = [col for col in df_laen.columns if 'intress' in col.lower() or 'rate' in col.lower()]
    
    if kp_veerg and intress_veerg:
        df_laen[kp_veerg[0]] = pd.to_datetime(df_laen[kp_veerg[0]], errors='coerce')
        df_laen['Aasta'] = df_laen[kp_veerg[0]].dt.year
        df_laen['Kvartal_Rooma'] = df_laen[kp_veerg[0]].dt.month.apply(kuu_to_kvartal)
        df_laen['Kvartal_ID'] = df_laen['Aasta'].astype(str) + " " + df_laen['Kvartal_Rooma']
        
        df_laen_kv = df_laen.groupby('Kvartal_ID')[intress_veerg[0]].mean().reset_index()
        df_laen_kv.rename(columns={intress_veerg[0]: 'Intress'}, inplace=True)
    else:
        df_laen_kv = pd.DataFrame(columns=['Kvartal_ID', 'Intress'])

    # E. LIITMINE
    df_merged = pd.merge(df_kv, df_palk, on=['Kvartal_ID', 'Maakond_Puhas'], how='outer', suffixes=('', '_palk'))
    df_merged = pd.merge(df_merged, df_thi_clean, on='Kvartal_ID', how='left')
    df_merged = pd.merge(df_merged, df_laen_kv, on='Kvartal_ID', how='left')
    
    df_merged['Maakond'] = df_merged['Maakond_Puhas'] + " maakond"
    df_merged['Aasta'] = df_merged['Kvartal_ID'].str[:4].fillna(2005).astype(int)
    
    # PIIRAME ANDMED AASTATEGA 2005 KUNI 2025
    df_merged = df_merged[(df_merged['Aasta'] >= 2005) & (df_merged['Aasta'] <= 2025)].copy()
    
    df_merged['Hind_m2'] = pd.to_numeric(df_merged['Hind_m2'], errors='coerce').fillna(1000)
    df_merged['Palk'] = pd.to_numeric(df_merged['Palk'], errors='coerce').fillna(1200)
    df_merged['Intress'] = pd.to_numeric(df_merged['Intress'], errors='coerce').fillna(3.5)
    
    return df_merged

with st.spinner("⏳ Andmete laadimine..."):
    df_kompass = laadi_ja_puhasta_andmed()

# 3. INTERAKTIIVNE KÜLGPANEEL (SLIDERID)
st.sidebar.header("👤 Sinu Personaalsed Andmed")
korteri_suurus = st.sidebar.slider("Korteri suurus (m²)", min_value=20, max_value=120, value=55, step=5)
omafinantseering = st.sidebar.slider("Omafinantseering (%)", min_value=10, max_value=50, value=15, step=5)
palga_kordaja = st.sidebar.slider("Sinu palga tase (kordne keskmisest)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)

st.sidebar.subheader("🎯 Eelarve kriteerium")
max_lubatud_laenuprotsent = st.sidebar.slider("Maksimaalne % netopalgast laenumakseks", min_value=20, max_value=50, value=35, step=5)

# 4. DÜNAAMILISED ARVUTUSED
df = df_kompass.copy()
df['net_salary'] = round((df['Palk'] * palga_kordaja) * 0.80, 2)
df['korteri_hind'] = round(df['Hind_m2'] * korteri_suurus, 2)
df['laenusumma'] = round(df['korteri_hind'] * (1 - omafinantseering / 100), 2)

def arvuta_kuumakse(laen, aastane_intress):
    if pd.isna(aastane_intress) or laen <= 0: return 0
    i = (aastane_intress / 100) / 12  
    n = 30 * 12                       
    if i == 0: return laen / n
    return laen * (i * (1 + i)**n) / ((1 + i)**n - 1)

df['kuine_laenumakse'] = round(df.apply(lambda row: arvuta_kuumakse(row['laenusumma'], row['Intress']), axis=1), 2)
df['palga_protsent_laenule'] = round((df['kuine_laenumakse'] / df['net_salary']) * 100, 1)

# Agregeerime aastapõhiseks heatmapi jaoks
df_yearly = df.groupby(['Maakond', 'Aasta']).agg({
    'palga_protsent_laenule': 'mean',
    'korteri_hind': 'mean',
    'kuine_laenumakse': 'mean',
    'net_salary': 'mean'
}).reset_index()

# Kujundame maatriksi
heatmap_data = df_yearly.pivot(index='Maakond', columns='Aasta', values='palga_protsent_laenule')
heatmap_data = heatmap_data.dropna(how='all')

# 5. EFEKTNE JA FIKSEERITUD SOOJUSKAAR
fig = px.imshow(
    heatmap_data,
    labels=dict(x="Aasta", y="Maakond", color="Laenumakse % sissetulekust"),
    x=heatmap_data.columns,
    y=heatmap_data.index,
    color_continuous_scale="RdYlGn_r", 
    range_color=[10, 60], 
    aspect="auto"
)

fig.update_traces(
    hovertemplate="<b>%{y} (%{x})</b><br>" +
                  "Laenumakse osakaal: %{z}% palgast<br>" +
                  "<extra></extra>"
)

fig.update_layout(
    title=f"Korteri ({korteri_suurus} m²) kuumakse osakaal sissetulekust",
    xaxis_nticks=len(heatmap_data.columns),
    height=550
)

st.plotly_chart(fig, use_container_width=True)

# 6. DÜNAAMILINE STATISTIKA (INSIGHTS)
st.subheader("🎯 Sinu personaalne taskukohasuse analüüs")

kogu_ruute = len(df_yearly)
taskukohased_ruudud = len(df_yearly[df_yearly['palga_protsent_laenule'] <= max_lubatud_laenuprotsent])
protsent_kattuvus = (taskukohased_ruudud / kogu_ruute) * 100 if kogu_ruute > 0 else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="Turu kättesaadavus Sulle", 
        value=f"{protsent_kattuvus:.1f}%", 
        delta=f"{taskukohased_ruudud} valikut võimalikest {kogu_ruute}-st"
    )
with col2:
    df_sobivad = df_yearly[df_yearly['palga_protsent_laenule'] <= max_lubatud_laenuprotsent]
    if not df_sobivad.empty:
        parim_ost = df_sobivad.loc[df_sobivad['palga_protsent_laenule'].idxmin()] # leiame kõige odavama laenumakse protsendiga koha
        st.info(f"🏆 **Optimaalne oaas turul:**\n"
                f"Piirkonnas **{parim_ost['Maakond']}** aastal **{parim_ost['Aasta']}** oli Sulle kõige säästlikum ostupunkt, "
                f"kus kuumakse võttis vaid **{parim_ost['palga_protsent_laenule']:.1f}%** palgast.")
    else:
        st.error("⚠️ Sinu seadistustega pole ükski piirkond taskukohane. Suurenda sissemakset või vähenda korteri pinda.")

with col3:
    df_sobivad_counts = df_sobivad.groupby('Aasta').size().reset_index(name='count') if not df_sobivad.empty else pd.DataFrame()
    if not df_sobivad_counts.empty:
        parim_aasta = df_sobivad_counts.loc[df_sobivad_counts['count'].idxmax()]['Aasta']
        st.success(f"📅 **Parim valikuvabaduse aasta:**\n"
                   f"Aastal **{parim_aasta}** oli Sul laual kõige rohkem erinevaid maakondi, mis mahtusid lubatud eelarve piiridesse.")