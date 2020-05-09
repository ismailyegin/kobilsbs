# Generated by Django 2.2.6 on 2020-05-09 00:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sbs', '0002_activity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='activity',
            name='compGeneralType',
        ),
        migrations.RemoveField(
            model_name='activity',
            name='compType',
        ),
        migrations.RemoveField(
            model_name='activity',
            name='isOpen',
        ),
        migrations.RemoveField(
            model_name='activity',
            name='registerFinishDate',
        ),
        migrations.RemoveField(
            model_name='activity',
            name='registerStartDate',
        ),
        migrations.AlterField(
            model_name='activity',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='activity',
            name='type',
            field=models.IntegerField(choices=[(0, 'YURT İÇİ FAALİYETLERİ'), (1, 'YURT DIŞI FAALİYETLERİ'), (2, 'EGİTİM FAALİYETLERİ')], db_column='Type'),
        ),
        migrations.AlterField(
            model_name='activity',
            name='year',
            field=models.IntegerField(),
        ),
    ]
