# Generated by Django 2.2.6 on 2020-06-02 16:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sbs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sportsclub',
            name='isRegister',
            field=models.BooleanField(choices=[(True, 'Spor Kulubü'), (False, 'Diger(Özel Salon-Dojo-Sportif Dernek)')],
                                      default=False),
        ),
    ]
