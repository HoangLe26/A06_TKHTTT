# Local English speech model

The application loads `vosk-model-small-en-us-0.15` from this directory.
The model is used at runtime but its large binary files are excluded from Git.

From the project root, install once:

```powershell
.\.venv\Scripts\python.exe -m pip install -r CodePython/requirements.txt
.\.venv\Scripts\python.exe tainguyen/CodePython/setup_vosk.py
```

The setup script downloads the official archive into `tainguyen/downloads`,
validates its entries and installs the extracted model here. It does not
overwrite an existing model folder. Runtime transcription never downloads
anything or uses API keys.

Model: https://alphacephei.com/vosk/models
License listed by the publisher: Apache 2.0.
# CLIP image model

`clip-vit-base-patch32/` stores the official English-prompt CLIP ViT-B/32 model.
Install model and generate product vectors:

```powershell
.\.venv\Scripts\python.exe tainguyen/CodePython/setup_clip.py
```

See `tainguyen/IMAGE_SEARCH_SETUP.md`. Model weights are gitignored; the generated
`CodePython/data/clip_embeddings.json` is kept as reproducible catalog data.
