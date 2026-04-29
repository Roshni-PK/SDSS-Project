# SMART DECISION PLATFORM

A startup-style Flask web app that recommends top retail products from CSV data using ratings, review signals, and user preferences.

## Features
- Domain homepage with clickable cards (Retail active, others coming soon)
- Retail recommendation form
- Intelligent ranking logic with usage and priority boosts
- Top 3 recommendation cards with rating stars + explanations
- Basic session authentication (signup/login/logout)

## Run Locally
1. Create environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start app:
   ```bash
   python main.py
   ```
3. Open:
   - `http://127.0.0.1:5000/`

## Project Structure
```
SDSS-Project/
├── main.py
├── requirements.txt
├── README.md
├── data/
│   └── products.csv
├── static/
│   └── css/
│       └── styles.css
└── templates/
    ├── base.html
    ├── home.html
    ├── login.html
    ├── signup.html
    ├── retail.html
    └── results.html
```
