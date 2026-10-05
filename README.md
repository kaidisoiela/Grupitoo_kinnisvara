ÄRIMÕISTED (Ilma tabelite ja andmebaasi nimedeta) 

* Kinnisvara  hind / turuväärtus: valitud piirkonnas (linnas/maakonnas) teostatud  korteriomandite ostu-müügitehingute keskmine ühe ruutmeetri (m²) hind  eurodes.
* Palgatase  (nominaalne): täisajaga töötavale inimesele arvestatud keskmine  brutotasu kuus või tunnis enne maksude mahaarvamist.
* Reaalne  ostujõud (kinnisvaraturul): suhtarv, mis näitab, mitu ruutmeetrit  kinnisvara on võimalik osta ühe keskmise brutokuupalga eest ilma laenuraha  kaasamata.
* Inflatsioon  (elukalliduse muutus): tarbija ostukorvi maksumuse muutus ajas, mida  mõõdetakse tarbijahinnaindeksi (THI) protsentuaalse muutusena võrreldes  baasaastaga.
* Turu  aktiivsus: tehingute koguarv konkreetses regioonis etteantud  ajaperioodil (kvartal/aasta). 

# 📊 Eesti Kinnisvaraturu ja Ostujõu Analüüs (2005–2026)

Tere tulemast kinnisvarahindade, keskmise brutopalga, tarbijahinnaindeksi (THI) ja eluasemelaenude intressimäärade andmeanalüüsi projekti! See infosüsteem koondab endas andmete puhastamise Pythonis, relatsioonilise andmebaasi disaini PostgreSQL-is, visuaalid Power BI-s ning interaktiivsed veebirakendused Streamlitis.

Kogu projekt ja kood on kättesaadavad GitHubi hoidlas kaustas **`Grupotoo_kinnisvara`**.

---

