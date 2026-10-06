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
4. Ava allalaetud kaust `Grupotoo_kinnisvara` arvutis File Exploreris või programmis **VS Code** (*File -> Open Folder*).

---

### SAMM 2: Algandmete puhastamine Pythoniga (VS Code)
Projekt põhineb algsetel välistest andmebaasidest alla tõmmatud toorandmetel (failid tähisega `_raw`), mis viiakse ühisele kvartalite ja (kinnisvarahindade ja brutopalkade puhul ka) maakondade tasemele, puhastades kuupäevad, numbrilised väärtused ja tekstid.

1. Veendu, et Sinu sisendkaustas on olemas järgmised toorfailid:
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

### SAMM 3: Andmete import PostgreSQL andmebaasi ning tähtskeemi loomine (DBeaver)
1. Ava **DBeaver** ja loo ühendus oma kohaliku PostgreSQL serveriga (`localhost`).
2. Ava fail **`Andmete_tootlemine_fact_dim_schema_jaoks.sql`** (*File -> Open Folder*)
3. Järgi DBeaveris SQL-redaktoris (*SQL Editor*) avanenud faili juhiseid, sh äsja loodud nelja `_py_final.csv` faili andmete korrektseks sissetõmbamiseks (pane tähele, et maa_ameti andmete impordi puhul tuleb mappida sissetõmmatava faili veerud eelnevalt loodud tabeli veergudega korrektselt).
4. Jooksuta läbi kogu skript.
5. Skript loob relatsioonilised andmetabelid: `dim_county`, `dim_time`, `fact_kv`, `fact_palk`, `fact_intressid` ja `fact_thi`.

---

### SAMM 4: Power BI visuaalide käivitus ja seadistamine
1. Ava projekti kaustast Power BI raporti fail **`KINNISVARA dashboard - final presentation.pbix`**.
2. Kuna Power BI raport teeb otseühenduse andmebaasiga, ava üleval vasakul SQL andmebaasist DBeaveriga loodud relatsioonilised andmetabelid (dim ja fact tabelid) (*Get data -> More.. -> otsi "PostgreSQL Database" ja vajuta "Connect"-> Server = Localhost, database = postgres, Advanced options all eemalda linnuke "Include relatsionship columns" eest -> vajuta "OK" -> vali kõik eelnevalt loodud dim ja fact tabelid `grupitoo_KV.` schema alt -> vajuta "Load"*))
3. Vasakult "Model View" alt kontrolli, et tähtskeemi seosed vastaksid sellele, mis olid loodud PostgreSQL andmebaasis.
4. Kuna R-skripti visuaal teeb otseühenduse andmebaasiga, ava R-skripti redaktori aken ja uuenda andmebaasiga ühenduse rida oma reaalse parooliga:
   ```R
   con <- dbConnect(RPostgres::Postgres(), dbname = "postgres", host = "localhost", port = 5432, user = "postgres", password = "TEIE_PAROOL")
   ```
5. Veendu, et R-visuaali *Values* sektsiooni on lohistatud andmetabelist väli **`Maakonna nimi`**.
6. Vajuta peamenüüs nuppu **Refresh** (Värskenda) – andmed ja kaardid kuvatakse ekraanile.

---

### SAMM 6: Interaktiivsete Pythoni veebiäppide käivitamine (Streamlit)
Rakendused pakuvad reaalajas simulaatoreid ja ostujõu analüüse. Äpid jooksevad lokaalses veebibrauseris.

1. Ava VS Code terminal ning **`Grupotoo_kinnisvara`** kaust, kus failid paiknevad (*File -> Open Folder*)

2. Ava fail **`KV_grupitöö_andmete_mudeldamine.ipynb`** ning vajuta **Run All**. Failis avatakse otse PostgreSQL andmebaasist varasemalt loodud tabelid (koodi alguses ühenduse loomisel vaata, et andmebaasi parool oleks korrektne ja toimiv), installitakse vajalikud Python teegid, tehakse esmane andmete töötlus, puhastamine ja analüüs ning salvestatakse samasse kausta koondfail **`kinnisvara_koondandmed.csv`**

3. Äppide käivitamiseks sisesta terminali vastav käsk (uue äpi jaoks ava terminalis plussmärgist `+` uus aken):

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
Grupitöö on valminud õppetöö raames. Grupitöö autoriteks on Kaidi Soiela, Siret Laaneoks, Merje Nõmmik ja Kristel Kuusik. Kõik õigused andmetele ja koodile kuuluvad autoritele.