# Software Engineering Job Tracker

## Team Roles
* **Alberto and Marshaun**: Project Lead
* **Alberto and Marshaun**: Backend Developer
* **Marshaun**: DevOps Engineer
* **Alberto**: Documentation Lead

## Project Overview
This repository contains a cloud-native FastAPI service for a Software Engineering Job Tracker. It aggregates job postings, tracks application statuses, and utilizes PostgreSQL for data storage, with all components orchestrated via Docker Compose.

## Run Instructions
1. Clone the repository to your local machine:
2. Navigate into the project directory:
3. Ensure Docker and Docker Compose are installed and running.
4. Build the image and start the service:
5. Access the API locally at `http://localhost:8000`.

## Teardown Instructions
To stop the application and clean up all associated data volumes, run the following exact command:
`docker compose down --volumes`

## Decisions
* **Concept Chosen:** Software Engineering Job Tracker.
* **Concepts Rejected:** Finance Manager and Fitness Supplement Analyzer.
* **Why:** The job tracker provides a highly achievable core loop (uploading job data, processing statuses asynchronously, and viewing applications) that perfectly fits the required service categories (relational database, message broker, object storage, and metrics) while maintaining a manageable scope.
