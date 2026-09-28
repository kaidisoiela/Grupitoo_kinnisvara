import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns

# --- LEHE SEADISTUS ---
st.set_page_config(page_title="Kinnisvaraturu Analüüs", layout="wide")
st.title("📊 Kinnisvara keskmise ruutmeetri hinna analüüs ja prognoos")
st.write("See rakendus võimaldab uurida Eesti makromajandusnäitajaid ja nende mõju kinnisvaraturule.")

# --- ANDMETE LAADIMINE ---
# Loome andmed otse Notebookist salvestatud puhtast CSV-failist
df_analuys = pd.read_csv("kinnisvara_koondandmed.csv")

# Ettevalmistus ja trendiindeksi loomine
# Sorteerime andmed KÕIGEPEALT ainult aja järgi, et järjekord oleks õige
df_loplis = df_analuys.sort_values(by=['fk_quarter_id']).copy()

# Loome unikaalsete kvartalite alusel järjekorranumbrid (0, 1, 2, 3...)
kvartali_järjestus = sorted(df_loplis['fk_quarter_id'].unique())
kvartali_mapping = {kvartal: i for i, kvartal in enumerate(kvartali_järjestus)}

# Määrame ajatrendi igale reale globaalselt
df_loplis['aja_trend'] = df_loplis['fk_quarter_id'].map(kvartali_mapping)

# Alles NÜÜD sorteerime lisaks maakondade kaupa, et OLS nihked (shift) töötaksid korrektselt
df_loplis = df_loplis.sort_values(by=['maakond', 'fk_quarter_id'])

# --- KASUTAJALIIDES (KÜLJERIBA VALIKUD) ---
st.sidebar.header("🛠️ Rakenduse seaded")

# 1. Piirkonna valik (mõjutab nii kirjeldavat analüüsi kui mudelit)
maakondade_nimekiri = ["Kogu Eesti"] + list(df_loplis['maakond'].unique())
valitud_maakond = st.sidebar.selectbox("Vali kuvatav piirkond:", options=maakondade_nimekiri)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 OLS mudeli parameetrid")

# 2. OLS mudeli sisendite valik külgribal (NÜÜD SIIN!)
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


# ==============================================================================
# Osa 1: ANDMEID KIRJELDAV ANALÜÜS JA DIAGRAMMID (ILMA OLS-ITA)
# ==============================================================================
st.header("📈 1. Andmete omavahelised seosed (kirjeldav analüüs)")
st.write("Siin saad uurida reaalsete andmete omavahelisi seoseid ja korrelatsioone ilma regressioonmudelita.")

# Filtreerime andmed vastavalt valitud maakonnale
if valitud_maakond == "Kogu Eesti":
    df_seosed = df_loplis.copy()
else:
    df_seosed = df_loplis[df_loplis['maakond'] == valitud_maakond].copy()

# Valime veerud, mille vahelisi seoseid uurida
veerud_analüüsiks = ['keskmine_ruutmeetri_hind', 'keskmine_brutopalk', 'tarbijahinnaindeks', 'kodulaenu_intressimäär']

veerud_est = {
    'keskmine_ruutmeetri_hind': 'Kinnisvara m² hind (€)',
    'keskmine_brutopalk': 'Keskmine brutopalk (€)',
    'tarbijahinnaindeks': 'Tarbijahinnaindeks (THI)',
    'kodulaenu_intressimäär': 'Kodulaenu intressimäär (%)'
}
df_seosed_renamed = df_seosed[veerud_analüüsiks].rename(columns=veerud_est)

# Loome kaks uut tulpa kirjeldavate graafikute kõrvuti kuvamiseks
col_seos1, col_seos2 = st.columns(2)

