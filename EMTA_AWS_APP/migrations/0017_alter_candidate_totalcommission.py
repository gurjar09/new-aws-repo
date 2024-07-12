from django.db import migrations, models

def set_default_totalcommission(apps, schema_editor):
    Candidate = apps.get_model('EMTA_AWS_APP', 'Candidate')
    # Set a default value for totalCommission if necessary
    Candidate.objects.filter(totalCommission='').update(totalCommission=0)

class Migration(migrations.Migration):

    dependencies = [
        ('EMTA_AWS_APP', '0016_alter_candidate_commission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='totalCommission',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.RunPython(set_default_totalcommission),
    ]
