# Implementation Plan: Community Dance Video Integration & Advanced Coaching Suite

We are expanding **BachataFlow Coach** with 7 high-impact tools that integrate real-world community dance videos and advanced coaching mechanisms, while preserving all existing functionality and requiring **zero paid API keys**.

## User Review Required

> [!IMPORTANT]
> **Zero External Keys Required**: All planned tools use either built-in Vertex AI capabilities (Gemini 3.6 Flash multimodal video understanding, Firestore Native), Google Cloud Sandbox, open public endpoints (YouTube oEmbed & zero-key search, OpenStreetMap Overpass/Nominatim), or deterministic rule engines. No paid third-party API subscriptions or billing setups are required.

> [!NOTE]
> **Payload Limit Safeguard**: Before deploying to Agent Runtime, any large media files (`.gif`, `.mp4`) will continue to be moved to `/tmp/` during `agents-cli deploy` so the in-memory archive stays well below the 8MB platform limit.

---

## Proposed Changes & Tool Architecture

### 1. Community & Real-World Dance Video Tools (3 Tools)

#### `search_community_dance_videos(query: str, style: Optional[str] = None)`
- **Purpose**: Search for real-world Bachata tutorial videos, demonstrations, and festival clips from YouTube without requiring a Google API key.
- **Mechanism**: Extracts top video IDs matching the query and enriches them via YouTube's official public `oEmbed` API to return title, author channel, thumbnail URL, and `youtube.com/watch?v=...` URL.
- **UI Integration**: Frontend A2UI will recognize YouTube watch URLs and render responsive embedded YouTube players directly inside the chat cards.

#### `get_curated_master_clips(style: Optional[str] = None, artist: Optional[str] = None)`
- **Purpose**: Instant retrieval of verified, high-quality demonstration clips from world-renowned master instructors (e.g. *Korke & Judith*, *Daniel & Desirée*, *Ataca y La Alemana*, *Marco & Sara*, *Melvin & Gatica*).
- **Mechanism**: Reads from a seeded Firestore collection `curated_master_clips` with fallback to a rich in-memory registry of 12+ master instructional demonstrations.

#### `analyze_social_dance_video(video_url: str, focus_area: Optional[str] = None)`
- **Purpose**: Accepts a video link (or YouTube Short) and uses Gemini's multimodal video understanding to provide an 8-count breakdown, identifying lead frame mechanics, follow styling, and rhythm syncopation.
- **Mechanism**: If YouTube metadata or video frames are provided, formats a targeted analysis via `gemini-3.6-flash` and returns a structured breakdown ready to be saved with `save_bachata_move`.

---

### 2. Advanced Coaching & Social Suite (4 Tools)

#### `build_seamless_social_combo(starting_move: str, desired_style: Optional[str] = None)`
- **Purpose**: Solves the #1 social dance dilemma: *"What move can I do next without breaking partner connection?"*
- **Mechanism**: Analyzes connection states (closed position, open two-hand, right-to-right hand, hammerlock, shadow position) to return 3 logically seamless follow-up moves.

#### `create_practice_metronome_timer(duration_minutes: int = 15, target_style: str = "Sensual")`
- **Purpose**: Builds an interval practice regimen (warm-up, technique drill, musicality speed round, cooldown) with targeted BPM cadences.
- **Mechanism**: Computes rounds and returns structured timing intervals rendered as an interactive practice routine card in A2UI.

#### `generate_dancer_quiz(topic: str = "musicality", difficulty: str = "Intermediate")`
- **Purpose**: Interactive assessment testing dancer knowledge of rhythm sections (*Derecho*, *Majao*, *Mambo*), lead/follow physics, and frame tension.
- **Mechanism**: Returns multi-choice questions with answers, explanations, and coaching tips.

#### `find_local_social_dances(city_or_region: str)`
- **Purpose**: Locates Latin dance clubs, social dances, and congresses in the requested city.
- **Mechanism**: Uses OpenStreetMap public directory search with fallback to a curated directory of premier global Bachata hotspots (NYC, Madrid, London, Miami, LA, Paris).

---

### 3. Frontend & A2UI Enhancements
#### [frontend/static/index.html](file:///config/Desktop/BuildWithGemini/bachata-flow-coach/frontend/static/index.html)
- Add YouTube video iframe detection for text nodes containing `youtube.com/watch?v=...` or `youtu.be/...`.
- Add quick prompt chips for the new features (e.g., "🎬 YouTube Master Clips", "🔀 Combo Flow Builder", "🎯 Musicality Quiz").

---

## Verification Plan

### Automated Tests
1. **Unit Tests in `test_tools.py`**:
   - Test all new tool functions individually with realistic arguments.
   - Verify non-empty, well-formed dict/list return formats.
   - Run: `uv run python -m unittest test_tools.py` (ensure 100% pass rate).

### End-to-End Verification
1. **Local Test**: Verify local execution in `app/agent.py` and frontend proxy.
2. **Cloud Run & Agent Runtime Deployment**:
   - Deploy backend to Agent Platform: `agents-cli deploy`.
   - Deploy frontend to Cloud Run: `gcloud run deploy`.
3. **End-to-End Live Check**:
   - Test YouTube video embedding in chat card.
   - Test master clips lookup.
   - Test combo transition engine.
   - Test old features (Omni video, song audio previews, Firestore move lookups).
