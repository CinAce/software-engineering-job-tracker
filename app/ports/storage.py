"""Object storage port using the S3 API.

All object-storage access for the application goes through this file.

The application talks to an S3-compatible API instead of depending on one
specific storage provider. Storage configuration, including endpoints,
bucket, region, and credentials, comes from environment variables.

An internal endpoint is used by the application for normal storage
operations. A public endpoint is used when generating presigned URLs for
clients outside the Docker Compose network.

The hostname is part of a SigV4 signature, so a presigned URL must be
created using the endpoint that the client will actually use.
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
    """A narrow client for the S3 API."""

    def __init__(
        self,
        bucket: str | None = None,
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
        region: str | None = None,
    ) -> None:
        self.bucket = bucket or os.environ["S3_BUCKET"]

        internal_endpoint = (
            endpoint_url
            or os.environ["S3_ENDPOINT_URL"]
        )

        public_endpoint = (
            public_endpoint_url
            or os.getenv("S3_PUBLIC_ENDPOINT_URL")
            or internal_endpoint
        )

        region_name = (
             region
                 or os.environ["S3_REGION"]
)

        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )

        self._client = boto3.client(
            "s3",
            endpoint_url=internal_endpoint,
            region_name=region_name,
            config=config,
        )

        self._public_client = boto3.client(
            "s3",
            endpoint_url=public_endpoint,
            region_name=region_name,
            config=config,
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(
                Bucket=self.bucket
            )

        except ClientError as exc:
            if exc.response["Error"]["Code"] not in (
                "404",
                "NoSuchBucket",
            ):
                raise

            self._client.create_bucket(
                Bucket=self.bucket
            )

    def empty_bucket(self) -> int:
        removed = 0

        paginator = self._client.get_paginator(
            "list_object_versions"
        )

        for page in paginator.paginate(
            Bucket=self.bucket
        ):
            targets = [
                {
                    "Key": item["Key"],
                    "VersionId": item["VersionId"],
                }
                for group in (
                    "Versions",
                    "DeleteMarkers",
                )
                for item in page.get(group, [])
            ]

            if targets:
                self._client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": targets},
                )

                removed += len(targets)

        return removed

    def put(
        self,
        key: str,
        fileobj: BinaryIO,
        content_type: str | None = None,
        original_name: str | None = None,
    ) -> None:
        extra = {}

        if content_type:
            extra["ContentType"] = content_type

        if original_name:
            extra["Metadata"] = {
                "original-name": original_name
            }

        self._client.upload_fileobj(
            fileobj,
            self.bucket,
            key,
            ExtraArgs=extra,
        )

    def get(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=self.bucket,
            Key=key,
        )

        return response["Body"].read()

    def head(self, key: str) -> dict:
        return self._client.head_object(
            Bucket=self.bucket,
            Key=key,
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )

    def list(
        self,
        prefix: str = "",
    ) -> Iterable[StoredObject]:
        paginator = self._client.get_paginator(
            "list_objects_v2"
        )

        for page in paginator.paginate(
            Bucket=self.bucket,
            Prefix=prefix,
        ):
            for item in page.get("Contents", []):
                yield StoredObject(
                    key=item["Key"],
                    size=item["Size"],
                    etag=item["ETag"].strip('"'),
                )

    def presigned_get(
        self,
        key: str,
        expires_in: int = 900,
    ) -> str:
        return self._public_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )

    def presigned_put(
        self,
        key: str,
        content_type: str | None = None,
        expires_in: int = 900,
    ) -> str:
        params = {
            "Bucket": self.bucket,
            "Key": key,
        }

        if content_type:
            params["ContentType"] = content_type

        return self._public_client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=expires_in,
        )
