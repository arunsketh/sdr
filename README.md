# ✈️ FAA SDR Explorer

A Streamlit web app for exploring the **FAA Service Difficulty Reports (SDR)** database — covering aircraft malfunctions, defects, and component failures reported by airlines, repair stations, and general aviation operators.

## 🚀 Deploy to Streamlit Cloud (One Click)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

1. Fork this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your forked repo
4. Set **Main file path** to `app.py`
5. Click **Deploy** ✅

---

## 🛠 Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/faa-sdr-explorer.git
cd faa-sdr-explorer

pip install -r requirements.txt

streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## 📊 Features

| Feature | Description |
|---|---|
| **Year selection** | Load SDR data for any year from 1995–present |
| **Live FAA data** | Fetches directly from FAA SDRS servers |
| **Filters** | Filter by aircraft make/model, part type, or operator |
| **Trend chart** | Monthly submission volume bar chart |
| **Aircraft breakdown** | Top makes (bar) and models (pie) |
| **Parts treemap** | Most frequently reported components |
| **Raw data table** | Column selector + CSV export |

---

## 📁 Project Structure

```
faa-sdr-explorer/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Streamlit theme & server config
└── README.md
```

---

## 🔗 Data Sources

- **FAA SDRS Portal**: https://sdrs.faa.gov
- **FAA SDR Downloads**: https://www.faa.gov/av-info/download_SDR
- **AviationDB SDR Query**: https://www.aviationdb.com/Aviation/SdrQuery.shtm

Data is sourced directly from the FAA and is in the public domain. Reports cover failures, malfunctions, and defects submitted under 14 CFR §§ 121.703, 125.409, 135.415, and 145.221.

---

## ⚠️ Disclaimer

This tool is for **research and informational purposes only**. For official regulatory use, consult [sdrs.faa.gov](https://sdrs.faa.gov) directly.
