# Murya Hausa speech recognition evaluation

20 November 2026

**Keep Omnilingual ASR CTC 300M v2 as the lead evaluation candidate.** On the 12 FLEURS clips, it had fewer word errors and lower median CPU processing time. Both candidates produced unreliable names and numbers for a live conversation.

## Models and method

- [Whisper Base](https://huggingface.co/Systran/faster-whisper-base/tree/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66) and [a-deji Whisper Small Hausa](https://huggingface.co/a-deji/whisper-small-hausa/tree/3aad5116188de6913bfdb579a2af8e0ac04caba5) were run on the original four clips.
- [CLEAR Global Whisper Small Hausa](https://huggingface.co/CLEAR-Global/whisper-small-clearglobal-hausa-asr-1.0.0/tree/287455a8ff93f285eb51d16c2f2c042e060d84fb) used Transformers 4.57.6 and PyTorch 2.10.0 on CPU. Whisper was set to transcribe in Hausa with greedy decoding.
- [Omnilingual ASR CTC 300M v2 ONNX export](https://huggingface.co/EmreAkgul/omniASR-CTC-300M-v2-ONNX/tree/6c1096d65763f1d268a7ed61fe8874596f0a4eb8) used ONNX Runtime 1.32.0 on CPU. The export and tokenizer passed the publisher's SHA-256 checks.
- Both systems received identical mono 16 kHz WAVs and used four CPU threads. Timings cover local transcription with each model already loaded. Browser, network, voice activity detection, and chat response time were outside the measurement.
- Word error rate counts insertions, deletions, and substitutions. Scoring case-folds and ignores punctuation while preserving hooked letters. The separate number score accepts specified digit and spoken forms and ignores joined word boundaries. Name and hooked-word scores require exact matches after tokenization. The scores use raw transcripts before Gyara.

## Original four clips

The smoke test used two human recordings from the [WAXAL Hausa test split](https://huggingface.co/datasets/google/WaxalNLP) and two synthetic examples from the [Murya landing page](https://murya.ng/). There were 36 reference words.

| Model | Runtime | Word errors | Median processing time |
| --- | --- | ---: | ---: |
| Whisper Base (Systran) | CTranslate2 CPU INT8 | 37/36 | 16.59 s |
| a-deji Whisper Small Hausa | Transformers CPU FP32 | 19/36 | 5.94 s |
| CLEAR Global Whisper Small Hausa | Transformers CPU FP32 | 17/36 | 6.07 s |
| Omnilingual ASR CTC 300M v2 | ONNX Runtime CPU FP32 | 16/36 | 5.81 s |

The separate 1.20-second Malama Asabe number probe said **goma sha huɗu**. CLEAR Global returned **boma shago**, and Omnilingual returned **wo mas shawuɗu**. This probe is excluded from both main tables.

## FLEURS Hausa comparison

The [FLEURS Hausa test split](https://huggingface.co/datasets/google/fleurs/viewer/ha_ng/test) supplied 12 selected recordings and their published references under CC BY 4.0, pinned to revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`. The clips contain 237 reference words. FLEURS labels 11 clips female and one male. The sample measures read speech and has one reference word each for **ɓ** and **ƴ**.

| Measure | CLEAR Global | Omnilingual 300M v2 |
| --- | ---: | ---: |
| Word errors | 105/237 (44.3%) | 82/237 (34.6%) |
| Exact words containing hooked consonants | 10/19 | 9/19 |
| Number targets matched | 2/4 | 1/4 |
| Exact name targets matched | 0/8 | 0/8 |
| Median processing time | 8.62 s | 5.77 s |
| Observed processing time range | 6.82–16.26 s | 4.03–14.35 s |

| Hooked consonant in the reference word | CLEAR Global | Omnilingual 300M v2 |
| --- | ---: | ---: |
| ɓ | 0/1 | 1/1 |
| ɗ | 1/5 | 2/5 |
| ƙ | 8/12 | 6/12 |
| ƴ | 1/1 | 0/1 |

The number targets were 19, 40,000, 150, and 200. The name targets were Apia, Samoa, Upolu, Dunlap Broadsides, Nyiragongo, Finland, James Paget, and Great Yarmouth.

## Next evaluation

Collect a 36-clip held-out set from consenting Murya volunteers. Include different speakers and recording conditions. Have a native Hausa reviewer approve the exact references before scoring.

| Clips | Coverage |
| ---: | --- |
| 12 | Hooked-consonant words in full sentences. Include ɓ, ɗ, ƙ, ƴ and contrasts such as **ɗa** and **da**. |
| 12 | Numbers and names. Include **goma sha huɗu**, numbers from 1 to 20, dates or amounts, and locally familiar place and personal names. |
| 12 | Natural greetings and short conversational turns. Include **Barka da yau**, both **ka** and **ki** where appropriate, and recording with ordinary background noise. |

Record a clip ID, pseudonymous speaker ID, scenario, approved Hausa reference, consent status, and specific words or numbers to check. Keep the held-out recordings private and reserve them for evaluation. Score raw and Gyara-normalized output separately. Measure elapsed time from the end of a spoken turn to the transcript. Review names, numbers, and hooked letters with a native speaker before considering a private live-voice trial.

## FLEURS clip transcripts

### Clip 1856

- **Audio file** — 5153420622149111720.wav · 12.48 s
- **Reference** — Finland babban wurin zuwan kwalekwale ne. “Ƙasa mai tafkuna dubu” tana kuma da dubban tsibirai, a cikin tafkuna da kuma cikin rukunin tsibirai.
- **CLEAR Global** — fannan babban wurin a kwalekwale ne ƙasa mai tafku na duhu suna kuma da tabbaci ibrahim a cikin tafku na da kuma cikin rukunin tsibirai (10 word errors)
- **Omnilingual** — finman babban wurin zuwa kfalekwale ne ƙasa mai tafkuna dubu sana kuma da dabban tsibirai a cikin tafkuna da kuma cikin rukunnin tsibirai (6 word errors)

### Clip 2006

- **Audio file** — 7524079887624895833.wav · 10.08 s
- **Reference** — Ana alaƙanta sinadarai kamar calcium da kanwa a zaman ƙarafa. Tabbas, akwai kuma ƙarafa kamar azurfa da zinare.
- **CLEAR Global** — ina albanta sinadirai kamar kashin bikin a zaman ƙare ba tabbas akwai kuma ƙarafa kamar azurfa da zinari (9 word errors)
- **Omnilingual** — ana alakantacina da rai kamar kashen da kanwa a zaman ƙarafa tabbata akwai kuma ƙarafa kamar azurfa da jinari (6 word errors)

### Clip 1700

- **Audio file** — 11573044181214866376.wav · 9.96 s
- **Reference** — Yana da sirinta a ƙarƙashin maria kuma ya fi kauri a ƙarƙashin tsaunuka.
- **CLEAR Global** — yana da sirrance a ƙarƙashin mariya kuma ya fi kauri a ƙarƙashin tsaunuka (2 word errors)
- **Omnilingual** — yana da sirinta a ƙarƙashin mariya kuma yafi ƙauri a ƙarkashin tsaunuka (5 word errors)

### Clip 1684

- **Audio file** — 15818758618245864173.wav · 10.08 s
- **Reference** — Apia ce babban birnin Samoa. Garin yana kan tsibirin Upolu kuma yana da yawan al’umma da kadan ya gaza da 40,000.
- **CLEAR Global** — afiace babban birnin samuwa garin yana kan tsibirin ukuwa ne kuma yana da yawan al'umma da kaɗan ya gasa da dubuwar arba'in (10 word errors)
- **Omnilingual** — afiya ce babban birnin samuwa garin yana kan tsibirin ufonu kuma yana da yawan al'umma daka ɗanya gaza da 100 (8 word errors)

### Clip 1860

- **Audio file** — 5237909452246482270.wav · 10.68 s
- **Reference** — Ofishin gwamnan ya ce jamia’an yan sanda goma sha tara ne su ka sami raunuka.
- **CLEAR Global** — ofishin gwamnati jami'an ƴan sanda goma sha tara ne suka sami raunuka (7 word errors)
- **Omnilingual** — ofishin gwamna ya ce jami'an yan sanda goma shatara ne suka same ra'ununka (8 word errors)

### Clip 1776

- **Audio file** — 16750529125476399000.wav · 9.96 s
- **Reference** — Cikin daren an buga tsakanin 150 da 200 wanda aka fi sani da “Dunlap Broadsides”.
- **CLEAR Global** — cikin daren an buga tsakanin ƙari da hamsin da dari biyu wanda aka fi san da tallafin ratsaƙi (8 word errors)
- **Omnilingual** — cikin daran an bugatakani 3532 wanda aka fi sani da donlab broadsite (8 word errors)

### Clip 1988

- **Audio file** — 1247298799945800901.wav · 11.82 s
- **Reference** — A lokacin 1920s, halaye mafi rinjaye na yawancin 'yan ƙasa da ƙasashe shine na zaman lafiya da keɓewa.
- **CLEAR Global** — a lokacin cin cancanci harayin mafirin jaya ne wancan yan kasa da ƙasa shi ne na zaman lafiya da ƙin biyu (13 word errors)
- **Omnilingual** — a lokacin 1920 haraye mafirin jaye na yawancin yan kasa da kasashe shi ne na zaman lafiya da keɓewa (8 word errors)

### Clip 1796

- **Audio file** — 2107353835950512431.wav · 12.72 s
- **Reference** — Wannan danshi ya zama dole don ƙirƙirar linta da rairayin bakin teku, waɗanda suka yi aiki a matsayin mazaunin namun daji.
- **CLEAR Global** — wannan ɗan shi ya zama dole ɗan cikin ƙirƙira rasha da rayin bakin te faɗanda suka yi aiki a matsayin matsaun na min da ce (14 word errors)
- **Omnilingual** — wannan ɗanshi ya zama dole don kirkirar linta da rairayin bakin teku wadanda suka yi aiki a matsayi mazaunin namun daji (4 word errors)

### Clip 1768

- **Audio file** — 12218214577858604075.wav · 18.06 s
- **Reference** — An sake gina mafi yawan gine-ginen da ke gefen rukunin ginin domin ƴan yawon buɗe ido su fahimci yadda asalin siffarsu ta ke.
- **CLEAR Global** — an sa ke gina mafi yawan ginegine da ke gefen rukunin gini domin ƴan yawon bude ido su fahimci yadda asalin sif faru su ta ke (9 word errors)
- **Omnilingual** — an sake gina mafi yawan ginaginan da ke gefen rukunin gini domin yan yawan buda ido su fahinci yadda asalin siffar su take (10 word errors)

### Clip 1757

- **Audio file** — 298180416450921511.wav · 14.28 s
- **Reference** — Rikiɗa a ƙwayoyin halitta na layin ƙwayar cuta ne kaɗai za a iya gadar wa yara, yayin da rikiɗa a wani wuri kan iya haddasa mutuwar ƙwayar halitta ko cutar sankara.
- **CLEAR Global** — rikada a ƙwayoyin halitta na layin ƙwayar cuta ne kaɗai za a iya gadar wayara ya yinda rikada a wani wuri kan iya haddasa mutuwar k ƙwayar haditta ko cutar sun ƙara (10 word errors)
- **Omnilingual** — rikiɗa a kwayoyin halitta na layin ƙwayar cuta ne kadai za iya gadarwa yara yayinda rikiɗa a wani ure kan iya haddasa mutuwar ƙwayar halitta ko cutar sankara (8 word errors)

### Clip 1919

- **Audio file** — 11574624762486864858.wav · 12.12 s
- **Reference** — Garin kuma shine tushe da zai hau dutsen Nyiragongo tare da wasu daga cikin mafi saukin farashi duwatsun Gorilla a Afirka.
- **CLEAR Global** — karin kuma shine rushe da zai hau dutsen yi rubin ta da wasu daga cikin mafi sauƙin farashin duwatsen gwiwa a afirka (9 word errors)
- **Omnilingual** — garin kuma shi ne tushe da zai hau dutsen niragongo tare da wasu daga cikin mafi sauƙin farashin duwatsin gorida a afrika (8 word errors)

### Clip 1902

- **Audio file** — 330839719228983546.wav · 12.84 s
- **Reference** — Da farko an kwantar da shi a asibitin James Paget da ke Great Yarmouth.
- **CLEAR Global** — da farko an kwantar da shi a asibitin james baƙet da ke gret yar mutu (4 word errors)
- **Omnilingual** — da farko an kwantar da shi a asibitin james parget da ke gret yarmout (3 word errors)
