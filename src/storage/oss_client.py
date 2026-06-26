"""阿里云 OSS 客户端封装 — 直接上传，不写本地磁盘"""

from src.util.config_loader import ConfigLoader


class OssClient:

    def __init__(self, config: ConfigLoader):
        import oss2
        auth = oss2.Auth(config.oss_access_key_id, config.oss_access_key_secret)
        self.bucket = oss2.Bucket(auth, config.oss_endpoint, config.oss_bucket)
        self.config = config
        get_logger().info(
            "OSS client ready (endpoint: %s, bucket: %s)",
            config.oss_endpoint, config.oss_bucket
        )

    def upload_string(self, key: str, content: str):
        try:
            self.bucket.put_object(key, content.encode("utf-8"))
            get_logger().info("Uploaded to OSS: %s/%s", self.config.oss_bucket, key)
        except Exception as e:
            get_logger().error("Failed to upload to OSS: %s", key, exc_info=e)

    def upload_file(self, key: str, filepath: str):
        try:
            self.bucket.put_object_from_file(key, filepath)
            get_logger().info("Uploaded file to OSS: %s/%s", self.config.oss_bucket, key)
        except Exception as e:
            get_logger().error("Failed to upload file to OSS: %s", key, exc_info=e)

    def build_key(self, layer: str, sub_dir: str, filename: str) -> str:
        prefix = self.config.oss_prefix
        if sub_dir:
            return f"{prefix}/{layer}/{sub_dir}/{filename}"
        return f"{prefix}/{layer}/{filename}"


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
