"""Object storage port — the S3 API.

The whole point of this module is what it does *not* contain: any provider name.

`boto3` speaks the S3 API. MinIO speaks the S3 API. So do a dozen commercial
services. The only thing that differs between them is the endpoint URL and the
credentials, and both of those come from the environment.

    modules 1-5   S3_ENDPOINT_URL=http://storage:9000     (MinIO, on your machine)
    modules 6-8   S3_ENDPOINT_URL=https://...             (whatever you chose)

Nothing below changes when you move. That is the lesson.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import BinaryIO, Iterable

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


@dataclass(frozen=True)
class StoredObject:
    key: str
    size: int
    etag: str


class ObjectStore:
    """A narrow S3-API client. Four operations, no provider-specific behavior."""

    def __init__(
        self,
        bucket: str | None = None,
        endpoint_url: str | None = None,
        region: str | None = None,
    ) -> None:
        self.bucket = bucket or os.environ["S3_BUCKET"]
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or os.environ["S3_ENDPOINT_URL"],
            region_name=region or os.getenv("S3_REGION", "us-east-1"),
            # path-style addressing works everywhere; virtual-host style does not
            # work against a local endpoint, so the course standardizes on path.
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    # -- lifecycle ------------------------------------------------------------
    def ensure_bucket(self) -> None:
        """Idempotent. Safe to call on every start."""
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
                raise
            self._client.create_bucket(Bucket=self.bucket)

    def empty_bucket(self) -> int:
        """Delete every object, including non-current versions.

        A plain bucket delete fails on a non-empty bucket, and on a versioned
        bucket 'empty' also means the delete markers. `bash scripts/cloud-down.sh <yourprovider>` depends
        on this working, so it is part of the port rather than a script.
        """
        removed = 0
        paginator = self._client.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=self.bucket):
            targets = [
                {"Key": item["Key"], "VersionId": item["VersionId"]}
                for group in ("Versions", "DeleteMarkers")
                for item in page.get(group, [])
            ]
            if targets:
                self._client.delete_objects(
                    Bucket=self.bucket, Delete={"Objects": targets}
                )
                removed += len(targets)
        return removed

    # -- objects --------------------------------------------------------------
    def put(self, key: str, fileobj: BinaryIO, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self._client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs=extra)

    def get(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def list(self, prefix: str = "") -> Iterable[StoredObject]:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                yield StoredObject(
                    key=item["Key"], size=item["Size"], etag=item["ETag"].strip('"')
                )

    def presigned_get(self, key: str, expires_in: int = 900) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def presigned_put(self, key: str, expires_in: int = 900) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
