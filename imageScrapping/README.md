# Image Scraper – Scam Prevention Dataset

Collect image datasets from websites (e.g. government scam prevention pages) for your practicum project.

## Features

- **Single URL**: Enter a website link and download all images on that page.
- **Bulk import**: Import a TXT file with one URL per line (row by row).
- **Output folder**: Choose where to save images; default is `downloaded_images` in the project folder.
- **UI**: Desktop app (Tkinter) – run in PyCharm with no extra server.

## Setup (PyCharm)

1. Open the project in PyCharm.
2. Use the existing virtual environment (`.venv`) or create one: **File → New → Python Virtual Environment**.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app: open `app_ui.py` and click **Run** (or right‑click → Run ‘app_ui’).

## Usage

1. **Single website**  
   Type the full URL in “Website URL”, then click **Start scraping**.  
   (You can click **Add URL** first to add it to the list, or leave the list empty and Start will use the typed URL.)

2. **Many websites**  
   - Put one URL per line in a `.txt` file.  
   - Click **Import TXT...** and select that file.  
   - Set **Output folder** and click **Start scraping**.

3. **Output**  
   All images found on the given page(s) are saved into the chosen folder.  
   Filenames are based on the image URL and an index to avoid overwriting.

## File structure

- `app_ui.py` – UI (run this in PyCharm).
- `image_scraper.py` – Scraping logic (can be used without UI).
- `requirements.txt` – Dependencies.
- `urls_sample.txt` – Example TXT for bulk import.

## Note

- Images are taken from the HTML (e.g. `<img src="...">`, `background-image`, links to image files).
- **JavaScript-rendered pages** (e.g. [BNM Financial Fraud Alerts](https://www.bnm.gov.my/financial-fraud-alerts)): if the first pass finds no images, the app automatically uses **Selenium** (Chrome in headless mode) to load the page and then scrapes all images. You need Chrome installed and `pip install selenium webdriver-manager`.
