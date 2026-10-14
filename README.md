# KD Kindle Dashboard

An old Kindle 4 turned into an e-ink dashboard showing Dubai gold rates and AED / INR / USD exchange rates, refreshed every hour.

| Part | Where | What it does |
|---|---|---|
| `generator/build.py` | GitHub Actions, hourly | Fetches rates and draws each page as a 600 x 800 PNG |
| `config.json` | this repo | Which pages show and in what order |
| `output` branch | this repo | Latest pages, read by the Kindle |
| `kindle/kddash/` | Kindle `extensions` folder | KUAL app that downloads, shows and flips pages |

Kindle buttons: page turn or 5-way left/right to flip, centre press to refresh now, Home/Back/Menu to exit.
