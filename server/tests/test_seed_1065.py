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
    cmd.handle(year=2025)
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
        assert sections.count() == 10

    def test_seed_creates_lines(self, seeded):
        lines = FormLine.objects.filter(section__form=seeded)
        assert lines.count() == 285

    def test_seed_is_idempotent(self, seeded):
        # Run again
        cmd = Seed1065Command()
        cmd.stdout = open("/dev/null", "w")  # noqa: SIM115
        cmd.handle(year=2025)
        cmd.stdout.close()
        assert FormLine.objects.filter(section__form=seeded).count() == 285

    def test_mapping_keys_populated(self, seeded):
        lines_with_keys = FormLine.objects.filter(
            section__form=seeded, mapping_key__gt=""
        )
        # Non-computed lines with mapping keys
        assert lines_with_keys.count() > 50

    def test_admin_section_exists(self, seeded):
        """Admin section for invoice/letter fields."""
        assert FormSection.objects.filter(form=seeded, code="admin").exists()

    def test_schedule_b_exists(self, seeded):
        """Schedule B — Other Information section."""
        assert FormSection.objects.filter(form=seeded, code="sched_b").exists()

    def test_schedule_k_guaranteed_payments(self, seeded):
        """K4a/K4b/K4c guaranteed payment lines exist."""
        k_lines = FormLine.objects.filter(
            section__form=seeded,
            line_number__in=["K4a", "K4b", "K4c"],
        )
        assert k_lines.count() == 3

    def test_schedule_k_self_employment(self, seeded):
        """K14a/K14b/K14c self-employment lines exist."""
        se_lines = FormLine.objects.filter(
            section__form=seeded,
            line_number__in=["K14a", "K14b", "K14c"],
        )
        assert se_lines.count() == 3

    def test_deductions_d_fields(self, seeded):
        """Named D_* deduction fields exist."""
        d_lines = FormLine.objects.filter(
            section__form=seeded,
            line_number__startswith="D_",
        )
        # ~30 named + 12 free-form (6 desc + 6 amount) + 2 computed (DED, NONDED)
        assert d_lines.count() >= 30

    def test_schedule_a_cogs(self, seeded):
        """Schedule A (COGS / Form 1125-A) exists."""
        assert FormSection.objects.filter(form=seeded, code="sched_a").exists()
        a_lines = FormLine.objects.filter(
            section__form=seeded,
            section__code="sched_a",
        )
        assert a_lines.count() == 10
