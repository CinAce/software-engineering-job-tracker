## Part 1: Project Overview


The Software Engineering Job Tracker is a backend service designed to help university computer science students organize, prepare, and analyze their internship and full-time job applications. Navigating the recruitment cycle requires keeping track of numerous companies, timelines, and tailored documents. By keeping all this information in one place, users can maintain a clear view of their active pipeline and upcoming deadlines. The application's core features revolve around logging a job posting, updating its status asynchronously, and associating it with specific user assets. Users will create job entries, attach their resumes or cover letters used for that application, and move the application through stages such as rejections, applying, or interviewing. The goal is to make job hunting as easy and laid-back as possible.

| **Service CategoryInterfaceFeature Application** |                          |                                                                                                                                    |
| ------------------------------------------------ | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Relational Data**                              | PostgreSQL wire protocol | Storing core application data, including job details, interview schedules, and current application statuses.                       |
| **Object Storage**                               | S3 API                   | Storing and retrieving user-uploaded files, such as tailored PDF resumes and cover letters tied to specific applications.          |
| **Message Broker**                               | AMQP 0-9-1               | Queuing asynchronous background tasks, such as parsing job descriptions from URLs or generating daily application summary reports. |
| **Metrics**                                      | Prometheus exposition    | Tracking system health, including the number of applications logged per minute and the latency of the resume upload endpoints.     |

### Part 2: API Endpoint Documentation



#### Core API Decisions



- **Timed-out POST:** POST is not idempotent[cite: 3]. If a `POST` request times out, the client should query the collection via `GET` using filtering parameters to check if the resource was successfully created before attempting to send the payload again.
- **DELETE Semantics:** Calling `DELETE` on a resource that has already been deleted will return a `404 Not Found`[cite: 3]. This ensures the client can rely on the fact that the specific resource they targeted does not exist.
- **Empty Collections:** If a nested collection is empty but the parent exists, the API returns a `200 OK` with an empty list `[]`[cite: 3]. It will only return a `404 Not Found` if the parent resource does not exist[cite: 3].

#### Auth Endpoints



- `POST /api/v1/auth/register` (Access: public)[cite: 3]
- `POST /api/v1/auth/login` (Access: public)[cite: 3]

#### Resource Endpoints



**1.** **`GET /api/v1/applications`** Retrieves a paginated list of the user's job applications, ordered by `created_at` descending.

- **Access:** owner[cite: 3]
- **Query parameters:** `limit` (integer, 1-100, default 20), `offset` (integer, >= 0)[cite: 3]
- **Response 200:** list `[ApplicationOut]`[cite: 3]
  ```
  [
    {
      "id": 1, 
      "company_id": 42, 
      "role": "Backend Engineer", 
      "status": "Interviewing", 
      "created_at": "2026-09-01T10:00:00Z"
    }
  ]
  ```
  **svg**
- **Errors:** `401` if unauthorized[cite: 3].

**2.** **`GET /api/v1/companies/{company_id}/applications`** Retrieves all applications submitted to a specific company (Nested Resource)[cite: 3].

- **Access:** owner[cite: 3]
- **Path parameters:** `company_id` (integer, > 0)[cite: 3]
- **Response 200:** list `[ApplicationOut]`[cite: 3]
  ```
  [
    {
      "id": 2, 
      "company_id": 42, 
      "role": "Full Stack Intern", 
      "status": "Applied", 
      "created_at": "2026-09-10T14:30:00Z"
    }
  ]
  ```
  **svg**
- **Errors:** `404` if the company does not exist. An empty list is `200`, not `404`[cite: 3].

**3.** **`POST /api/v1/applications`** Creates a new job application record.

- **Access:** owner[cite: 3]
- **Request body:** `ApplicationCreate`[cite: 3]
  ```
  {
    "company_id": 42, 
    "role": "Backend Engineer", 
    "resume_id": 7
  }
  ```
  **svg**
- **Response 201:** `ApplicationOut`[cite: 3]
- **Errors:** `404` if `company_id` or `resume_id` does not exist, `422` for validation errors[cite: 3].

**4.** **`DELETE /api/v1/applications/{application_id}`** Deletes a specific job application record.

- **Access:** owner[cite: 3]
- **Path parameters:** `application_id` (integer, > 0)[cite: 3]
- **Response 204:** No Content[cite: 3]
- **Errors:** `404` if the application does not exist[cite: 3].

**5.** **`GET /api/v1/applications/{application_id}`** Retrieves the full details of a specific job application record[cite: 3].

- **Access:** owner[cite: 3]
- **Path parameters:** `application_id` (integer, > 0)[cite: 3]
- **Response 200:** `ApplicationOut`[cite: 3]
  ```
  {
    "id": 1, 
    "company_id": 42, 
    "role": "Backend Engineer", 
    "status": "Interviewing", 
    "created_at": "2026-09-01T10:00:00Z"
  }
  ```
  **svg**
