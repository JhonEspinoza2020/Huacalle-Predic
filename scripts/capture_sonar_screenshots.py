"""Capture SonarQube dashboard screenshots for documentation."""
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "docs" / "sonarqube-capturas"
BASE = "http://localhost:9000"
LOGIN = "admin"
PASSWORD = "PredictHuacalle123!"
PROJECT = "predicthuacalle"

PAGES = [
    ("01-dashboard-proyecto.png", f"/dashboard?id={PROJECT}"),
    ("02-resumen-calidad.png", f"/component_measures?id={PROJECT}&metric=Coverage"),
    ("03-cobertura-tests.png", f"/component_measures?id={PROJECT}&view=list"),
    ("04-actividad-analisis.png", f"/project/activity?id={PROJECT}"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto(f"{BASE}/sessions/new", wait_until="networkidle")
        page.fill('input[name="login"]', LOGIN)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url("**/projects**", timeout=60000)

        for filename, path in PAGES:
            page.goto(f"{BASE}{path}", wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / filename), full_page=True)
            print(f"Saved {filename}")

        browser.close()

    print(f"Capturas guardadas en: {OUT}")


if __name__ == "__main__":
    main()
