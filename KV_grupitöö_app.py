import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine


# --- LEHE SEADISTUS ---
st.set_page_config(page_title="Kinnisvaraturu Regressioonianalüüs", layout="wide")
st.title("📊 Kinnisvara keskmise ruutmeetri hinna analüüs ja prognoos")
st.write("See rakendus tõmbab andmed PostgreSQL andmebaasist ning arvutab dünaamiliselt regressioonmudeli tulemused.")



# --- ANDMETE LAADIMINE ---

# Loeme andmed otse sinu Notebookist salvestatud puhtast CSV-failist
df_analuys = pd.read_csv("kinnisvara_koondandmed.csv")

# --- ETTEVALMISTUS JA TREND ---
df_loplis = df_analuys.sort_values(by=['maakond', 'fk_quarter_id']).copy()
kvartali_järjestus = sorted(df_loplis['fk_quarter_id'].unique())
kvartali_mapping = {kvartal: i for i, kvartal in enumerate(kvartali_järjestus)}
df_loplis['aja_trend'] = df_loplis['fk_quarter_id'].map(kvartali_mapping)




# --- OLS KASUTAJALIIDES (KÜLJERIBA VALIKUD) ---
st.sidebar.header("🛠️ Mudeli seaded")

# 1. Sisendnäitajate valik
makro_tunnused = {
    "Palk (1-kvartalise nihkega)": "palk_lag",
    "Tarbijahinnaindeks (1-kvartalise nihkega)": "thi_lag",
    "Kodulaenu intressimäär (1-kvartalise nihkega)": "intress_lag"
}

valitud_makro_tekst = st.sidebar.multiselect(
    "Vali mudelisse kaasatavad majandusnäitajad:",
    options=list(makro_tunnused.keys()),
    default=list(makro_tunnused.keys())
)

# 2. Asukoha filtreerimine graafiku jaoks
maakondade_nimekiri = ["Kogu Eesti"] + list(df_loplis['maakond'].unique())
valitud_maakond = st.sidebar.selectbox("Vali kuvatav piirkond graafikul:", options=maakondade_nimekiri)

if not valitud_makro_tekst:
    st.error("Palun vali vähemalt üks majandusnäitaja, et mudelit käivitada!")
    st.stop()

# --- MUDELI DÜNAAMILINE ARVUTAMINE ---
# Teeme dummyd
df_dummies_all = pd.get_dummies(df_loplis, columns=['maakond'], drop_first=True, dtype=int)

# Arvutame nihked (nihe = 1, kuna see oli parim)
nihe = 1
df_dummies_all['palk_lag'] = df_dummies_all.groupby('fk_county_id')['keskmine_brutopalk'].shift(nihe)
df_dummies_all['thi_lag'] = df_dummies_all.groupby('fk_county_id')['tarbijahinnaindeks'].shift(nihe)
df_dummies_all['intress_lag'] = df_dummies_all.groupby('fk_county_id')['kodulaenu_intressimäär'].shift(nihe)

# Valitud reaalsed veerunimed
valitud_veerud = [makro_tunnused[t] for t in valitud_makro_tekst]

# Eemaldame tühjad read põhinedes vaid valitud veergudel
kriitilised_veerud = valitud_veerud + ['aja_trend', 'keskmine_ruutmeetri_hind']
df_mudel_puhas = df_dummies_all.dropna(subset=kriitilised_veerud)

# Sõltumatud muutujad (X)
maakonna_veerud = [col for col in df_mudel_puhas.columns if col.startswith('maakond_')]
tunnused = valitud_veerud + ['aja_trend'] + maakonna_veerud

X = df_mudel_puhas[tunnused]
X = sm.add_constant(X)
Y = df_mudel_puhas['keskmine_ruutmeetri_hind']

# Treenime OLS mudeli
mudel = sm.OLS(Y, X).fit()

# Ennustame väärtused
df_mudel_puhas['prognoositud_hind'] = mudel.predict(X)

# Toome tagasi tekstilise maakonna graafiku jaoks
df_mudel_puhas['maakond'] = df_loplis.loc[df_mudel_puhas.index, 'maakond']

# --- VÄLJUNDI KUVAMINE ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📈 Mudeli headus")
    st.metric(label="R-squared (Seletusvägi)", value=f"{mudel.rsquared:.4f}")
    
    st.subheader("📋 Tunnuste mõju ja olulisus")
    # Teeme koefitsientide tabeli puhtaks pandase andmetabeliks
    tulemuste_tabel = pd.DataFrame({
        "Koefitsient (coef)": mudel.params[valitud_veerud + ['aja_trend']],
        "p-väärtus (P>|t|)": mudel.pvalues[valitud_veerud + ['aja_trend']]
    })
    
    # Lisame märke olulisuse kohta
    tulemuste_tabel['Statistiliselt oluline?'] = tulemuste_tabel['p-väärtus (P>|t|)'] < 0.05
    tulemuste_tabel['Statistiliselt oluline?'] = tulemuste_tabel['Statistiliselt oluline?'].map({True: "✅ Jah", False: "❌ Ei"})
    
    st.dataframe(tulemuste_tabel.style.format({"Koefitsient (coef)": "{:.2f}", "p-väärtus (P>|t|)": "{:.4f}"}))

