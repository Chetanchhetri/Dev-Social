# DevSocial Backend 🚀

DevSocial is a feature-rich, high-performance social and project-management backend built with **FastAPI**, **SQLAlchemy**, **PostgreSQL**, and an integrated **fine-tuned local AI engine**. It empowers developers to host and sync project repositories, share multi-media community posts, and run instant AI-powered code reviews and explanations entirely on-device.

---

## 🌟 Key Features

* **Project Repository Management:**
  * **GitHub Import:** Sandboxed shallow cloning of public GitHub repositories with automated directory auditing.
  * **ZIP Project Extraction:** Secure upload and extraction of ZIP archives with built-in Zip-Bomb and path traversal protection.
  * **Git Synchronization:** One-click `git pull` syncing to keep imported projects updated with upstream remote sources.
  * **Recursive File Tree Indexing:** Builds lightweight JSON file tree structures for frontend visualization.

* **Community Posts & Multi-Media Hub:**
  * **Multi-Format Media Attachments:** Support for uploading **Images** (`.jpg`, `.png`, `.webp`, `.gif`), **Videos** (`.mp4`, `.mov`, `.mkv`), **PDFs**, and **Presentations** (`.ppt`, `.pptx`).
  * **Project & Link Linking:** Connect posts directly to an imported GitHub/ZIP project or external demo URL.
  * **Text Commentary:** Full support for post body text, code snippets, and markdown responses.

* **Integrated AI Code Review & Explainer Engine:**
  * **Fine-Tuned LLM:** Powered by `chetan272006/Qwen2.5-Coder-3B-Instruct` served locally via Hugging Face Transformers.
  * **Automated Code Review (`/ai/review`):** Audits code for security vulnerabilities (e.g., SQL injection, hardcoded secrets), performance bottlenecks, and anti-patterns, returning structured JSON scores and issue lists.
  * **AI Code Explainer (`/ai/explain`):** Generates line-by-line breakdowns, algorithmic logic summaries, and conceptual walkthroughs tailored to specific target audiences (`beginner`, `developer`, `non-technical`).

---

## 🏗️ Architecture & Security Highlights

* **Transactional State Machine:** Manages project lifecycle operations (`CREATED` $\rightarrow$ `RESERVED` $\rightarrow$ `STAGED` $\rightarrow$ `PROMOTED` $\rightarrow$ `COMPLETED`) using PostgreSQL 64-bit advisory locks (`pg_advisory_xact_lock`) to prevent race conditions during concurrent imports.
* **Isolated Media Namespaces:** Storage is strictly segregated into dedicated, isolated directories:
  * `uploads/projects/`: Active project files and working trees.
  * `uploads/posts/`: Community post media attachments.
  * `uploads/staging/`: Temporary workspaces for safe pre-promotion validation.
  * `uploads/backups/`: Rolling rollback snapshots during sync operations.
* **Hardened Sandbox Execution:** Runs Git CLI processes with strict flags (`core.hooksPath=/devnull`, `core.symlinks=false`), low-speed timeouts, and minimal environment variables to block execution of malicious hooks or symbolic link exploits.
* **Storage Quota & Fail-Closed Guards:** Enforces a 1 GB storage quota per user, 50 MB single-file limits, directory depth caps, and host disk capacity checks.
* **Cross-Platform Resilience:** Features custom permission handlers (`_safe_rmtree`) with `stat.S_IWRITE` to ensure read-only `.git/objects/pack` files clean up properly on Windows environments.

---

