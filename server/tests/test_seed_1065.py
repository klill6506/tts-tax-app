import pytest

from apps.returns.management.commands.seed_1065 import Command as Seed1065Command
from apps.returns.models import FormDefinition, FormLine, FormSection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded(db):
    """Seed 1065 form definition."""
    cmd = Seed1065Command()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1065")


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeed1065:
    def test_seed_creates_form(self, seeded):
        assert seeded.code == "1065"
        assert seeded.name == "U.S. Return of Partnership Income"

    def test_seed_creates_sections(self, seeded):
        sections = FormSection.objects.filter(form=seeded)
        assert sections.count() == 6

    def test_seed_creates_lines(self, seeded):
        lines = FormLine.objects.filter(section__form=seeded)
        assert lines.count() == 97

    def test_seed_is_idempotent(self, seeded):
        # Run again
        cmd = Seed1065Command()
        cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
        cmd.handle()
        cmd.stdout.close()
        assert FormLine.objects.filter(section__form=seeded).count() == 97

    def test_mapping_keys_populated(self, seeded):
        lines_with_keys = FormLine.objects.filter(
            section__form=seeded, mapping_key__gt=""
        )
        # 82 non-computed lines have mapping keys
        assert lines_with_keys.count() > 50
