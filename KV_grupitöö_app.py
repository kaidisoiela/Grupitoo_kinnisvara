import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns


# --- CUSTOM VISUAL STYLING VIA INJECTED CSS ---
st.markdown("""
    <style>
        /* Changes the style of all data tables/dataframes */
        .dataframe {
            font-size: 13px !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
        }
        
        /* Adds a smooth aesthetic drop shadow to the metric blocks (like R-squared) */
        [data-testid="stMetricSimpleValue"] {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: #2ca02c !important;
        }
        
        /* Smooths out the custom HTML text cards we added earlier */
        p {
            line-height: 1.5 !important;
        }
    </style>
""", unsafe_allow_html=True)

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

# 2. OLS mudeli sisendite valik külgribal
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


# --- TASKUKOHASUSE INDEKSI AEGRIDA JA GRAAFIK ---
st.markdown("---")
st.subheader(f"📈 Kinnisvara taskukohasuse indeksi muutus ajas ({valitud_maakond})")
st.write("Graafik näitab, mitu ruutmeetrit kinnisvara sai vastavas piirkonnas osta ühe kuu keskmise brutopalga eest.")

# 1. Arvutame taskukohasuse aegrea (palk / ruutmeetri hind)
df_seosed['taskukohasus'] = df_seosed['keskmine_brutopalk'] / df_seosed['keskmine_ruutmeetri_hind']

# 2. Grupeerime kvartalite lõikes ja sorteerime kronoloogiliselt
df_taskukohasus_aeg = df_seosed.groupby('fk_quarter_id').agg({
    'taskukohasus': 'mean'
}).sort_index()

# Muudame indeksi tekstiks, et Matplotlib käitleks seda diskreetse ajana
df_taskukohasus_aeg.index = df_taskukohasus_aeg.index.astype(str)

# 3. Joonistame graafiku
fig_tasku, ax_tasku = plt.subplots(figsize=(10, 5))
ax_tasku.plot(
    df_taskukohasus_aeg.index, 
    df_taskukohasus_aeg['taskukohasus'], 
    marker='o', 
    color='#2ca02c',  # Roheline joon tähistab ostujõudu/taskukohasust
    linewidth=2, 
    label='Taskukohasuse indeks'
)

# Kujundus ja x-telje piirang (et sildid ei kuhjuks, kuvame iga 4. kvartali sildi)
ax_tasku.set_title(f'Ostujõu dünaamika: Kvartali m² arv ühe brutopalga kohta ({valitud_maakond})', fontsize=12)
ax_tasku.set_xlabel('Kvartal')
ax_tasku.set_ylabel('m² ühe brutopalga kohta')
    
sammu_tihedus = 4
valitud_positsioonid = list(range(len(df_taskukohasus_aeg)))[::sammu_tihedus]
valitud_sildid = list(df_taskukohasus_aeg.index)[::sammu_tihedus]
    
from matplotlib.ticker import FixedLocator, FixedFormatter
ax_tasku.xaxis.set_major_locator(FixedLocator(valitud_positsioonid))
ax_tasku.xaxis.set_major_formatter(FixedFormatter(valitud_sildid))
    
plt.setp(ax_tasku.get_xticklabels(), rotation=45, ha='right')
    
plt.xticks(rotation=45, ha='right')
ax_tasku.grid(True, alpha=0.3, linestyle=':')
ax_tasku.legend()
    
# Kuvame Streamlitis
st.pyplot(fig_tasku)


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
    X = sm.add_constant(X) 
    
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
       
       # --- MUDELI DÜNAAMILINE JUHEND JA TÕLGENDUS (VARIANT B) ---
        st.write("") 
        st.markdown("<p style='font-size: 16px; font-weight: bold; margin-bottom: 5px;'>💡 Kuidas neid regressioonitulemusi tõlgendada?</p>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-size: 13px; color: #555555; margin-bottom: 5px;'><b>const (vabaliige):</b> Eesti kinnisvara keskmine ruutmeetri baashind (tingimustes, kus majandusnäitajad ja maakondade mõjud on nullis).</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 13px; color: #555555; margin-bottom: 5px;'><b>näitaja_lag:</b> Kui keskmine näitaja tõuseb 1 ühiku (või 1€) võrra, muutub ruutmeetri hind järgmises kvartalis koefitsiendi võrra.</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 13px; color: #555555; line-height: 1.4;'><b>aja_trend:</b> Negatiivne koefitsient tuleneb brutopalga ja tarbijahinnaindeksi ülitugevast pikaajalisest kasvutrendist. Kuna palga ja THI tõus kannavad endas juba kogu majanduse pikaajalist inflatsioonilist komponenti, toimib ajamuutuja mudelis puhta matemaatilise korrigeerijana (detrendijana), mis hoiab ära palga mõju ülehindamise.</p>", unsafe_allow_html=True)



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







