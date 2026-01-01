"""Tests for foundry_converters module imports."""

import pytest


@pytest.mark.unit
class TestModuleImports:
    """Tests that all exports are accessible."""

    def test_imports_from_root(self):
        """Should import key items from foundry_converters."""
        from foundry_converters import (
            convert_to_foundry,
            ParsedActorData,
            Attack,
            Trait,
            convert_xml_to_journal_data,
        )

        assert callable(convert_to_foundry)
        assert ParsedActorData is not None

    def test_imports_from_actors(self):
        """Should import from foundry_converters.actors."""
        from foundry_converters.actors import (
            convert_to_foundry,
            ParsedActorData,
            Attack,
            Trait,
            DamageFormula,
            parse_senses,
        )

        assert callable(convert_to_foundry)
        assert callable(parse_senses)

    def test_imports_from_journals(self):
        """Should import from foundry_converters.journals."""
        from foundry_converters.journals import convert_xml_to_journal_data

        assert callable(convert_xml_to_journal_data)