- **Errors:** `404` if the application does not exist[cite: 3].

**6.** **`PATCH /api/v1/applications/{application_id}`** Updates specific fields of an existing application, such as advancing its status[cite: 3].

- **Access:** owner[cite: 3]
- **Path parameters:** `application_id` (integer, > 0)[cite: 3]
- **Request body:** `ApplicationUpdate`[cite: 3]
  ```
  {
    "status": "Offer Received"
  }
  ```
  **svg**
- **Response 200:** `ApplicationOut`[cite: 3]
  ```
  {
    "id": 1, 
    "company_id": 42, 
    "role": "Backend Engineer", 
    "status": "Offer Received", 
    "created_at": "2026-09-01T10:00:00Z"
  }
  ```
  **svg**
- **Errors:** `404` if the application does not exist, `422` for validation failures[cite: 3].

**7.** **`POST /api/v1/companies`** Creates a new company record to associate with applications[cite: 3].

- **Access:** owner[cite: 3]
- **Request body:** `CompanyCreate`[cite: 3]
  ```
  {
    "name": "Crozier: Consulting Engineers", 
    "industry": "Consulting"
  }
  ```
  **svg**
- **Response 201:** `CompanyOut` (will include a `Location` header pointing to the new resource)[cite: 3]
  ```
  {
    "id": 42, 
    "name": "Crozier: Consulting Engineers", 
    "industry": "Consulting"
  }
  ```
  **svg**
- **Errors:** `409` if the company already exists (duplicate unique key), `422` for validation errors[cite: 3].

**8.** **`GET /api/v1/companies/{company_id}`** Retrieves the details of a specific company[cite: 3].

- **Access:** owner[cite: 3]
- **Path parameters:** `company_id` (integer, > 0)[cite: 3]
- **Response 200:** `CompanyOut`[cite: 3]
  ```
  {
    "id": 42, 
    "name": "Crozier: Consulting Engineers", 
    "industry": "Consulting"
  }
  ```
  **svg**
- **Errors:** `404` if the company does not exist[cite: 3].

**9.** **`POST /api/v1/resumes`** Logs the metadata for a tailored resume uploaded for an application[cite: 3].

- **Access:** owner[cite: 3]
- **Request body:** `ResumeCreate`[cite: 3]
  ```
  {
    "file_name": "FullStack_Resume_v2.pdf", 
    "notes": "Tailored for full-stack development roles"
  }
  ```
  **svg**
- **Response 201:** `ResumeOut` (will include a `Location` header)[cite: 3]
  ```
  {
    "id": 7, 
    "file_name": "FullStack_Resume_v2.pdf", 
    "notes": "Tailored for full-stack development roles", 
    "uploaded_at": "2026-09-02T11:15:00Z"
  }
  ```
  **svg**
- **Errors:** `422` if required fields are missing or invalid[cite: 3].

**10.** **`GET /api/v1/resumes/{resume_id}`** Retrieves the metadata for a specific uploaded resume[cite: 3].

- **Access:** owner[cite: 3]
- **Path parameters:** `resume_id` (integer, > 0)[cite: 3]
- **Response 200:** `ResumeOut`[cite: 3]
  ```
  {
    "id": 7, 
    "file_name": "FullStack_Resume_v2.pdf", 
    "notes": "Tailored for full-stack development roles", 
    "uploaded_at": "2026-09-02T11:15:00Z"
  }
  ```
  **svg**
- **Errors:** `404` if the resume record does not exist[cite: 3].

### Part 3: Data Models

The following Pydantic v2 models define the request and response data used by the application. The models cover applications, companies, and resumes and provide basic validation before data reaches the database.

```python
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatus(str, Enum):
    SAVED = "Saved"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFER_RECEIVED = "Offer Received"
    REJECTED = "Rejected"


class ApplicationCreate(BaseModel):
    company_id: int = Field(gt=0)
    resume_id: int | None = Field(default=None, gt=0)
    role: str = Field(min_length=2, max_length=100)
    job_url: str | None = Field(
        default=None,
        max_length=2083,
        pattern=r"^https?://.+"
    )
    status: ApplicationStatus = Field(default=ApplicationStatus.SAVED)


class ApplicationUpdate(BaseModel):
    company_id: int | None = Field(default=None, gt=0)
    resume_id: int | None = Field(default=None, gt=0)
    role: str | None = Field(default=None, min_length=2, max_length=100)
    job_url: str | None = Field(
        default=None,
        max_length=2083,
        pattern=r"^https?://.+"
    )
    status: ApplicationStatus | None = Field(default=None)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    resume_id: int | None
    role: str
    status: ApplicationStatus
    created_at: datetime


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(
        default=None,
        max_length=2083,
        pattern=r"^https?://.+"
    )


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(
        default=None,
        max_length=2083,
        pattern=r"^https?://.+"
    )


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: str | None
    website: str | None


class ResumeCreate(BaseModel):
    file_name: str = Field(
        min_length=5,
        max_length=255,
        pattern=r"^.+\.pdf$"
    )
    notes: str | None = Field(default=None, max_length=1000)


class ResumeUpdate(BaseModel):
    file_name: str | None = Field(
        default=None,
        min_length=5,
        max_length=255,
        pattern=r"^.+\.pdf$"
    )
    notes: str | None = Field(default=None, max_length=1000)


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    notes: str | None
    uploaded_at: datetime
```

