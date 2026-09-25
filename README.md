DevSocial Backend 🚀

A secure, AI-powered backend for developer communities, project repositories, media sharing, and local code intelligence.

DevSocial Backend is a FastAPI-based backend platform that combines project repository management, community posts, secure media handling, and a locally hosted AI code-review and explanation engine.

The backend is built around FastAPI, SQLAlchemy, PostgreSQL/pgvector, Git, and Hugging Face Transformers, with security-focused controls around repository imports, ZIP extraction, filesystem operations, and project synchronization.

✨ Highlights

📦 GitHub repository importing with sandboxed shallow cloning

🗜️ Secure ZIP project uploads with path-traversal and Zip-Bomb protections

🔄 Sandboxed Git synchronization for imported repositories

🌳 Recursive project file-tree indexing for frontend visualization

📝 Developer community posts with text, code, project, and external-link support

🖼️ Multi-media uploads for images, videos, PDFs, and presentations

🤖 Local AI code review powered by a fine-tuned Qwen2.5-Coder model

💡 AI code explanations for different audience levels

🔐 Transactional project lifecycle management using PostgreSQL advisory locks

💾 Separated storage namespaces for projects, posts, staging, and backups

🛡️ Fail-closed storage and filesystem safeguards

🪟 Windows-aware filesystem cleanup for imported Git repositories

🧩 Core Capabilities

1. Project Repository Management

DevSocial provides a controlled workflow for bringing external projects into the platform.

GitHub Import

Imports public GitHub repositories using shallow cloning.

Performs directory and project-structure auditing.

Stores project metadata and a lightweight file-tree representation.

ZIP Project Upload

Accepts project archives as ZIP files.

Validates archive size and structure.

Protects against:

Path traversal

Zip-Bomb style compression abuse

Excessive directory depth

Repository Synchronization

Synchronizes imported repositories with their upstream Git remote.

Uses a staged workflow and backup directories to reduce the impact of failed operations.

File Tree Indexing

Recursively builds lightweight JSON file-tree structures suitable for frontend visualization.

2. Community Posts & Media

Posts can combine developer-oriented content with project references and media.

Supported media includes:

Type

Formats

Images

.jpg, .png, .webp, .gif

Videos

.mp4, .mov, .mkv

Documents

.pdf

Presentations

.ppt, .pptx

Posts can also contain:

Text commentary

Code snippets

Markdown content

Links to imported projects

External demo URLs

3. AI Code Review & Explanation

DevSocial integrates a locally served fine-tuned language model:

Model: chetan272006/Qwen2.5-Coder-3B-Instruct

The model is served through the Hugging Face Transformers stack.

AI Code Review

POST /ai/review

The reviewer analyzes submitted code for issues such as:

Security vulnerabilities

SQL injection

Hardcoded secrets

Performance problems

Common programming anti-patterns

The endpoint returns structured review information including a score, detected issues, and suggested improvements.

AI Code Explanation

POST /ai/explain

The explainer can provide:

Line-by-line explanations

Algorithm and logic summaries

Architectural walkthroughs

Conceptual explanations

Supported audience targets include:

beginner

developer

non-technical

🏗️ Architecture

At a high level, DevSocial follows a layered FastAPI architecture:

                         ┌──────────────────────┐
                         │      Client / UI      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI API     │
                         │   Routes + Schemas   │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
      ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
      │ Project       │     │ Community     │     │ AI Services   │
      │ Services      │     │ Post Services │     │ Qwen2.5-Coder  │
      └───────┬───────┘     └───────┬───────┘     └───────────────┘
              │                     │
              └──────────────┬──────┘
                             ▼
                    ┌──────────────────┐
                    │ PostgreSQL       │
                    │ + pgvector       │
                    └──────────────────┘

                    Filesystem Storage
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          projects       posts       staging
                                      │
                                      ▼
                                   backups

🔐 Security Architecture

Security is a core part of the project-import and media-storage workflows.

Transactional Project State Machine

Project operations move through a controlled lifecycle:

CREATED
   │
   ▼
RESERVED
   │
   ▼
STAGED
   │
   ▼
PROMOTED
   │
   ▼
COMPLETED