with col_seos1:
    st.subheader(f"🧮 Korrelatsioonimaatriks ({valitud_maakond})")
    st.write("Näitab näitajate vahelist seost vahemikus -1 (vastandlik) kuni +1 (tugev samasuunaline seos).")
    
    corr_matrix = df_seosed_renamed.corr()
    fig_corr, ax_corr = plt.subplots(figsize=(6, 4.5))
    sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", vmin=-1, vmax=1, fmt=".2f", ax=ax_corr, cbar=False)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig_corr)

with col_seos2:
    st.subheader("🎯 Kahe näitaja hajuvusdiagramm")
    st.write("Vali telgedele näitajad, et näha nende omavahelist reaalset jaotust ja lineaarsust.")
    
    x_telg = st.selectbox("Vali näitaja X-teljele:", options=list(veerud_est.values()), index=1)
    y_telg = st.selectbox("Vali näitaja Y-teljele:", options=list(veerud_est.values()), index=0)
    
    fig_scat, ax_scat = plt.subplots(figsize=(6, 4.5))
    sns.regplot(
        data=df_seosed_renamed, 
        x=x_telg, 
        y=y_telg, 
        scatter_kws={'alpha':0.6, 'color': '#1f77b4'}, 
        line_kws={'color': '#d62728', 'linestyle': '--'},
        ax=ax_scat
    )
    ax_scat.grid(True, alpha=0.3, linestyle=':')
    plt.tight_layout()
    st.pyplot(fig_scat)


# ==============================================================================
# Osa 2: MULTIPLNE REGRESSIOONMUDEL (OLS)
# ==============================================================================
st.markdown("---")
st.header("🤖 2. Regressioonianalüüs (OLS mudel)")
st.write("Selles sektsioonis arvutatakse makromajanduslike näitajate mõju ja mudeli prognoosid dünaamiliselt uuesti.")

if not valitud_makro_tekst:
    st.warning("⚠️ Palun vali vasakult külgribalt vähemalt üks majandusnäitaja, et käivitada OLS regressioonmudel!")
