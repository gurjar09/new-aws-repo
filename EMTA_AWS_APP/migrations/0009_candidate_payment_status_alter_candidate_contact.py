# Generated by Django 5.0.3 on 2024-07-08 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EMTA_AWS_APP', '0008_alter_candidate_contact'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='Payment_Status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Success', 'Success'), ('Under Process', 'Under Process')], default='Pending', max_length=30),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='Contact',
            field=models.CharField(choices=[('No', 'No'), ('Yes', 'Yes')], default='No', max_length=10),
        ),
    ]
