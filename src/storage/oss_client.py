"""阿里云 OSS 客户端封装"""

import os
from typing import Optional

from src.util.config_loader import ConfigLoader


class OssClient:
    """阿里云 OSS 客户端"""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.enabled = config.oss_enabled
        self.bucket = None

        if self.enabled:
            import oss2
            auth = oss2.Auth(config.oss_access_key_id, config.oss_access_key_secret)
            self.bucket = oss2.Bucket(auth, config.oss_endpoint, config.oss_bucket)
            logger = get_logger()
            logger.info(
                "OSS client initialized (endpoint: %s, bucket: %s)",
                config.oss_endpoint, config.oss_bucket
            )
        else:
            get_logger().info("OSS is disabled, data will be saved locally only")

    def upload_string(self, key: str, content: str):
        """上传字符串内容到 OSS"""
        if not self.enabled or self.bucket is None:
            return
        try:
            self.bucket.put_object(key, content.encode("utf-8"))
            get_logger().info("Uploaded to OSS: %s/%s", self.config.oss_bucket, key)
        except Exception as e:
            get_logger().error("Failed to upload to OSS: %s", key, exc_info=e)

    def upload_file(self, key: str, filepath: str):
        """上传本地文件到 OSS"""
        if not self.enabled or self.bucket is None:
            return
        try:
            self.bucket.put_object_from_file(key, filepath)
            get_logger().info("Uploaded file to OSS: %s/%s", self.config.oss_bucket, key)
        except Exception as e:
            get_logger().error("Failed to upload file to OSS: %s", key, exc_info=e)

    def build_key(self, layer: str, sub_dir: Optional[str], filename: str) -> str:
        """构建 OSS 对象键（路径）"""
        prefix = self.config.oss_prefix
        if sub_dir:
            return f"{prefix}/{layer}/{sub_dir}/{filename}"
        return f"{prefix}/{layer}/{filename}"

    def close(self):
        """关闭客户端"""
        if self.enabled:
            get_logger().info("OSS client shut down")


def get_logger():
    from src.util.logger_config import get_logger
    return get_logger(__name__)
