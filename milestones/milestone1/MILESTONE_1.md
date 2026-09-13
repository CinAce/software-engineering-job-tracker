### Part 2: API Endpoint Documentation

#### Core API Decisions
*   **Timed-out POST:** POST is not idempotent[cite: 3]. If a `POST` request times out, the client should query the collection via `GET` using filtering parameters to check if the resource was successfully created before attempting to send the payload again.
*   **DELETE Semantics:** Calling `DELETE` on a resource that has already been deleted will return a `404 Not Found`[cite: 3]. This ensures the client can rely on the fact that the specific resource they targeted does not exist.
*   **Empty Collections:** If a nested collection is empty but the parent exists, the API returns a `200 OK` with an empty list `[]`[cite: 3]. It will only return a `404 Not Found` if the parent resource does not exist[cite: 3].

#### Auth Endpoints
*   `POST /api/v1/auth/register` (Access: public)[cite: 3]
*   `POST /api/v1/auth/login` (Access: public)[cite: 3]

#### Resource Endpoints

**1. `GET /api/v1/applications`**
Retrieves a paginated list of the user's job applications, ordered by `created_at` descending.
*   **Access:** owner[cite: 3]
*   **Query parameters:** `limit` (integer, 1-100, default 20), `offset` (integer, >= 0)[cite: 3]
*   **Response 200:** list `[ApplicationOut]`[cite: 3]
    ```json
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
*   **Errors:** `401` if unauthorized[cite: 3].

**2. `GET /api/v1/companies/{company_id}/applications`**
Retrieves all applications submitted to a specific company (Nested Resource)[cite: 3].
*   **Access:** owner[cite: 3]
*   **Path parameters:** `company_id` (integer, > 0)[cite: 3]
*   **Response 200:** list `[ApplicationOut]`[cite: 3]
    ```json
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
*   **Errors:** `404` if the company does not exist. An empty list is `200`, not `404`[cite: 3].

**3. `POST /api/v1/applications`**
Creates a new job application record.
*   **Access:** owner[cite: 3]
*   **Request body:** `ApplicationCreate`[cite: 3]
    ```json
    {
      "company_id": 42, 
      "role": "Backend Engineer", 
      "resume_id": 7
    }
    ```
*   **Response 201:** `ApplicationOut`[cite: 3]
*   **Errors:** `404` if `company_id` or `resume_id` does not exist, `422` for validation errors[cite: 3].

**4. `DELETE /api/v1/applications/{application_id}`**
Deletes a specific job application record.
*   **Access:** owner[cite: 3]
*   **Path parameters:** `application_id` (integer, > 0)[cite: 3]
*   **Response 204:** No Content[cite: 3]
*   **Errors:** `404` if the application does not exist[cite: 3].

**5. `GET /api/v1/applications/{application_id}`**
Retrieves the full details of a specific job application record[cite: 3].
*   **Access:** owner[cite: 3]
*   **Path parameters:** `application_id` (integer, > 0)[cite: 3]
*   **Response 200:** `ApplicationOut`[cite: 3]
    ```json
    {
      "id": 1, 
      "company_id": 42, 
      "role": "Backend Engineer", 
      "status": "Interviewing", 
      "created_at": "2026-09-01T10:00:00Z"
    }
    ```
*   **Errors:** `404` if the application does not exist[cite: 3].

**6. `PATCH /api/v1/applications/{application_id}`**
Updates specific fields of an existing application, such as advancing its status[cite: 3].
*   **Access:** owner[cite: 3]
*   **Path parameters:** `application_id` (integer, > 0)[cite: 3]
*   **Request body:** `ApplicationUpdate`[cite: 3]
    ```json
    {
      "status": "Offer Received"
    }
    ```
*   **Response 200:** `ApplicationOut`[cite: 3]
    ```json
    {
      "id": 1, 
      "company_id": 42, 
      "role": "Backend Engineer", 
      "status": "Offer Received", 
      "created_at": "2026-09-01T10:00:00Z"
    }
    ```
*   **Errors:** `404` if the application does not exist, `422` for validation failures[cite: 3].

**7. `POST /api/v1/companies`**
Creates a new company record to associate with applications[cite: 3].
*   **Access:** owner[cite: 3]
*   **Request body:** `CompanyCreate`[cite: 3]
    ```json
    {
      "name": "Crozier: Consulting Engineers", 
      "industry": "Consulting"
    }
    ```
*   **Response 201:** `CompanyOut` (will include a `Location` header pointing to the new resource)[cite: 3]
    ```json
    {
      "id": 42, 
      "name": "Crozier: Consulting Engineers", 
      "industry": "Consulting"
    }
    ```
*   **Errors:** `409` if the company already exists (duplicate unique key), `422` for validation errors[cite: 3].

**8. `GET /api/v1/companies/{company_id}`**
Retrieves the details of a specific company[cite: 3].
*   **Access:** owner[cite: 3]
*   **Path parameters:** `company_id` (integer, > 0)[cite: 3]
*   **Response 200:** `CompanyOut`[cite: 3]
    ```json
    {
      "id": 42, 
      "name": "Crozier: Consulting Engineers", 
      "industry": "Consulting"
    }
    ```
*   **Errors:** `404` if the company does not exist[cite: 3].

**9. `POST /api/v1/resumes`**
Logs the metadata for a tailored resume uploaded for an application[cite: 3].
*   **Access:** owner[cite: 3]
*   **Request body:** `ResumeCreate`[cite: 3]
    ```json
    {
      "file_name": "FullStack_Resume_v2.pdf", 
      "notes": "Tailored for full-stack development roles"
    }
    ```
*   **Response 201:** `ResumeOut` (will include a `Location` header)[cite: 3]
    ```json
    {
      "id": 7, 
      "file_name": "FullStack_Resume_v2.pdf", 
      "notes": "Tailored for full-stack development roles", 
      "uploaded_at": "2026-09-02T11:15:00Z"
    }
    ```
*   **Errors:** `422` if required fields are missing or invalid[cite: 3].

**10. `GET /api/v1/resumes/{resume_id}`**
Retrieves the metadata for a specific uploaded resume[cite: 3].
*   **Access:** owner[cite: 3]
*   **Path parameters:** `resume_id` (integer, > 0)[cite: 3]
*   **Response 200:** `ResumeOut`[cite: 3]
    ```json
    {
      "id": 7, 
      "file_name": "FullStack_Resume_v2.pdf", 
      "notes": "Tailored for full-stack development roles", 
      "uploaded_at": "2026-09-02T11:15:00Z"
    }
    ```
*   **Errors:** `404` if the resume record does not exist[cite: 3].
