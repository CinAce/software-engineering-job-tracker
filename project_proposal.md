# Project Proposal: Software Engineering Job Tracker

## Overview
From the time between being a junior to the time when you graduate from university, being a student can at times be very stressful. Applying for tech roles frequently involves juggling several applications across different platforms or keeping track of interview rounds. To solve this, we are developing a centralized cloud-native job tracking API with the goal of providing an environment where users can log, update, and analyze personal application pipelines from initial submission to a final offer.

The core of the application is built using FastAPI for handling incoming user requests. It will use a relational database to manage data such as user profiles and job descriptions. Furthermore, the entire project will be fully containerized using Docker and orchestrated with Docker Compose to streamline the often chaotic job and internship application process.

## Users
Primary users of this product include computer science university students, recent graduates, and tech professionals looking to systematically track and manage their active job or internship application pipelines.

## MVP Features
1. Working FastAPI endpoints providing CRUD (Create, Read, Update, Delete) operations for job application entries.
2. Status pipeline tracking to update and manage every job entry through stages (e.g., Applied, Interviewing, Offer).
3. Relational data storage to securely hold company information, dates, and application notes.

## Out of Scope
1. Automatic resume parsing from uploaded PDF/Word documents.
2. Direct API integrations with external applicant tracking systems (such as Workday or Greenhouse).
3. Automated email or SMS reminder notifications for upcoming interviews.

## The Four Service Categories
* **Object Storage:** Will use the **S3 API** to store and retrieve user-uploaded documents (e.g., resumes and cover letters).
* **Database:** Will use the **PostgreSQL wire protocol** to manage structured relational data like users, applications, and status history.
* **Message Broker:** Will use **AMQP 0-9-1** to asynchronously queue and process background units of work (such as processing analytics or batch notifications).
* **Metrics Pipeline:** Will use **Prometheus exposition format** to emit system and application metrics for performance monitoring.

## Success Criteria
The project will be considered successful if users can efficiently perform end-to-end tracking of 10+ job applications through all pipeline stages with zero data loss, sub-200ms API response times locally, and complete all required asynchronous workflows.

## Team Information
* **Alberto Diaz Munoz** | CMU ID: 898508 | GitHub: `ADMMAC`
* **Marshaun Adams** | CMU ID: 901302 | GitHub: `CinAce`
* **Meeting Time Slots:** Mondays and Friday afternoons
* **Communication Channels:** Slack/Messages, Email, Zoom, and Blackboard
* **Team Roles:** 
  * Project Lead: Alberto and Marshaun
  * Backend Developer: Alberto and Marshaun
  * DevOps Engineer: Marshaun
  * Documentation Lead: Alberto
  *(Note: Roles will rotate throughout the semester)*
