import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Veebilehe seadistamine
st.set_page_config(page_title="Kinnisvara ja Ostujõud", layout="wide")
st.title("📊 Kinnisvarahinna, palga ja ostujõu trendid")
st.markdown("Vali külgribalt maakonnad ja kasuta joonise all ajajoone kohal olevat liugurit, et muuta näitajaid reaalajas.")

# 2. Andmete laadimine ja nutikas liitmine
@st.cache_data
def load_and_merge_data():
    try:
        df_hind = pd.read_csv('maa_amet_py_final.csv')
        df_palk = pd.read_csv('Eesti_keskmine_palk_py_final.csv')

        # Ühtlustame Maa-ameti nimed
        df_hind = df_hind.rename(columns={'Aeg_Plokk': 'Aeg', 'Maakond': 'Maakond', 'Keskmine_hind': 'Hind'})
        
        # Tuvastame dünaamiliselt palgafaili veerud
        p_aeg = next((c for c in df_palk.columns if 'quar' in c.lower() or 'aeg' in c.lower()), None)
        p_palk = next((c for c in df_palk.columns if 'sal' in c.lower() or 'palk' in c.lower()), None)
        p_maakond = next((c for c in df_palk.columns if 'count' in c.lower() or 'maak' in c.lower()), None)
        
        if p_aeg and p_palk:
            df_palk = df_palk.rename(columns={p_aeg: 'Aeg', p_palk: 'Palk'})
            if p_maakond:
                df_palk = df_palk.rename(columns={p_maakond: 'Maakond'})
        
        # Puhastame võtmeveerud tühikutest
        df_hind['Aeg'] = df_hind['Aeg'].astype(str).str.strip()
        df_palk['Aeg'] = df_palk['Aeg'].astype(str).str.strip()
        
        # Kontrollime, kas palgafailis on maakondade eristus olemas
        if 'Maakond' in df_palk.columns and df_palk['Maakond'].nunique() > 1:
            df_hind['Maakond'] = df_hind['Maakond'].astype(str).str.strip()
            df_palk['Maakond'] = df_palk['Maakond'].astype(str).str.strip()
            
            df_hind['Maakond_clean'] = df_hind['Maakond'].str.lower().str.replace(' maakond', '').str.strip()
            df_palk['Maakond_clean'] = df_palk['Maakond'].str.lower().str.replace(' maakond', '').str.strip()
            
            df = pd.merge(df_hind, df_palk[['Aeg', 'Palk', 'Maakond_clean']], on=['Aeg', 'Maakond_clean'], how='inner')
            df = df.drop(columns=['Maakond_clean'])
        else:
            df = pd.merge(df_hind, df_palk[['Aeg', 'Palk']], on='Aeg', how='inner')
        
        # Arvutame OSTUJÕU
        df['Ostujõud_m2'] = df['Palk'] / df['Hind']
        
        # Sorteerime tulemused kronoloogiliselt
        df['Aasta_sort'] = df['Aeg'].str[:4].astype(int)
        df = df.sort_values(by=['Aasta_sort', 'Aeg'])
        
        return df
    except Exception as e:
        st.error(f"Viga andmete laadimisel või liitmisel: {e}")
        return None

df = load_and_merge_data()

