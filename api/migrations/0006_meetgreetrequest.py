from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0005_membershipwindow_sitevisit_ticketorder_and_more'),
    ]
    operations = [
        migrations.CreateModel(
            name='MeetGreetRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member_name', models.CharField(max_length=200)),
                ('member_email', models.EmailField()),
                ('preferred_date', models.CharField(max_length=50)),
                ('time_slot', models.CharField(max_length=50)),
                ('city', models.CharField(max_length=200)),
                ('hotel_name', models.CharField(blank=True, max_length=200)),
                ('hotel_room_type', models.CharField(blank=True, max_length=50)),
                ('group_size', models.CharField(blank=True, max_length=50)),
                ('vip_extras', models.TextField(blank=True)),
                ('special_requests', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending','Pending'),('confirmed','Confirmed'),('rejected','Rejected')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
