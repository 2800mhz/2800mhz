#!/usr/bin/env python3
"""
GitHub Traffic Tracker
Çalıştırınca GitHub API'den clone/view verisini çeker,
daha önce kaydedilmemiş günleri kümülatif JSON'a ekler,
sonra README'yi günceller ve commit + push atar.
"""

import os
import json
import datetime
import subprocess
import requests

# --- CONFIG ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USER  = "2800mhz"
DATA_FILE    = "traffic_data.json"
README_FILE  = "README.md"

REPOS = [
    "2800mhz",
    "imperial-ai-archive-backend",
    "nasal-nation-stats",
    "panoramic-dream-weaver",
    "cell-lab",
    "RTM-2",
]

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

# --- FETCH ---
def fetch_traffic(repo):
    clones_url = f"https://api.github.com/repos/{GITHUB_USER}/{repo}/traffic/clones?per=day"
    views_url  = f"https://api.github.com/repos/{GITHUB_USER}/{repo}/traffic/views?per=day"

    cr = requests.get(clones_url, headers=HEADERS)
    vr = requests.get(views_url,  headers=HEADERS)

    clones_by_day = {}
    for item in cr.json().get("clones", []):
        day = item["timestamp"][:10]
        clones_by_day[day] = {"clones": item["count"], "unique_clones": item["uniques"]}

    views_by_day = {}
    for item in vr.json().get("views", []):
        day = item["timestamp"][:10]
        views_by_day[day] = {"views": item["count"], "unique_views": item["uniques"]}

    return clones_by_day, views_by_day

# --- LOAD / SAVE ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    # İlk çalıştırma
    return {
        "repos": {},
        "seen_days": {},   # repo -> [kayıtlı günler]
        "totals": {},      # repo -> {clones, unique_clones, views, unique_views}
        "last_updated": None,
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --- UPDATE README ---
def update_readme(data):
    totals = data["totals"]
    total_clones = sum(v.get("clones", 0)        for v in totals.values())
    total_unique = sum(v.get("unique_clones", 0) for v in totals.values())
    total_views  = sum(v.get("views", 0)         for v in totals.values())
    last_updated = data["last_updated"]

    block = f"""<!-- TRAFFIC_START -->
<p align="center">
  <img src="https://img.shields.io/badge/Total%20Clones-{total_clones}-4479A1?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Unique%20Cloners-{total_unique}-2ea44f?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Total%20Views-{total_views}-orange?style=for-the-badge" />
</p>
<p align="center"><sub>~ Auto-updated: {last_updated}</sub></p>

<!-- TRAFFIC_END -->"""

    with open(README_FILE, encoding="utf-8") as f:
        content = f.read()

    if "<!-- TRAFFIC_START -->" in content:
        import re
        content = re.sub(
            r"<!-- TRAFFIC_START -->.*?<!-- TRAFFIC_END -->",
            block,
            content,
            flags=re.DOTALL,
        )
    else:
        content += "\n\n" + block

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("[OK] README güncellendi.")

# --- GIT ---
def git_push():
    subprocess.run(["git", "add", DATA_FILE, README_FILE], check=True)
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True
    )
    if result.returncode == 0:
        print("[i]  Değişiklik yok, push atlanıyor.")
        return
    subprocess.run(["git", "commit", "-m", "chore: update traffic stats [skip ci]"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("[OK] Push tamam.")

# --- MAIN ---
def main():
    if not GITHUB_TOKEN:
        print("[!] GITHUB_TOKEN bulunamadı! export GITHUB_TOKEN=ghp_xxx")
        return

    data = load_data()

    # Eksik anahtarları garantiye al
    data.setdefault("seen_days", {})
    data.setdefault("totals", {})

    new_days_total = 0

    for repo in REPOS:
        print(f"[>] {repo} çekiliyor...")
        clones_by_day, views_by_day = fetch_traffic(repo)

        seen = set(data["seen_days"].get(repo, []))

        if repo not in data["totals"]:
            data["totals"][repo] = {"clones": 0, "unique_clones": 0, "views": 0, "unique_views": 0}

        t = data["totals"][repo]
        new_days = 0

        all_days = set(clones_by_day.keys()) | set(views_by_day.keys())
        for day in sorted(all_days):
            if day in seen:
                continue  # Bu günü zaten saydık, atla
            seen.add(day)
            new_days += 1

            c = clones_by_day.get(day, {})
            v = views_by_day.get(day, {})
            t["clones"]        += c.get("clones", 0)
            t["unique_clones"] += c.get("unique_clones", 0)
            t["views"]         += v.get("views", 0)
            t["unique_views"]  += v.get("unique_views", 0)

        data["seen_days"][repo] = list(seen)
        print(f"   → {new_days} yeni gün eklendi. Toplam: {t['clones']} clone, {t['views']} view")
        new_days_total += new_days

    data["last_updated"] = datetime.date.today().isoformat()
    save_data(data)
    print(f"\n[S] JSON kaydedildi. Toplam {new_days_total} yeni gün işlendi.")

    update_readme(data)
    git_push()

if __name__ == "__main__":
    main()