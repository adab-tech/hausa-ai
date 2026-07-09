# Y Combinator (YC) Application Answers Draft

**Company Name:** ADAB Tech / Hausa AI  
**Founder:** Adamu Danjuma Abubakar  
**Domain:** Applied AI, Speech Synthesis, African Natural Language Processing (NLP)

---

## 1. What is your company going to make?
We are building **Hausa AI**, the first sovereign, edge-optimized conversational AI stack for West African languages, starting with a linguistically-grounded Text-to-Speech (TTS) engine for the 80 million Hausa speakers in Nigeria, Niger, and West Africa. 

Unlike general cloud-based AI tools, Hausa AI runs entirely offline — our shipped multi-speaker model is a **73.5 MB ONNX file that synthesizes in real time on a laptop CPU**, no quantization required. It incorporates strict orthographic validation for Hausa hooked letters (`ɓ`, `ɗ`, `ƙ`, `ƴ`) and enforces native right-to-left pitch accent rules (High/Low tones), producing natural, culturally aligned human-like dialogue instead of robotic or foreign-accented speech. This is not a plan: the engine is deployed in our FastAPI + React stack today, with 8 native voices fine-tuned on Google's WAXAL corpus — to our knowledge the first WAXAL-trained TTS built by a native speaker of the target language.

---

## 2. Why did you choose this idea? What is your unique insight?
As an applied computational linguist and PhD candidate in African NLP, I realized that global tech companies view African languages as a "low-resource" afterthought. Standard TTS models (like Meta's MMS or general cloud APIs) treat Hausa as a flat phonetic transcription. 

However, Hausa is a **tonal language** with phonemic vowel lengths. Without proper tone mapping, a synthesized word like *fada* is ambiguous: it can mean *fádà* (palace/court) or *fádaá* (speaking/fighting). Existing models also strip native Unicode hooked letters (resolving `ɗan` to `dan`), completely altering the meaning. 

Our unique insight is that **linguistic sovereignty drives model accuracy** — and we have now demonstrated it end-to-end. We fine-tune a multi-speaker VITS-family (Piper) architecture in **grapheme mode with a custom 42-symbol Hausa alphabet** (espeak-ng has no Hausa voice — we made the orthography itself the model's input, so hooked letters can never be flattened), layered with our orthography normalizer and *Litvinova's Right-to-Left tonal melody heuristics*. When Meta's MMS Hausa model was auditioned as a possible base, our native-speaker evaluation rejected it — our from-WAXAL voices beat it. We also **doubled our usable training corpus (2.83 h → 6.03 h) from the same source recordings** via a character-level forced-alignment segmentation method robust to ASR errors — a data-economics edge every "low-resource" competitor lacks. The shipped model is 73.5 MB — edge deployment without quantization, eliminating cloud latency and API overhead in infrastructure-constrained regions.

---

## 3. What is the market size?
Hausa is spoken by over **80 million people** across West Africa, predominantly in Northern Nigeria and Niger, making it the most widely spoken Chadic language and a major lingua franca of commerce. 

Nigeria alone is the largest economy in Africa with a population of 220M+ projected to double by 2050. The market for localized voice solutions in banking, customer care (IVR), healthcare outreach, and offline education is massive. Because internet bandwidth is expensive and erratic in Nigeria, our local-first, offline-compatible edge engine is the only feasible way to scale conversational AI to the next 100 million internet users in West Africa.

---

## 4. Who are the founders and what are their backgrounds?
*   **Adamu Danjuma Abubakar** (Founder & CEO): An applied computational linguist researching African NLP and its application to AI. I have a rich background in literature, linguistics, and cultural studies, and I am currently a PhD candidate. I lead the engineering of our G2P normalization pipeline and VITS multi-speaker training.
*   **Unique fit:** Building high-quality speech engines for West African languages requires combining advanced machine learning (VITS, ONNX optimization) with deep phonological domain expertise. Very few teams possess this intersection.

---

## 5. How will you make money?
We operate a B2B / B2G hybrid business model:
1.  **On-Premise Enterprise Licensing:** Annual licenses for banks, fintechs, and telecom companies in Nigeria to run localized customer service bots and Interactive Voice Response (IVR) systems on their own servers with zero API costs.
2.  **SDK & Cloud API:** A low-cost API/SDK for developers building localized apps, charged per second of synthesized audio.
3.  **Local-First Devices:** Partnering with educational organizations and government agencies to pre-install our local synthesis and LLM engines on offline devices (e.g. tablet-based learning in rural schools).

---

## 6. How is what you are doing new? Who are your competitors?
Our competitors are:
1.  **Big Tech (Meta MMS, Google Cloud TTS):** These are massive, general-purpose models. They are cloud-dependent, suffer from robotic accents, and fail on phonetic hooks and tonal rules.
2.  **Multilingual Startups (YourTTS derivatives):** These models suffer from **voice leakage**, where the voice embeddings of European base languages (English/Portuguese) bleed into the Hausa audio, causing a noticeable foreign accent.

**Our Advantage:** 
*   **Linguistic Integrity:** 100% hook validation and R-to-L tone mapping; grapheme-native training means the model literally cannot strip a hooked letter.
*   **Zero Leakage:** Fine-tuned on WAXAL native speaker profiles, every quality gate judged by a native-speaker ear — including the head-to-head audition where our voices beat Meta MMS-Hausa.
*   **Edge-Native:** 73.5 MB ONNX running real-time on commodity CPUs — shipped, not projected.
*   **Data Multiplier:** proprietary alignment pipeline that more than doubled training hours from unchanged source audio (documented in our technical report).
