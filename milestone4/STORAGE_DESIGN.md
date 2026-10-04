# Storage Design

## Object Key Design

The application uses two object key formats:

```text
uploads/YYYY/MM/DD/<uuid>.<ext>
direct/YYYY/MM/DD/<uuid>.<ext>
```

The `uploads/` prefix is used for normal files uploaded through the FastAPI application. The `direct/` prefix is used for files uploaded directly to object storage with a presigned PUT URL.

The date folders help organize the objects. A UUID is generated for every object so the application does not depend on the original filename being unique.

For example, two users could both upload a file named `resume.pdf` and receive keys like:

```text
uploads/2026/10/04/550e8400-e29b-41d4-a716-446655440000.pdf
uploads/2026/10/04/7a12aee1-c287-4fc9-a854-52c7bc188912.pdf
```

Both files can still have `resume.pdf` stored as their original filename in the database, but the generated UUIDs keep their object keys unique.

One tradeoff is that the original filename cannot be determined just by looking at the object key. For normal API uploads, the application keeps the original filename in the relational database and also stores it in the object's metadata.

## Content Type

The application determines the content type using an allowlist based on the file extension. It does not trust the content type supplied by the client.

The allowed types are:

| Extension | Content Type |
| --- | --- |
| `.csv` | `text/csv` |
| `.jpeg` | `image/jpeg` |
| `.jpg` | `image/jpeg` |
| `.pdf` | `application/pdf` |
| `.png` | `image/png` |
| `.txt` | `text/plain` |

This gives the application control over which types of files can be stored and served.

A dangerous example would be allowing an HTML file to be stored as `text/html`. If it was later opened using a presigned URL, the browser could treat the object as a web page and execute active content. Because of this risk, HTML is not included in the application's allowlist.

If a file should be stored but not displayed by the browser, a safer choice would be a type such as `application/octet-stream` and serving the object as a download.

## Bucket Layout

The application uses one bucket with separate prefixes:

```text
bucket/
├── uploads/
│   └── YYYY/MM/DD/<uuid>.<ext>
└── direct/
    └── YYYY/MM/DD/<uuid>.<ext>
```

### uploads/

**Writer:** FastAPI through `app/ports/storage.py`

**Readers:** FastAPI and clients using presigned GET URLs

Files under this prefix are uploaded through the application. The application validates the file before storing it and creates a relational database row containing the key, original filename, content type, size, and upload time.

### direct/

**Writer:** Client using a presigned PUT URL issued by FastAPI

**Readers:** Object storage tools and application workflows after reconciliation

For a direct upload, FastAPI creates the presigned URL, but the actual file bytes go directly from the client to object storage. The application does not receive the file bytes during the PUT.

This means a direct upload can create an object without creating a matching relational database row.

## Reconciliation

The current project uses `scripts/storage_report.py` to demonstrate a reconciliation sweep.

The report compares the objects in storage with the relational database index. It can detect:

- an object that exists in storage but has no database row
- a database row whose object no longer exists

For this project, a reconciliation sweep is the first choice because it works with the current local S3-compatible storage setup and is simple to run.

A future production version could use a completion callback or an object-store event after a successful direct upload. The current gap is that issuing a presigned PUT URL does not guarantee that the client will complete the upload or that a database row will be created afterward.

## Upload and Delete Ordering

For a normal API upload, the application validates the file first, writes the object to object storage, and then creates the relational database row. If the database write fails, the application attempts to delete the object it just created. If that cleanup also fails, an object could remain in storage without a matching database row.

For deletion, the application deletes the object first and then deletes its database row. If the object deletion fails, the database row is left unchanged. If the object is deleted successfully but deleting the database row fails, a database row could remain without its object.

The reconciliation report can detect both mismatch cases.