# ==============================================================================
# Osa 3: GRANGERI KAUSAALSUSE ANALÜÜS
# ==============================================================================
st.markdown("---")
st.header("⏳ 3. Grangeri kausaalsuse analüüs (Ajaline juhtroll)")
st.write("""
    Siin uuritakse statistiliselt, kas makromajanduslikud näitajad on **juhtivad indikaatorid**, 
    mille ajalugu aitab kinnisvarahindade liikumist ajas ette prognoosida.
""")

# Kasutame testi jaoks puhastatud andmeid (Kogu Eesti baasil, kuna test nõuab katkematut aegrida)
df_granger = df_loplis.groupby('fk_quarter_id').agg({
    'keskmine_ruutmeetri_hind': 'mean',
    'keskmine_brutopalk': 'mean',
    'tarbijahinnaindeks': 'mean',
    'kodulaenu_intressimäär': 'mean'
}).sort_index()

# Grangeri test nõuab statsionaarseid andmeid, seega kasutame muutusi (diff)
df_granger_diff = df_granger.diff().dropna()

from statsmodels.tsa.stattools import grangercausalitytests

# Lubame kasutajal valida, millist seost testida
st.subheader("🎯 Vali näitaja, mille mõju suunda testida:")
testitav_näitaja = st.selectbox(
    "Vali sõltumatu tunnus:",
    options=["keskmine_brutopalk", "kodulaenu_intressimäär", "tarbijahinnaindeks"],
    format_func=lambda x: "Keskmine brutopalk" if x=="keskmine_brutopalk" else ("Kodulaenu intressimäär" if x=="kodulaenu_intressimäär" else "Tarbijahinnaindeks")
)

# Testime nihkeid 1 kuni 4 kvartalit
MAX_LAG = 8

try:
    # Jooksutame testi
    testi_tulemused = grangercausalitytests(
        df_granger_diff[[ 'keskmine_ruutmeetri_hind', testitav_näitaja ]], 
        maxlag=MAX_LAG
    )
    
    # Koostame tulemuste tabeli kasutajale kuvamiseks
    granger_read = []
    for nihe in range(1, MAX_LAG + 1):
        # Võtame ssr_chi2test p-väärtuse (üks levinumaid teste)
        p_val = testi_tulemused[nihe][0]['ssr_chi2test'][1]
        oluline = "✅ Jah (Mõjutab ajas ette)" if p_val < 0.05 else "❌ Ei (Seos puudub)"
        granger_read.append({
            "Nihe (kvartalit)": nihe,
            "p-väärtus": p_val,
            "Statistiliselt juhtiv roll?": oluline
        })
        
    df_granger_tulemused = pd.DataFrame(granger_read)
    
    # Kuvame tabeli kõrvuti tekstiga
    col_g1, col_ols_tulemused_seletus = st.columns([1, 1])
    
    with col_g1:
        st.dataframe(
            df_granger_tulemused.style.format({"p-väärtus": "{:.4f}"}),
            use_container_width=True
        )
        
except Exception as e:
    st.error(f"Testi käivitamisel tekkis tõrge: {e}")

# Lisame õpetliku tekstilise seletuse
st.write("") 
st.markdown("<p style='font-size: 16px; font-weight: bold; margin-bottom: 5px;'>💡 Makromajanduslik kokkuvõte: Kuidas Grangeri testi tulemusi üldistatult tõlgendada?</p>", unsafe_allow_html=True)