PostgreSQL pg_advisory_xact_lock is used to coordinate concurrent project operations and reduce race conditions during imports and synchronization.

Isolated Storage Namespaces

uploads/
├── projects/    # Active project files and working trees
├── posts/       # Community media
├── staging/     # Temporary validation workspaces
└── backups/     # Rollback snapshots

Separating these namespaces helps prevent temporary files, uploaded media, and active repositories from being mixed together.

Hardened Git Execution

Git operations are executed through controlled subprocesses with security-focused settings including:

core.hooksPath=/dev/null

core.symlinks=false

Low-speed/time-out protections

Minimal process environment variables

These controls are intended to reduce exposure to malicious Git hooks and symbolic-link-based filesystem attacks.

Storage & Resource Guards

The backend enforces limits including:

1 GB storage quota per user

50 MB single-file limit

Directory-depth limits

Host disk-capacity checks

Fail-closed validation during storage operations

Cross-Platform Cleanup

The _safe_rmtree cleanup mechanism accounts for read-only Git files such as .git/objects/pack, particularly on Windows environments.

🛠️ Tech Stack

Layer

Technology

API Framework

FastAPI

Validation

Pydantic v2

Database

PostgreSQL

Vector Extension

pgvector

ORM

SQLAlchemy 2.0

AI Runtime

Hugging Face Transformers

ML Framework

PyTorch

Code Model

chetan272006/Qwen2.5-Coder-3B-Instruct

Version Control

Git CLI

Containerization

Docker / Docker Compose

Language

Python 3.10+

📁 Project Structure

devsocial-backend/
├── config/
│   └── settings.py              # Pydantic settings & environment configuration
│
├── db/
│   └── session.py               # Database engine, sessions & seed functions
│
├── models/
│   ├── user.py                  # User & UserRole ORM models
│   ├── project.py               # Project & operation state models
│   └── post.py                  # Post & media attachment models
│
├── routes/
│   ├── auth_routes.py           # Authentication & user endpoints
│   ├── project_routes.py        # GitHub import, ZIP & synchronization
│   ├── post_routes.py           # Posts & media upload endpoints
│   └── ai_routes.py             # AI review & explanation endpoints
│
├── schemas/
│   ├── project_schema.py        # Project validation schemas
│   ├── post_schema.py           # Post & media schemas
│   └── ai_schema.py             # AI request & response schemas
│
├── services/
│   ├── github_service.py        # Git import, staging & reconciliation
│   ├── post_service.py          # Media validation & storage
│   └── ai_code_service.py       # Local Qwen2.5-Coder inference pipeline
│
├── uploads/
│   ├── projects/                # Active project directories
│   ├── posts/                   # Community media
│   ├── staging/                 # Temporary staging directories
│   └── backups/                 # Rollback backups
│
├── app.py                       # FastAPI entry point
├── docker-compose.yml           # PostgreSQL + pgvector setup
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation

🚀 Getting Started

Prerequisites

Make sure the following are available:

Python 3.10+

Docker & Docker Compose

Git CLI available on the system PATH

Sufficient system memory for local model inference

Optional CUDA-compatible GPU for accelerated inference

Note: Actual AI inference requirements depend on the model configuration, quantization, device, and runtime settings. The local Qwen2.5-Coder model is the most resource-intensive component of the stack.

1. Clone the Repository

git clone https://github.com/Chetanchhetri/devsocial-backend.git
cd devsocial-backend

2. Create a Virtual Environment

Linux / macOS

python3 -m venv .venv
source .venv/bin/activate

Windows PowerShell

python -m venv .venv
.\.venv\Scripts\Activate.ps1

3. Install Dependencies

pip install -r requirements.txt

4. Start PostgreSQL

Start the PostgreSQL + pgvector environment using Docker Compose:

docker-compose up -d

Verify that the database container is running before starting the API.

5. Configure Environment Variables

Create a .env file in the project root:

DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/devsocial_db

MEDIA_DIR=uploads

SUPERADMIN_NAME=Superadmin
SUPERADMIN_EMAIL=admin@devsocial.local
SUPERADMIN_PASSWORD=securepassword123

Security note

