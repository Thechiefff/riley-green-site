from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0006_meetgreetrequest'),
    ]
    operations = [
        migrations.AddField(
            model_name='donationrequest',
            name='proof_image',
            field=models.ImageField(blank=True, null=True, upload_to='donation_proofs/'),
        ),
    ]
