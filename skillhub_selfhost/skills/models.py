# skillhub_selfhost/skills/models.py
from tortoise.models import Model
from tortoise import fields

# Skill 的来源。local = 本地上传（有磁盘文件与 SkillVersion），
# gitlab = 远程引用（无版本，内容实时从仓库拉取）。
SOURCE_LOCAL = "local"
SOURCE_GITLAB = "gitlab"


class Skill(Model):
    id = fields.UUIDField(pk=True)
    # 名称只在同一作者内唯一：不同用户可以各自拥有一个叫 foo 的 skill
    name = fields.CharField(max_length=128, index=True)
    display_name = fields.CharField(max_length=256)
    description = fields.TextField()
    tags = fields.JSONField(default=[])
    author = fields.ForeignKeyField("models.User", related_name="skills")
    original_author = fields.CharField(max_length=128, null=True)
    source_url = fields.CharField(max_length=1024, null=True)
    source_type = fields.CharField(max_length=16, default=SOURCE_LOCAL)
    source_branch = fields.CharField(max_length=255, null=True)
    source_path = fields.CharField(max_length=1024, null=True)
    download_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "skills"
        unique_together = ("author_id", "name")


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