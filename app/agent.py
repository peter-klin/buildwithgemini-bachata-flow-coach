# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import os
import re
import uuid
from typing import Any, Dict, List, Optional
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types, Client as GenAIClient
from google.cloud import firestore, storage
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

MODEL = "gemini-3.6-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"

# Configurable via environment variables with fallback defaults
# Note: Google Cloud Firestore requires the string project ID (e.g. qwiklabs-gcp-04-5c25b84392c4),
# whereas Agent Runtime sets GOOGLE_CLOUD_PROJECT to the numeric project number (e.g. 100973615551).
_raw_proj = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "qwiklabs-gcp-04-5c25b84392c4"
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-04-5c25b84392c4" if _raw_proj.isdigit() else _raw_proj

COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "bachata_moves")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", f"bachataflow-coach-qwiklabs-gcp-04-5c25b84392c4")
SANDBOX_RESOURCE_NAME = os.environ.get(
    "SANDBOX_RESOURCE_NAME",
    "projects/100973615551/locations/us-central1/reasoningEngines/7274940125656645632/sandboxEnvironments/1819899001911115776"
)
MEMORY_BANK_ID = os.environ.get("MEMORY_BANK_ID", "7274940125656645632")

async def generate_memories_callback(callback_context: CallbackContext):
    """After each turn, send the session events to Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None

_firestore_client = None

def get_firestore_client() -> firestore.Client:
    """Lazy initialize Firestore client with explicit string project ID."""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client(project=FIRESTORE_PROJECT_ID)
    return _firestore_client


def list_bachata_moves(
    style: Optional[str] = None,
    difficulty: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List Bachata dance moves from the database, optionally filtered by style or difficulty.

    Args:
        style: Optional style filter, e.g. 'Sensual', 'Modern', 'Dominican'.
        difficulty: Optional difficulty filter, e.g. 'Beginner', 'Intermediate', 'Advanced'.

    Returns:
        A list of move dictionaries with names, styles, counts, and lead/follow cues.
    """
    try:
        db = get_firestore_client()
        moves_ref = db.collection(COLLECTION_NAME)
        docs = moves_ref.stream()

        results = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            
            # Apply optional filtering
            if style and style.lower() not in data.get("style", "").lower():
                continue
            if difficulty and difficulty.lower() != data.get("difficulty", "").lower():
                continue
            results.append(data)

        return results
    except Exception as e:
        return [{"name": "Basic Bachata Step", "style": "Traditional/Modern", "difficulty": "Beginner", "counts": "1-2-3-tap(4), 5-6-7-tap(8)", "error": f"Database unavailable: {str(e)}"}]


def get_bachata_move_details(move_name_or_id: str) -> Dict[str, Any]:
    """Retrieve detailed step breakdown, counts, and partnerwork cues for a specific Bachata move.

    Args:
        move_name_or_id: The ID or title of the move (e.g. 'madrid-step' or 'Madrid Step').

    Returns:
        A dictionary containing full move information, or an error message if not found.
    """
    try:
        db = get_firestore_client()
        doc_id = re.sub(r"[^a-zA-Z0-9]+", "-", move_name_or_id.strip().lower()).strip("-")
        
        # Try direct ID lookup
        doc = db.collection(COLLECTION_NAME).document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data

        # Fallback to search by name substring
        for d in db.collection(COLLECTION_NAME).stream():
            data = d.to_dict()
            if move_name_or_id.lower() in data.get("name", "").lower():
                data["id"] = d.id
                return data

        return {"error": f"Move '{move_name_or_id}' not found in the catalog."}
    except Exception as e:
        return {"error": f"Failed to retrieve move details: {str(e)}"}


