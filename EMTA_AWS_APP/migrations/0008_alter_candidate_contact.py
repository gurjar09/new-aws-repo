# Generated by Django 5.0.3 on 2024-07-08 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EMTA_AWS_APP', '0007_candidate_commission_generate_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='Contact',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Success', 'Success'), ('Under Process', 'Under Process')], default='Pending', max_length=30),
        ),
    ]