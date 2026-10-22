# Milestone 4 - Object Storage Integration

This milestone adds object storage to the Software Engineering Job Tracker. Files are stored in RustFS using the S3-compatible API, while file information is stored in the SQLite database.

The application supports normal API uploads and downloads as well as presigned GET and PUT URLs.

## Setup

**1. Create the local environment file**

The project uses `.env.local` for local secrets and storage settings. This file is ignored by Git.

Create it from the example if needed:

    cp .env.local.example .env.local

The following environment variables are needed:

- `BROKER_USER` - RabbitMQ username
- `BROKER_PASSWORD` - RabbitMQ password
- `S3_ENDPOINT_URL` - internal object storage endpoint used by FastAPI
- `S3_PUBLIC_ENDPOINT_URL` - object storage endpoint used in presigned URLs
- `S3_BUCKET` - object storage bucket name
- `S3_REGION` - S3 region
- `AWS_ACCESS_KEY_ID` - object storage access key
- `AWS_SECRET_ACCESS_KEY` - object storage secret key

For local RustFS, the endpoint layout is:

    S3_ENDPOINT_URL=http://storage:9000
    S3_PUBLIC_ENDPOINT_URL=http://localhost:9000

The internal endpoint is used by the application container. The public endpoint is used in presigned URLs that the client opens from the host computer.

Do not commit `.env.local` or real credentials.

**2. Build and start the project**

    docker compose --env-file .env.local up -d --build

Check the containers:

    docker compose --env-file .env.local ps

Check the FastAPI health endpoint from inside the application container:

    docker compose --env-file .env.local exec -T app curl -s http://localhost:8000/health

The health response should show both the database and storage as `ok`.

## File Endpoints

**Upload one file**

Endpoint:

    POST /files

Example:

    printf 'Example upload\n' > example.txt

    curl -i \
      -X POST \
      -F "file=@example.txt" \
      http://localhost:8000/files

A successful upload returns `201 Created`.

The application validates the file before writing it to storage.

- Files larger than 10 MiB return `413`.
- Unsupported file types return `400`.

Allowed file extensions are:

- `.csv`
- `.jpeg`
- `.jpg`
- `.pdf`
- `.png`
- `.txt`

**Upload multiple files**

Endpoint:

    POST /files/multiple

Example:

    printf 'First file\n' > one.txt
    printf 'name,value\nexample,1\n' > two.csv

    curl -i \
      -X POST \
      -F "files=@one.txt" \
      -F "files=@two.csv" \
      http://localhost:8000/files/multiple

**List files**

Endpoint:

    GET /files

Example:

    curl -s http://localhost:8000/files

Pagination:

    curl -s "http://localhost:8000/files?limit=2&offset=0"

Filter by content type:

    curl -s "http://localhost:8000/files?content_type=text/plain"

Filter by part of the original filename:

    curl -s "http://localhost:8000/files?filename=example"

**Download through the API**

Endpoint:

    GET /files/download/{file_id}

Example using file ID 6:

    curl -i http://localhost:8000/files/download/6

FastAPI retrieves the object and returns the file using its stored content type.

**Delete a file**

Endpoint:

    DELETE /files/{file_id}

Example:

    curl -i \
      -X DELETE \
      http://localhost:8000/files/6

The object is removed from object storage and its database row is deleted.

Do not run this example against a file that you want to keep.

## Presigned URLs

**Presigned GET**

Endpoint:

    GET /files/{file_id}/url

Example:

    curl -s http://localhost:8000/files/6/url

The API returns a temporary URL. The client then downloads the file directly from object storage instead of sending the file bytes through FastAPI.

The default expiration is 900 seconds, or 15 minutes.

The allowed expiration range is 60 through 3600 seconds.

After expiration, object storage rejects the signed request and the client must request a new URL.

**Presigned PUT**

Endpoint:

    POST /files/presign?filename=example.txt

Example:

    curl -s -X POST \
      "http://localhost:8000/files/presign?filename=example.txt"

The response contains an object key, content type, expiration time, and presigned URL.

The client can then upload the file directly to that object-storage URL:

    printf 'Direct upload example\n' > example.txt

    curl -X PUT \
      -H "Content-Type: text/plain" \
      --upload-file example.txt \
      "$PUT_URL"