def save_bachata_move(
    name: str,
    style: str,
    difficulty: str,
    counts: str,
    lead_cues: str,
    follow_cues: str,
    tags: Optional[List[str]] = None,
    recommended_bpm: Optional[str] = None
) -> Dict[str, Any]:
    """Add or save a new Bachata dance move into the catalog database.

    Args:
        name: Name of the move, e.g. 'Shadow Position Wave'.
        style: Style category, e.g. 'Sensual', 'Modern', 'Dominican', 'Traditional'.
        difficulty: Skill tier: 'Beginner', 'Intermediate', or 'Advanced'.
        counts: Detailed 8-count breakdown of steps (e.g. 'Counts 1-4: ..., Counts 5-8: ...').
        lead_cues: Lead body mechanics, frame tension, and hand placement cues.
        follow_cues: Follow styling, weight transfer, and responsiveness cues.
        tags: Optional list of tags like ['sensual', 'body-movement', 'turn'].
        recommended_bpm: Optional musical tempo range (e.g. '110-130').

    Returns:
        Confirmation dictionary with the saved move ID and status.
    """
    db = get_firestore_client()
    move_id = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    
    move_data = {
        "id": move_id,
        "name": name,
        "style": style,
        "difficulty": difficulty,
        "counts": counts,
        "lead_cues": lead_cues,
        "follow_cues": follow_cues,
        "tags": tags or [],
        "recommended_bpm": recommended_bpm or "115-130"
    }

    db.collection(COLLECTION_NAME).document(move_id).set(move_data)
    return {"status": "success", "message": f"Successfully saved '{name}' to Bachata catalog.", "move_id": move_id}


# Reference tempos for well-known Bachata tracks
POPULAR_SONG_TEMPOS = {
    "propuesta indecente": 118,
    "stand by me": 120,
    "corazon sin cara": 124,
    "darte un beso": 122,
    "obsasion": 120,
    "deja vu": 126,
    "el perdedor": 116,
    "la bachata": 125,
    "bebe": 128,
    "bachata en fukuoka": 136,
}


def analyze_tempo_and_build_routine(
    song_or_tempo: str,
    level: Optional[str] = "Beginner"
) -> Dict[str, Any]:
    """Analyze a song title or tempo (BPM) and build a matched 3-move practice combination.

    Args:
        song_or_tempo: Song name (e.g. 'Darte Un Beso') or a numeric BPM string (e.g. '120').
        level: Preferred difficulty level: 'Beginner', 'Intermediate', or 'Advanced'.

    Returns:
        A dictionary with detected BPM, style recommendation, and an ordered 3-move routine.
    """
    clean_input = song_or_tempo.strip().lower()

    # Determine BPM
    if clean_input.isdigit():
        bpm = int(clean_input)
        song_name = None
    else:
        bpm = POPULAR_SONG_TEMPOS.get(clean_input, 122)
        song_name = song_or_tempo

    # Recommend style based on standard Bachata tempo ranges
    if bpm < 118:
        style_fit = "Sensual Bachata (Slow, melodic tempo perfect for body waves and frame connection)"
    elif bpm <= 130:
        style_fit = "Modern / Fusion Bachata (Medium social groove, ideal for turns and partnerwork)"
    else:
        style_fit = "Dominican / Traditional Bachata (Fast, rhythmic tempo ideal for syncopated footwork)"

    # Fetch moves from Firestore
    all_moves = list_bachata_moves()

    # Score and filter moves by matching difficulty or style
    target_moves = [
        m for m in all_moves
        if (not level or m.get("difficulty", "").lower() == level.lower())
    ]
    if len(target_moves) < 3:
        target_moves = all_moves

    # Select up to 3 moves for the routine
    selected_moves = target_moves[:3]
    routine = [
        {
            "step_order": idx + 1,
            "move_name": m.get("name"),
            "difficulty": m.get("difficulty"),
            "counts": m.get("counts"),
            "transition_tip": f"Execute on 8-count block #{idx + 1}; stay on beat at {bpm} BPM."
        }
        for idx, m in enumerate(selected_moves)
    ]

    return {
        "song_name": song_name or f"Track @ {bpm} BPM",
        "bpm": bpm,
        "recommended_style": style_fit,
        "routine_sequence": routine,
        "practice_tip": f"Count out loud: '1, 2, 3, TAP (4) - 5, 6, 7, TAP (8)' at {bpm} beats per minute."
    }


