import unittest
from app.agent import get_bachata_move_details, list_bachata_moves, analyze_tempo_and_build_routine, search_bachata_songs

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

if __name__ == "__main__":
    unittest.main()
