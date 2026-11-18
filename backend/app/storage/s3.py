from collections.abc import Iterator
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.storage.base import StorageBackend


class S3Storage(StorageBackend):
    """MinIO / S3-compatible object storage backend."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except ClientError:
                pass

    def put_file(self, key: str, file_path: Path, content_type: str = "application/octet-stream") -> None:
        self.client.upload_file(
            str(file_path),
            self.bucket,
            key.lstrip("/"),
            ExtraArgs={"ContentType": content_type},
        )

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key.lstrip("/"),
            Body=data,
            ContentType=content_type,
        )

    def download_file(self, key: str, dest_path: Path) -> None:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.client.download_file(self.bucket, key.lstrip("/"), str(dest_path))
        except ClientError as exc:
            raise FileNotFoundError(key) from exc

    def get_bytes(self, key: str) -> bytes:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key.lstrip("/"))
            return resp["Body"].read()
        except ClientError as exc:
            raise FileNotFoundError(key) from exc

    def get_size(self, key: str) -> int:
        try:
            resp = self.client.head_object(Bucket=self.bucket, Key=key.lstrip("/"))
            return int(resp["ContentLength"])
        except ClientError as exc:
            raise FileNotFoundError(key) from exc

    def iter_range(
        self, key: str, start: int, end: int, chunk_size: int = 262144
    ) -> Iterator[bytes]:
        try:
            resp = self.client.get_object(
                Bucket=self.bucket,
                Key=key.lstrip("/"),
                Range=f"bytes={start}-{end}",
            )
            body = resp["Body"]
            while True:
                chunk = body.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        except ClientError as exc:
            raise FileNotFoundError(key) from exc

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key.lstrip("/"))
            return True
        except ClientError:
            return False

    def delete_prefix(self, prefix: str) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix.lstrip("/")):
            objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects:
                self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": objects})

    def healthcheck(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False