## 📋 Eeltingimused (Mida Sul on vaja?)
Enne alustamist veendu, et Sinu arvutisse on installeeritud järgmised programmid:
*   [Git](https://git-scm.com) (Koodi allalaadimiseks)
*   [Visual Studio Code (VS Code)](https://visualstudio.com) + Pythoni laiend (*Extension*)
*   [DBeaver Community](https://dbeaver.io) (Andmebaasi haldamiseks)
*   [PostgreSQL](https://postgresql.org) (Kohalik andmebaasiserver)
*   [Power BI Desktop](https://microsoft.com) (Raportite vaatamiseks)

---

## 🛠️ SAMM-SAMMULT PAIGALDUSJUHEND

### SAMM 1: Projekti allalaadimine GitHubist
1. Ava oma arvutis **Terminal** (Mac/Linux) või **Command Prompt / PowerShell** (Windows).
2. Liigu kausta, kuhu soovid projekti salvestada (nt `cd Desktop`).
3. Klooni projekt käsu abil:
   ```bash
   git clone https://github.com
   ```
4. Ava allalaetud kaust `Grupotoo_kinnisvara` programmis **VS Code** (*File -> Open Folder*).

---

### SAMM 2: Algandmete puhastamine Pythoniga (VS Code)
Projekt põhineb algsetel toorandmetel (failid tähisega `_raw`), mis viiakse ühisele kvartalite ja maakondade tasemele, puhastades kuupäevad, valuutad (ainult EUR) ja tekstid.

1. Veendu, Sinu sisendkaustas on olemas järgmised toorfailid:
   * **Kinnisvarastatistika:** `Kinnisvara hinnastatistika_05_08_raw.csv` kuni `_26_raw.csv`
   * **Palgainfo:** `PA004_20260922-103201_raw.csv`, `PA21_..._raw.csv`, `PA117_..._raw.csv`
   * **Tarbijahinnaindeks:** `tarbijahinna_indeks_2005_2025_raw.csv`
   * **Laenuintressid:** `Intress_EP_raw.csv`

2. Ava VS Code'is ja jooksuta järjest (klõpsates **Run All**) järgmised Jupyter Notebook (`.ipynb`) failid:
   * **`brutopalkade_import.ipynb`**
   * **`maa_ametist_andmete_import.ipynb`**
   * **`tarbijahinnaindeks_2005_2025.ipynb`**
   * **`intresside_puhastamine_tootlemine.ipynb`**

**Tulemus:** Kausta tekivad puhastatud failid: `Eesti_keskmine_palk_py_final.csv`, `maa_amet_py_final.csv`, `puhastatud_eluasemelaenud_py_final.csv` ja `thi_py_final.csv`.

---

### SAMM 3: Andmete import PostgreSQL andmebaasi (DBeaver)
1. Ava **DBeaver** ja loo ühendus oma kohaliku PostgreSQL serveriga (`localhost`).
2. Loo uus andmebaas nimega `postgres` ja selle sisse skeem `grupitoo_kv`.
3. Tee skeemi tabelite nimekirjal (*Tables*) paremklikk, vali **Import Data**, määra tüübiks *CSV* ning impordi äsja loodud neli `_final.csv` faili andmebaasi tabeliteks.

---

### SAMM 4: Tähtskeemi loomine SQL-iga
Andmete kohandamiseks analüüsimudelile loome faktitabelid ja dimensioonitabelid.

1. Ava DBeaveris SQL-redaktor (*SQL Editor*).
2. Kopeeri sinna faili **`Andmete_tootlemine_fact_dim_schema_jaoks.sql`** sisu ja käivita see.
3. Skript loob relatsioonilised andmetabelid: `dim_county`, `dim_time`, `fact_kv` ja `fact_palk`.

---

### SAMM 5: Power BI visuaalide käivitus ja seadistamine
1. Ava projekti kaustast Power BI raporti fail (.pbix).
2. Kuna R-skripti visuaal teeb otseühenduse andmebaasiga, ava R-skripti redaktori aken ja uuenda andmebaasiga ühenduse rida oma reaalse parooliga:
   ```R
   con <- dbConnect(RPostgres::Postgres(), dbname = "postgres", host = "localhost", port = 5432, user = "postgres", password = "TEIE_PAROOL")
   ```
3. Veendu, et R-visuaali *Values* sektsiooni on lohistatud andmetabelist väli **`Maakonna nimi`**.
4. Vajuta peamenüüs nuppu **Refresh** (Värskenda) – andmed ja kaardid kuvatakse ekraanile.

---

### SAMM 6: Interaktiivsete Pythoni veebiäppide käivitamine (Streamlit)
Rakendused pakuvad reaalajas simulaatoreid ja ostujõu analüüse. Äpid jooksevad lokaalses veebibrauseris.

1. Ava VS Code terminal ja paigalda vajalikud teegid:
   ```bash
   pip install streamlit pandas numpy plotly statsmodels
   ```

2. Äppide käivitamiseks sisesta terminali vastav käsk (uue äpi jaoks ava terminalis plussmärgist `+` uus aken):

   * **📊 ÄPP 1: Kinnisvaraturu põhimudel ja trendijooned**
     ```bash
     streamlit run KV_grupitöö_app_täiendatud.py
     ```
   * **📐 ÄPP 2: Kinnisvara Ostujõu Indeks (Mitu m² saab 1 kuu brutopalga eest?)**
     ```bash
     streamlit run KV_grupitöö_Sireti_app.py
     ```
   * **🗺️ ÄPP 3: Eelarve kriteeriumite ja laenukoormuse soojuskaart (Heatmap)**
     ```bash
     streamlit run KV_grupitöö_Sireti_app2.py
     ```

*Märkus: Äpi sulgemiseks või terminali vabastamiseks vajuta terminali aknas **`Ctrl` + `C`**.*

---
### 👥 Autorid ja grupiliikmed
Grupitöö on valminud õppetöö raames. Kõik õigused andmetele ja koodile kuuluvad autoritele.