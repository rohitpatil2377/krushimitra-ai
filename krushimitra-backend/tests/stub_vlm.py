"""A fake OpenAI-compatible vision server, standing in for the self-hosted Gemma.

It lets us verify the whole adapter -> abstain gate -> knowledge-lookup -> capture chain
without a real GPU, including the awkward replies real servers produce (markdown fences,
confidence as a percentage, HTTP 500).
"""
from fastapi import FastAPI, Request, Response

app = FastAPI()
STATE: dict = {"detect": None, "severity": None, "status": 200}


@app.post("/scenario")
async def scenario(req: Request) -> dict:
    STATE.update(await req.json())
    return {"ok": True}


@app.post("/v1/chat/completions")
async def completions(req: Request) -> Response:
    body = await req.json()
    if STATE["status"] != 200:
        return Response(content='{"error":"boom"}', status_code=STATE["status"],
                        media_type="application/json")

    # Reject JSON mode like Ollama does, to exercise the retry path.
    if STATE.get("reject_json_mode") and "response_format" in body:
        return Response(content='{"error":"response_format unsupported"}', status_code=400,
                        media_type="application/json")

    parts = body["messages"][0]["content"]
    if isinstance(parts, str):  # a plain text probe (scripts/probe_vision_model.py step 2)
        return Response(content=__import__("json").dumps(
            {"choices": [{"message": {"role": "assistant", "content": "READY"}}]}),
            media_type="application/json")

    prompt = next(p["text"] for p in parts if p["type"] == "text")
    has_image = any(p["type"] == "image_url" for p in parts)

    if "Describe this image" in prompt:  # probe step 3
        assert has_image, "probe failed to attach the image"
        return Response(content=__import__("json").dumps(
            {"choices": [{"message": {"role": "assistant",
                                      "content": "A green onion leaf with dark lesions."}}]}),
            media_type="application/json")

    assert has_image, "adapter failed to attach the image"
    content = STATE["severity"] if "affected_area_pct" in prompt else STATE["detect"]
    return Response(
        content=__import__("json").dumps(
            {"choices": [{"message": {"role": "assistant", "content": content}}]}
        ),
        media_type="application/json",
    )
