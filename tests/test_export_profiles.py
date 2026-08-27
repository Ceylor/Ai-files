"""Tests for src/modules/mod10_final_features – export profiles, transitions, subtitles, color grading."""

from src.modules.mod10_final_features.export_profiles import ExportProfiles


class TestExportProfiles:
    """Tests for export profile definitions."""

    def test_all_qualities_exist(self):
        ep = ExportProfiles()
        expected = ["hd", "fhd", "4k"]
        for name in expected:
            assert name in ep.QUALITY_PRESETS, f"Quality '{name}' missing"

    def test_all_platforms_exist(self):
        ep = ExportProfiles()
        expected = ["tiktok", "yt_shorts", "instagram_reels", "youtube"]
        for name in expected:
            assert name in ep.PLATFORM_PRESETS, f"Platform '{name}' missing"

    def test_hd_quality_height(self):
        ep = ExportProfiles()
        assert ep.QUALITY_PRESETS["hd"]["height"] == 720

    def test_fhd_quality_height(self):
        ep = ExportProfiles()
        assert ep.QUALITY_PRESETS["fhd"]["height"] == 1080

    def test_4k_quality_height(self):
        ep = ExportProfiles()
        assert ep.QUALITY_PRESETS["4k"]["height"] == 2160

    def test_tiktok_vertical(self):
        ep = ExportProfiles()
        assert ep.PLATFORM_PRESETS["tiktok"]["aspect"] == "9:16"

    def test_youtube_horizontal(self):
        ep = ExportProfiles()
        assert ep.PLATFORM_PRESETS["youtube"]["aspect"] == "16:9"

    def test_list_platforms(self):
        ep = ExportProfiles()
        platforms = ep.list_platforms()
        assert "tiktok" in platforms
        assert len(platforms) >= 4

    def test_list_qualities(self):
        ep = ExportProfiles()
        qualities = ep.list_qualities()
        assert "fhd" in qualities
        assert len(qualities) >= 3

    def test_get_platform(self):
        ep = ExportProfiles()
        p = ep.get_platform("tiktok")
        assert p is not None
        assert p["aspect"] == "9:16"

    def test_get_platform_unknown(self):
        ep = ExportProfiles()
        assert ep.get_platform("nonexistent") is None

    def test_get_quality(self):
        ep = ExportProfiles()
        q = ep.get_quality("hd")
        assert q is not None
        assert q["height"] == 720

    def test_resolve_default(self):
        ep = ExportProfiles()
        result = ep.resolve()
        assert "width" in result
        assert "height" in result
        assert "bitrate" in result
        assert "vf" in result

    def test_resolve_tiktok_fhd(self):
        ep = ExportProfiles()
        result = ep.resolve(platform="tiktok", quality="fhd")
        assert result["height"] == 1080
        assert result["aspect"] == "9:16"
        assert result["width"] < result["height"]  # vertical

    def test_resolve_youtube_hd(self):
        ep = ExportProfiles()
        result = ep.resolve(platform="youtube", quality="hd")
        assert result["height"] == 720
        assert result["aspect"] == "16:9"
        assert result["width"] > result["height"]  # horizontal

    def test_resolve_custom_duration(self):
        ep = ExportProfiles()
        result = ep.resolve(platform="tiktok", max_duration=30)
        assert result["max_duration"] == 30


class TestTransitions:
    """Tests for transition engine."""

    def test_transition_engine_init(self):
        from src.modules.mod10_final_features.transitions import TransitionEngine
        engine = TransitionEngine()
        assert engine is not None

    def test_transition_engine_has_pick_transition(self):
        from src.modules.mod10_final_features.transitions import TransitionEngine
        engine = TransitionEngine()
        assert hasattr(engine, 'pick_transition')

    def test_pick_transition_returns_valid(self):
        from src.modules.mod10_final_features.transitions import TransitionEngine
        engine = TransitionEngine()
        result = engine.pick_transition(None, None)
        assert result in engine.TRANSITIONS

    def test_pick_transition_with_analysis(self):
        from src.modules.mod10_final_features.transitions import TransitionEngine
        engine = TransitionEngine()
        a1 = {"emotion": "excited", "motion_energy": 0.9}
        a2 = {"emotion": "calm", "motion_energy": 0.2}
        result = engine.pick_transition(a1, a2)
        assert result in engine.TRANSITIONS


class TestColorGrader:
    """Tests for color grading."""

    def test_color_grader_init(self):
        from src.modules.mod10_final_features.color_grade import ColorGrader
        grader = ColorGrader()
        assert grader is not None


class TestSubtitleStyler:
    """Tests for subtitle styling."""

    def test_styler_init(self):
        from src.modules.mod10_final_features.subtitles_style import EmojiSubtitleStyler
        styler = EmojiSubtitleStyler()
        assert styler is not None
