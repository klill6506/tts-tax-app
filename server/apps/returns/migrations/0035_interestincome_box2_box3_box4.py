# Generated migration: expand InterestIncome with 1099-INT boxes 2, 3, and 4.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("returns", "0034_w2income_employer_snapshot_and_box15"),
    ]

    operations = [
        migrations.AddField(
            model_name="interestincome",
            name="early_withdrawal_penalty",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="1099-INT Box 2: Early withdrawal penalty (flows to Schedule 1, Line 18).",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="interestincome",
            name="treasury_interest",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="1099-INT Box 3: Interest on U.S. Treasury obligations (taxable; flows to Line 2b).",
                max_digits=15,
            ),
        ),
        migrations.AddField(
            model_name="interestincome",
            name="federal_tax_withheld",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="1099-INT Box 4: Federal income tax withheld (flows to Line 25b).",
                max_digits=15,
            ),
        ),
    ]
