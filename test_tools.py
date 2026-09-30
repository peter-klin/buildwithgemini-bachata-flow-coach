import unittest
from app.agent import (
    get_bachata_move_details,
    list_bachata_moves,
    analyze_tempo_and_build_routine,
    search_bachata_songs,
    search_community_dance_videos,
    get_curated_master_clips,
    analyze_social_dance_video,
    build_seamless_social_combo,
    create_practice_metronome_timer,
    generate_dancer_quiz,
    find_local_social_dances
)

class TestBachataTools(unittest.TestCase):
    def test_list_bachata_moves(self):
        moves = list_bachata_moves()
        self.assertIsInstance(moves, list)
        self.assertGreater(len(moves), 0)

    def test_get_bachata_move_found(self):
        res = get_bachata_move_details("Madrid Step")
        self.assertEqual(res["name"], "Madrid Step")
        self.assertIn("counts", res)
        self.assertIn("lead_cues", res)
        self.assertIn("follow_cues", res)

    def test_get_bachata_move_not_found(self):
        res = get_bachata_move_details("NonExistentMove999")
        self.assertIn("error", res)

    def test_analyze_tempo_and_build_routine(self):
        res = analyze_tempo_and_build_routine(song_or_tempo="125", level="Beginner")
        self.assertIn("bpm", res)
        self.assertEqual(res["bpm"], 125)
        self.assertIn("routine_sequence", res)
        self.assertEqual(len(res["routine_sequence"]), 3)

    def test_search_bachata_songs(self):
        songs = search_bachata_songs("Propuesta Indecente", "Romeo Santos")
        self.assertIsInstance(songs, list)
        self.assertGreater(len(songs), 0)
        self.assertEqual(songs[0]["artist"], "Romeo Santos")

    def test_search_community_dance_videos(self):
        clips = search_community_dance_videos("sensual body wave", max_results=2)
        self.assertIsInstance(clips, list)
        self.assertGreater(len(clips), 0)
        self.assertIn("watch_url", clips[0])

    def test_get_curated_master_clips(self):
        clips = get_curated_master_clips(style="Sensual")
        self.assertIsInstance(clips, list)
        self.assertGreater(len(clips), 0)
        self.assertTrue(any("Korke" in c["artists"] or "Daniel" in c["artists"] for c in clips))

    def test_analyze_social_dance_video(self):
        analysis = analyze_social_dance_video("https://www.youtube.com/shorts/test12345", focus_area="frame tension")
        self.assertIn("timing_breakdown", analysis)
        self.assertIn("lead_mechanics", analysis)
        self.assertIn("follow_styling", analysis)

    def test_build_seamless_social_combo(self):
        combo = build_seamless_social_combo("Madrid Step")
        self.assertIn("ending_connection_state", combo)
        self.assertIn("recommended_transitions", combo)
        self.assertEqual(len(combo["recommended_transitions"]), 3)

    def test_create_practice_metronome_timer(self):
        regimen = create_practice_metronome_timer(duration_minutes=20, target_style="Dominican")
        self.assertEqual(regimen["total_minutes"], 20)
        self.assertEqual(len(regimen["intervals"]), 4)

    def test_generate_dancer_quiz(self):
        quiz = generate_dancer_quiz(topic="musicality", difficulty="Intermediate")
        self.assertIn("question", quiz)
        self.assertIn("options", quiz)
        self.assertIn("correct_answer", quiz)

    def test_find_local_social_dances(self):
        ny_venues = find_local_social_dances("New York")
        self.assertIn("venues", ny_venues)
        self.assertGreater(len(ny_venues["venues"]), 0)

        madrid_venues = find_local_social_dances("Madrid")
        self.assertIn("venues", madrid_venues)
        self.assertGreater(len(madrid_venues["venues"]), 0)

if __name__ == "__main__":
    unittest.main()