For a direct presigned PUT, the number of file bytes sent through FastAPI is:

    0 bytes

FastAPI only creates the signed URL. The client sends the actual file directly to object storage.

A direct PUT can create an object without a database row. The storage reconciliation report detects this condition.

## Presigned URL Hostname

The hostname used to create a presigned URL is part of the SigV4 signature.

Because of this, a URL signed for:

    http://storage:9000

cannot simply be changed to:

    http://localhost:9000

after it is created.

The application uses an internal endpoint for server-side storage operations and a public endpoint when generating URLs for clients.

## Database Index

The relational database stores file metadata.

Each stored file includes:

- object key
- original filename
- content type
- size in bytes
- upload time

The actual file contents are stored in object storage instead of the relational database.

## Object Keys

Normal API uploads use:

    uploads/YYYY/MM/DD/<uuid>.<extension>

Direct presigned uploads use:

    direct/YYYY/MM/DD/<uuid>.<extension>

User filenames are not used as object keys. UUIDs prevent files with the same original filename from colliding.

More information is in `STORAGE_DESIGN.md`.

## Storage Report

The storage report is located at:

    scripts/storage_report.py

The application image does not include the `scripts` directory. To run the report using the same Python environment and configuration as the application, copy the script into the running app container:

    docker compose --env-file .env.local cp scripts/storage_report.py app:/app/storage_report.py

Then run:

    docker compose --env-file .env.local exec -T app python storage_report.py

The report checks:

- objects without required metadata
- object keys that do not follow the key scheme
- objects with no database row
- database rows with no object
- bytes used by each top-level prefix
- total stored bytes

Exit codes:

    0 = clean
    1 = mismatches were found
    2 = the report could not complete

Clean and dirty report evidence is stored in:

    milestone4/evidence/report-clean.txt
    milestone4/evidence/report-dirty.txt

## Upload and Delete Ordering

For a normal upload, the application writes the object first and then writes the database row.

If the object upload fails, no database row is created.

If the database write fails after the object was uploaded, the application attempts to delete the object. If that cleanup also fails, an object without a database row can remain. The reconciliation report can detect this orphan.

For deletion, the object is deleted first and the database row is deleted second.

If the object deletion fails, the database row remains. If the object is deleted but the database delete fails, a database row can remain without its object. The reconciliation report can also detect this condition.

## Versioned Bucket Cleanup

A versioned S3 bucket may still contain old object versions and delete markers even when a normal object listing looks empty.

Because of this, cleanup for a versioned bucket must enumerate object versions and delete markers instead of relying only on `list_objects_v2`.

The `empty_bucket()` method in `app/ports/storage.py` uses `list_object_versions` and removes both `Versions` and `DeleteMarkers`.

This matters for later teardown because hidden versions can continue using storage even when the current objects appear to be gone.

## Architecture

The Milestone 4 architecture diagram is:

    milestone4/architecture-diagram.png

The normal file path sends file bytes through Nginx and FastAPI to object storage.

The presigned path is different. FastAPI creates the temporary URL, but the client transfers the actual file bytes directly with object storage.

## Evidence

Milestone evidence is stored in:

    milestone4/evidence/

The evidence files are:

- `upload.txt`
- `presigned.txt`
- `report-clean.txt`
- `report-dirty.txt`
- `teardown.txt`

`upload.txt` demonstrates upload validation, database metadata, object metadata, and deletion.

`presigned.txt` demonstrates direct GET and PUT operations.

`report-clean.txt` demonstrates a clean reconciliation report.

`report-dirty.txt` demonstrates detection of storage and database mismatches.

`teardown.txt` is created during the final teardown test.

## Provider Route

This project uses Route B for Milestone 4.

No real cloud account or paid cloud object-storage resources were created. RustFS is used locally as the S3-compatible object store.

Provider research and the planned cloud choice are documented in:

- `PROVIDER_SHORTLIST.md`
- `COST_AND_RISK.md`

## Team Work
**Alberto Diaz**

- Storage design documentation
- Provider research
- Cost and risk documentation
- Milestone 4 testing and evidence

**Marshaun Adams**

- Object storage integration
- File upload, listing, download, and delete endpoints
- Presigned GET and PUT support
- Storage reconciliation report


Other existing parts of the group project were developed during earlier milestones and remain part of the cumulative application.