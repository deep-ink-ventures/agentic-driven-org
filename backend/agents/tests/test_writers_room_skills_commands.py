"""Tests for writers room workforce skills and commands folder structure."""

from agents.blueprints import get_blueprint


class TestStoryArchitectSkillsAndCommands:
    """Verify story_architect has commands in files and auto-discovered skills."""

    def test_commands_discovered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "write_structure" in names
        assert "fix_structure" in names
        assert "outline_act_structure" in names
        assert "map_subplot_threads" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("story_architect", "writers_room")
        skills = bp.skills_description
        assert "Three-Act Tension Mapping" in skills
        assert "Premise-to-Theme Ladder" in skills
        assert "Narrative Clock Design" in skills
        assert "Setup-Payoff Ledger" in skills
        assert "Structural Reversal Engineering" in skills

    def test_skills_format(self):
        bp = get_blueprint("story_architect", "writers_room")
        skills = bp.skills_description
        lines = [line for line in skills.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")

    def test_commands_use_blueprint_default(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["write_structure"].get("model") is None
        assert cmds["fix_structure"].get("model") is None


class TestDialogWriterSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "write_content" in names
        assert "fix_content" in names
        assert "write_scene_dialogue" in names
        assert "rewrite_for_subtext" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        skills = bp.skills_description
        assert "Subtext Layering" in skills
        assert "Voice Fingerprinting" in skills
        assert "Conflict Escalation Rhythm" in skills
        assert "Exposition Laundering" in skills
        assert "Silence and Non-Verbal Scripting" in skills

    def test_skills_format(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        skills = bp.skills_description
        lines = [line for line in skills.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")

    def test_commands_use_blueprint_default(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["write_content"].get("model") is None
        assert cmds["fix_content"].get("model") is None


class TestCharacterDesignerSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("character_designer", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "write_characters" in names
        assert "fix_characters" in names
        assert "build_character_profile" in names
        assert "design_character_voice" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("character_designer", "writers_room")
        skills = bp.skills_description
        assert "Wound-Want-Need Triangle" in skills
        assert "Contradiction Mapping" in skills
        assert "Behavioral Pressure Testing" in skills
        assert "Relationship Web Dynamics" in skills
        assert "Arc Milestone Design" in skills

    def test_skills_format(self):
        bp = get_blueprint("character_designer", "writers_room")
        skills = bp.skills_description
        lines = [line for line in skills.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")


class TestStoryResearcherSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("story_researcher", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "research" in names
        assert "revise_research" in names
        assert "profile_voice" in names
        assert "research_setting" in names
        assert "fact_check_narrative" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("story_researcher", "writers_room")
        skills = bp.skills_description
        assert "Lived-Detail Extraction" in skills
        assert "Anachronism Detection" in skills
        assert "Expert Knowledge Scaffolding" in skills
        assert "Cultural Sensitivity Audit" in skills
        assert "World-Building Consistency Check" in skills

    def test_skills_format(self):
        bp = get_blueprint("story_researcher", "writers_room")
        skills = bp.skills_description
        lines = [line for line in skills.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")


class TestStructureAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        names = {c["name"] for c in bp.get_commands()}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        skills = bp.skills_description
        assert "Pacing Heat Map" in skills
        assert "Scene Necessity Audit" in skills
        assert "Structural Symmetry Analysis" in skills
        assert "Point-of-View Discipline Check" in skills
        assert "Transition Flow Scoring" in skills

    def test_skills_format(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        lines = [line for line in bp.skills_description.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")


class TestCharacterAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("character_analyst", "writers_room")
        names = {c["name"] for c in bp.get_commands()}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("character_analyst", "writers_room")
        skills = bp.skills_description
        assert "Motivation Chain Validation" in skills
        assert "Consistency Drift Detection" in skills
        assert "Agency Audit" in skills
        assert "Distinctiveness Index" in skills
        assert "Emotional Arc Tracking" in skills

    def test_skills_format(self):
        bp = get_blueprint("character_analyst", "writers_room")
        lines = [line for line in bp.skills_description.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")


class TestDialogueAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        names = {c["name"] for c in bp.get_commands()}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        skills = bp.skills_description
        assert "Subtext Density Test" in skills
        assert "Voice Distinctiveness Scoring" in skills
        assert "Information Control Analysis" in skills
        assert "On-the-Nose Detection" in skills
        assert "Power Dynamic Mapping" in skills

    def test_skills_format(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        lines = [line for line in bp.skills_description.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")


class TestMarketAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("market_analyst", "writers_room")
        names = {c["name"] for c in bp.get_commands()}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("market_analyst", "writers_room")
        skills = bp.skills_description
        assert "Comp Title Analysis" in skills
        assert "Genre Convention Mapping" in skills
        assert "Audience Expectation Profiling" in skills
        assert "Commercial Hook Assessment" in skills
        assert "Trend Positioning" in skills

    def test_skills_format(self):
        bp = get_blueprint("market_analyst", "writers_room")
        lines = [line for line in bp.skills_description.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")


class TestFormatAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("format_analyst", "writers_room")
        names = {c["name"] for c in bp.get_commands()}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("format_analyst", "writers_room")
        skills = bp.skills_description
        assert "Manuscript Standards Compliance" in skills
        assert "Typographical Consistency Audit" in skills
        assert "Scene Break and Chapter Logic" in skills
        assert "Dialogue Punctuation and Attribution" in skills
        assert "Whitespace and Density Balance" in skills

    def test_skills_format(self):
        bp = get_blueprint("format_analyst", "writers_room")
        lines = [line for line in bp.skills_description.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")


class TestProductionAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("production_analyst", "writers_room")
        names = {c["name"] for c in bp.get_commands()}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("production_analyst", "writers_room")
        skills = bp.skills_description
        assert "Submission Package Readiness" in skills
        assert "Rights and Adaptation Potential" in skills
        assert "Production Complexity Scoring" in skills
        assert "Revision Prioritization Matrix" in skills
        assert "Publication Timeline Planning" in skills

    def test_skills_format(self):
        bp = get_blueprint("production_analyst", "writers_room")
        lines = [line for line in bp.skills_description.strip().split("\n") if line.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