Do not commit .env files or production credentials to Git.

Use strong, unique credentials when deploying outside a local development environment.

6. Start the Backend

python app.py

The API will be available at:

http://localhost:8000

📚 API Documentation

Once the server is running:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

These interfaces provide interactive API documentation generated by FastAPI.

🔌 API Reference

Projects

Method

Endpoint

Purpose

POST

/projects/import-github?user_id=1

Import a public GitHub repository, audit its structure, and index its file tree

POST

/projects/upload-zip

Upload and extract a ZIP project with security checks

POST

/projects/{project_id}/sync?user_id=1

Synchronize an imported repository with its remote origin

Community Posts

Method

Endpoint

Purpose

POST

/posts/create?user_id=1

Create a post with text, media, project references, or external links

GET

/posts/{post_id}

Retrieve a post and its media metadata

AI

Method

Endpoint

Purpose

POST

/ai/review

Review code for vulnerabilities, bugs, and other issues

POST

/ai/explain

Explain code architecture, logic, and execution flow

🤖 Example: AI Code Review

Request

POST /ai/review

{
  "code_snippet": "def get_user_data(user_id):\n    query = f'SELECT * FROM users WHERE id = {user_id}'\n    return db.execute(query).fetchall()",
  "programming_language": "python"
}

Example Response

{
  "model": "chetan272006/Qwen2.5-Coder-3B-Instruct",
  "status": "FAILED",
  "score": 50,
  "issues": [
    "SQL Injection Vulnerability",
    "Insecure Database Query String Interpolation"
  ],
  "suggestions": [
    "Use parameterized queries to prevent SQL injection.",
    "Consider using ORM libraries like SQLAlchemy for database interactions."
  ]
}

The example demonstrates how the AI reviewer can identify unsafe SQL construction and provide remediation suggestions.

🔄 Project Import Workflow

A typical repository import follows this sequence:

GitHub / ZIP
     │
     ▼
Input Validation
     │
     ▼
Staging Workspace
     │
     ▼
Security / Structure Checks
     │
     ▼
Project Promotion
     │
     ▼
Metadata + File Tree
     │
     ▼
Completed Project

Using a staging area allows validation to happen before project files are promoted into the active project namespace.

🛡️ Security Checklist

The current architecture includes protections for:

ZIP path traversal

ZIP compression abuse / Zip-Bomb checks

Git hook execution mitigation

Git symbolic-link restrictions

Storage quotas

Individual file-size limits

Directory-depth restrictions

Disk-capacity checks

Isolated staging directories

Rollback backup directories

Transaction-level advisory locking

Controlled Git subprocess execution

Security controls should still be reviewed and tested before production deployment.

🧪 Development

For local development, the recommended workflow is:

1. Start PostgreSQL / pgvector
2. Activate the Python virtual environment
3. Install dependencies
4. Configure .env
5. Start FastAPI
6. Open /docs
7. Exercise project, post, and AI endpoints

Because repository import and synchronization interact with the host filesystem and Git executable, development environments should be treated as trusted infrastructure.

⚠️ Production Considerations

Before deploying DevSocial publicly, review at minimum:

Authentication and authorization around every project and media operation

File upload limits and MIME/content validation

Filesystem permissions

Database credentials and secrets management

Reverse-proxy configuration

HTTPS/TLS

Rate limiting

AI inference resource limits

Logging and audit trails

Container and host isolation

Resource exhaustion protections

Backup and restore procedures

The repository-import functionality in particular should be deployed with appropriate filesystem isolation because it processes externally supplied project content.

🤝 Contributing

Contributions are welcome.

Typical contribution workflow:

git checkout -b feature/your-feature
# make your changes
git add .
git commit -m "feat: describe your change"
git push origin feature/your-feature

Then open a Pull Request describing:

What changed

Why the change was needed

Any security implications

API changes

Testing performed

Bug reports and feature requests can also be submitted through GitHub Issues.

📄 License

This project is available under the MIT License.

See the repository's LICENSE file for the complete license text.

👨‍💻 Project

DevSocial Backend

Built with:

FastAPI · PostgreSQL · SQLAlchemy · pgvector · PyTorch · Transformers · Git

