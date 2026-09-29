"""Seed script for BachataFlow Coach moves collection in Firestore."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-5c25b84392c4"
COLLECTION_NAME = "bachata_moves"

MOVES = [
    {
        "id": "madrid-step",
        "name": "Madrid Step",
        "style": "Modern / Sensual",
        "difficulty": "Beginner",
        "counts": "Counts 1-4: Step side left, together, side left, tap with hip pop. Counts 5-8: Repeat to right.",
        "lead_cues": "Maintain soft tension in palms, initiate side-to-side weight transfer through the torso.",
        "follow_cues": "Keep frame engaged, match lead's compression, isolate hip movement on count 4 and 8 tap.",
        "tags": ["footwork", "basic", "social-ready"],
        "recommended_bpm": "115-130"
    },
    {
        "id": "sensual-body-wave",
        "name": "Sensual Body Wave",
        "style": "Sensual",
        "difficulty": "Intermediate",
        "counts": "Counts 1-2: Chest forward and up. Counts 3-4: Roll through abdomen and hips into tap.",
        "lead_cues": "Right hand on follow's right shoulder blade, gentle diagonal push-up and roll downward.",
        "follow_cues": "Do not tense neck; lead the wave from the ribcage through the pelvis, keep knees soft.",
        "tags": ["sensual", "body-movement", "styling"],
        "recommended_bpm": "100-125"
    },
    {
        "id": "shadow-position-walk",
        "name": "Shadow Position Walk",
        "style": "Sensual / Modern",
        "difficulty": "Intermediate",
        "counts": "Counts 1-4: Prep and turn follow into shadow in front. Counts 5-8: Walk forward in tandem.",
        "lead_cues": "Lead follow into open right turn, catch left hip/waist with right hand, walk on matching counts.",
        "follow_cues": "Stay directly in front of lead's chest, step forward with right foot on count 5.",
        "tags": ["partnerwork", "shadow", "sensual"],
        "recommended_bpm": "110-130"
    },
    {
        "id": "syncopated-footwork-basic",
        "name": "Syncopated Dominican Footwork",
        "style": "Dominican / Traditional",
        "difficulty": "Advanced",
        "counts": "Counts 1, 2, & 3, 4: Quick syncopated ball-change on & 3, ground tap on 4.",
        "lead_cues": "Lower center of gravity, keep upper body still while feet work fast underneath.",
        "follow_cues": "Stay on balls of feet, mirror lead footwork, listen to the requinto guitar syncopation.",
        "tags": ["dominican", "footwork", "musicality", "syncopation"],
        "recommended_bpm": "125-145"
    },
    {
        "id": "hammerlock-sweetheart-exit",
        "name": "Hammerlock to Sweetheart Wrap",
        "style": "Modern",
        "difficulty": "Intermediate",
        "counts": "Counts 1-4: Inside turn to hammerlock behind back. Counts 5-8: Cross-body unwind to sweetheart wrap.",
        "lead_cues": "Keep hands low on hammerlock to protect follow's shoulder, guide unwind on count 5.",
        "follow_cues": "Maintain arm bend, never force or pull against the hammerlock arm connection.",
        "tags": ["partnerwork", "turns", "wrap"],
        "recommended_bpm": "115-135"
    }
]

def seed():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    batch = db.batch()
    
    for move in MOVES:
        doc_ref = db.collection(COLLECTION_NAME).document(move["id"])
        batch.set(doc_ref, move)
        print(f"Queued move: {move['name']} ({move['id']})")
        
    batch.commit()
    print(f"Successfully seeded {len(MOVES)} moves into '{COLLECTION_NAME}'!")

if __name__ == "__main__":
    seed()
