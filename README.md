# NEPSE Floorsheet Historical Data Scraper

A Selenium-based web scraper for collecting historical floorsheet data 
from [merolagani.com](https://merolagani.com/Floorsheet.aspx) for the 
Nepal Stock Exchange (NEPSE).

---

## 📊 Data Coverage
- **Source:** merolagani.com
- **Date Range:** 2014-05-05 to present
- **Format:** CSV files (one per trading day)
- **File naming:** `YYYY_MM_DD_floorsheet.csv`

---

## 📁 CSV Structure
Each file contains:
| Column | Description |
|---|---|
| # | Row number |
| Transact. No. | Unique transaction ID (contains date) |
| Symbol | Stock symbol |
| Buyer | Buyer broker number |
| Seller | Seller broker number |
| Quantity | Shares traded |
| Rate | Price per share |
| Amount | Total transaction value |
| Date | Trading date |

---

## ⚙️ Requirements

### System Requirements
- Ubuntu 22.04 or 24.04 LTS
- Python 3.10+
- Google Chrome (latest stable)
- ChromeDriver (matching Chrome version)
- Minimum 8GB RAM (for parallel scraping)
- Minimum 30GB disk space

### AWS Recommended Setup
- Instance: **m7i.large** or **c7i.large** (free tier eligible)
- Storage: **30GB EBS**
- Region: **ap-south-1** (Mumbai) for best latency to Nepal

### Python Dependencies
-selenium:4.0.0
-webdriver-manager>=4.0.0
-pandas>=2.0.0
-lxml>=5.0.0
-html5lib>=1.1

---

## 🚀 Installation

### Step 1 — System Setup
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-venv python3-pip screen -y
```

### Step 2 — Install Chrome
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y
sudo apt install chromium-chromedriver -y
rm google-chrome-stable_current_amd64.deb
```

### Step 3 — Verify Chrome & ChromeDriver
```bash
google-chrome --version
chromedriver --version
```
⚠️ **Important:** Chrome and ChromeDriver versions must match!

### Step 4 — Python Environment
```bash
mkdir -p ~/nepse/NEPSE_data
cd ~/nepse
python3 -m venv venv
source venv/bin/activate
pip install selenium webdriver-manager pandas lxml html5lib
```

### Step 5 — If disk quota exceeded during pip install
```bash
mkdir -p ~/tmp
TMPDIR=~/tmp pip install --no-cache-dir selenium webdriver-manager pandas lxml html5lib
```

---

## 📝 Configuration

Edit these variables at top of script:

```python
DRIVE_FOLDER = "/home/ubuntu/nepse/NEPSE_data"  # save location
START_DATE   = datetime.date(2014, 5, 5)         # start date
END_DATE     = datetime.date(2026, 4, 17)        # end date
PAGE_DELAY   = 1.0   # seconds between page clicks
DATE_DELAY   = 1.5   # seconds between dates
```

---

## 🏃 Running

### Single scraper
```bash
source ~/nepse/venv/bin/activate
cd ~/nepse && python3 scraper.py 2>&1 | tee scraper.log
```

### Parallel scrapers (recommended for large date ranges)
```bash
# Run in background using screen
screen -dmS s1 bash -c 'cd ~/nepse && source venv/bin/activate && python3 sc1.py 2>&1 | tee log1.txt'
screen -dmS s2 bash -c 'cd ~/nepse && source venv/bin/activate && python3 sc2.py 2>&1 | tee log2.txt'
screen -dmS s3 bash -c 'cd ~/nepse && source venv/bin/activate && python3 sc3.py 2>&1 | tee log3.txt'
```

### Check progress
```bash
# Total files downloaded
ls ~/nepse/NEPSE_data | wc -l

# Latest file per year
for year in 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026; do
    latest=$(ls ~/nepse/NEPSE_data/${year}*.csv 2>/dev/null | tail -1)
    if [ -z "$latest" ]; then
        echo "$year: ❌ No files"
    else
        echo "$year: ✅ $latest"
    fi
done
```

### Verify data integrity
```bash
# Check first transaction of each file (should match date)
for f in ~/nepse/NEPSE_data/*.csv; do
    echo -n "$f: "
    sed -n '2p' "$f" | cut -d',' -f2
done
```

---

## ⚠️ Known Issues & Solutions

### 1. Date filter not working (most critical issue!)
**Problem:** Simple GET/POST requests ignore date filter — always returns latest data.

**Root cause:** Merolagani uses ASP.NET WebForms with JavaScript-dependent date filtering.

**Solution:** Use Selenium to control real Chrome browser — types date into form field and clicks search button.

**Verification:** Check transaction numbers — they contain the date (e.g., `201405051927097` = 2014-05-05).

---

### 2. First file of each scraper gets wrong data
**Problem:** First request always returns today's data regardless of date set.

**Root cause:** Browser session not fully initialized before first search.

**Solution:** Visit merolagani homepage 3 times before starting loop:
```python
for _ in range(3):
    driver.get("https://merolagani.com/Floorsheet.aspx")
    time.sleep(5)
    dismiss_alert(driver)
```

---

### 3. Notification popup blocking scraper
**Problem:** "Allow notifications?" popup crashes page reading.

**Solution:** Add to Chrome options:
```python
options.add_argument("--disable-notifications")
options.add_experimental_option("prefs", {
    "profile.default_content_setting_values.notifications": 2
})
```
And call `dismiss_alert()` after every major action.

---

### 4. Memory issues with parallel scrapers
**Problem:** Each Chrome instance uses ~400-600MB RAM. Running 6+ scrapers crashes server.

**Solution:**
- Use instance with minimum 8GB RAM
- Run maximum 3-4 scrapers simultaneously
- Restart Chrome every 100 dates:
```python
if i % 100 == 0:
    driver.quit()
    driver = create_driver()
```

---

### 5. Disk quota exceeded during pip install
**Problem:** `/tmp` partition is too small for large packages like numpy/pandas.

**Solution:**
```bash
mkdir -p ~/tmp
TMPDIR=~/tmp pip install --no-cache-dir pandas numpy
```

---

### 6. ChromeDriver version mismatch
**Problem:** Chrome and ChromeDriver versions must match exactly.

**Solution:** Install ChromeDriver after Chrome:
```bash
sudo apt install chromium-chromedriver -y
```
Or use webdriver-manager to auto-match versions.

---

### 7. Page navigation failures
**Problem:** Some pages fail to load — `🚩 Page X failed`.

**Root cause:** Heavy pages (recent data has 150-200 pages) timeout.

**Solution:** These are minor — script skips failed pages and continues. Missing ~2-3 pages per day is acceptable loss.

---

### 8. IP rate limiting
**Problem:** Running too many parallel scrapers causes merolagani to rate limit or block IP.

**Solution:**
- Run maximum 3 scrapers simultaneously
- Keep `PAGE_DELAY = 1.0` and `DATE_DELAY = 1.5`
- If blocked, wait 30 minutes and restart

---

## 📊 Performance

| Setup | Files/hour | Notes |
|---|---|---|
| 1 scraper | ~20-25 | Safe, reliable |
| 3 scrapers | ~60-70 | Recommended |
| 6 scrapers | ~100+ | Risk of IP block |

**Note:** Recent years (2022-2026) are much slower because each day has 100-200 pages vs 5-20 pages for older years.

---

## 💾 Downloading Data

### Via AWS S3
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Sync to S3
aws s3 sync ~/nepse/NEPSE_data s3://your-bucket-name/
```

### Via WinSCP (Windows)
1. Download WinSCP from winscp.net
2. Protocol: SFTP
3. Host: your EC2 public IP
4. Username: ubuntu
5. Key file: your .ppk file
6. Navigate to `/home/ubuntu/nepse/NEPSE_data`

---

## 🔄 Resume Capability

Script automatically skips already downloaded files:
```python
def already_downloaded(date_str):
    filename = date_str.replace("-", "_") + "_floorsheet.csv"
    return os.path.exists(os.path.join(DRIVE_FOLDER, filename))
```

If script crashes, just restart — it continues from where it left off!

---

## 📅 Splitting Date Ranges for Parallel Scraping

```python
# sc1.py
START_DATE = datetime.date(2014, 5, 5)
END_DATE   = datetime.date(2016, 12, 31)

# sc2.py
START_DATE = datetime.date(2017, 1, 1)
END_DATE   = datetime.date(2019, 12, 31)

# sc3.py
START_DATE = datetime.date(2020, 1, 1)
END_DATE   = datetime.date(2022, 12, 31)

# sc4.py
START_DATE = datetime.date(2023, 1, 1)
END_DATE   = datetime.date(2026, 4, 17)
```

All scripts save to same `NEPSE_data` folder — no conflicts since filenames are date-based!

---

## 🛠️ AWS Setup Guide

1. Launch EC2 instance (m7i.large recommended)
2. Create default VPC if none exists
3. Add 30GB EBS storage
4. Allow SSH in security group
5. Connect via EC2 Instance Connect (browser terminal)
6. Follow installation steps above

**Estimated cost:** ~$0.10/hour × 24 hours = ~$2.40 for full historical scrape

---

## 📌 Important Notes

- Market is closed on weekends and Nepali public holidays
- Script automatically detects closed days (0 records = closed)
- Transaction numbers contain date: `YYYYMMDDXXXXXXX`
- Data goes back to approximately **2014** on merolagani
- Recent data (2022+) has significantly more transactions per day
- Always verify data by checking transaction numbers match file dates

---

## 🤝 Contributing

Feel free to contribute improvements:
- Better error handling
- Async scraping
- Database integration
- Data validation scripts

---

## 📄 License

MIT License — free to use for research and personal projects.

---

## ⚡ Quick Start Summary

```bash
# 1. Install dependencies
sudo apt update && sudo apt install python3-venv python3-pip chromium-chromedriver -y
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y

# 2. Setup Python
mkdir -p ~/nepse/NEPSE_data && cd ~/nepse
python3 -m venv venv && source venv/bin/activate
pip install selenium pandas lxml html5lib

# 3. Run scraper
python3 scraper.py 2>&1 | tee scraper.log