if df is not None and not df.empty:
    # 3. FILTREERIMINE: Maakondade mitmikvalik külgribal
    st.sidebar.header("Andmete filtreerimine")
    maakonnad = sorted(df['Maakond'].unique())
    
    vaikimisi = [m for m in ["Harju maakond", "Tartu maakond"] if m in maakonnad]
    valitud_maakonnad = st.sidebar.multiselect(
        "Vali maakonnad võrdlemiseks:", 
        options=maakonnad, 
        default=vaikimisi if vaikimisi else [maakonnad]
    )
    
    if valitud_maakonnad:
        # Sorteeritud unikaalsed ajapunktid liuguri jaoks
        ajapunktid = sorted(df['Aeg'].unique())
        
        # Me loome mälupuhvri (Session State), et hoida meeles kasutaja valitud aega kahe akna vahel
        if 'aktiivne_periood' not in st.session_state:
            st.session_state.aktiivne_periood = ajapunktid[-1]

        # 4. KUVAME ÜLEMISED NÄITAJAD (Metrics) - Reageerivad valitud perioodile
        st.markdown(f"### 📍 Perioodi andmed: **{st.session_state.aktiivne_periood}**")
        
        df_kaardid = df[(df['Aeg'] == st.session_state.aktiivne_periood) & (df['Maakond'].isin(valitud_maakonnad))]
        
        # Kuvame iga valitud maakonna kohta andmed dünaamiliselt kaardikestena pealkirja all
        for m_nimi in valitud_maakonnad:
            df_m_pundar = df_kaardid[df_kaardid['Maakond'] == m_nimi]
            if not df_m_pundar.empty:
                rida = df_m_pundar.iloc[0]
                st.write(f"🏠 **{m_nimi}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Keskmine hind", f"{round(rida['Hind'])} €/m²")
                col2.metric("Keskmine palk", f"{round(rida['Palk'])} €")
                col3.metric("Ostujõud turul", f"{round(rida['Ostujõud_m2'], 2)} m² kuupalga eest")
        
        st.markdown("---")
        
        # 5. GRAAFIKU LOOMINE
        st.subheader("Trendijoonte võrdlev joonis")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        varvid = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#e377c2']
        df_filtered_all = df[df['Maakond'].isin(valitud_maakonnad)]
        
        for idx, maakond in enumerate(valitud_maakonnad):
            df_m = df_filtered_all[df_filtered_all['Maakond'] == maakond]
            color = varvid[idx % len(varvid)]
            
            # Joon 1: Keskmine hind (Pidev joon, vasak telg)
            fig.add_trace(
                go.Scatter(x=df_m['Aeg'], y=df_m['Hind'], name=f"{maakond} - Hind (€/m²)", line=dict(color=color, width=2.5)),
                secondary_y=False,
            )
            
            # Joon 2: Keskmine palk (Katkendlik joon, vasak telg)
            fig.add_trace(
                go.Scatter(x=df_m['Aeg'], y=df_m['Palk'], name=f"{maakond} - Palk (€)", line=dict(color=color, width=1.5, dash='dash')),
                secondary_y=False,
            )
            
            # Joon 3: Ostujõu trend (Paks punkt joon, parem telg)
            fig.add_trace(
                go.Scatter(x=df_m['Aeg'], y=df_m['Ostujõud_m2'], name=f"{maakond} - Ostujõud (m²)", line=dict(color=color, width=4, dash='dot')),
                secondary_y=True,
            )
            
        # Lisame vertikaalse punase indikaatorjoone märgistamaks kohta, kus liugur parajasti asub
        fig.add_vline(x=st.session_state.aktiivne_periood, line_width=2, line_dash="dash", line_color="red")
            
        fig.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=500,
            margin=dict(l=20, r=20, t=10, b=10)
        )
        
        fig.update_xaxes(title_text=None, tickangle=-45) # Eemaldame siit telje nime, sest liugur tuleb otse alla
        fig.update_yaxes(title_text="<b>Raha skaala</b> (Eurodes €)", secondary_y=False)
        fig.update_yaxes(title_text="<b>Ostujõu skaala</b> (m² ühe kuupalga eest)", secondary_y=True)
        
        # Kuvame joonise
        st.plotly_chart(fig, use_container_width=True)
        
        # 6. SÜNKRONISEERITUD AJAJOONE LIUGUR OTSE JOONISE ALLA
        # Paigutame liuguri täpselt joonise alla x-telje peale, et see mõjuks joonise osana
        valitud_liugurilt = st.select_slider(
            "🎛️ AJATELJE LIUGUR: Nihuta nuppu vasakule-paremale, et vaadata ajaloolisi väärtuseid ülemistes kastides (graafikul näitab asukohta punane katkendlik joon):",
            options=ajapunktid,
            value=st.session_state.aktiivne_periood,
            key="ajatelg_slider"
        )
        
        # Kui kasutaja nihutab liugurit, uuendame seisu ja teeme reaalajas värskenduse
        if valitud_liugurilt != st.session_state.aktiivne_periood:
            st.session_state.aktiivne_periood = valitud_liugurilt
            st.rerun()
        
        st.markdown("---")
        
        # 7. Andmetabel
        with st.expander("Vaata detailseid võrdlusandmeid tabelina"):
            st.dataframe(df_filtered_all[['Aeg', 'Maakond', 'Hind', 'Palk', 'Ostujõud_m2']].reset_index(drop=True))
    else:
        st.warning("Palun vali külgribalt vähemalt üks maakond võrdluseks.")
else:
    st.error("Andmete laadimine ebaõnnestus. Kontrolli failide asukohti.")