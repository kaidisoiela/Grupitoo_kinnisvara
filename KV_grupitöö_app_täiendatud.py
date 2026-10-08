import streamlit as st
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from statsmodels.tsa.stattools import grangercausalitytests
from matplotlib.ticker import FixedLocator, FixedFormatter

# --- KASUTAJALIIDESE STIILID (CSS) ---
st.markdown("""
    <style>
        .dataframe {
            font-size: 13px !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
        }
        [data-testid="stMetricSimpleValue"] {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: #2ca02c !important;
        }
        p {
            line-height: 1.6 !important;
        }
        .info-box {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# --- LEHE SEADISTUS ---
st.set_page_config(page_title="Kinnisvaraturu analüüs", layout="wide")
st.title("📊 Kinnisvarahindade ja majandusnäitajate seoste analüüs")

st.markdown("""
<div class="info-box">
    <h3>👋 Tere tulemast kinnisvaraturu analüsaatorisse!</h3>
    <p>See rakendus aitab Sul lihtsal viisil mõista, kuidas Eesti majanduse käekäik (palgad, hinnatõus ja intressid) mõjutab kinnisvara ruutmeetri hinda.</p>
</div>
""", unsafe_allow_html=True)

# --- ANDMETE LAADIMINE ---
@st.cache_data
def laadi_andmed():
    df = pd.read_csv("kinnisvara_koondandmed.csv")
    df_loplis = df.sort_values(by=['fk_quarter_id']).copy()
    kvartali_järjestus = sorted(df_loplis['fk_quarter_id'].unique())
    kvartali_mapping = {kvartal: i for i, kvartal in enumerate(kvartali_järjestus)}
    df_loplis['aja_trend'] = df_loplis['fk_quarter_id'].map(kvartali_mapping)
    df_loplis = df_loplis.sort_values(by=['maakond', 'fk_quarter_id'])
    return df_loplis

try:
    df_loplis = laadi_andmed()
except Exception as e:
    st.error(f"Andmefaili 'kinnisvara_koondandmed.csv' ei leitud. Palun veendu, et fail on samas kaustas. Viga: {e}")
    st.stop()

# --- KASUTAJALIIDES (KÜLJERIBA VALIKUD) ---
st.sidebar.header("🛠️ Seaded ja valikud")

maakondade_nimekiri = ["Kogu Eesti"] + list(df_loplis['maakond'].unique())
valitud_maakond = st.sidebar.selectbox("1. Vali piirkond, mida uurida:", options=maakondade_nimekiri)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Statistilise mudeli sisendid")

makro_tunnused = {
    "Keskmine brutopalk (1-kvartali nihkega)": "palk_lag",
    "Tarbijahinnaindeks / Elukallidus (1-kvartali nihkega)": "thi_lag",
    "Kodulaenu intressimäär (1-kvartali nihkega)": "intress_lag"
}

valitud_makro_tekst = st.sidebar.multiselect(
    "2. Milliseid näitajaid mudelis arvesse võtta?",
    options=list(makro_tunnused.keys()),
    default=list(makro_tunnused.keys())
)

# ==============================================================================
# Osa 1: ANDMEID KIRJELDAV ANALÜÜS JA DIAGRAMMID
# ==============================================================================
st.header("📈 1. Millised on andmed ja kuidas nad omavahel seotud on?")
st.write("Enne tuleviku ennustamist vaatame, mida räägib meile ajalugu.")

if valitud_maakond == "Kogu Eesti":
    df_seosed = df_loplis.copy()
else:
    df_seosed = df_loplis[df_loplis['maakond'] == valitud_maakond].copy()

veerud_analüüsiks = ['keskmine_ruutmeetri_hind', 'keskmine_brutopalk', 'tarbijahinnaindeks', 'kodulaenu_intressimäär']
veerud_est = {
    'keskmine_ruutmeetri_hind': 'Kinnisvara m² hind (€)',
    'keskmine_brutopalk': 'Keskmine brutopalk (€)',
    'tarbijahinnaindeks': 'Elukallidus (THI)',
    'kodulaenu_intressimäär': 'Laenuintress (%)'
}
df_seosed_renamed = df_seosed[veerud_analüüsiks].rename(columns=veerud_est)

col_seos1, col_seos2 = st.columns(2)

with col_seos1:
    st.subheader(f"🧮 Näitajate vahelised seosed ({valitud_maakond})")
    st.write("**Kuidas tabelit lugeda:** Number vahemikus 0 kuni 1 tähendab, et näitajad liiguvad samas suunas (nt palga tõustes tõuseb ka kinnisvara hind). Mida lähedamal number on ühele (1.00), seda tugevam on seos.")
    
    corr_matrix = df_seosed_renamed.corr()
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=0)
    corr_matrix_trimmed = corr_matrix.iloc[1:, :-1]
    mask_trimmed = mask[1:, :-1]
    fig_corr, ax_corr = plt.subplots(figsize=(6, 4.5))
    sns.heatmap(corr_matrix_trimmed, annot=True, cmap="Blues", vmin=-1, vmax=1, fmt=".2f", ax=ax_corr, cbar=False, mask=mask_trimmed)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig_corr)

with col_seos2:
    st.subheader("🎯 Vali kaks näitajat ja vaata nende seost")
    st.write("Punane joon näitab üldist suunda. Kui joon ronib ülespoole, siis ühe näitaja suurenemine toob kaasa ka teise suurenemise.")
    
    x_telg = st.selectbox("Vali näitaja alumisele (X) teljele:", options=list(veerud_est.values()), index=1)
    y_telg = st.selectbox("Vali näitaja vasakule (Y) teljele:", options=list(veerud_est.values()), index=0)
    
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
st.subheader(f"📊 Kinnisvara taskukohasus ehk ostujõud ajas ({valitud_maakond})")
st.write("See graafik näitab lihtsat suhtarvu: **mitu ruutmeetrit kodupinna pinda sai osta täpselt ühe kuu keskmise brutopalga eest** konkreetsel perioodil.")

df_seosed['taskukohasus'] = df_seosed['keskmine_brutopalk'] / df_seosed['keskmine_ruutmeetri_hind']
df_taskukohasus_aeg = df_seosed.groupby('fk_quarter_id').agg({'taskukohasus': 'mean'}).sort_index()
df_taskukohasus_aeg.index = df_taskukohasus_aeg.index.astype(str)

fig_tasku, ax_tasku = plt.subplots(figsize=(10, 3.5))
ax_tasku.plot(df_taskukohasus_aeg.index, df_taskukohasus_aeg['taskukohasus'], marker='o', color='#1f77b4', linewidth=2)
ax_tasku.set_ylabel('m² ühe brutopalga eest')
ax_tasku.set_xlabel('Kvartal')

sammu_tihedus = 4
valitud_positsioonid = list(range(len(df_taskukohasus_aeg)))[::sammu_tihedus]
valitud_sildid = list(df_taskukohasus_aeg.index)[::sammu_tihedus]
ax_tasku.xaxis.set_major_locator(FixedLocator(valitud_positsioonid))
ax_tasku.xaxis.set_major_formatter(FixedFormatter(valitud_sildid))
plt.setp(ax_tasku.get_xticklabels(), rotation=45, ha='right')
ax_tasku.grid(True, alpha=0.3, linestyle=':')
st.pyplot(fig_tasku)


# ==============================================================================
# Osa 2: VÄHIMRUUTUDE REGRESSIOONMUDEL
# ==============================================================================

st.markdown("---")
st.header("🔬 2. Statistiline mudel näitajate vaheliste seoste leidmiseks")
st.write("Siin arvutame välja, kui täpselt suudavad valitud majandusnäitajad ajaloos toimunud hinnamuutusi selgitada, rakendades regressioonmudelit vähimruutude meetodil (OLS).")

if not valitud_makro_tekst:
    st.warning("⚠️ Palun vali vasakult menüüst vähemalt üks majandusnäitaja!")
else:
    df_dummies = pd.get_dummies(df_loplis, columns=['maakond'], drop_first=True, dtype=int)
    df_dummies['maakond_nimi_graafikule'] = df_loplis['maakond']

    nihe = 1
    df_dummies['palk_lag'] = df_dummies.groupby('fk_county_id')['keskmine_brutopalk'].shift(nihe)
    df_dummies['thi_lag'] = df_dummies.groupby('fk_county_id')['tarbijahinnaindeks'].shift(nihe)
    df_dummies['intress_lag'] = df_dummies.groupby('fk_county_id')['kodulaenu_intressimäär'].shift(nihe)

    valitud_veerud = [makro_tunnused[t] for t in valitud_makro_tekst]
    kriitilised_veerud = valitud_veerud + ['aja_trend', 'keskmine_ruutmeetri_hind']
    df_mudel_puhas = df_dummies.dropna(subset=kriitilised_veerud).copy()

    maakonna_veerud = [col for col in df_mudel_puhas.columns if col.startswith('maakond_') and col != 'maakond_nimi_graafikule']
    tunnused = valitud_veerud + ['aja_trend'] + maakonna_veerud

    X = df_mudel_puhas[tunnused]
    X = sm.add_constant(X) 
    Y = df_mudel_puhas['keskmine_ruutmeetri_hind']

    mudel = sm.OLS(Y, X).fit()
    df_mudel_puhas['prognoositud_hind'] = mudel.predict(X)

    # --- MUDELI TÄPSUS JA SELETUS (TÄISLAIUSES) ---
    st.subheader("📋 Kuidas erinevad näitajad hinda mõjutavad?")
    
    r2 = mudel.rsquared
    st.metric(label="📊 Mudeli usaldusväärsus / üldine täpsus", value=f"{r2*100:.1f}%")
    st.write(f"See tähendab, et valitud näitajad suudavad selgitada tervelt **{r2*100:.1f}%** kogu Eesti kinnisvarahindade kõikumisest.")

    # Ajanihke (lag) selgitus täislaiuses infokastina
    st.markdown("""
    <div style="background-color: #eef2f7; padding: 15px; border-radius: 8px; border-left: 4px solid #1f77b4; margin-top: 10px; margin-bottom: 20px;">
        <strong>⏱️ Mis on "ajanihe" (mudelis: <i>lag</i>)?</strong><br/>
        Kinnisvaraturg reageerib majandusele viivitusega. Kui täna tõuseb palk või intress, ei muutu korterite hinnad samal sekundil. 
        Inimestel kulub aega uute oludega kohanemiseks, pangaga suhtlemiseks ja tehinguni jõudmiseks. 
        Seetõttu kasutab mudel <strong>1 kvartali pikkust ajanihet</strong> — see tähendab, et täna näidatav mõju põhineb tegelikult sellel, mis toimus majanduses 1 kvartal tagasi.
    </div>
    """, unsafe_allow_html=True)

    kuvatavad_tunnused = ['const'] + valitud_veerud + ['aja_trend']
    
    tõlgitud_nimed = {
        'const': 'Baashind (kui muud näitajad on nullis)',
        'palk_lag': 'Brutopalga tõus 1€ võrra (1 kvartal tagasi)',
        'thi_lag': 'Elukalliduse tõus 1 ühiku võrra (1 kvartal tagasi)',
        'intress_lag': 'Laenuintressi tõus 1% võrra (1 kvartal tagasi)',
        'aja_trend': 'Aja loomulik möödumine (1 kvartal)'
    }
    
    moju_toestatud = []
    for p in mudel.pvalues[kuvatavad_tunnused]:
        if p < 0.05:
            moju_toestatud.append("🟢 Kindel seos")
        else:
            moju_toestatud.append("🔴 Juhuslik seos")

    tulemuste_tabel = pd.DataFrame({
        "Majandusnäitaja": [tõlgitud_nimed.get(x, x) for x in kuvatavad_tunnused],
        "Mõju m² hinnale (€)": mudel.params[kuvatavad_tunnused],
        "Hinnang": moju_toestatud
    })
    
    st.dataframe(
        tulemuste_tabel.style.format({"Mõju m² hinnale (€)": "{:+.2f} €"}),
        use_container_width=True
    )
    st.write("🟢 **Kindel seos** – matemaatiliselt on tõestatud, et see näitaja ennustab hinda stabiilselt. &nbsp;&nbsp;&nbsp;&nbsp; 🔴 **Juhuslik seos** – selle näitaja mõju võib olla antud andmete põhjal juhuslik.")
   
    # --- JOONGRAAFIK (MUGAVALT JA SUURELT TABELI ALL) ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📉 Aegrea võrdlus: Päris elu vs mudeli arvutus")
    st.write("Sellelt graafikult näed, kui täpselt suutis matemaatiline mudel (punane joon) tegelikke ajaloolisi hindu (sinine joon) jäljendada.")
    
    if valitud_maakond == "Kogu Eesti":
        df_graafik = df_mudel_puhas.groupby('fk_quarter_id').agg({'keskmine_ruutmeetri_hind': 'mean', 'prognoositud_hind': 'mean'}).sort_index()
        pealkiri = "Kogu Eesti: Päris elu vs mudeli arvutus"
    else:
        df_graafik = df_mudel_puhas[df_mudel_puhas['maakond_nimi_graafikule'] == valitud_maakond].groupby('fk_quarter_id').agg({'keskmine_ruutmeetri_hind': 'mean', 'prognoositud_hind': 'mean'}).sort_index()
        pealkiri = f"{valitud_maakond}: Päris elu vs mudeli arvutus"

    kvartali_positsioonid = list(range(len(df_graafik)))
    kvartali_sildid = [str(x) for x in df_graafik.index]

    fig_line, ax_line = plt.subplots(figsize=(12, 5.5))
    ax_line.plot(kvartali_positsioonid, df_graafik['keskmine_ruutmeetri_hind'], marker='o', color='#1f77b4', linewidth=2.5, label='Päriselt toimunud tehinguhind')
    ax_line.plot(kvartali_positsioonid, df_graafik['prognoositud_hind'], marker='s', linestyle='--', color='#d62728', linewidth=2, label='Mudeli poolt arvatud hind')
    
    ax_line.set_title(pealkiri, fontsize=12)
    ax_line.set_xlabel('Kvartal')
    ax_line.set_ylabel('Hind (€/m²)')

    sammu_tihedus = 4
    ax_line.xaxis.set_major_locator(plt.FixedLocator(kvartali_positsioonid[::sammu_tihedus]))
    ax_line.xaxis.set_major_formatter(plt.FixedFormatter(kvartali_sildid[::sammu_tihedus]))
    plt.setp(ax_line.get_xticklabels(), rotation=45, ha='right')
    ax_line.grid(True, alpha=0.3, linestyle=':')
    ax_line.legend()
    plt.tight_layout()
    st.pyplot(fig_line)


# ==============================================================================
# Osa 3: AJALINE JUHTROLL
# ==============================================================================
st.markdown("---")
st.header("⏳ 3. Mis juhtub enne? (Ajaline juhtroll ehk millist näitajat enne vaadata)")
st.write("Majanduses võtavad asjad aega. Siin testime, kas majandusnäitajate muutused käivad kinnisvarahindadest ajaliselt ees ehk kas nad on nn varajased hoiatussignaalid. Arvutused on tehtud Grangeri kausaalsuse regressioonmudeliga. ")

df_granger = df_loplis.groupby('fk_quarter_id').agg({
    'keskmine_ruutmeetri_hind': 'mean',
    'keskmine_brutopalk': 'mean',
    'tarbijahinnaindeks': 'mean',
    'kodulaenu_intressimäär': 'mean'
}).sort_index()

df_granger_diff = df_granger.diff().dropna()

st.subheader("🎯 Vali näitaja, mille ajalist eelnevat ennustusvõimet testida:")
testitav_näitaja = st.selectbox(
    "Vali majandusnäitaja:",
    options=["keskmine_brutopalk", "kodulaenu_intressimäär", "tarbijahinnaindeks"],
    format_func=lambda x: "Keskmine brutopalk" if x=="keskmine_brutopalk" else ("Kodulaenu intressimäär" if x=="kodulaenu_intressimäär" else "Tarbijahinnaindeks / Elukallidus")
)

MAX_LAG = 8

try:
    testi_tulemused = grangercausalitytests(df_granger_diff[['keskmine_ruutmeetri_hind', testitav_näitaja]], maxlag=MAX_LAG)
    
    granger_read = []
    for nihe in range(1, MAX_LAG + 1):
        p_val = testi_tulemused[nihe][0]['ssr_chi2test'][1]
        oluline = "🟢 JAH – käib turust ajaliselt ees" if p_val < 0.05 else "⚪ EI – ajalist mõju ei tuvastatud"
        granger_read.append({
            "Ajanihe (kvartalit hiljem)": f"{nihe} kvartalit (u {nihe*3} kuud)",
            "Kas see näitaja ennustab tulevikku ette?": oluline
        })
        
    df_granger_tulemused = pd.DataFrame(granger_read)
    st.dataframe(df_granger_tulemused, use_container_width=True)
        
except Exception as e:
    st.error(f"Testi käivitamisel tekkis tõrge: {e}")

# ==============================================================================
# Osa 4: STSENAARENDE PROGNOOSIMINE
# ==============================================================================
st.markdown("---")
st.header("🔮 4. Mängi tulevikuga: 3-aastane stsenaariumide simulaator")
st.write("Muuda liugureid ja vaata, kuhu tüürib kinnisvara ruutmeetri hind järgmise 3 aasta jooksul. Ennustus eeldab, et prognoosi sisendiks määratud näitajad kehtivad igal 3 aastal.")

viimased_andmed = df_loplis.sort_values(by=['fk_quarter_id', 'maakond']).iloc[-1]
hetke_palk = viimased_andmed['keskmine_brutopalk']
hetke_thi = viimased_andmed['tarbijahinnaindeks']
hetke_intress = viimased_andmed['kodulaenu_intressimäär']
viimane_aja_trend = df_loplis['aja_trend'].max()

col_s1, col_s2 = st.columns([1, 2])

with col_s1:
    st.subheader("🛠️ Sinu prognoos majandusele:")
    palk_kasv_pct = st.slider("Brutopalga oodatav kasv aastas (%):", min_value=-5.0, max_value=15.0, value=5.0, step=0.5)
    thi_kasv_pct = st.slider("Elukalliduse (hinnatõusu) kasv aastas (%):", min_value=-2.0, max_value=20.0, value=3.0, step=0.5)
    tuleviku_intress = st.slider("Kodulaenu intressimäära keskmine tase (%):", min_value=0.0, max_value=8.0, value=float(hetke_intress), step=0.1)

with col_s2:
    st.subheader("📈 Kinnisvara hinna prognoositav tulevikujoon:")
    
    coef_palk = mudel.params.get('palk_lag', 0)
    coef_thi = mudel.params.get('thi_lag', 0)
    coef_intress = mudel.params.get('intress_lag', 0)
    coef_trend = mudel.params.get('aja_trend', 0)
    coef_const = mudel.params.get('const', 0)
    
    maakonna_lisa = 0
    if valitud_maakond != "Kogu Eesti":
        maakonna_lisa = mudel.params.get(f"maakond_{valitud_maakond}", 0)

    prognoos_kvartalid = []
    jooksev_palk = hetke_palk
    jooksev_thi = hetke_thi
    
    palk_kv_kasv = (1 + palk_kasv_pct / 100) ** 0.25
    thi_kv_kasv = (1 + thi_kasv_pct / 100) ** 0.25
    
    for i in range(1, 13):
        jooksev_palk *= palk_kv_kasv
        jooksev_thi *= thi_kv_kasv
        jooksev_aja_trend = viimane_aja_trend + i
        
        y_prognoos = (coef_const + (jooksev_palk * coef_palk) + (jooksev_thi * coef_thi) + 
                      (tuleviku_intress * coef_intress) + (jooksev_aja_trend * coef_trend) + maakonna_lisa)
        
        prognoos_kvartalid.append({
            "Kvartal tulevikus": f"+{i} KV ({i*3} kuu pärast)",
            "Prognoositud ruutmeetri hind (€)": y_prognoos
        })
        
    df_simulatsioon = pd.DataFrame(prognoos_kvartalid)
    
    fig_sim, ax_sim = plt.subplots(figsize=(10, 4.5))
    ax_sim.plot(df_simulatsioon["Kvartal tulevikus"], df_simulatsioon["Prognoositud ruutmeetri hind (€)"], marker='s', linestyle='--', color='#1f77b4', linewidth=2)
    ax_sim.set_ylabel('Hind (€/m²)')
    plt.xticks(rotation=45, ha='right')
    ax_sim.grid(True, alpha=0.3, linestyle=':')
    plt.tight_layout()
    st.pyplot(fig_sim)

st.info("💡 Vihje simulaatori proovimiseks: Kui määrad palgakasvuks 0% ja inflatsiooniks 0%, näed, et hind hakkab langema. See on normaalne, sest mudel eeldab, et kinnisvarahind püsib stabiilsena vaid siis, kui ka palgad stabiilselt kasvavad!")
