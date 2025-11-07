# monitor_github.py
import os, json, requests, time
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DATA_FILE = Path("seen_jobs.json")
URLS_FILE = Path("urls.txt")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def load_seen():
    if DATA_FILE.exists():
        try:
            return set(json.loads(DATA_FILE.read_text()))
        except Exception:
            return set()
    return set()

def save_seen(seen):
    DATA_FILE.write_text(json.dumps(sorted(list(seen)), indent=2))

def get_search_urls():
    if not URLS_FILE.exists():
        return []
    return [line.strip() for line in URLS_FILE.read_text().splitlines() if line.strip() and not line.strip().startswith("#")]

def normalize_job_url(url):
    if url.startswith("//"):
        url = "https:" + url
    return url.split("?")[0].rstrip("/")

def find_jobs_on_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    jobs = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").strip()
        if any(k in href.lower() for k in ["/job", "/jobs", "apply", "careers"]) or ("job" in text.lower()):
            job_url = normalize_job_url(href)
            if job_url.startswith("http"):
                jobs.add(job_url)
    return list(jobs)

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Telegram not configured. Skipping send.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": False}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print("Telegram API returned", r.status_code, r.text)
    except Exception as e:
        print("Telegram send error:", e)

def main():
    print("[*] Start check")
    seen = load_seen()
    urls = get_search_urls()
    if not urls:
        print("[!] No URLs found in urls.txt. Add search-result URLs (one per line).")
        return
    new_jobs = []
    for u in urls:
        print(f"Checking: {u}")
        found = find_jobs_on_page(u)
        for job in found:
            if job not in seen:
                new_jobs.append(job)
                seen.add(job)
                # send message per job
                send_telegram(f"New job found:\n{job}")
                # polite pause
                time.sleep(1)
    if new_jobs:
        print(f"[+] {len(new_jobs)} new job(s) found.")
    else:
        print("[-] No new jobs found.")
    save_seen(seen)
    print("[*] Done")

if __name__ == "__main__":
    main()
