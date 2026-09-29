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

# Hardcoded project ID, GCS bucket, Sandbox resource, and Memory Bank ID as strings to prevent resolution issues
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-04-5c25b84392c4"
COLLECTION_NAME = "bachata_moves"
GCS_BUCKET_NAME = "bachataflow-coach-qwiklabs-gcp-04-5c25b84392c4"
SANDBOX_RESOURCE_NAME = (
    "projects/100973615551/locations/us-central1/reasoningEngines/7274940125656645632/"
    "sandboxEnvironments/1819899001911115776"
)
MEMORY_BANK_ID = "7274940125656645632"

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


def get_bachata_move_details(move_name_or_id: str) -> Dict[str, Any]:
    """Retrieve detailed step breakdown, counts, and partnerwork cues for a specific Bachata move.

    Args:
        move_name_or_id: The ID or title of the move (e.g. 'madrid-step' or 'Madrid Step').

    Returns:
        A dictionary containing full move information, or an error message if not found.
    """
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
        "When a dancer asks for a video demonstration, video clip, dynamic movement, or animated footwork, "
        "use generate_dance_video and return the public video URL so the dancer can watch the video clip. "
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
        "If you generated a video, include a Text component with the public https video URL so it can be played. "
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
