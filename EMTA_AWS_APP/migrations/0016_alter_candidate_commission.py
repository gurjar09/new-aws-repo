

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EMTA_AWS_APP', '0015_alter_candidate_commission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='commission',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
