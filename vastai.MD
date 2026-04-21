# Vast.ai Telepítési Jegyzet (ImageAgent)

Ez a dokumentum a `FRANK` (ImageAgent) stack többszöri Vast.ai telepítéséhez készült.
Tartalmazza:
- a teljes telepítési folyamatot,
- a valós hibákat, amik előjöttek,
- a működő megoldásokat.

## 1. Cél architektúra

- App: `FastAPI` (`ImageAgent`) a szerveren, `8090` porton
- LLM: `Ollama` + modell `huihui_ai/qwen3-coder-next-abliterated`
- Image backend: `ComfyUI` + FLUX workflow
- Kimeneti képek: `/workspace/FRANK/outputs/images`

## 2. Előfeltételek Vast.ai példányon

- GPU-s instance (teszt alatt: NVIDIA H200)
- SSH hozzáférés
- Internetelérés modellek letöltéséhez
- Python 3.11 elérhető

## 3. SSH és port-forward

Helyi gépről:

```powershell
ssh -p 31379 root@ssh7.vast.ai -L 8090:localhost:8090 -L 8188:localhost:8188
```

Ezután helyben:
- App UI: `http://localhost:8090`
- ComfyUI: `http://localhost:8188`

## 4. Repo telepítés

Szerveren:

```bash
cd /workspace
git clone https://github.com/minuszka/FRANK.git
cd FRANK
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env
mkdir -p outputs/images
```

## 5. App konfiguráció (.env)

Ajánlott végleges értékek Vast környezethez:

```env
APP_HOST=0.0.0.0
APP_PORT=8090
COMFYUI_BASE_URL=http://127.0.0.1:8188
OLLAMA_BASE_URL=http://127.0.0.1:21434
OLLAMA_MODEL=huihui_ai/qwen3-coder-next-abliterated
COMFYUI_TIMEOUT_SECONDS=900
```

Megjegyzés: a `11434` itt auth proxy mögött volt (401), emiatt a belső működő endpoint `21434`.

## 6. Ollama telepítés/indítás

A környezetben az `ollama` már elérhető volt, csak indítani és modellt húzni kellett:

```bash
nohup ollama serve > /workspace/logs/ollama.log 2>&1 &
ollama pull huihui_ai/qwen3-coder-next-abliterated
```

Ellenőrzés:

```bash
curl -sS http://127.0.0.1:21434/api/tags
```

## 7. ComfyUI telepítés/indítás

```bash
cd /workspace
git clone https://github.com/comfyanonymous/ComfyUI.git
python3 -m pip install -r /workspace/ComfyUI/requirements.txt
nohup python3 /workspace/ComfyUI/main.py --listen 127.0.0.1 --port 8188 > /workspace/logs/comfyui.log 2>&1 &
```

Ellenőrzés:

```bash
curl -sS http://127.0.0.1:8188/system_stats
```

## 8. FLUX modellek és fájlok (kritikus)

Nem elég egy checkpoint; FLUX-hoz text encoder + VAE is kell.

Szükséges célfájlok:
- `/workspace/ComfyUI/models/checkpoints/flux1-dev.safetensors`
- `/workspace/ComfyUI/models/unet/flux1-dev-fp8.safetensors` (symlink is lehet)
- `/workspace/ComfyUI/models/clip/clip_l.safetensors`
- `/workspace/ComfyUI/models/clip/t5xxl_fp16.safetensors`
- `/workspace/ComfyUI/models/vae/ae.safetensors`

Használt letöltési források (teszt során működtek):

```bash
mkdir -p /workspace/ComfyUI/models/{checkpoints,unet,clip,vae}
curl -L --fail https://huggingface.co/Kijai/flux-fp8/resolve/main/flux1-dev-fp8.safetensors -o /workspace/ComfyUI/models/checkpoints/flux1-dev.safetensors
ln -sf ../checkpoints/flux1-dev.safetensors /workspace/ComfyUI/models/unet/flux1-dev-fp8.safetensors
curl -L --fail https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors -o /workspace/ComfyUI/models/clip/clip_l.safetensors
curl -L --fail https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors -o /workspace/ComfyUI/models/clip/t5xxl_fp16.safetensors
curl -L --fail https://huggingface.co/alisher123/Flux1-dev-vae/resolve/main/ae.safetensors -o /workspace/ComfyUI/models/vae/ae.safetensors
```

Megjegyzés: az official `black-forest-labs/FLUX.1-dev` repo gated volt (401), ezért kellett publikus alternatíva.

## 9. Kód oldali FLUX kompatibilitási módosítások

A projektben szükséges volt:
- `app/workflows/flux_dev_workflow.json` átalakítása FLUX node-láncra (`UNETLoader`, `DualCLIPLoader`, `CLIPTextEncodeFlux`, `VAELoader`, `ModelSamplingFlux`, `KSampler`)
- `app/services/comfyui_service.py` frissítése, hogy:
  - FLUX prompt node-okhoz `clip_l`/`t5xxl` mezőket töltsön,
  - `ModelSamplingFlux` width/height mezőit is paraméterezze
- `app/prompts/image_prompt_instruction.txt` escape fix (`{{ ... }}`), különben `.format()` összeomolhat
- `app/services/router_service.py` javítás magyar, elgépeléses képkérésekhez

## 10. Start script-ek (újratelepítéshez erősen ajánlott)