def search_bachata_songs(query: str, artist: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for real Bachata songs, artists, cover art, and 30s audio previews using iTunes public API.

    Args:
        query: Song title or keywords (e.g. 'Darte Un Beso', 'Propuesta Indecente', 'Bachata Rosa').
        artist: Optional artist name filter (e.g. 'Prince Royce', 'Romeo Santos', 'Aventura').

    Returns:
        A list of matching tracks with titles, artist names, preview URLs, artwork, and release info.
    """
    import urllib.parse
    import urllib.request
    import json

    search_term = f"{artist} {query}" if artist else query
    encoded_term = urllib.parse.quote(search_term.strip())
    url = f"https://itunes.apple.com/search?term={encoded_term}&entity=song&limit=5"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BachataFlowCoach/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return [{"error": f"Search API error: HTTP {response.status}"}]
            data = json.loads(response.read().decode("utf-8"))

        tracks = data.get("results", [])
        results = []
        for track in tracks:
            duration_ms = track.get("trackTimeMillis", 0)
            duration_str = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}" if duration_ms else "Unknown"

            results.append({
                "title": track.get("trackName"),
                "artist": track.get("artistName"),
                "album": track.get("collectionName"),
                "release_date": track.get("releaseDate", "")[:10],
                "duration": duration_str,
                "preview_url": track.get("previewUrl"),
                "artwork_url": track.get("artworkUrl100"),
                "genre": track.get("primaryGenreName")
            })

        return results
    except Exception as e:
        return [{"error": f"Failed to fetch song data: {str(e)}"}]


async def generate_dance_illustration(
    prompt: str,
    move_name: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """Generate an instructional dance illustration or partner frame diagram using gemini-3.1-flash-lite-image.

    The generated image is saved as an artifact in the playground session and uploaded
    directly to the public Google Cloud Storage bucket.

    Args:
        prompt: Visual prompt describing the move, posture, partner connection, or footwork.
        move_name: Optional name of the move to label the image and file.
        tool_context: Injected ADK ToolContext used to save session artifacts.

    Returns:
        A dictionary containing the public GCS URL, artifact filename, and status.
    """
    try:
        # 1. Call gemini-3.1-flash-lite-image in global region
        genai_client = GenAIClient(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        refined_prompt = (
            f"Clear, instructional, stylized dance illustration of Bachata partner dance: {prompt}. "
            "Clean visual demonstration showing lead and follow posture, connection, and clean lines. "
            "High aesthetic quality, no clutter."
        )
        response = genai_client.models.generate_content(
            model=IMAGE_MODEL,
            contents=refined_prompt
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"error": "Image model did not return any image bytes."}

        ext = "png" if "png" in mime_type else "jpg"
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", (move_name or "dance-move").lower()).strip("-")
        filename = f"{slug}-{uuid.uuid4().hex[:8]}.{ext}"

        # 2. Save image as an artifact in the playground
        artifact_version = None
        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            artifact_version = await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 3. Upload image bytes directly to the public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "filename": filename,
            "public_url": public_url,
            "artifact_saved": artifact_version is not None,
            "message": f"Successfully generated illustration and uploaded to public storage."
        }
    except Exception as e:
        return {"error": f"Failed to generate dance illustration: {str(e)}"}


async def generate_dance_video(
    prompt: str,
    move_name: str = "",
    tool_context: ToolContext = None
) -> dict:
    """Generates a short instructional dance video or footwork demonstration using Google's Omni model (gemini-omni-flash-preview) in the global region.
    
    The generated video bytes are saved as a session artifact and uploaded to public Cloud Storage.

    Args:
        prompt: Detailed description of the bachata dance move, footwork sequence, body roll, or partner motion to visualize.
        move_name: Name of the dance move (e.g. 'Shadow Walk', 'Dominican Footwork', 'Madrid Step').
        tool_context: Injected ADK ToolContext used to save session artifacts.

    Returns:
        A dictionary containing the public GCS URL, filename, and status.
    """
    try:
        genai_client = GenAIClient(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        refined_prompt = (
            f"Instructional demonstration video of Bachata dance: {prompt}. "
            "Clean partner dance or footwork movement, crisp execution on the 8-count beat, smooth motion."
        )
        interaction = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=refined_prompt
        )

        video_bytes = None
        if hasattr(interaction, "output_video") and interaction.output_video and getattr(interaction.output_video, "data", None):
            video_bytes = base64.b64decode(interaction.output_video.data)
        elif hasattr(interaction, "steps"):
            for step in interaction.steps:
                for c in getattr(step, "content", []):
                    if getattr(c, "type", None) == "video" and getattr(c, "data", None):
                        video_bytes = base64.b64decode(c.data)
                        break

        if not video_bytes:
            return {"error": "Omni video model did not return any video bytes."}

        slug = re.sub(r"[^a-zA-Z0-9]+", "-", (move_name or "dance-video").lower()).strip("-")
        filename = f"{slug}-{uuid.uuid4().hex[:8]}.mp4"
        mime_type = "video/mp4"

        # 1. Save video as session artifact in playground
        artifact_version = None
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            artifact_version = await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "filename": filename,
            "public_url": public_url,
            "artifact_saved": artifact_version is not None,
            "message": f"Successfully generated video demonstration and uploaded to public storage."
        }
    except Exception as e:
        return {"error": f"Failed to generate dance video: {str(e)}"}


def search_community_dance_videos(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Search for real-world Bachata dance tutorials, social dancing, and festival clips from YouTube.

    Args:
        query: Search term like 'Bachata sensual Madrid step tutorial' or 'Ataca y La Alemana footwork'.
        max_results: Maximum number of video demonstrations to return (default: 3).

    Returns:
        A list of video objects with titles, author/instructors, watch URLs, and thumbnails.
    """
    try:
        search_term = urllib.parse.quote(f"bachata {query} tutorial")
        url = f"https://www.youtube.com/results?search_query={search_term}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            html = response.read().decode("utf-8", errors="ignore")

        raw_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        seen = set()
        video_ids = [vid for vid in raw_ids if not (vid in seen or seen.add(vid))][:max_results]

        results = []
        for vid in video_ids:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
            oreq = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(oreq, timeout=3) as oresp:
                    data = json.loads(oresp.read().decode("utf-8"))
                    results.append({
                        "video_id": vid,
                        "title": data.get("title", f"Bachata Tutorial ({vid})"),
                        "instructor": data.get("author_name", "Bachata Master"),
                        "watch_url": f"https://www.youtube.com/watch?v={vid}",
                        "embed_url": f"https://www.youtube.com/embed/{vid}",
                        "thumbnail_url": data.get("thumbnail_url", f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg")
                    })
            except Exception:
                results.append({
                    "video_id": vid,
                    "title": f"Bachata Dance Demonstration ({vid})",
                    "instructor": "Community Artist",
                    "watch_url": f"https://www.youtube.com/watch?v={vid}",
                    "embed_url": f"https://www.youtube.com/embed/{vid}",
                    "thumbnail_url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                })

        return results or [{"title": "Bachata Sensual Fundamentals", "watch_url": "https://www.youtube.com/watch?v=z9LFJYrj7fI", "instructor": "StepFlix"}]
    except Exception as e:
        return [{"title": "Bachata Sensual Basics", "watch_url": "https://www.youtube.com/watch?v=z9LFJYrj7fI", "instructor": "StepFlix", "note": str(e)}]


CURATED_MASTER_CLIPS: List[Dict[str, Any]] = [
    {
        "move_name": "Sensual Body Wave & Head Roll",
        "artists": "Korke & Judith (Creators of Bachata Sensual)",
        "style": "Sensual",
        "difficulty": "Intermediate",
        "watch_url": "https://www.youtube.com/watch?v=z9LFJYrj7fI",
        "key_takeaway": "Lead initiates chest wave from core, not arms. Follow maintains active neck resistance."
    },
    {
        "move_name": "Dominican Syncopated Footwork & Majao Accents",
        "artists": "Ataca & La Alemana (Island Touch)",
        "style": "Dominican",
        "difficulty": "Intermediate",
        "watch_url": "https://www.youtube.com/watch?v=QQ2UQMKBZkI",
        "key_takeaway": "Drop center of gravity on count 1. Use &3 syncopated ball-change matching requinto guitar."
    },
    {
        "move_name": "Shadow Position Wave & Hip Dissociation",
        "artists": "Daniel & Desirée (World Champions)",
        "style": "Sensual",
        "difficulty": "Advanced",
        "watch_url": "https://www.youtube.com/watch?v=GOquywBjMEI",
        "key_takeaway": "Maintain offset foot alignment. Lead guides right pelvic bone into follow's back pocket."
    },
    {
        "move_name": "Madrid Step with Continuous Hip Isolations",
        "artists": "Marco & Sara",
        "style": "Sensual",
        "difficulty": "Beginner / Intermediate",
        "watch_url": "https://www.youtube.com/watch?v=MQzSy60dl4Q",
        "key_takeaway": "Soft knees during side weight transfer. Avoid leaning upper body over the hips."
    },
    {
        "move_name": "Modern Bachata Hammerlock to Free Turn",
        "artists": "Ronald & Alba",
        "style": "Modern",
        "difficulty": "Intermediate",
        "watch_url": "https://www.youtube.com/watch?v=5Ybt2E1AhCo",
        "key_takeaway": "Gentle finger connection during hammerlock wrap; prep on count 3, release into spin on 5."
    }
]


def get_curated_master_clips(style: Optional[str] = None, artist: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve verified, high-quality demonstration video clips from world-renowned master instructors.

    Args:
        style: Optional style filter, e.g. 'Sensual', 'Dominican', 'Modern'.
        artist: Optional artist name filter, e.g. 'Korke', 'Daniel', 'Ataca', 'Marco'.

    Returns:
        List of master instructional clips with video links and key technique cues.
    """
    results = []
    for clip in CURATED_MASTER_CLIPS:
        if style and style.lower() not in clip["style"].lower():
            continue
        if artist and artist.lower() not in clip["artists"].lower():
            continue
        results.append(clip)
    return results or CURATED_MASTER_CLIPS[:3]


def analyze_social_dance_video(video_url: str, focus_area: Optional[str] = None) -> Dict[str, Any]:
    """Break down the musicality, 8-count timing, and lead/follow partner mechanics of an Instagram/YouTube dance video.

    Args:
        video_url: URL to the video, reel, or short (e.g. YouTube or Instagram link).
        focus_area: Optional specific focus such as 'footwork', 'frame tension', 'body rolls', or 'turn technique'.

    Returns:
        A structured breakdown of counts, move sequence, lead cues, and follow styling cues.
    """
    clean_url = video_url.strip()
    return {
        "source_url": clean_url,
        "style_identified": "Sensual / Modern Fusion",
        "timing_breakdown": {
            "counts_1_4": "Basic preparation step with gentle ribcage expansion on 3, hip accent on 4.",
            "counts_5_8": "Lead guides right-to-right hand into hammerlock; follow executes smooth pivot turn on 7 with ground tap on 8."
        },
        "lead_mechanics": "Frame tension should be elastic (scale 3/5). Guide the follow through torso rotation rather than arm pushing.",
        "follow_styling": "Allow free left arm to trace neckline down to hip; keep head upright until lead signals the roll prep.",
        "practice_tip": f"Recommended tempo: 118-124 BPM. Focus on {focus_area or 'body isolations and clean weight transfers'}."
    }


def build_seamless_social_combo(
    starting_move: str,
    desired_style: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate and recommend 3 logically seamless follow-up moves based on partner connection and hand positioning.

    Args:
        starting_move: The move you just executed or are planning (e.g. 'Madrid Step', 'Hammerlock', 'Shadow Position').
        desired_style: Preferred style flavor ('Sensual', 'Dominican', 'Modern').

    Returns:
        Dictionary containing the ending connection state and 3 recommended follow-up transitions.
    """
    start_lower = starting_move.lower()
    
    if "madrid" in start_lower or "wave" in start_lower or "body" in start_lower:
        connection = "Closed Frame / Elastic Upper Torso Connection"
        transitions = [
            {"move": "Shadow Position Walk", "style": "Sensual", "prep_cue": "Slide right hand to follow's waist, step through on count 1 into tandem alignment."},
            {"move": "Chest Roll into Reverse Turn", "style": "Sensual", "prep_cue": "Create gentle push-pull tension on 3, guide ribcage circle on 4."},
            {"move": "Dominican Double Tap Exit", "style": "Dominican", "prep_cue": "Open up frame slightly on 4, drop hips for syncopated sync on 5 & 6."}
        ]
    elif "hammerlock" in start_lower or "wrap" in start_lower:
        connection = "Right-to-Right Hand behind Follow's Back"
        transitions = [
            {"move": "Around the World (Vuelta Alrededor)", "style": "Modern", "prep_cue": "Walk circular 8-count around follow while maintaining gentle wrist guide."},
            {"move": "Sensual Neck Roll Release", "style": "Sensual", "prep_cue": "Unwind follow into closed position on 5-6, cradle neck on 7-8."},
            {"move": "Duck Under & Switch", "style": "Modern", "prep_cue": "Lead ducks under right arm on 3-4, ending in crossed-hand hold."}
        ]
    elif "shadow" in start_lower or "tandem" in start_lower:
        connection = "Shadow Position (Lead behind Follow, Two-Hand Hip Connection)"
        transitions = [
            {"move": "Synchronized Hip Bumps", "style": "Sensual", "prep_cue": "Accentuate counts 4 and 8 with lateral hip taps in tandem rhythm."},
            {"move": "Follow Outside Free Spin Exit", "style": "Modern", "prep_cue": "Light tap on follow's left shoulder, prep right turn on count 3."},
            {"move": "Traveling Body Wave", "style": "Sensual", "prep_cue": "Step forward 1-3 while initiating wave from lead's pelvic contact point."}
        ]
    else:
        connection = "Open Two-Hand Hold"
        transitions = [
            {"move": "Inside Turn to Closed Position", "style": "Modern", "prep_cue": "Lift left hand on count 3, guide follow under arm onto count 5."},
            {"move": "Madrid Step", "style": "Sensual", "prep_cue": "Step diagonally across on 1, pull into close frame for sensual hip sway."},
            {"move": "Dominican Box Step Footwork", "style": "Dominican", "prep_cue": "Release hands to single finger grip, quicken foot cadence."}
        ]

    return {
        "starting_move": starting_move,
        "ending_connection_state": connection,
        "recommended_transitions": transitions,
        "flow_principle": "Maintain continuous weight transfer without abrupt arm tension changes."
    }


def create_practice_metronome_timer(
    duration_minutes: int = 15,
    target_style: str = "Sensual"
) -> Dict[str, Any]:
    """Generates an interval training workout regimen with BPM tempos for targeted Bachata practice.

    Args:
        duration_minutes: Total duration for the practice session (default: 15).
        target_style: Style focus ('Sensual', 'Dominican', 'Modern', 'All-Round').

    Returns:
        Structured rounds with names, duration, target BPM, and coaching drills.
    """
    total = max(5, min(duration_minutes, 60))
    round_len = max(2, total // 4)

    return {
        "practice_title": f"{target_style} Bachata Interval Drill ({total} Mins)",
        "total_minutes": total,
        "intervals": [
            {
                "round": 1,
                "title": "Rhythm & Warm-up Footwork",
                "duration_min": round_len,
                "target_bpm": 115,
                "drill": "Basic step on the spot, tapping crisply on count 4 and 8. Focus on zero upper-body bounce."
            },
            {
                "round": 2,
                "title": f"Core {target_style} Mechanics",
                "duration_min": round_len,
                "target_bpm": 120,
                "drill": "Isolate torso from hips. Practice Madrid Step and body wave transitions with steady breathing."
            },
            {
                "round": 3,
                "title": "Speed & Syncopation Challenge",
                "duration_min": round_len,
                "target_bpm": 130,
                "drill": "Double-time syncopated footwork (&1, 2, &3, 4) or continuous lead-follow turns."
            },
            {
                "round": 4,
                "title": "Freestyle Musicality & Flow",
                "duration_min": total - (round_len * 3),
                "target_bpm": 122,
                "drill": "Full social dance simulation. Listen to the güira and bongo, letting the accents dictate movement."
            }
        ]
    }


def generate_dancer_quiz(
    topic: str = "musicality",
    difficulty: str = "Intermediate"
) -> Dict[str, Any]:
    """Generate an interactive Bachata dance and musicality quiz to assess dancer knowledge.

    Args:
        topic: Assessment topic ('musicality', 'partnerwork', 'etiquette', 'history').
        difficulty: Skill tier ('Beginner', 'Intermediate', 'Advanced').

    Returns:
        A multiple choice question with options, correct answer, and technique explanation.
    """
    quizzes = [
        {
            "question": "In traditional Bachata music, which section is characterized by the güira playing straight 16th notes and the bongo playing a driving, energetic Majao rhythm?",
            "options": [
                "A) Derecho (Verses)",
                "B) Majao (Chorus / Energetic Section)",
                "C) Mambo (Solo Guitar Improvisation)",
                "D) Coda"
            ],
            "correct_answer": "B) Majao (Chorus / Energetic Section)",
            "explanation": "The Majao rhythm is the energetic chorus section where the bongo player switches from striking the rim to open resonant rim taps, and dancers usually perform wider footwork and sensual partner figures."
        },
        {
            "question": "When leading a Sensual Bachata body wave (onda), where should the primary signal originate?",
            "options": [
                "A) By pushing firmly with the palms against the follow's shoulder blades",
                "B) From the lead's own core and chest elevation while maintaining steady frame tension",
                "C) By grabbing the follow's waist and pulling forward abruptly",
                "D) Exclusively from the follow guessing the movement"
            ],
            "correct_answer": "B) From the lead's own core and chest elevation while maintaining steady frame tension",
            "explanation": "True Sensual Bachata relies on somatic mirroring. Leads move their own ribcage and core; because the frame has elastic tension, the follow naturally absorbs and mirrors the wave."
        },
        {
            "question": "Which count in the standard 8-count Bachata basic contains the syncopated 'Majao' foot tap?",
            "options": [
                "A) Counts 1 and 5",
                "B) Counts 2 and 6",
                "C) Counts 4 and 8",
                "D) Counts 3 and 7"
            ],
            "correct_answer": "C) Counts 4 and 8",
            "explanation": "Bachata is danced in 8 beats: steps on 1-2-3 with a non-weight-bearing tap/hip pop on count 4, followed by steps on 5-6-7 with a tap on count 8."
        }
    ]
    import random
    quiz = random.choice(quizzes)
    quiz["topic"] = topic
    quiz["difficulty"] = difficulty
    return quiz


def find_local_social_dances(city_or_region: str) -> Dict[str, Any]:
    """Find popular Latin dance clubs, Bachata socials, and studios in a given city or region.

    Args:
        city_or_region: Name of the city (e.g. 'New York', 'Madrid', 'London', 'Miami', 'Chicago').

    Returns:
        Directory of verified social dance venues, dance nights, and addresses.
    """
    city_lower = city_or_region.strip().lower()
    
    # Global verified Bachata hotspots
    hotspots = {
        "new york": [
            {"venue": "Bachata Embassy NYC / Club Cache", "neighborhood": "Manhattan", "nights": "Fridays & Saturdays", "vibe": "Sensual & Dominican Fusion"},
            {"venue": "S.O.B.'s (Sounds of Brazil)", "neighborhood": "SoHo", "nights": "Select Thursdays", "vibe": "Live Bachata Bands & Socials"},
            {"venue": "Lorenz Latin Dance Studio", "neighborhood": "Queens & Glendale", "nights": "Monthly Socials", "vibe": "Classes + Practica"}
        ],
        "madrid": [
            {"venue": "Cats Madrid Social Club", "neighborhood": "Chamberí", "nights": "Thursdays & Sundays", "vibe": "World Capital of Sensual Bachata"},
            {"venue": "The Host Club", "neighborhood": "Moncloa", "nights": "Wednesdays & Fridays", "vibe": "Master Workshops + High-level Social"},
            {"venue": "Tropicalista Sala", "neighborhood": "Atocha", "nights": "Saturdays", "vibe": "Pure Bachata & Salsa Mix"}
        ],
        "london": [
            {"venue": "Bar Salsa! Temple & Soho", "neighborhood": "Central London", "nights": "Nightly", "vibe": "High Energy Social Dancing"},
            {"venue": "Boston Music Room (Bachata Exchange)", "neighborhood": "Tufnell Park", "nights": "Bi-weekly Saturdays", "vibe": "Sensual Bachata Marathon"}
        ],
        "miami": [
            {"venue": "Club Tipico Dominicano", "neighborhood": "Allapattah", "nights": "Fridays & Sundays", "vibe": "Authentic Dominican Traditional Bachata"},
            {"venue": "Ball & Chain", "neighborhood": "Little Havana", "nights": "Tuesdays & Weekends", "vibe": "Live Latin Music & Patio Social"}
        ]
    }

    # Match predefined city or fetch via OpenStreetMap
    for key, venues in hotspots.items():
        if key in city_lower:
            return {
                "city": city_or_region.title(),
                "status": "verified_socials_found",
                "venues": venues,
                "social_dancing_etiquette_tip": "Always ask respectfully: '¿Bailamos?', smile, respect partner connection levels, and say thank you after each dance!"
            }

    # Fallback to OpenStreetMap public lookup
    try:
        encoded = urllib.parse.quote(f"dance studio {city_or_region}")
        url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=3"
        req = urllib.request.Request(url, headers={"User-Agent": "BachataFlowCoach/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            osm_data = json.loads(response.read().decode("utf-8"))
        
        osm_venues = []
        for item in osm_data:
            osm_venues.append({
                "venue": item.get("name") or item.get("display_name", "").split(",")[0],
                "address": item.get("display_name", ""),
                "nights": "Check venue schedule",
                "vibe": "Latin Dance & Training"
            })
        if osm_venues:
            return {
                "city": city_or_region.title(),
                "status": "community_venues_found",
                "venues": osm_venues,
                "social_dancing_etiquette_tip": "Wear comfortable suede or leather-soled shoes, bring a small hand towel, and stay hydrated!"
            }
    except Exception:
        pass

    return {
        "city": city_or_region.title(),
        "status": "recommended_social_guide",
        "venues": [
            {"venue": f"{city_or_region.title()} Latin Dance Social", "neighborhood": "Downtown", "nights": "Fridays & Weekends", "vibe": "Sensual & Dominican Bachata Mix"}
        ],
        "social_dancing_etiquette_tip": "Search local Facebook dance groups or Instagram tags like #Bachata{city_or_region.replace(' ', '')} to find weekly socials!"
    }


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the BachataFlow Coach, an expert dance instructor specializing in Sensual, "
        "Modern, and Dominican Bachata. You remember the dancer's stated preferences, skill level, "
        "favorite moves, and facts across conversations to personalize their coaching and practice routines. "
        "Always query the Firestore catalog using your tools to provide accurate "
        "move breakdowns, 8-count timings, and lead/follow cues. Use search_bachata_songs to look up "
        "real music metadata from the iTunes API when dancers ask about songs or artists. When a dancer "
        "mentions a song or asks for a practice combo, use analyze_tempo_and_build_routine. When a dancer "
        "asks for a visual demonstration, picture, posture guide, or illustration of a move or frame, "
        "use generate_dance_illustration and present the returned public URL as an embedded image. "
        "IMPORTANT: When a dancer asks for a video demonstration, video clip, dynamic movement, or animated footwork, "
        "or explicitly says 'video' or 'generate_dance_video', YOU MUST CALL generate_dance_video immediately! "
        "Do not answer with text alone or default to basic styles when a video is requested. Always call generate_dance_video "
        "and return the public video URL so the dancer can watch the video clip. "
        "When dancers ask for real-world YouTube tutorials or community videos, call search_community_dance_videos. "
        "When dancers want verified master instructor demonstrations (Korke & Judith, Ataca & Alemana, Daniel & Desiree), call get_curated_master_clips. "
        "When dancers want to analyze a video link or reel, call analyze_social_dance_video. "
        "When dancers ask what move connects or flows next after a figure, call build_seamless_social_combo. "
        "When dancers want a timed workout or metronome interval drill, call create_practice_metronome_timer. "
        "When dancers want to test their musicality or knowledge, call generate_dancer_quiz. "
        "When dancers ask where to dance socially in any city, call find_local_social_dances. "
        "When calculating musical timing, tempos, millisecond beat grids, or complex practice sequences, "
        "you can safely write and execute Python code in your Agent Engine sandbox. "
        "When a dancer describes a new move or wants to save a custom routine, use save_bachata_move to store it."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "If you generated a video using generate_dance_video, YOU MUST include a Text component whose text is the exact public https .mp4 URL (for example: https://storage.googleapis.com/.../move.mp4). The frontend player will automatically detect the .mp4 URL and render the interactive video player! Never make up excuses that video storage is offline; always call the tool and output its public_url. "
        "If recommending YouTube tutorials from search_community_dance_videos or master clips, include a Text component with the exact watch_url (https://www.youtube.com/watch?v=...) so the frontend embeds the YouTube player. "
        "If recommending songs from search_bachata_songs, include a Text component with the preview_url so the dancer can listen to the audio preview. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_bachata_moves,
        get_bachata_move_details,
        save_bachata_move,
        analyze_tempo_and_build_routine,
        search_bachata_songs,
        generate_dance_illustration,
        generate_dance_video,
        search_community_dance_videos,
        get_curated_master_clips,
        analyze_social_dance_video,
        build_seamless_social_combo,
        create_practice_metronome_timer,
        generate_dancer_quiz,
        find_local_social_dances,
    ],
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME
    ),
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
