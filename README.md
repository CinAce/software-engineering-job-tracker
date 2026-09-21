# Software Engineering Job Tracker[cite: 4]

## Team Roles[cite: 4]
* **Alberto and Marshaun**: Project Lead[cite: 4]
* **Alberto and Marshaun**: Backend Developer[cite: 4]
* **Marshaun**: DevOps Engineer[cite: 4]
* **Alberto**: Documentation Lead[cite: 4]

## Project Overview[cite: 4]
This repository contains a cloud-native FastAPI service for a Software Engineering Job Tracker[cite: 4]. It aggregates job postings, tracks application statuses, and utilizes PostgreSQL for data storage, with all components orchestrated via Docker Compose[cite: 4].

## Local Development Runbook
### Prerequisites and Secrets
This project requires local secrets that are not committed to version control. 
1. Copy the example environment file: `cp .env.local.example .env.local`
2. Open `.env.local` and set the `BROKER_USER` and `BROKER_PASSWORD` variables. If these are not set, the stack will refuse to start.

### Run Instructions
1. Clone the repository to your local machine:[cite: 4]
   `git clone <your-repository-url>`
2. Navigate into the project directory:[cite: 4]
   `cd <your-project-directory>`
3. Ensure Docker and Docker Compose are installed and running.[cite: 4]
4. Start the core services and wait for them to be healthy:
   `docker compose --env-file .env.local up -d --wait`
5. Scale the API to 3 replicas for load balancing:
   `docker compose --env-file .env.local up -d --scale app=3`
6. Restart the gateway so Nginx resolves the new replica IPs:
   `docker compose --env-file .env.local restart gateway`
7. Access the API locally at `http://localhost:8000`.[cite: 4]

## Teardown Instructions[cite: 4]
To stop the application and clean up all associated data volumes, run the following exact command:[cite: 4]
`docker compose --env-file .env.local down --volumes`

## Decisions[cite: 4]
* **Concept Chosen:** Software Engineering Job Tracker.[cite: 4]
* **Concepts Rejected:** Finance Manager and Fitness Supplement Analyzer.[cite: 4]
* **Why:** The job tracker provides a highly achievable core loop (uploading job data, processing statuses asynchronously, and viewing applications) that perfectly fits the required service categories (relational database, message broker, object storage, and metrics) while maintaining a manageable scope.[cite: 4]