`/workspace/start_ollama.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /workspace/logs
if ! pgrep -f "ollama serve" >/dev/null; then
  nohup ollama serve > /workspace/logs/ollama.log 2>&1 &
fi
```

`/workspace/start_comfyui.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /workspace/logs
if ! pgrep -f "/workspace/ComfyUI/main.py --listen 127.0.0.1 --port 8188" >/dev/null; then
  nohup python3 /workspace/ComfyUI/main.py --listen 127.0.0.1 --port 8188 > /workspace/logs/comfyui.log 2>&1 &
fi
```

`/workspace/start_imageagent.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /workspace/logs
cd /workspace/FRANK
. .venv/bin/activate
export OLLAMA_BASE_URL=http://127.0.0.1:21434
export OLLAMA_MODEL=huihui_ai/qwen3-coder-next-abliterated
export COMFYUI_BASE_URL=http://127.0.0.1:8188
export APP_HOST=0.0.0.0
export APP_PORT=8090
if ! pgrep -f "uvicorn app.main:app --host 0.0.0.0 --port 8090" >/dev/null; then
  nohup uvicorn app.main:app --host 0.0.0.0 --port 8090 > /workspace/logs/imageagent.log 2>&1 &
fi
```

`/workspace/start_all.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
/workspace/start_ollama.sh
/workspace/start_comfyui.sh
/workspace/start_imageagent.sh
```

`/workspace/status_all.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
pgrep -af 'ollama serve|ComfyUI/main.py|uvicorn app.main:app' || true
ss -lntp | grep -E ':(8090|8188|21434|11434)\b' || true
curl -sS http://127.0.0.1:8090/health || true
curl -sS http://127.0.0.1:8188/system_stats | head -c 200 || true
curl -sS http://127.0.0.1:21434/api/tags | head -c 200 || true
```

## 11. Validációs parancsok

Text/chat:

```bash
curl -sS -X POST http://127.0.0.1:8090/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Explain recursion briefly with a JavaScript example.","session_id":"smoke","stream":false}'
```

Image direct:

```bash
curl -sS -X POST http://127.0.0.1:8090/api/generate-image \
  -H 'Content-Type: application/json' \
  -d '{"action":"generate_image","prompt":"a cinematic futuristic Budapest skyline at sunset","negative_prompt":"blurry, low quality, text, watermark","width":1024,"height":1024,"steps":10,"guidance":4.0,"seed":12345,"style_hint":"cinematic","output_format":"png"}'
```

Image routed chat:

```bash
curl -sS -X POST http://127.0.0.1:8090/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"készíts egy képet, orbán viktorról és magyar péterről","session_id":"smoke","stream":false}'
```

## 12. Felmerült hibák és megoldások

### Hiba: Vast auto-tmux miatt SSH scriptelés zajos/instabil
- Tünet: nem-interaktív parancsok furcsán futnak, timeout
- Megoldás: ideiglenesen stdin-es workaround, majd non-interaktív SSH használata

### Hiba: `8080` foglalt
- Tünet: Uvicorn bind error (`address already in use`)
- Ok: Vast alapon Jupyter használja a 8080-at
- Megoldás: app átállítás `8090`-re

### Hiba: `OLLAMA_BASE_URL=http://127.0.0.1:11434` -> 401
- Ok: ezen a környezeten `11434` auth proxy mögötti caddy endpoint
- Megoldás: belső endpoint: `http://127.0.0.1:21434`

### Hiba: ComfyUI nem indul (`torchaudio` symbol hiba)
- Tünet: `_torchaudio.abi3.so` undefined symbol
- Ok: torch/torchaudio ABI mismatch
- Megoldás: torchaudio újratelepítés torch-hoz igazítva (`2.9.1+cu128`)

### Hiba: FLUX timeout / nincs output
- Ok: hiányzó FLUX kiegészítő modellek (CLIP/VAE), vagy hibás workflow node-lánc
- Megoldás: szükséges modellek letöltése + FLUX-kompatibilis workflow

### Hiba: `clip input is invalid: None`
- Ok: checkpoint nem tartalmaz text encoder-t, de workflow `CheckpointLoaderSimple` clip-jét használja
- Megoldás: `DualCLIPLoader` + `CLIPTextEncodeFlux` használata

### Hiba: chat image kérésre csak promptszöveg jön
- Ok: router túl gyenge magyar/elgépeléses mintákra
- Megoldás: normalizáló + verb+noun image routing logika

### Hiba: prompt template crash (`'\\n  "action"'`)
- Ok: `.format()` és JSON kapcsos zárójelek ütközése
- Megoldás: prompt fájlban `{{ ... }}` escape

## 13. Újratelepítési rövid checklist

1. SSH + tunnel (`8090`, `8188`)
2. Repo clone + `.venv` + `pip install -r requirements.txt`
3. `.env` Vast kompatibilis értékekre
4. Ollama serve + modell pull
5. ComfyUI install + start
6. FLUX modellek (checkpoint + unet link + clip_l + t5xxl + ae)
7. Start script-ek (`start_*.sh`)
8. `status_all.sh` ellenőrzés
9. Smoke teszt: `/health`, `/api/chat`, `/api/generate-image`

---

Ha új Vast instance indul, ezt a fájlt követve 1:1 reprodukálható a működő környezet.