st.markdown("<p style='font-size: 13px; color: #555555; margin-bottom: 5px;'><b>1. Palk ja inflatsioon (THI) kui turu juhtmootorid (Nihked 5-8 kvartalit):</b> Testi tulemused näitavad, et nii keskmine brutopalk kui ka Tarbijahinnaindeks (THI) on turu jaoks <i>pikaajalised juhtivad indikaatorid</i>. Mõlema näitaja lühiajaline mõju (1-4 kvartalit) on ebaoluline, mis viitab turu inertsusele. Reaalsed muutused majanduses ja tarbijate ostujõus jõuavad kinnisvaraturu tehinguhindadesse reaalselt alles <b>1,5 kuni 2 aasta pärast</b>, kui ostjad on uute tingimustega kohanenud ja kogunud vajalikud finantstagatised.</p>", unsafe_allow_html=True)

st.markdown("<p style='font-size: 13px; color: #555555; margin-bottom: 5px;'><b>2. Kodulaenu intressimäär kui reageeriv indikaator (Kõik nihked 'Ei'):</b> Erinevalt palgast ja inflatsioonist ei oma kodulaenu intressimäär (Euribor) pikaajalist hinda ettejuhtivat rolli. Intressimäärade muutused ei liigu turust eespool, vaid toimivad koostöös teiste näitajatega kohese reaktsioonina kuumale majanduskeskkonnale. See kinnitab, et intresside mõju analüüsimisel tuleb vaadata jooksvat stressi-testi, mitte pikaajalist ajaloolist viivitust.</p>", unsafe_allow_html=True)

st.markdown("<p style='font-size: 13px; color: #555555; line-height: 1.4;'><b>Kokkuvõte grupitööle:</b> Grangeri test tõestab, et Eesti kinnisvaraturg reageerib fundamentaalsetele muutustele (palk ja inflatsioon) pikaajalise nihkega, mis annab turuosalistele võimaluse prognoosida tulevasi hinnahüppeid ette, jälgides tänaseid sissetulekute ja elukalliduse trende.</p>", unsafe_allow_html=True)





# ==============================================================================
# Osa 4: STSENAARENDE PROGNOOSIMINE (3-AASTANE TULEVIKUPROGNOOS GRAAFIKUNA)
# ==============================================================================
st.markdown("---")
st.header("🔮 4. 3-aastane tuleviku prognoos ja stsenaariumide simulatsioon")
st.write("""
    Määra allolevate liugurite abil **oodatav majanduskeskkonna areng (protsentuaalne kasv aastas)**. 
    Rakendus simuleerib OLS mudeli koefitsientide põhjal kinnisvara hinna liikumist **3 aastat (12 kvartalit) tulevikku**.
""")

# 1. Leiame kõige viimase reaalse kvartali baasandmed [2026. aasta andmete põhjal]
viimased_andmed = df_loplis.sort_values(by=['fk_quarter_id', 'maakond']).iloc[-1]
viimane_kvartal_id = viimased_andmed['fk_quarter_id']
hetke_palk = viimased_andmed['keskmine_brutopalk']
hetke_thi = viimased_andmed['tarbijahinnaindeks']
hetke_intress = viimased_andmed['kodulaenu_intressimäär']
viimane_aja_trend = df_loplis['aja_trend'].max()

# 2. Kasutajaliides (Liugurid protsentuaalse kasvu jaoks)
col_s1, col_s2 = st.columns([1, 2])

with col_s1:
    st.subheader("🛠️ Stsenaariumi sisendid:")
    
    palk_kasv_pct = st.slider(
        "Brutopalga oodatav kasv aastas (%):", 
        min_value=-5.0, max_value=15.0, value=5.0, step=0.5
    )
    
    thi_kasv_pct = st.slider(
        "Tarbijahinnaindeksi (THI/inflatsioon) kasv aastas (%):", 
        min_value=-2.0, max_value=20.0, value=3.0, step=0.5
    )
    
    tuleviku_intress = st.slider(
        "Kodulaenu intressimäära (Euribor + marginaal) tase (%):", 
        min_value=0.0, max_value=8.0, value=float(hetke_intress), step=0.1
    )

