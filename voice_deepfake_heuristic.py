#!/usr/bin/env python3
"""
voice_deepfake_heuristic.py
Heuristic-only "suspicion score" for synthetic speech.
NOT a definitive detector.

Dependencies:
  pip install numpy scipy librosa soundfile
Usage:
  python voice_deepfake_heuristic.py input.wav
"""

import sys
import numpy as np
import librosa

def frame_stats(x, sr):
    # STFT magnitude
    S = np.abs(librosa.stft(x, n_fft=1024, hop_length=256, win_length=1024))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)

    # Spectral flatness: synthetic often has "over-smooth" or abnormal flatness patterns
    flat = librosa.feature.spectral_flatness(S=S).flatten()

    # Spectral centroid / rolloff
    centroid = librosa.feature.spectral_centroid(S=S, sr=sr).flatten()
    rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr, roll_percent=0.85).flatten()

    # High-frequency energy ratio (HF): many TTS have weird HF behavior (too clean/too strong/too weak)
    hf_band = (freqs >= 4000) & (freqs <= 8000)
    lf_band = (freqs >= 300) & (freqs < 4000)
    hf_energy = S[hf_band, :].sum(axis=0) + 1e-12
    lf_energy = S[lf_band, :].sum(axis=0) + 1e-12
    hf_ratio = (hf_energy / lf_energy)

    # Pitch stability / variability (F0)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        x, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"),
        sr=sr, frame_length=1024, hop_length=256
    )
    f0v = f0[~np.isnan(f0)]
    if len(f0v) < 10:
        f0_mean = np.nan
        f0_std = np.nan
        f0_cv = np.nan
    else:
        f0_mean = float(np.mean(f0v))
        f0_std = float(np.std(f0v))
        f0_cv = float(f0_std / (f0_mean + 1e-12))

    # Zero-crossing rate & RMS dynamics
    zcr = librosa.feature.zero_crossing_rate(x, frame_length=1024, hop_length=256).flatten()
    rms = librosa.feature.rms(y=x, frame_length=1024, hop_length=256).flatten()

    def safe(v):
        return float(np.nan_to_num(np.mean(v)))

    feats = {
        "flat_mean": safe(flat),
        "flat_std": float(np.std(flat)),
        "centroid_mean": safe(centroid),
        "rolloff_mean": safe(rolloff),
        "hf_ratio_mean": safe(hf_ratio),
        "hf_ratio_std": float(np.std(hf_ratio)),
        "f0_mean": f0_mean,
        "f0_std": f0_std,
        "f0_cv": f0_cv,
        "zcr_mean": safe(zcr),
        "rms_mean": safe(rms),
        "rms_std": float(np.std(rms)),
    }
    return feats

def suspicion_score(feats):
    """
    Rule-based score 0~100.
    This is not scientifically absolute; tune thresholds with your own data.
    """
    score = 0.0
    reasons = []

    # Spectral flatness: too stable/too uniform can be suspicious
    if feats["flat_std"] < 0.02:
        score += 20; reasons.append("스펙트럼 플랫니스 변동이 너무 낮음(과도하게 매끈)")
    if feats["hf_ratio_std"] < 0.15:
        score += 15; reasons.append("고주파/중저주파 에너지 비율 변동이 낮음(코덱/합성 의심)")

    # Pitch variability: some TTS has unnaturally stable F0 (or weird jumps)
    if not np.isnan(feats["f0_cv"]) and feats["f0_cv"] < 0.05:
        score += 20; reasons.append("피치 변동이 비정상적으로 낮음(로봇틱/합성 가능)")
    if not np.isnan(feats["f0_std"]) and feats["f0_std"] > 80:
        score += 10; reasons.append("피치 표준편차가 과도하게 큼(불연속 점프 의심)")

    # RMS dynamics: overly constant loudness can be TTS-ish
    if feats["rms_std"] < 0.01:
        score += 15; reasons.append("음량(RMS) 변동이 너무 일정함")

    # ZCR oddities: not strong, but can add a bit
    if feats["zcr_mean"] < 0.03:
        score += 5; reasons.append("ZCR이 낮은 편(부드러운 합성/노이즈 억제 가능)")

    # Clamp
    score = max(0.0, min(100.0, score))
    return score, reasons

def main():
    if len(sys.argv) != 2:
        print("Usage: python voice_deepfake_heuristic.py input.wav", file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]
    x, sr = librosa.load(path, sr=16000, mono=True)
    # trim silence
    x, _ = librosa.effects.trim(x, top_db=25)

    feats = frame_stats(x, sr)
    score, reasons = suspicion_score(feats)

    print("=== Deepfake Suspicion (Heuristic) ===")
    print(f"File: {path}")
    print(f"Score: {score:.1f} / 100")
    print("\n[Features]")
    for k, v in feats.items():
        print(f"- {k}: {v}")

    print("\n[Reasons]")
    if reasons:
        for r in reasons:
            print(f"- {r}")
    else:
        print("- 뚜렷한 합성 패턴은 약함(단, 이것이 '진짜'를 의미하진 않음)")

    print("\n[Next]")
    print("- 이 점수는 참고용. 최종은 '콜백+세이프워드'로 확정해라.")
    print("- 통화코덱/압축/잡음이면 탐지 신뢰도 낮아진다.")

if __name__ == "__main__":
    main()
