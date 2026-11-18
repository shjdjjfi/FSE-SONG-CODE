from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="Song",
            fields=[("id", models.AutoField(primary_key=True, serialize=False))],
        ),
        migrations.CreateModel(
            name="SongProfile",
            fields=[("id", models.AutoField(primary_key=True, serialize=False))],
        ),
    ]