with col_s2:
    st.subheader("📈 Kinnisvara hinna prognoositav trajektoor:")
    
    # Eraldame mudelist vajalikud koefitsiendid
    coef_palk = mudel.params.get('palk_lag', 0)
    coef_thi = mudel.params.get('thi_lag', 0)
    coef_intress = mudel.params.get('intress_lag', 0)
    coef_trend = mudel.params.get('aja_trend', 0)
    coef_const = mudel.params.get('const', 0)
    
    # Maakonna spetsiifiline lisa
    maakonna_lisa = 0
    if valitud_maakond != "Kogu Eesti":
        maakonna_lisa = mudel.params.get(f"maakond_{valitud_maakond}", 0)

    # 3. Arvutame prognoosi 12 kvartalit (3 aastat) ette [1]
    prognoos_kvartalid = []
    
    # Baaspunktiks on viimane teadaolev reaalne seis
    jooksev_palk = hetke_palk
    jooksev_thi = hetke_thi
    
    # Kvartalipõhised kasvumäärad (tuletatud aastasest kasvust)
    palk_kv_kasv = (1 + palk_kasv_pct / 100) ** 0.25
    thi_kv_kasv = (1 + thi_kasv_pct / 100) ** 0.25
    
    for i in range(1, 13): # 12 kvartalit = 3 aastat [1]
        # Arvutame uued majandustunnused jooksvasse kvartalisse (liitintressi loogika)
        jooksev_palk *= palk_kv_kasv
        jooksev_thi *= thi_kv_kasv
        jooksev_aja_trend = viimane_aja_trend + i
        
        # OLS prognoosivalem
        y_prognoos = (
            coef_const + 
            (jooksev_palk * coef_palk) + 
            (jooksev_thi * coef_thi) + 
            (tuleviku_intress * coef_intress) + 
            (jooksev_aja_trend * coef_trend) + 
            maakonna_lisa
        )
        
        prognoos_kvartalid.append({
            "Kvartali samm": f"+{i} KV",
            "Prognoositud hind": y_prognoos
        })
        
    df_simulatsioon = pd.DataFrame(prognoos_kvartalid)
    
    # 4. Joonistame tuleviku prognoosgraafiku
    fig_sim, ax_sim = plt.subplots(figsize=(10, 4.5))
    ax_sim.plot(
        df_simulatsioon["Kvartali samm"], 
        df_simulatsioon["Prognoositud hind"], 
        marker='s', 
        linestyle='--', 
        color='#e377c2', 
        linewidth=2, 
        label='Mudeli simulatsioon'
    )
    
    ax_sim.set_title(f'Kinnisvara m² hinna prognoos 3 aastat tulevikku ({valitud_maakond}) [1]', fontsize=11)
    ax_sim.set_xlabel('Prognoosi periood (kvartalite samm)')
    ax_sim.set_ylabel('Hind (€/m²)')
    ax_sim.grid(True, alpha=0.3, linestyle=':')
    ax_sim.legend()
    
    st.pyplot(fig_sim)

# Selgitav tekst Variant B stiilis
st.write("") 
st.markdown("<p style='font-size: 16px; font-weight: bold; margin-bottom: 5px;'>💡 Kuidas 3-aastast simulatsiooni majanduslikult tõlgendada? [1]</p>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 13px; color: #555555; margin-bottom: 5px;'><b>Protsentuaalne liitkasv:</b> Sisestades liuguritesse näiteks palga kasvu 5% ja inflatsiooni (THI) kasvu 3%, arvutab rakendus taustal automaatselt välja nende näitajate absoluutsed väärtused igas tuleviku kvartalis, võttes arvesse liitintressi mju. Samal ajal liigub kronoloogiliselt edasi ka <i>aja_trend</i> näitaja.</p>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 13px; color: #555555;'><b>Aja trendi ja majandusnäitajate võistlus:</b> Kuna OLS mudelis on ajamuutuja koefitsient negatiivne ja brutopalga koefitsient ülitugevalt positiivne, näitab graafiku joon sulle reaalset tuleviku tasakaalupunkti. Kui paned palgakasvuks 0% ja inflatsiooniks 0%, näed, kuidas joon hakkab langema (kuna ajatrend tõmbab hinda alla). Kui aga sisestad reaalse palgakasvu (nt 6-8%), võidab palga positiivne mõju ajatrendi miinuse ja graafiku joon hakkab näitama loogilist pikaajalist hinnatõusu.</p>", unsafe_allow_html=True)
