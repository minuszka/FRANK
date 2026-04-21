# ImageAgent

Helyben futó, moduláris full-stack asszisztens, amely:
- Ollama LLM-et használ szöveghez és kódolási feladatokhoz.
- ComfyUI-n keresztül FLUX-alapú képgenerálást kezel.
- Egyetlen chat felületen egyesíti a `chat / code / image` útvonalakat.

## 1. Mi ez a projekt

Az ImageAgent egy FastAPI backend + egyszerű web frontend alkalmazás.

Fő képességek:
- routing: `chat`, `code`, `image` feladatok automatikus szétválasztása
- Ollama-alapú szöveges és kódos válaszadás
- LLM alapú image instruction extraction (JSON)
- ComfyUI workflow alapú képgenerálás
- lokális image mentés és chat preview
- session alapú beszélgetési előzmény

## 2. Előfeltételek

- Python `3.11+`
- Ollama fut helyben
- Letöltött modell: `huihui_ai/qwen3-coder-next-abliterated`
- ComfyUI fut helyben API-val
- FLUX workflow elérhető és a node ID-k egyeznek a backend mappinggel

## 3. Python környezet létrehozása

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

## 4. Függőségek telepítése

```bash
pip install -r requirements.txt
```

## 5. `.env` beállítás

```bash
cp .env.example .env
```

Windows:

```powershell
Copy-Item .env.example .env
```

Kötelező változók:
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `COMFYUI_BASE_URL`
- `OUTPUT_DIR`
- `APP_HOST`
- `APP_PORT`
- `DEFAULT_IMAGE_WIDTH`
- `DEFAULT_IMAGE_HEIGHT`
- `DEFAULT_IMAGE_STEPS`
- `DEFAULT_IMAGE_GUIDANCE`
- `LOG_LEVEL`

## 6. Ollama futtatása

```bash
ollama serve
```

## 7. Használt modell letöltése

```bash
ollama pull huihui_ai/qwen3-coder-next-abliterated
```

## 8. ComfyUI indítása

Indítsd a ComfyUI-t API-val (alapértelmezett: `http://127.0.0.1:8188`).

Példa (a pontos parancs a ComfyUI telepítésedtől függ):

```bash
python main.py --listen 127.0.0.1 --port 8188
```

## 9. FLUX workflow használata

A workflow itt található:

- `app/workflows/flux_dev_workflow.json`

Fontos:
- a ComfyUI workflow node ID-k környezetenként eltérhetnek
- a backend jelenleg ezeket az ID-ket írja:
  - prompt: node `6`
  - negative prompt: node `7`
  - sampler (steps/cfg/seed): node `3`
  - latent size: node `5`
  - save node: node `9`

Ha a helyi workflow más, módosítsd a konstansokat itt:
- `app/services/comfyui_service.py`

## 10. Az app indítása

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Majd nyisd meg:

`http://127.0.0.1:8000`

## 11. Gyakori hibák

1. `Ollama unavailable / 503`
- Ellenőrizd, hogy fut-e az Ollama (`ollama serve`)
- Ellenőrizd az `OLLAMA_BASE_URL` értéket

2. `ComfyUI unavailable / 503`
- Ellenőrizd, hogy fut-e a ComfyUI API
- Ellenőrizd a `COMFYUI_BASE_URL` értéket

3. `workflow_node_missing`
- A JSON workflow node ID-k nem egyeznek a backend elvárásokkal
- Frissítsd `ComfyUIService` konstansait

4. Kép nem jelenik meg, bár generálás sikeresnek tűnik
- Ellenőrizd az `outputs/images` mappa írási jogait
- Ellenőrizd, hogy a `/view` endpoint visszaad-e bináris képet ComfyUI-ban

5. LLM JSON parse hiba image extraction során
- A backend fallback logikát használ
- Nézd meg a logot és finomítsd az `image_prompt_instruction.txt` promptot

## 12. Jövőbeli bővítési ötletek

- LLM-alapú router finomhangolás a rule-based réteg fölé
- Több image backend (SDXL, SD3.5, RealVisXL) adapteres architektúrával
- Perzisztens history (SQLite/PostgreSQL)
- Auth és multi-user session kezelés
- Job queue képgeneráláshoz
- Részletes telemetry és request tracing

## API endpointok

- `GET /health`
- `GET /api/config`
- `POST /api/chat`
- `POST /api/chat/stream` (SSE stream)
- `POST /api/generate-image`
- `GET /api/images/{filename}`
- `GET /api/history?session_id=default`
- `DELETE /api/history?session_id=default`

## Projektstruktúra

```text
project-root/
  app/
    main.py
    config.py
    dependencies.py
    api/
      routes_health.py
      routes_chat.py
      routes_images.py
      routes_history.py
    services/
      ollama_service.py
      router_service.py
      image_prompt_service.py
      comfyui_service.py
      chat_service.py
      history_service.py
      image_backend_base.py
    schemas/
      chat.py
      image.py
      common.py
    core/
      logging.py
      exceptions.py
      utils.py
    prompts/
      image_prompt_instruction.txt
      router_prompt.txt
    workflows/
      flux_dev_workflow.json
    static/
      css/styles.css
      js/app.js
    templates/
      index.html
  outputs/
    images/
  tests/
    test_health.py
    test_router.py
    test_prompt_parser.py
    test_history_service.py
  .env.example
  requirements.txt
  README.md
```

## Tesztek futtatása

```bash
pytest -q
```

## Rövid indítási lépések

1. Python venv létrehozás és aktiválás.
2. `pip install -r requirements.txt`
3. `.env.example` másolása `.env`-re.
4. `ollama serve`
5. `ollama pull huihui_ai/qwen3-coder-next-abliterated`
6. ComfyUI indítás (`127.0.0.1:8188`)
7. `uvicorn app.main:app --reload`
8. Böngészőben: `http://127.0.0.1:8000`