else:
    # 1. Kasutame algseid andmeid ja loome dummies (drop_first=True tagab taustabaasi)
    df_dummies = pd.get_dummies(df_loplis, columns=['maakond'], drop_first=True, dtype=int)
    
    # Säilitame eraldi veeru graafiku filtreerimiseks ilma nimekonfliktita
    df_dummies['maakond_nimi_graafikule'] = df_loplis['maakond']

    # 2. Arvutame nihked täpselt nii nagu sinu toimivas koodis (nihe = 1)
    nihe = 1
    df_dummies['palk_lag'] = df_dummies.groupby('fk_county_id')['keskmine_brutopalk'].shift(nihe)
    df_dummies['thi_lag'] = df_dummies.groupby('fk_county_id')['tarbijahinnaindeks'].shift(nihe)
    df_dummies['intress_lag'] = df_dummies.groupby('fk_county_id')['kodulaenu_intressimäär'].shift(nihe)

    # Valitud reaalsed veerunimed vastavalt kasutaja valikule külgribal
    valitud_veerud = [makro_tunnused[t] for t in valitud_makro_tekst]

    # Eemaldame tühjad read põhinedes vaid valitud veergudel ja sihttunnusel
    kriitilised_veerud = valitud_veerud + ['aja_trend', 'keskmine_ruutmeetri_hind']
    df_mudel_puhas = df_dummies.dropna(subset=kriitilised_veerud).copy()

    # 3. Sõltumatud muutujad (X) - Lisame globaalse konstandi tagasi!
    maakonna_veerud = [col for col in df_mudel_puhas.columns if col.startswith('maakond_') and col != 'maakond_nimi_graafikule']
    tunnused = valitud_veerud + ['aja_trend'] + maakonna_veerud

    X = df_mudel_puhas[tunnused]
    X = sm.add_constant(X)  # <-- SEE RIDA MUUDAB INTRESSI MÄRGI NEGATIIVSEKS!
    
    Y = df_mudel_puhas['keskmine_ruutmeetri_hind']

    # 4. Treenime OLS mudeli
    mudel = sm.OLS(Y, X).fit()

    # Ennustame väärtused joongraafiku jaoks
    df_mudel_puhas['prognoositud_hind'] = mudel.predict(X)

    # Kuvame mudeli väljundid kahes tulbas kõrvuti
    col_ols1, col_ols2 = st.columns(2)

    with col_ols1:
        st.subheader("📋 Tunnuste mõju ja olulisus")
        st.metric(label="R-squared (Mudeli seletusvägi)", value=f"{mudel.rsquared:.4f}")

        # Filtreerime tabelist välja pikad maakondade read, et tabel oleks puhas
        kuvatavad_tunnused = ['const'] + valitud_veerud + ['aja_trend']

        # Teeme koefitsientide tabeli
        tulemuste_tabel = pd.DataFrame({
            "Koefitsient (coef)": mudel.params[kuvatavad_tunnused],
            "p-väärtus (P>|t|)": mudel.pvalues[kuvatavad_tunnused]
        })
        
        tulemuste_tabel['Statistiliselt oluline?'] = tulemuste_tabel['p-väärtus (P>|t|)'] < 0.05
        tulemuste_tabel['Statistiliselt oluline?'] = tulemuste_tabel['Statistiliselt oluline?'].map({True: "✅ Jah", False: "❌ Ei"})
        
        st.dataframe(tulemuste_tabel.style.format({"Koefitsient (coef)": "{:.2f}", "p-väärtus (P>|t|)": "{:.4f}"}))

    with col_ols2:
        st.subheader("📉 Aegrea võrdlus: Ennustus vs Tegelik")
        
        # Filtreerime joonise andmeid vastavalt kasutaja valitud maakonnale
        if valitud_maakond == "Kogu Eesti":
            df_graafik = df_mudel_puhas.groupby('fk_quarter_id').agg({
                'keskmine_ruutmeetri_hind': 'mean',
                'prognoositud_hind': 'mean'
            }).sort_index()
            pealkiri = "Eesti keskmine: Tegelik vs Mudeli prognoos"
        else:
            df_graafik = df_mudel_puhas[df_mudel_puhas['maakond_nimi_graafikule'] == valitud_maakond].groupby('fk_quarter_id').agg({
                'keskmine_ruutmeetri_hind': 'mean',
                'prognoositud_hind': 'mean'
            }).sort_index()
            pealkiri = f"{valitud_maakond}: Tegelik vs Mudeli prognoos"

        # Loome puhta loogilise ajatelje Matplotlibi jaoks, et vältida siltide ülekuhjumist
        kvartali_positsioonid = list(range(len(df_graafik)))
        kvartali_sildid = [str(x) for x in df_graafik.index]

        fig_line, ax_line = plt.subplots(figsize=(10, 5))
        ax_line.plot(kvartali_positsioonid, df_graafik['keskmine_ruutmeetri_hind'], marker='o', color='#1f77b4', linewidth=2.5, label='Tegelik hind')
        ax_line.plot(kvartali_positsioonid, df_graafik['prognoositud_hind'], marker='s', linestyle='--', color='#d62728', linewidth=2, label='Mudeli prognoos')
        
        ax_line.set_title(pealkiri, fontsize=12)
        ax_line.set_xlabel('Kvartal')
        ax_line.set_ylabel('Hind (€/m²)')

        # Sildid kord aastas (iga 4. kvartal) ja joondus paremale
        sammu_tihedus = 4
        ax_line.xaxis.set_major_locator(plt.FixedLocator(kvartali_positsioonid[::sammu_tihedus]))
        ax_line.xaxis.set_major_formatter(plt.FixedFormatter(kvartali_sildid[::sammu_tihedus]))
        
        plt.setp(ax_line.get_xticklabels(), rotation=45, ha='right')

        ax_line.grid(True, alpha=0.3, linestyle=':')
        ax_line.legend()
        
        st.pyplot(fig_line)