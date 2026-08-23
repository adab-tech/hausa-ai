import os
import json
import re
from collections import Counter
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# Locate the waxal_hausa directory relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WAXAL_DIR = os.path.join(BASE_DIR, "waxal_hausa")
METADATA_PATH = os.path.join(WAXAL_DIR, "metadata.jsonl")
AUDIO_DIR = os.path.join(WAXAL_DIR, "audio")

def _load_metadata():
    if not os.path.exists(METADATA_PATH):
        return []
    samples = []
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples

@router.get("/waxal/stats")
async def get_waxal_stats():
    """Compute and return statistical overview of the WAXAL dataset."""
    samples = _load_metadata()
    if not samples:
        return {"error": "Dataset metadata not found. Please pull the dataset first."}

    total_samples = len(samples)
    speakers = {}
    gender_counts = Counter()
    sample_gender_counts = Counter()
    spk_sample_counts = Counter()
    
    all_words = []
    sentence_lengths = []
    
    # Track representations of hooked characters
    unicode_hooks = {
        "ɗ": 0, "Ɗ": 0,
        "ɓ": 0, "Ɓ": 0,
        "ƙ": 0, "Ƙ": 0,
        "ƴ": 0, "Ƴ": 0,
    }
    
    ascii_patterns = {
        "d'": re.compile(r"[dD]['\u2019]"),
        "k'": re.compile(r"[kK]['\u2019]"),
        "b'": re.compile(r"[bB]['\u2019]"),
        "'y": re.compile(r"['\u2019][yY]"),
    }
    ascii_hook_counts = Counter()

    for s in samples:
        spk = s.get("speaker_id", "unknown")
        gender = s.get("gender", "unknown")
        text = s.get("text", "")
        
        # Speaker info
        if spk not in speakers:
            speakers[spk] = gender
            gender_counts[gender] += 1
        sample_gender_counts[gender] += 1
        spk_sample_counts[spk] += 1
        
        # Word info
        words = text.split()
        sentence_lengths.append(len(words))
        all_words.extend(words)
        
        # Character count
        for char in text:
            if char in unicode_hooks:
                unicode_hooks[char] += 1
                
        # ASCII hook count
        for key, pattern in ascii_patterns.items():
            matches = len(pattern.findall(text))
            if matches > 0:
                ascii_hook_counts[key] += matches

    total_words = len(all_words)
    vocab = set(w.lower().strip(".,;:!?\"'()[]{}«»") for w in all_words)
    unique_words = len(vocab)
    ttr = unique_words / total_words if total_words > 0 else 0

    # Format speaker stats
    speakers_list = []
    for spk, count in sorted(spk_sample_counts.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        speakers_list.append({
            "speaker_id": spk,
            "gender": speakers.get(spk, "unknown"),
            "samples": count
        })

    return {
        "general": {
            "total_samples": total_samples,
            "total_speakers": len(speakers),
            "male_speakers": gender_counts.get("Male", 0),
            "female_speakers": gender_counts.get("Female", 0),
            "male_samples": sample_gender_counts.get("Male", 0),
            "female_samples": sample_gender_counts.get("Female", 0),
        },
        "speakers": speakers_list,
        "linguistic": {
            "total_words": total_words,
            "vocab_size": unique_words,
            "type_token_ratio": round(ttr, 4),
            "avg_sentence_length": round(sum(sentence_lengths) / total_samples, 2) if total_samples > 0 else 0,
            "min_sentence_length": min(sentence_lengths) if sentence_lengths else 0,
            "max_sentence_length": max(sentence_lengths) if sentence_lengths else 0,
        },
        "orthography": {
            "unicode": {
                "d_hook": unicode_hooks.get("ɗ", 0) + unicode_hooks.get("Ɗ", 0),
                "b_hook": unicode_hooks.get("ɓ", 0) + unicode_hooks.get("Ɓ", 0),
                "k_hook": unicode_hooks.get("ƙ", 0) + unicode_hooks.get("Ƙ", 0),
                "y_hook": unicode_hooks.get("ƴ", 0) + unicode_hooks.get("Ƴ", 0),
            },
            "ascii": dict(ascii_hook_counts)
        }
    }

@router.get("/waxal/samples")
async def get_waxal_samples(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    speaker_id: Optional[str] = None,
    gender: Optional[str] = None,
    query: Optional[str] = None
):
    """Retrieve filtered, paginated list of samples from the WAXAL dataset."""
    samples = _load_metadata()
    if not samples:
        return {"samples": [], "total_count": 0, "total_pages": 0}

    filtered = []
    for s in samples:
        # Speaker filter
        if speaker_id and s.get("speaker_id") != speaker_id:
            continue
        # Gender filter
        if gender and s.get("gender") != gender:
            continue
        # Search query filter
        if query:
            q = query.lower()
            text = s.get("text", "").lower()
            if q not in text:
                continue
        filtered.append(s)

    total_count = len(filtered)
    total_pages = (total_count + page_size - 1) // page_size
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = filtered[start_idx:end_idx]

    return {
        "samples": paginated,
        "total_count": total_count,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size
    }

@router.get("/waxal/tts")
async def get_waxal_tts(
    text: str,
    speaker_id: Optional[str] = None
):
    """Find the closest WAXAL sample matching the input text."""
    samples = _load_metadata()
    if not samples:
        raise HTTPException(status_code=404, detail="WAXAL metadata not found")

    # Filter by speaker if provided. An unmatched speaker_id must NOT fall
    # back to searching the whole (unfiltered, mixed-gender) dataset -- that
    # risks silently matching and returning a recording from the wrong
    # gender/voice, exactly the failure mode _find_closest_waxal_sample's own
    # docstring in audio.py warns about. Error instead.
    if speaker_id:
        spk_str = str(speaker_id)
        filtered = [s for s in samples if str(s.get("speaker_id")) == spk_str]
        if not filtered:
            raise HTTPException(
                status_code=404,
                detail=f"No WAXAL samples found for speaker_id={speaker_id!r}",
            )
        samples = filtered

    # Compute similarity for each sample
    best_sample = None
    best_score = -1.0
    
    import re
    words_input = set(re.findall(r'\w+', text.lower()))
    
    if words_input:
        for s in samples:
            s_text = s.get("text_normalized", s.get("text", ""))
            words_s = set(re.findall(r'\w+', s_text.lower()))
            if not words_s:
                continue
            # Jaccard similarity
            score = len(words_input.intersection(words_s)) / len(words_input.union(words_s))
            if score > best_score:
                best_score = score
                best_sample = s

    if not best_sample:
        # Fallback
        if samples:
            best_sample = samples[0]
            best_score = 0.0
        else:
            raise HTTPException(status_code=404, detail="No samples found")

    audio_file = best_sample.get("audio_file", "")
    basename = os.path.basename(audio_file)

    return {
        "sample": best_sample,
        "similarity": best_score,
        "audio_url": f"/api/waxal/audio/{basename}"
    }

@router.get("/waxal/audio/{filename}")
async def get_waxal_audio(filename: str):
    """Serve a local audio file from the staged WAXAL audio folder."""
    # Sanitize path to prevent directory traversal
    filename = os.path.basename(filename)
    audio_path = os.path.join(AUDIO_DIR, filename)
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    return FileResponse(audio_path, media_type="audio/mpeg")
