# Generated by Django 5.2.3 on 2025-06-12 21:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_rename_id_rapport_notification_rapport_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='rapport',
            new_name='id_rapport',
        ),
        migrations.RenameField(
            model_name='notification',
            old_name='user',
            new_name='id_user',
        ),
    ]
