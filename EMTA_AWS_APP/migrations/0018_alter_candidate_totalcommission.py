# Generated by Django 5.0.3 on 2024-07-12 07:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EMTA_AWS_APP', '0017_alter_candidate_totalcommission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='totalCommission',
            field=models.CharField(max_length=10),
        ),
    ]
