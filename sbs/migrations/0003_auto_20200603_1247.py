# Generated by Django 2.2.6 on 2020-06-03 09:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sbs', '0002_sportsclub_isregister'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sportsclub',
            options={'default_permissions': (), 'managed': False},
        ),
        migrations.AddField(
            model_name='license',
            name='isFerdi',
            field=models.BooleanField(default=False),
        ),
    ]
