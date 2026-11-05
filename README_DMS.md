# DMS - Developments Management System

Sistema di gestione progetti, task, idee e discussioni di sviluppo ingegneristico, realizzato fedelmente secondo la specifica del documento **`DMS (Developements Mng Syst) - LAYOUT 2.docx`**.

---

## ⬇️ Download Diretto (Ultima Versione)

Puoi scaricare direttamente l'eseguibile aggiornato all'ultimo commit da questo link diretto:
👉 **[Scarica DMS.exe (Ultima Versione)](https://raw.githubusercontent.com/davidegalbersanini/DMS/main/DMS.exe)**

---

## 🚀 Come Avviare l'Applicazione su Qualsiasi PC (Zero Installazione)

Hai a disposizione l'eseguibile unico autonomo:
```text
DMS.exe
```

👉 **Cosa devi dare a un collega che ha un PC vergine?**
* Puoi inviargli semplicemente il file **`DMS.exe`** (oppure copiare `DMS.exe` sulla cartella di rete condivisa).
* Il collega deve solo fare **doppio clic su `DMS.exe`**.
* **Non serve installare Python, non servono permessi di amministratore e non serve configurare nulla sul PC.**

---

## 🌐 Configurazione Cartella di Rete Condivisa (Multi-Utente)

* **Al primo avvio**: `DMS.exe` mostra una finestra che chiede dove risiede la cartella di rete comune (es. `\\server\condivisa\DMS\` oppure un disco di rete `Z:\DMS\`).
* **In qualsiasi momento**: Puoi cambiare il percorso cliccando sul pulsante **`Cartella di Rete`** in alto a destra.
* **Tutti i dati e i file sono centralizzati**:
  * Il database SQLite comune `dms_database.db`.
  * La cartella dei documenti `FILES/` (dove ogni attività ha la sua sottocartella `FILES/00001/`, `FILES/00002/`, ecc., apribile da tutti tramite il tasto **`FOLDER`**).

---

## 📋 Funzionalità Principali

### 1. Vista Principale (Dashboard & Tabella)
* **VIEW SETUP**: Selettori rapidi per includere/escludere tipi (*Project, Task, Idea, Discussion*) e stati normalmente nascosti (*Closed, Cancelled, On Hold, Rejected*).
* **Filtri Avanzati & Ricerca Globale**: Filtra per anno (2027–2031), Urgenza, Beneficiary, Cluster, PM, Proto n., oppure digita qualsiasi parola nella casella di ricerca globale.
* **Pulsanti Azione**:
  * **`+ NEW ID`**: Genera all'istante una nuova riga con codice progressivo a 5 cifre.
  * **`Azioni in scadenza (5gg)`**: Mostra le attività con azioni aperte che scadono entro i prossimi 5 giorni (le righe urgenti vengono evidenziate visivamente in arancione/rosso).
  * **`Esporta Dati`**: Scarica l'intero database (o i dati filtrati) in formato **Excel `.xlsx`** nativo.
  * **`Print Report`**: Genera un **PDF A4 orizzontale (Landscape)** pulito e impaginato delle attività filtrate.
  * **`Ordina`**: Ordina per Urgenza, Rilevanza, o primo anno attivo.
* **Inline-Editing**: Tutte le celle principali (Titolo, Urgenza, Rilevanza, PM, PE, Beneficiary, Cluster, Basic/Kit, Proto, Anni, Status) sono modificabili al volo direttamente nella tabella.
* **Tasti di Riga**:
  * **`OPEN`**: Apre la finestra di dettaglio del singolo ID.
  * **`CANCEL`**: Mette l'attività in stato Cancelled/Rejected.
  * **`FOLDER`**: Apre la cartella Windows dell'attività in Esplora Risorse (creandola automaticamente se non esiste).

### 2. Finestra Singolo ID
* **Navigazione Rapida**: Frecce `← Precedente` e `Successivo →` per sfogliare i record tra quelli filtrati senza chiudere la finestra.
* **Regole dinamiche Type → Status**: Il menu a tendina dello stato si adatta dinamicamente alle regole della specifica:
  * *Discussion*: `1) To Start`, `2) On Going`, `3) To Promote`, `4) Closed /Canceled`, `5) On hold`
  * *Idea*: `1) Draft`, `2) Submitted`, `3) Rejected (1)`, `4) To be Quoted`, `5) Approved`, `6) Rejected`, `7) Rejected 2`, `8) On Hold`
  * *Project / Task*: `1) Planned`, `2) Scheduled`, `3) On Going`, `4) To be closed`, `5) Closed/Cancelled`, `6) On Hold`
* **Drivers, Streams e Platforms**: Selezione con comodi checkbox multipli.
* **4 Tab Organizzati**:
  1. **Execution**: Note & Actions (Rich text con colori ed evidenziatori), Plan & Deliverables, Supplier, Tabella Team dinamica (*Function* + *N. Surname*).
  2. **Master Data**: Codici Clarity, ISPI, Other ID, BCR, CR, QSD, NDC, WBS Code/Description, Booking n. (rich text), RDA Record (rich text).
  3. **Action Log**: Tabella azioni con Action, Owner, Status (*OPEN, ON GOING, NEXT, ON HOLD, CLOSED*) e Target Date (con evidenziazione scadenze entro 5 giorni).
  4. **AFC (Financials)**: Scelta `AFC 1` e `AFC 2` e matrice costi/ore (*ENG HRS, OTHER HRS, NRC VENDOR*) tra Full Life e 2027 (*BDG, ACTUAL, REMAINING, FORECAST*).

### 3. Gestione Liste & Anagrafiche
Accessibile con un click dal pulsante in alto a destra **`Gestione Liste & Anagrafica`**:
* Permette di aggiungere, modificare o eliminare voci per:
  * **Persone** (utilizzate in comune per PM, PE, Action Owner e Team)
  * **Funzioni Team**
  * **Drivers**
  * **Streams**
  * **Platforms**
  * **Beneficiari**
  * **Clusters**
  * **Prototipi**
