# Generated by Django 2.2.6 on 2020-05-02 02:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sbs', '0009_auto_20200502_0453'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='gender',
            field=models.IntegerField(blank=True, choices=[(0, 'Erkek'), (1, 'Kadın')], null=True),
        ),
    ]
