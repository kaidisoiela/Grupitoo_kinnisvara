import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# === SAMM 1: ÄPI LEHE JA PEALKIRJADE SEADISTUS ===
st.set_page_config(page_title="Kinnisvara Ostujõu Indeks", layout="wide")

# --- LISATUD EFEKT: MAJAKESTE JA EURODE SADU TAASTAL ---
# We inject the animation elements into the parent document so they display globally.
efekti_html = """
<script>
    // Access the main Streamlit document outside of this sandboxed iframe
    const parentDoc = window.parent.document;
    
    // Create the global animation container if it doesn't exist yet
    let sajuKast = parentDoc.getElementById('globaalne-rahasadu');
    if (!sajuKast) {
        sajuKast = parentDoc.createElement('div');
        sajuKast.id = 'globaalne-rahasadu';
        sajuKast.style.position = 'fixed';
        sajuKast.style.top = '0';
        sajuKast.style.left = '0';
        sajuKast.style.width = '100vw';
        sajuKast.style.height = '100vh';
        sajuKast.style.pointerEvents = 'none'; // Allows clicking through elements
        sajuKast.style.zIndex = '99999';       // Ensures it sits above standard panels
        sajuKast.style.overflow = 'hidden';
        parentDoc.body.appendChild(sajuKast);
    }
    
    const sümbolid = ['🏠', '💶', '🪙', '🔑'];
    
    function looElement() {
        const el = parentDoc.createElement('div');
        el.innerText = sümbolid[Math.floor(Math.random() * sümbolid.length)];
        el.style.position = 'absolute';
        el.style.top = '-50px';
        el.style.left = Math.random() * 100 + 'vw';
        el.style.fontSize = Math.random() * 20 + 15 + 'px'; 
        el.style.opacity = Math.random() * 0.4 + 0.3;       
        el.style.transform = `rotate(${Math.random() * 360}deg)`;
        
        const kukkumisKiirus = Math.random() * 5 + 5; // Falls for 5 to 10 seconds
        el.style.transition = `top ${kukkumisKiirus}s linear, left ${kukkumisKiirus}s ease-in-out, transform ${kukkumisKiirus}s linear`;
        
        sajuKast.appendChild(el);
        
        // Trigger the drop transition smoothly
        setTimeout(() => {
            el.style.top = '105vh';
            el.style.left = (parseFloat(el.style.left) + (Math.random() * 10 - 5)) + 'vw';
            el.style.transform = `rotate(${Math.random() * 720}deg)`;
        }, 50);
        
        // Remove item safely once it clears the viewport bounds
        setTimeout(() => {
            el.remove();
        }, kukkumisKiirus * 1000);
    }
    
    // Check if interval is already active to prevent multi-triggering on script reruns
    if (!window.saduKäimas) {
        window.saduKäimas = true;
        setInterval(looElement, 700); // Generates an item every 700ms
    }
</script>
"""
# Render the script injection block
st.components.v1.html(efekti_html, height=0, width=0)

st.title("📐 Mitu ruutmeetrit korterit saad osta ühe kuupalgaga?")
st.markdown("""
    Antud äpp arvutab makromajandusandmete põhjal välja **Kinnisvara Ostujõu Indeksi**.
    See näitab visuaalselt, mitu ruutmeetrit Eesti korteriomandit sai keskmise (või Sinu enda) 
    ühe kuu netopalgaga konkreetses maakonnas reaalajas osta aastatel 2005–2025.
""")

# === SAMM 2: ANDMETE LAADIMINE JA FORMAATIDE ÜHTLUSTAMINE ===
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

    df_palk = pd.read_csv("Eesti_keskmine_palk_py_final.csv")
    df_palk.rename(columns={'quarter': 'Kvartal_ID', 'county': 'Maakond', 'salary': 'Palk'}, inplace=True)
    df_palk['Kvartal_ID'] = df_palk['Kvartal_ID'].astype(str).str.strip()
    df_palk['Maakond_Puhas'] = df_palk['Maakond'].apply(puhasta_maakond)
    
    df_kv = pd.read_csv("maa_amet_py_final.csv")
    if 'Aeg_Plokk' in df_kv.columns: 
        df_kv.rename(columns={'Aeg_Plokk': 'Kvartal_ID'}, inplace=True)
    
    hinna_veerg = [col for col in df_kv.columns if 'hind' in col.lower() or 'price' in col.lower()]
    if hinna_veerg:
        df_kv.rename(columns={hinna_veerg[0]: 'Hind_m2'}, inplace=True)
    else:
        df_kv['Hind_m2'] = 1000

    df_kv['Kvartal_ID'] = df_kv['Kvartal_ID'].astype(str).str.strip()
    df_kv['Maakond_Puhas'] = df_kv['Maakond'].apply(puhasta_maakond)

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

    df_merged = pd.merge(df_kv, df_palk, on=['Kvartal_ID', 'Maakond_Puhas'], how='inner', suffixes=('', '_palk'))
    df_merged = pd.merge(df_merged, df_thi_clean, on='Kvartal_ID', how='left')
    
    df_merged['Maakond'] = df_merged['Maakond_Puhas'] + " maakond"
    df_merged['Aasta'] = df_merged['Kvartal_ID'].str[:4].astype(int)
    
    df_merged = df_merged[(df_merged['Aasta'] >= 2005) & (df_merged['Aasta'] <= 2025)].copy()
    
    df_merged['Hind_m2'] = pd.to_numeric(df_merged['Hind_m2'], errors='coerce').fillna(1000)
    df_merged['Palk'] = pd.to_numeric(df_merged['Palk'], errors='coerce').fillna(1200)
    
    return df_merged

