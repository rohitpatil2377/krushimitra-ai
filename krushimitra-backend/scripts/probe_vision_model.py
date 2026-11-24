#!/usr/bin/env python
"""Probe a self-hosted vision model before trusting it with farmers' crops.

Answers, in order, the four things that decide whether a deployment is usable:

  1. Is the server reachable, and which models does it serve?
  2. Does it answer text at all (auth and routing correct)?
  3. Does it accept an IMAGE?  A text-only serving config of a multimodal model will refuse —
     and Gemma 3 *1B has no vision encoder at all*, so a 1B deployment fails here by design.
  4. Given a real crop photo, what does it actually say — and does it abstain when it should?

Usage:
    # reads VISION_BASE_URL / VISION_API_KEY / VISION_MODEL from krushimitra-backend/.env
    PYTHONPATH=. .venv/bin/python scripts/probe_vision_model.py

    # or explicitly, with real photos to judge quality
    PYTHONPATH=. .venv/bin/python scripts/probe_vision_model.py \
        --base-url http://10.0.0.5:8000/v1 --model gemma-3-27b-it \
        --image leaf1.jpg --crop onion --expect onion_purple_blotch

Pass --image several times to score a small batch. Quality is not assumed — it is measured.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import struct
import sys
import zlib

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.services.vision.labels import resolve  # noqa: E402

OK, BAD, WARN = "✅", "❌", "⚠️ "



def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data)) + tag + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def tiny_png(width: int = 64, height: int = 64, rgb: tuple[int, int, int] = (72, 140, 64)) -> bytes:
    """A real, decodable PNG - a plain green square, built with stdlib only.

    This replaces a hand-faked JPEG (magic header + zero padding + EOI marker) that no decoder
    could actually read. That fake produced a FALSE NEGATIVE against a working multimodal
    endpoint: the server accepted the request, handed the bytes to its image loader, the loader
    said "cannot identify image file", and this script concluded "not multimodal".

    A probe that cannot tell "your model has no vision" from "my test image was broken" is
    worse than no probe, so step 3 now sends something every decoder can open.
    """
    scanlines = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(scanlines, 9))
        + _png_chunk(b"IEND", b"")
    )


def headers(key: str | None) -> dict:
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


async def step_models(base: str, key: str | None) -> list[str]:
    print("\n[1/4] Server reachable + model list")
    try:
        async with httpx.AsyncClient(timeout=30, verify=settings.vision_verify_ssl) as c:
            r = await c.get(f"{base}/models", headers=headers(key))
        if r.status_code != 200:
            print(f"  {WARN} GET /models -> HTTP {r.status_code} (not fatal; some servers omit it)")
            return []
        names = [m.get("id", "?") for m in r.json().get("data", [])]
        print(f"  {OK} serving {len(names)} model(s): {', '.join(names) or '(none listed)'}")
        return names
    except httpx.HTTPError as exc:
        print(f"  {BAD} cannot reach {base}: {exc}")
        print("     Check the URL, that the port is open from this machine, and any firewall.")
        sys.exit(1)


async def chat(base: str, key: str | None, model: str, content, max_tokens: int = 300) -> tuple[int, str]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(
        timeout=settings.vision_timeout_s, verify=settings.vision_verify_ssl
    ) as c:
        r = await c.post(f"{base}/chat/completions", json=payload, headers=headers(key))
    if r.status_code != 200:
        return r.status_code, r.text[:400]
    try:
        return 200, r.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError):
        return 200, f"(unexpected shape) {r.text[:300]}"


async def step_text(base: str, key: str | None, model: str) -> bool:
    print("\n[2/4] Text generation (auth + routing)")
    code, body = await chat(base, key, model, "Reply with exactly: READY", max_tokens=16)
    if code != 200:
        print(f"  {BAD} HTTP {code}: {body}")
        print("     401/403 => wrong API key. 404 => wrong model name or base path.")
        return False
    print(f"  {OK} model replied: {body.strip()[:80]!r}")
    return True


async def step_vision(base: str, key: str | None, model: str, image: bytes) -> bool:
    print("\n[3/4] Image input accepted (is this deployment really multimodal?)")
    import base64

    mime = (
        "image/png" if image[:4] == b"\x89PNG"
        else "image/webp" if image[:4] == b"RIFF"
        else "image/jpeg"
    )
    uri = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    code, body = await chat(
        base, key, model,
        [
            {"type": "text", "text": "Describe this image in under 15 words."},
            {"type": "image_url", "image_url": {"url": uri}},
        ],
    )
    if code != 200:
        print(f"  {BAD} HTTP {code}: {body}")
        # Three different failures look alike from here, and calling them all "no vision
        # support" once cost us a wrong conclusion about a working endpoint. Separate them.
        lowered = body.lower()
        if "cannot identify image" in lowered or "failed to load image" in lowered:
            print("     The server REACHED an image decoder and could not read the bytes.")
            print("     That means the deployment DOES handle images — the picture was the")
            print("     problem, not the model. Re-run with --image <a real photo.jpg>.")
        elif any(w in lowered for w in ("image_url", "content type", "not supported", "unsupported", "multimodal")):
            print("     The server REJECTED the multimodal message format itself, so this model")
            print("     has no vision encoder. Use it for the chatbot (LLM_BASE_URL) instead.")
        else:
            print("     Could not tell why from the response. Either vision is disabled in the")
            print("     serving config, or the model has no vision encoder. Ask whoever runs")
            print("     the gateway whether this deployment is multimodal.")
        return False
    print(f"  {OK} image accepted. Model said: {body.strip()[:140]!r}")
    return True


async def step_diagnose(images: list[pathlib.Path], crop: str | None, expect: list[str]) -> None:
    print("\n[4/4] Real diagnosis through our own adapter (prompt, abstain gate and all)")
    if not images:
        print(f"  {WARN} no --image given, so quality is UNMEASURED.")
        print("     Pass real diseased-crop photos to find out whether it is actually any good:")
        print("     --image leaf1.jpg --crop onion --expect onion_purple_blotch")
        return

    from app.services.vision.selfhosted import SelfHostedDetector, SelfHostedSeverity

    detector, severity = SelfHostedDetector(), SelfHostedSeverity()
    hits = 0
    for i, path in enumerate(images):
        want = expect[i] if i < len(expect) else None
        try:
            diag = await detector.diagnose(path.read_bytes(), crop=crop)
        except Exception as exc:
            print(f"  {BAD} {path.name}: {exc}")
            continue

        abstained = diag.confidence < settings.vision_min_confidence
        verdict = " (ABSTAINS)" if abstained else ""
        summary = f"{path.name}: {diag.disease} @ {diag.confidence:.2f}{verdict}"
        if want:
            wanted = resolve(want, crop).slug
            correct = wanted == diag.disease and not abstained
            hits += correct
            print(f"  {OK if correct else BAD} {summary}  expected={wanted}")
        else:
            print(f"    {summary}")
        if diag.symptoms:
            print(f"      saw: {diag.symptoms}")
        if not abstained:
            try:
                sev = await severity.estimate(path.read_bytes(), diag)
                print(f"      severity: {sev.level} {sev.severity_pct}% risk={sev.risk_level}")
            except Exception as exc:
                print(f"      {WARN} severity failed: {exc}")

    if expect:
        print(f"\n  Top-1 accuracy on this batch: {hits}/{len(images)}")
        print("  Context: field accuracy for shipped crop-disease apps runs ~65-80%.")
        print("  A model below that should stay behind the abstain gate, not in front of farmers.")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=settings.vision_base_url)
    ap.add_argument("--api-key", default=settings.vision_api_key)
    ap.add_argument("--model", default=settings.vision_model)
    ap.add_argument("--insecure", action="store_true",
                    help="skip TLS verification — the `curl -k` case, for a self-signed "
                         "certificate on an internal UAT endpoint")
    ap.add_argument("--image", action="append", default=[], type=pathlib.Path)
    ap.add_argument("--crop", default=None, help="onion | soybean | pomegranate")
    ap.add_argument("--expect", action="append", default=[],
                    help="ground-truth label per --image, in the same order")
    args = ap.parse_args()

    if not args.base_url:
        print(f"{BAD} No endpoint. Set VISION_BASE_URL in .env or pass --base-url.")
        sys.exit(2)

    base = args.base_url.rstrip("/")
    print(f"Probing {base}  model={args.model}  key={'set' if args.api_key else 'none'}")

    # Step 4 runs through the real adapter, which reads these from settings — so CLI flags have
    # to be pushed into settings or the adapter would look for an endpoint that isn't configured.
    settings.vision_base_url = base
    settings.vision_api_key = args.api_key
    settings.vision_model = args.model
    if args.insecure:
        settings.vision_verify_ssl = False

    await step_models(base, args.api_key)
    if not await step_text(base, args.api_key, args.model):
        sys.exit(1)

    probe_image = (
        args.image[0].read_bytes()
        if args.image
        else tiny_png()
    )
    if not args.image:
        print(f"  {WARN} using a dummy image for step 3 — it only tests acceptance, not quality.")
    if not await step_vision(base, args.api_key, args.model, probe_image):
        sys.exit(1)

    await step_diagnose(args.image, args.crop, args.expect)
    print("\nDone. Set VISION_BASE_URL in krushimitra-backend/.env to make this live for the app.")


if __name__ == "__main__":
    asyncio.run(main())
