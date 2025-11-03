"""Tests for AttackSave model."""

import pytest
from foundry.actors.models import AttackSave, DamageFormula


class TestAttackSaveModel:
    """Tests for AttackSave model."""

    def test_basic_attack_save(self):
        """Should create basic attack save."""
        save = AttackSave(
            ability="con",
            dc=13,
            damage=[DamageFormula(number=2, denomination=6, bonus="", type="poison")],
            on_save="half"
        )

        assert save.ability == "con"
        assert save.dc == 13
        assert len(save.damage) == 1
        assert save.on_save == "half"

    def test_ongoing_damage_attack_save(self):
        """Should support ongoing damage effects."""
        save = AttackSave(
            ability="con",
            dc=21,
            damage=[],  # No immediate damage
            ongoing_damage=[DamageFormula(number=6, denomination=6, bonus="", type="poison")],
            duration_rounds=10,
            effect_description="Poisoned - can't regain HP"
        )

        assert save.ongoing_damage is not None
        assert len(save.ongoing_damage) == 1
        assert save.duration_rounds == 10

    def test_attack_save_on_save_validation(self):
        """Should validate on_save literal values."""
        # Valid values should work
        save1 = AttackSave(ability="dex", dc=15, on_save="half")
        save2 = AttackSave(ability="dex", dc=15, on_save="none")
        save3 = AttackSave(ability="dex", dc=15, on_save="full")

        assert save1.on_save == "half"
        assert save2.on_save == "none"
        assert save3.on_save == "full"

    def test_attack_save_frozen(self):
        """Should be immutable."""
        save = AttackSave(ability="wis", dc=14)

        with pytest.raises(Exception):  # Pydantic frozen error
            save.dc = 15
