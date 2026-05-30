# ADAB Tech Nigeria Ltd — Startup & Funding Roadmap

This document serves as the master checklist and roadmap for the legal, business, and funding milestones of **ADAB Tech Nigeria Ltd** and the **Hausa AI** project. 

---

## 1. Legal Incorporation & Structuring

To position the company for venture capital (including Y Combinator) and institutional research grants, we will establish a dual-corporate structure (Delaware C-Corp parent with a Nigerian subsidiary).

- [ ] **Nigerian CAC Registration: ADAB Tech Nigeria Ltd**
  - **Objective:** Register a local entity with the Corporate Affairs Commission (CAC) to facilitate local operations, hire local talent, and qualify for Nigerian government technology grants.
  - **Next Steps:**
    - Reserve the name *ADAB Tech Nigeria Ltd* on the CAC portal.
    - Prepare association articles detailing the applied computational linguistics and NLP focus.
    - Appoint initial directors and shareholders.
- [ ] **Delaware C-Corp Incorporation (US Parent)**
  - **Objective:** Establish a US entity to receive venture capital funding, protect IP, and satisfy Y Combinator's default legal requirement.
  - **Next Steps:**
    - **GitHub Student Developer Pack Discount:** Redeem the GitHub Developer Pack coupon for startup incorporation.
    - **Stripe Atlas / Clerky:** Use the developer pack discount to reduce the Atlas fee (normally $500) to a lower or waived rate to incorporate.
    - Set up a US corporate bank account (e.g., via Mercury or Wise) linked to the Delaware C-Corp.

---

## 2. Venture Accelerator & Pitching

- [ ] **Y Combinator (YC) Application**
  - **Objective:** Apply to YC with Hausa AI to secure pre-seed funding ($500k standard terms) and access the global startup network.
  - **Next Steps:**
    - Draft the application on the YC founder portal.
    - **Key Angle:** Highlight the huge under-served market of 80M+ Hausa speakers and our proprietary, linguistically sovereign, edge-optimized speech synthesis technology.
    - Record the 1-minute founder video demonstrating the local FastAPI + React web interface with the custom VITS multi-speaker voice.
    - Submit the application before the deadline.

---

## 3. Non-Dilutive Funding & Research Grants

As a PhD candidate researching African NLP and computational linguistics, you are highly qualified for non-dilutive government and scientific grants.

- [ ] **US National Science Foundation (NSF) SBIR/STTR Grants**
  - **Objective:** Secure up to $275,000 in Phase I funding (and up to $1.1M in Phase II) for research and development of low-resource African speech technology.
  - **Next Steps:**
    - Register the Delaware C-Corp on SAM.gov (requires a Unique Entity ID).
    - Identify a hosting academic partner (if pursuing STTR) or apply as a small business (SBIR).
    - Draft the project description emphasizing the innovation of *Litvinova's Right-to-Left Tonal Melody heuristics* applied to VITS.
- [ ] **Nigerian Government Technology Funding**
  - **Objective:** Secure local grants or partnership funding from agencies under the Federal Ministry of Communications, Innovation and Digital Economy.
  - **Next Steps:**
    - Monitor NITDA (National Information Technology Development Agency) grant openings.
    - Explore the *3MTT (Three Million Technical Talent)* program and local innovation support initiatives for indigenous language AI tools.

---

## 4. Technical Alignment & Execution

To support the business goals, the core technical tasks must be completed on schedule to serve as demo material for YC and grant proposals.

- [x] **Linguistic Hardening (Completed)**
  - Normalized hooked orthography (`ɗ`, `ɓ`, `ƙ`, `ƴ`) and integrated standard R-to-L tone heuristics.
  - Tested and achieved a 96.67% sovereign linguistic score on the validation test suite.
- [ ] **Local Model Deployment**
  - [ ] Complete training Epochs (1,000 epochs goal) on the active `hausa-ai-train-vm` instance.
  - [ ] Export the final multi-speaker VITS model weights (`best_model.pth`) to ONNX format.
  - [ ] Run INT8 quantization using `flywheel_optimizer.py` to reduce model footprint to ~250MB.
  - [ ] Sync the optimized model files to the local `models/vits/` directory.
- [ ] **Frontend & Dashboard Release**
  - [ ] Connect the frontend UI to the local VITS FastAPI websocket stream.
  - [ ] Verify the *Axiom Trace / Hanya* dashboard displays correct syllable-level pitch markings for live syntheses.
