# skillhub_selfhost/skills/models.py
from tortoise.models import Model
from tortoise import fields


class Skill(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=128, unique=True, index=True)
    display_name = fields.CharField(max_length=256)
    description = fields.TextField()
    tags = fields.JSONField(default=[])
    author = fields.ForeignKeyField("models.User", related_name="skills")
    original_author = fields.CharField(max_length=128, null=True)
    source_url = fields.CharField(max_length=1024, null=True)
    download_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "skills"


class SkillVersion(Model):
    id = fields.UUIDField(pk=True)
    skill = fields.ForeignKeyField("models.Skill", related_name="versions")
    version = fields.CharField(max_length=32)
    release_notes = fields.TextField(null=True)
    file_size = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "skill_versions"
        unique_together = ("skill_id", "version")


class DownloadLog(Model):
    id = fields.UUIDField(pk=True)
    skill = fields.ForeignKeyField("models.Skill", related_name="download_logs")
    version = fields.CharField(max_length=32)
    downloaded_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "download_logs"