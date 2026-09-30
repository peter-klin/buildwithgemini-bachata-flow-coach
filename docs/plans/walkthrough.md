# Walkthrough: Community Dance Video Suite & Advanced Coaching Tools

All 7 proposed tools and capabilities have been designed, tested, deployed to both Vertex AI Agent Runtime and Cloud Run, and synchronized with your GitHub repository.

---

## 🛠️ What Was Added (Total: 16 Tools & Capabilities)

### 1. 🎬 Real Community YouTube Tutorials & Master Clips
- **`search_community_dance_videos`**: Searches live YouTube Bachata tutorials and enriches video IDs with the official public `oEmbed` API to return video titles, creator channels, and thumbnails.
- **`get_curated_master_clips`**: Instant retrieval of verified demonstration videos from world champions:
  - *Korke & Judith* (Sensual Body Wave & Head Roll)
  - *Daniel & Desirée* (Shadow Position Wave & Hip Dissociation)
  - *Ataca & La Alemana* (Dominican Syncopated Footwork & Majao Accents)
  - *Marco & Sara* (Madrid Step & Hip Isolations)
  - *Ronald & Alba* (Modern Bachata Hammerlock to Free Turn)
- **`analyze_social_dance_video`**: Structured 8-count breakdown of Instagram reels / YouTube shorts with lead cues, follow styling, and rhythm focus.
- **Responsive YouTube Embed in A2UI**:
  - Frontend auto-detects `youtube.com/watch?v=...`, `youtu.be/...`, or `youtube.com/embed/...` and injects a 16:9 responsive embedded YouTube player directly inside the A2UI card.

### 2. 🔀 Advanced Coaching & Social Suite
- **`build_seamless_social_combo`**: Evaluates connection states (*Closed frame*, *Hammerlock*, *Shadow*, *Two-hand hold*) to compute 3 logically fluid follow-up figures.
- **`create_practice_metronome_timer`**: Interval training workout regimen with target BPMs and technique drills.
- **`generate_dancer_quiz`**: Interactive assessment testing dancer knowledge of rhythm sections (*Derecho*, *Majao*, *Mambo*), frame physics, and timing.
- **`find_local_social_dances`**: Locates Latin dance clubs, weekly socials, and studios in any city worldwide using OpenStreetMap and verified Latin dance directories.

---

## 🧪 Verification & Results

### 1. Automated Unit Tests (`test_tools.py`)
Ran `uv run python -m unittest test_tools.py`:
```text
Ran 12 tests in 2.476s
OK
```
All 12 test suites passed covering move retrieval, song recommendations, YouTube queries, master clips, combo transitions, practice timers, quizzes, and social finders.

### 2. End-to-End Live Validation on Cloud Run
Tested live against `https://bachataflow-coach-ui-100973615551.us-central1.run.app`:
- **Combo Transition Query**:
  - Input: *"What move flows seamlessly after a Madrid Step? Build me a combo"*
  - Result: Returned structured A2UI card with starting connection state and 3 recommended follow-ups.
- **YouTube Master Clips Query**:
  - Input: *"Show me real YouTube master tutorials for Sensual Bachata body waves by Korke and Judith"*
  - Result: Returned verified master clip with YouTube watch URL `https://www.youtube.com/watch?v=z9LFJYrj7fI`, triggering responsive iframe embedding in the UI.

---

## 🚀 Live Links & Resources

- **Live Cloud Run Web App**: [https://bachataflow-coach-ui-100973615551.us-central1.run.app](https://bachataflow-coach-ui-100973615551.us-central1.run.app)
- **GitHub Repository**: [https://github.com/peter-klin/buildwithgemini-bachata-flow-coach](https://github.com/peter-klin/buildwithgemini-bachata-flow-coach)
