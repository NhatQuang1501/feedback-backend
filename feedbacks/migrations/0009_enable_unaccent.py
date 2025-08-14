from django.db import migrations
from django.contrib.postgres.operations import UnaccentExtension


class Migration(migrations.Migration):

	dependencies = [
		("feedbacks", "0008_alter_attachment_file_url"),
	]

	operations = [
		UnaccentExtension(),
	]