with col2:
    st.subheader("📉 Aegrea võrdlus")
    
    # Filtreerime andmeid vastavalt kasutaja valitud maakonnale
    if valitud_maakond == "Kogu Eesti":
        df_graafik = df_mudel_puhas.groupby('fk_quarter_id').agg({
            'keskmine_ruutmeetri_hind': 'mean',
            'prognoositud_hind': 'mean'
        }).sort_index()
        pealkiri = "Eesti keskmine kinnisvara ruutmeetri hind: Tegelik vs Mudeli prognoos"
    else:
        df_graafik = df_mudel_puhas[df_mudel_puhas['maakond'] == valitud_maakond].groupby('fk_quarter_id').agg({
            'keskmine_ruutmeetri_hind': 'mean',
            'prognoositud_hind': 'mean'
        }).sort_index()
        pealkiri = f"{valitud_maakond}: Tegelik vs Mudeli prognoos"

    df_graafik.index = df_graafik.index.astype(str)

    # Joonistame graafiku
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_graafik.index, df_graafik['keskmine_ruutmeetri_hind'], marker='o', color='#1f77b4', linewidth=2.5, label='Tegelik hind')
    ax.plot(df_graafik.index, df_graafik['prognoositud_hind'], marker='s', linestyle='--', color='#d62728', linewidth=2, label='Mudeli prognoos')
    
    ax.set_title(pealkiri, fontsize=12)
    ax.set_xlabel('Kvartali ID')
    ax.set_ylabel('Hind (€/m²)')
    plt.xticks(rotation=45)
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend()
    
    st.pyplot(fig)



    # --- UUS BLOKK: ANALÜÜS ILMA OLS-ITA ---
st.markdown("---")
st.header("📊 Andmete omavahelised seosed (ilma mudelita)")
st.write("Siin saad uurida reaalsete andmete omavahelisi seoseid ja korrelatsioone ilma regressioonmudelita.")

# Filtreerime andmed vastavalt küljeribal valitud maakonnale
if valitud_maakond == "Kogu Eesti":
    df_seosed = df_analuys.copy()
else:
    df_seosed = df_analuys[df_analuys['maakond'] == valitud_maakond].copy()

# Valime veerud, mille vahelisi seoseid uurida
veerud_analüüsiks = ['keskmine_ruutmeetri_hind', 'keskmine_brutopalk', 'tarbijahinnaindeks', 'kodulaenu_intressimäär']

# Teeme uued veerud kasutajale loetavamaks
veerud_est = {
    'keskmine_ruutmeetri_hind': 'Kinnisvara m² hind (€)',
    'keskmine_brutopalk': 'Keskmine brutopalk (€)',
    'tarbijahinnaindeks': 'Tarbijahinnaindeks (THI)',
    'kodulaenu_intressimäär': 'Kodulaenu intressimäär (%)'
}
df_seosed_renamed = df_seosed[veerud_analüüsiks].rename(columns=veerud_est)

# Loome kaks uut tulpa kõrvuti kuvamiseks
col_seos1, col_seos2 = st.columns(2)

with col_seos1:
    st.subheader(f"🧮 Korrelatsioonimaatriks ({valitud_maakond})")
    st.write("Näitab näitajate vahelist seost vahemikus -1 (vastandlik) kuni +1 (tugev samasuunaline seos).")
    
    # Arvutame korrelatsiooni
    corr_matrix = df_seosed_renamed.corr()
    
    # Joonistame kuumuskaardi (Heatmap)
    fig_corr, ax_corr = plt.subplots(figsize=(6, 4.5))
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", vmin=-1, vmax=1, fmt=".2f", ax=ax_corr, cbar=False)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig_corr)

with col_seos2:
    st.subheader("🎯 Kahe näitaja hajuvusdiagramm")
    
    # Lubame kasutajal ise valida, milliseid näitajaid võrrelda
    x_telg = st.selectbox("Vali näitaja X-teljele:", options=list(veerud_est.values()), index=1)
    y_telg = st.selectbox("Vali näitaja Y-teljele:", options=list(veerud_est.values()), index=0)
    
    # Joonistame hajuvusdiagrammi koos lineaarse trendijoonega (regplot ilma OLS raportita)
    fig_scat, ax_scat = plt.subplots(figsize=(6, 4.5))
    sns.regplot(
        data=df_seosed_renamed, 
        x=x_telg, 
        y=y_telg, 
        scatter_kws={'alpha':0.6, 'color': '#1f77b4'}, 
        line_kws={'color': '#d62728', 'linestyle': '--'},
        ax=ax_scat
    )
    ax_scat.set_title(f"{x_telg} vs {y_telg} ({valitud_maakond})", fontsize=10)
    ax_scat.grid(True, alpha=0.3, linestyle=':')
    plt.tight_layout()
    st.pyplot(fig_scat)