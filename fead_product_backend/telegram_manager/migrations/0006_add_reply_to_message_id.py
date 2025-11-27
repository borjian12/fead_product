# telegram_manager/migrations/0006_add_reply_to_message_id.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('telegram_manager', '0005_remove_telegrammessage_reply_to_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegrammessage',
            name='reply_to_message_id',
            field=models.BigIntegerField(blank=True, help_text='Telegram message ID to reply to (optional)', null=True, verbose_name='Reply to Message ID'),
        ),
    ]