# BachataFlow Coach 💃

An intelligent, multi-modal dance instructor agent built with the Google Agent Development Kit (ADK) and deployed to Agent Platform (Agent Runtime). BachataFlow Coach helps dancers learn Bachata fundamentals, breakdown complex Sensual, Modern, and Dominican patterns, discover tempo-matched practice music, and visualize moves with AI-generated illustrations and video demonstrations.

![BachataFlow Coach Demo](bachata_coach_demo.gif)

---

## 🌟 Key Features & Architecture

BachataFlow Coach integrates real Google Cloud tools and Gemini models:

- **Firestore Move Catalog**: Fetches real dance move data (timing breakdown, lead/follow mechanics, styling, and common pitfalls) stored in a Firestore database.
- **Vertex AI Memory Bank**: Preserves user dance preferences (skill level, favorite styles, practice history) across multiple sessions using managed agent memory.
- **A2UI Rich Surface Interface**: Generates interactive UI cards (v0.8 Basic Catalog) with formatted headings, captions, and structured columns rendered natively in the chat frontend.
- **Gemini Flash Lite Image Generation**: Uses `gemini-3.1-flash-lite-image` in the `global` region to synthesize step-by-step visual dance illustrations.
- **Gemini Omni Video Generation**: Uses Google’s `gemini-omni-flash-preview` model via the Interactions API to generate animated video demonstrations.
- **Google Cloud Storage (GCS)**: Stores generated illustration JPGs and video MP4s with public URLs for low-latency streaming and artifact persistence.
- **Code Execution Sandbox**: Integrates `AgentEngineSandboxCodeExecutor` to safely execute Python code in an isolated sandbox environment.
- **Music Recommendation Tool**: Grounds song recommendations in authentic Bachata tempos (BPM) and styles (Sensual, Dominican, Urban/Modern).

---

## 📁 Repository Structure

```
├── app/
│   ├── agent.py               # Root ADK agent, tools, callbacks, and prompt
│   ├── a2ui_utils.py          # A2UI after_model_callback transformer
│   └── __init__.py
├── frontend/
│   ├── main.py                # FastAPI proxy communicating via A2A protocol
│   ├── requirements.txt
│   ├── Dockerfile             # Container configuration for Cloud Run
│   └── static/
│       └── index.html         # Latin dance themed chat UI & A2UI renderer
├── agents-cli-manifest.yaml   # Agent Engine deployment manifest
├── deployment_metadata.json   # Deployed Agent Runtime identifiers
├── bachata_coach_demo.gif     # Looping demo recording
└── README.md
```

---

## 🚀 Running Locally

### 1. Prerequisites

- Python 3.10+
- Google Cloud SDK (`gcloud`) authenticated to your project:
  ```bash
  gcloud auth application-default login
  ```
- Install dependencies:
  ```bash
  pip install -r app/requirements.txt
  pip install -r frontend/requirements.txt
  ```

### 2. Run the Agent with ADK Web Playground

To launch the local ADK developer UI with Memory Bank support:
```bash
uv run adk web . --port 8000 --reload_agents --memory_service_uri=agentengine://<AGENT_ENGINE_ID>
```

### 3. Run the Custom Frontend

From the `frontend/` directory:
```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/us-central1/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT="8080"
python main.py
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

---

## 🛠️ Deployment

### Deploy Agent to Agent Runtime
```bash
agents-cli deploy --project <PROJECT_ID> --region us-central1 --no-confirm-project
```

### Deploy Frontend to Cloud Run
```bash
cd frontend
gcloud run deploy bachataflow-coach-ui \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<AGENT_ENGINE_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```
