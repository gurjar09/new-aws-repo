# Generated by Django 5.0.3 on 2024-07-12 08:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EMTA_AWS_APP', '0019_candidate_sagar'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='candidate',
            name='sagar',
        ),
        migrations.AlterField(
            model_name='candidate',
            name='totalCommission',
            field=models.CharField(default='0', max_length=100),
        ),
    ]