with st.spinner("⏳ Andmete ettevalmistamine..."):
    df_ostujoud = laadi_ja_puhasta_andmed()

# === SAMM 3: INTERAKTIIVNE KÜLGPANEEL (MÄNGULISUS) ===
st.sidebar.header("👤 Sinu Personaalsed Sätted")

koik_maakonnad = sorted(df_ostujoud['Maakond'].unique())
valitud_maakonnad = st.sidebar.multiselect(
    "Vali maakonnad võrdluseks:", 
    options=koik_maakonnad, 
    default=['Harju maakond', 'Tartu maakond', 'Pärnu maakond']
)

palga_kordaja = st.sidebar.slider(
    "Sinu palgatase võrreldes keskmisega:", 
    min_value=0.5, max_value=3.0, value=1.0, step=0.1,
    help="1.0 tähendab täpselt maakonna keskmist palku. 2.0 tähendab, et teenid poole rohkem."
)

# === SAMM 4: MATEMAATILISED REAALAJA ARVUTUSED ===
df_calc = df_ostujoud.copy()
df_calc['net_salary'] = (df_calc['Palk'] * palga_kordaja) * 0.80
df_calc['Ostetavad_Ruutmeetrid'] = round(df_calc['net_salary'] / df_calc['Hind_m2'], 2)

df_yearly = df_calc.groupby(['Maakond', 'Aasta']).agg({
    'Ostetavad_Ruutmeetrid': 'mean',
    'Palk': 'mean',
    'Hind_m2': 'mean'
}).reset_index()

df_filtered = df_yearly[df_yearly['Maakond'].isin(valitud_maakonnad)]

# === SAMM 5: INTERAKTIIVSE JOONDIAGRAMMI LOOMINE PLOTLY-GA ===
if not df_filtered.empty:
    fig = px.line(
        df_filtered, 
        x="Aasta", 
        y="Ostetavad_Ruutmeetrid", 
        color="Maakond",
        markers=True,
        title="Kinnisvara Ostujõu Indeks (Ruutmeetrit ühe kuupalga eest)",
        labels={"Ostetavad_Ruutmeetrid": "Mitu m² saab 1 kuu netopalga eest", "Aasta": "Aasta"}
    )
    
    fig.update_traces(
        hovertemplate="<b>%{json_backend_country} (%{x})</b><br>" +
                      "Ostujõud: <b>%{y:.2f} m²</b> kuupalga eest<br>" +
                      "<extra></extra>"
    )
    
    fig.update_layout(
        xaxis_nticks=21, 
        hovermode="x unified", 
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # === SAMM 6: DÜNAAMILINE STATISTIKA ===
    st.subheader("🧐 Sinu profiili tähelepanekud:")
    
    parim_hetk = df_filtered.loc[df_filtered['Ostetavad_Ruutmeetrid'].idxmax()]
    halvim_hetk = df_filtered.loc[df_filtered['Ostetavad_Ruutmeetrid'].idxmin()]
    
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"🟢 **Kõige suurem ostujõud (Kuldajastu):** Aastal **{parim_hetk['Aasta']}** piirkonnas **{parim_hetk['Maakond']}**, "
                   f"kus ühe kuupalgaga sai osta tervelt **{parim_hetk['Ostetavad_Ruutmeetrid']:.2f} m²** korterit. "
                   f"Sel hetkel oli keskmine brutopalk {parim_hetk['Palk']:.0f} € ja ruutmeetri hind {parim_hetk['Hind_m2']:.0f} €.")
    with col2:
        st.error(f"🔴 **Kõige madalam ostujõud (Kriisiaasta):** Aastal **{halvim_hetk['Aasta']}** piirkonnas **{halvim_hetk['Maakond']}**, "
                   f"kus kuupalk venitas välja kõigest **{halvim_hetk['Ostetavad_Ruutmeetrid']:.2f} m²**. "
                   f"Turg oli ülekuumenenud (ruutmeeter {halvim_hetk['Hind_m2']:.0f} € ja brutopalk {halvim_hetk['Palk']:.0f} €).")
else:
    st.warning("Palun vali vasakult menüüst vähemalt üks maakond, et graafikut kuvada.")