### Part 4: Database Schema

The database uses SQLAlchemy 2.0 ORM models. There are three main tables: `companies`, `applications`, and `resumes`. Foreign keys connect applications to their company and resume while allowing records to be removed without unnecessarily losing related application data.

```python
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ApplicationStatusEnum(str, Enum):
    SAVED = "Saved"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFER_RECEIVED = "Offer Received"
    REJECTED = "Rejected"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(2083), nullable=True)

    applications = relationship(
        "Application",
        back_populates="company",
        cascade="all, delete-orphan"
    )


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    storage_s3_key = Column(String(512), nullable=False)
    notes = Column(String(1000), nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    applications = relationship("Application", back_populates="resume")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    role = Column(String(100), nullable=False)
    job_url = Column(String(2083), nullable=True)
    status = Column(
        SQLEnum(ApplicationStatusEnum),
        nullable=False,
        default=ApplicationStatusEnum.SAVED
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    company = relationship("Company", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
```

The `company_id` foreign key uses `CASCADE`, so deleting a company also removes its associated applications. The `resume_id` foreign key uses `SET NULL`, so deleting a resume does not delete the application that used it. Instead, the application stays in the database without the resume attached.

Schema changes will be managed with **Alembic** migrations. This keeps database changes versioned and avoids relying on `Base.metadata.create_all` for changes to an existing database.

### Part 5: Error Contract

The API will use one general error format so clients do not have to handle a different response structure for each endpoint.

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested application record does not exist.",
    "details": [
      {
        "field": "application_id",
        "issue": "No application found with ID 999"
      }
    ]
  }
}
```

The three main fields are:

- `error.code` is a machine-readable error identifier.
- `error.message` gives a short explanation of what went wrong.
- `error.details` contains more specific information about the field or parameter that caused the error.

### Validation Errors

FastAPI normally returns validation errors using a `{"detail": [...]}` response. The application will use a custom `RequestValidationError` handler to convert these errors into the same error format used by the rest of the API.

Example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body validation failed.",
    "details": [
      {
        "field": "role",
        "issue": "String should have at least 2 characters"
      }
    ]
  }
}
```

### Status Codes

| Status Code | Meaning |
|---|---|
| `200 OK` | Request completed successfully. |
| `201 Created` | A new resource was created. |
| `204 No Content` | Resource was deleted successfully. |
| `400 Bad Request` | Request contains invalid or malformed parameters. |
| `401 Unauthorized` | Authentication is missing or invalid. |
| `403 Forbidden` | User does not have permission to access the resource. |
| `404 Not Found` | Requested resource does not exist. |
| `409 Conflict` | Request conflicts with an existing resource, such as a duplicate company name. |
| `422 Unprocessable Entity` | Request data failed validation. |
| `500 Internal Server Error` | Unexpected application error. |
| `503 Service Unavailable` | A required service such as PostgreSQL or S3 is unavailable. |

### Example Error Responses

#### 401 Unauthorized

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication credentials were missing or invalid.",
    "details": []
  }
}
```

#### 403 Forbidden

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to modify this application record.",
    "details": []
  }
}
```

#### 404 Not Found

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The specified company_id does not exist.",
    "details": [
      {
        "field": "company_id",
        "issue": "Company ID 42 was not found"
      }
    ]
  }
}
```

#### 409 Conflict

```json
{
  "error": {
    "code": "RESOURCE_CONFLICT",
    "message": "A company with this name already exists in the system.",
    "details": [
      {
        "field": "name",
        "issue": "Company 'Crozier: Consulting Engineers' already exists"
      }
    ]
  }
}
```

### Dependency Failures

If PostgreSQL or another required service is temporarily unavailable, the API will return `503 Service Unavailable` instead of `500 Internal Server Error`. A `Retry-After: 30` header will be included so the client knows the failure may be temporary.

Internal information such as stack traces, raw SQL queries, database schema details, and system hostnames will not be included in API error responses.
