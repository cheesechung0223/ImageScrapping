# Scam Prevention Project – Planning Checklist

**Project:** Analyzing Visual and Textual Features for Scam Prevention  
**Goal:** Collect images → Extract visual & textual cues → Analyze & visualize → Support scam awareness

---

## Phase 1: Data collection

- [ ] **1.1** List target agencies/sources (e.g. BNM, PDRM, banks, Amaran Scam, etc.)
- [ ] **1.2** Collect URLs of scam-prevention pages (save in `urls_sample.txt` or similar)
- [ ] **1.3** Run Image Scraper for each URL; use a **unique folder name** per site (or leave auto)
- [ ] **1.4** Organise output: one folder per website under `downloaded_images/`
- [ ] **1.5** Manually remove bad/duplicate images if needed
- [ ] **1.6** (Optional) Build a simple inventory: list of folders, image count per source, date collected

**Deliverable:** A clean image dataset in folders by source, ready for analysis.

---

## Phase 2: Set up analysis environment

- [ ] **2.1** Decide: Google Vision API **or** open-source (e.g. Tesseract + object detection)
- [ ] **2.2** If Google Vision: create GCP project, enable Vision API, get API key / service account
- [ ] **2.3** Install SDK: `pip install google-cloud-vision` (or Tesseract + `pytesseract` / EasyOCR)
- [ ] **2.4** Create a small script or Jupyter notebook that:
  - Loads one image
  - Calls Vision (or OCR) and prints labels + text
- [ ] **2.5** Run on 2–3 sample images to confirm pipeline works

**Deliverable:** Working pipeline (code + env) that returns object labels and/or OCR text for an image.

---

## Phase 3: Batch feature extraction

- [ ] **3.1** Write a script/module that:
  - Iterates over all images in your dataset (or per folder)
  - Calls Vision API (or OCR + object detection) for each image
  - Saves results in a structured format (e.g. JSON or CSV per image or per folder)
- [ ] **3.2** Define what to extract (align with project goals):
  - **Visual:** object labels, icon/symbol categories, colours, layout (if needed)
  - **Textual:** full OCR text, or key phrases (e.g. “don’t share OTP”, “call 997”)
- [ ] **3.3** Run batch extraction on full dataset
- [ ] **3.4** Store outputs in a dedicated folder (e.g. `extraction_results/`) and keep filenames linked to source folder/image

**Deliverable:** A dataset of extracted features (visual + textual) per image/source.

---

## Phase 4: Align with scam markers / tips (literature)

- [ ] **4.1** Read Kubilay et al. (2023) and list “scam markers” or “scam tips” they use
- [ ] **4.2** (Optional) Add 1–2 more references (e.g. Baesens et al., or local guidelines) and list cues
- [ ] **4.3** Create a short mapping: which of your extracted **visual** and **textual** cues match these markers/tips?
- [ ] **4.4** Note gaps: what agencies often show vs. what literature says is useful

**Deliverable:** A simple table or list: “Extracted cue” ↔ “Scam marker/tip from literature”.

---

## Phase 5: Analytics & visualisation

- [ ] **5.1** Choose 2–3 analysis angles, e.g.:
  - Frequency of visual cues (e.g. warning icons, colours) across agencies
  - Frequency of key text phrases (e.g. “997”, “don’t share”, “report”)
  - Comparison: which agencies use which cues most?
- [ ] **5.2** Build visualisations (in Jupyter or Python scripts), e.g.:
  - Bar charts / heatmaps of cue usage by source
  - Word clouds or keyword frequency from OCR text
  - Simple summary stats (e.g. “X% of images contain hotline number”)
- [ ] **5.3** (If required) Propose a **summarisation** idea: e.g. one-page “scam alert summary” format, or dashboard layout, and show a mock or example

**Deliverable:** A set of charts + short written interpretation; optional: summarisation mock-up.

---

## Phase 6: Report & presentation

- [ ] **6.1** Write up: method (data collection, Vision/OCR, feature list), results (tables + figures), discussion (alignment with literature, limitations)
- [ ] **6.2** Export key figures and tables for report/appendices
- [ ] **6.3** Prepare practicum presentation (slides) with: aim, method, main results, implications for scam awareness
- [ ] **6.4** List limitations and future work (e.g. more agencies, other languages, real-time alerts)

**Deliverable:** Practicum report + presentation.

---

## Quick reference – suggested tools

| Task | Suggested tool |
|------|-----------------|
| Collect images | Your Image Scraper (PyCharm) |
| Try Vision/OCR on a few images | Jupyter notebook |
| Batch extraction script | PyCharm (.py modules) |
| Analysis & charts | Jupyter or PyCharm + matplotlib/ seaborn |
| Report writing | Word/Google Docs; figures from Jupyter/PyCharm |

---

## References (from project brief)

- Google Vision API: https://cloud.google.com/vision?hl=en  
- Kubilay et al. (2023). Can you spot a scam? Measuring and improving scam identification ability. *Journal of Development Economics*, 165, 103147.  
- Baesens et al. (2015). *Fraud analytics using descriptive, predictive, and social network techniques*. John Wiley & Sons.

---

*You can tick the boxes as you complete each step. Good luck with your practicum.*
