# Robinson English–Hausa dictionary (1914, Vol. II)

Archival PDF, OCR text, parsed JSONL, and ML exports live here. See **ATTRIBUTION.md** for full bibliographic credit (Charles H. Robinson; Cambridge University Press; Internet Archive scan).

## Quick commands

```bash
# Parse Archive.org DJVU text → JSONL + web index
python utils/extract_robinson_dictionary.py

# Export translation-style pairs for fine-tuning / embeddings
python utils/prepare_robinson_ml.py
```

Outputs:

| Path | Description |
|------|-------------|
| `robinson_en_ha.jsonl` | Full parsed entries |
| `robinson_en_ha_index.json` | Compact search index (Hausa Explorer) |
| `../processed/robinson/en_ha_pairs.jsonl` | ML pair export |

PDF: `Robinson_Dictionary_of_Hausa_Vol2_English-Hausa_1914.pdf`  
Source URL: https://ia600607.us.archive.org/18/items/dictionaryofhaus02robiuoft/dictionaryofhaus02robiuoft.pdf
