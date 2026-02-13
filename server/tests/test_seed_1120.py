import pytest

from apps.returns.management.commands.seed_1120 import Command as Seed1120Command
from apps.returns.models import FormDefinition, FormLine, FormSection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded(db):
    """Seed 1120 form definition."""
    cmd = Seed1120Command()
    cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
    cmd.handle()
    cmd.stdout.close()
    return FormDefinition.objects.get(code="1120")


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeed1120:
    def test_seed_creates_form(self, seeded):
        assert seeded.code == "1120"
        assert seeded.name == "U.S. Corporation Income Tax Return"

    def test_seed_creates_sections(self, seeded):
        sections = FormSection.objects.filter(form=seeded)
        assert sections.count() == 9

    def test_seed_creates_lines(self, seeded):
        lines = FormLine.objects.filter(section__form=seeded)
        assert lines.count() == 172

    def test_seed_is_idempotent(self, seeded):
        # Run again
        cmd = Seed1120Command()
        cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
        cmd.handle()
        cmd.stdout.close()
        assert FormLine.objects.filter(section__form=seeded).count() == 172

    def test_mapping_keys_populated(self, seeded):
        lines_with_keys = FormLine.objects.filter(
            section__form=seeded, mapping_key__gt=""
        )
        # Most lines have mapping keys (except computed ones)
        assert lines_with_keys.count() > 100