## 🛠️ Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Async web engine, Pydantic v2 validation, automatic OpenAPI generation)
* **Database & ORM:** [PostgreSQL](https://www.postgresql.org/) (with `pgvector` extension) & [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
* **AI Model Engine:** [Hugging Face Transformers](https://huggingface.co/docs/transformers/index), [PyTorch](https://pytorch.org/), and `chetan272006/Qwen2.5-Coder-3B-Instruct`
* **Version Control CLI:** System `git` binary via hardened `subprocess` execution

---

## 📁 Directory Structure

```text
devsocial-backend/
├── config/
│   └── settings.py          # Pydantic BaseSettings & Environment configuration
├── db/
│   └── session.py           # Database engine, session pooling, and seed functions
├── models/
│   ├── user.py              # User & UserRole ORM models
│   ├── project.py           # Project & ProjectOperation state machine models
│   └── post.py              # Community Post & Media attachment models
├── routes/
│   ├── auth_routes.py       # Authentication & user endpoints
│   ├── project_routes.py    # GitHub import, ZIP upload, and repo sync endpoints
│   ├── post_routes.py       # Community post creation & media upload endpoints
│   └── ai_routes.py         # AI Code Reviewer & Explainer endpoints
├── schemas/
│   ├── project_schema.py    # Project request & response validation schemas
│   ├── post_schema.py       # Post & Media attachment validation schemas
│   └── ai_schema.py         # AI request & response validation schemas
├── services/
│   ├── github_service.py    # Repository cloning, staging, state machine, and storage reconciliation
│   ├── post_service.py      # Media classification, size validation, and post storage
│   └── ai_code_service.py   # Singleton pipeline for local Qwen2.5-Coder LLM inference
├── uploads/                 # Local media storage root
│   ├── projects/            # Active project directories
│   ├── posts/               # Community media uploads
│   ├── staging/             # Temporary staging directories
│   └── backups/             # Rollback backup directories
├── app.py                   # FastAPI main entry point & router registration
├── docker-compose.yml       # Docker container setup for PostgreSQL + pgvector
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

🚀 Getting Started
Prerequisites
Python 3.10+

Docker & Docker Compose (for running PostgreSQL)

Git CLI installed and available on host system PATH

RAM / VRAM: Minimum ~4 GB free RAM (for running CPU inference) or 4 GB+ VRAM (for CUDA GPU acceleration)

Installation & Local Setup
Clone the Repository:

Bash
git clone [https://github.com/Chetanchhetri/devsocial-backend.git](https://github.com/Chetanchhetri/devsocial-backend.git)
cd devsocial-backend
Create and Activate Virtual Environment:

Linux/macOS:

Bash
python3 -m venv .venv
source .venv/bin/activate
Windows (PowerShell):

PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Install Dependencies:

Bash
pip install -r requirements.txt
Start PostgreSQL Database via Docker Compose:

Bash
docker-compose up -d
Configure Environment Variables:
Create a .env file in the root directory:

Code snippet
DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/devsocial_db
MEDIA_DIR=uploads
SUPERADMIN_NAME=Superadmin
SUPERADMIN_EMAIL=admin@devsocial.local
SUPERADMIN_PASSWORD=securepassword123
Start the FastAPI Backend Server:

Bash
python app.py
Access Interactive API Documentation:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

📖 API Endpoint Reference
1. Projects & Code Storage (/projects)
Method	Endpoint	Description
POST	/projects/import-github?user_id=1	Clones a public GitHub repo, audits structure, indexes file tree, and saves metadata.
POST	/projects/upload-zip	Uploads and extracts a project .zip archive with size/compression checks.
POST	/projects/{project_id}/sync?user_id=1	Triggers a sandboxed git pull operation to synchronize with remote origin.
2. Community Posts & Media (/posts)
Method	Endpoint	Description
POST	/posts/create?user_id=1	Creates a new post with optional Images, Videos, PDFs, PPTs, text, and project links.
GET	/posts/{post_id}	Fetches a post by ID with media attachment paths and metadata.
3. AI Code Reviewer & Explainer (/ai)
Method	Endpoint	Description
POST	/ai/review	Audits code snippet for bugs, vulnerabilities, and score using fine-tuned Qwen2.5-Coder.
POST	/ai/explain	Explains code architecture, logic, and line-by-line flow tailored for a target audience.
💡 Usage Examples
AI Code Review Request (POST /ai/review)

🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request or open an Issue for bug reports and feature requests.

📜 License
This project is open-source and available under the MIT License.
