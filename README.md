# MCP Tool Calling Agent

An intelligent **MCP-based tool-calling agent** that uses LangGraph, Streamlit, Databricks, vector search, and permission-aware tools to answer enterprise queries and perform controlled actions using structured company data and documents.

The project demonstrates how **Agentic AI, Model Context Protocol (MCP), tool calling, retrieval, permissions, Docker, testing, and CI/CD** can be combined into a practical enterprise application.

---

## 🚀 Project Overview

The **MCP Tool Calling Agent** is an AI-powered enterprise assistant designed to understand user queries, determine what information or tool is required, execute the appropriate tool, and generate a meaningful response.

Instead of depending only on a language model's internal knowledge, the agent can interact with external tools and structured enterprise resources.

The system supports:

* 🤖 Agentic AI reasoning
* 🔧 MCP-based tool calling
* 📊 Employee, department, and project information
* 📄 Company policy document retrieval
* 🔍 Vector-based document search
* 🔐 Permission-aware tool execution
* 🧠 LangGraph-based agent workflow
* 🖥️ Streamlit user interface
* 🐳 Docker containerization
* 🧪 Automated testing
* 🔄 Jenkins CI/CD integration
* ☁️ Databricks integration
* 📋 Structured logging and project documentation

---

# 🎯 Problem Statement

Enterprise information is usually distributed across multiple systems such as:

* Employee databases
* Department records
* Project information
* Company policies
* Internal documents
* Data platforms

Traditional applications require users to know exactly where the information exists and how to retrieve it.

This project provides an **AI-driven interface** where a user can ask a natural-language question and the agent determines the appropriate action.

### Example

Instead of manually searching multiple sources:

> "Who is working on the current AI project?"

the user can simply ask the agent.

The agent can determine the required tool, retrieve the relevant information, and provide the result.

---

# 💡 Solution

The project introduces an agentic architecture where the AI acts as an orchestrator.

### Basic workflow

```text
User
  ↓
Streamlit UI
  ↓
AI Agent
  ↓
LangGraph Workflow
  ↓
Intent / Tool Selection
  ↓
MCP Client
  ↓
MCP Server
  ↓
Permission Validation
  ↓
Selected Tool
  ↓
Data / Documents / Databricks
  ↓
Tool Result
  ↓
Agent
  ↓
Final Response
  ↓
Streamlit UI
```

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │       USER           │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    STREAMLIT UI      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    AGENT WORKFLOW    │
                    │      LangGraph       │
                    └──────────┬───────────┘
                               │
                     ┌─────────┴─────────┐
                     │                   │
                     ▼                   ▼
             ┌──────────────┐    ┌──────────────┐
             │ Tool Calling │    │ Vector Search│
             └──────┬───────┘    └──────┬───────┘
                    │                   │
                    ▼                   ▼
             ┌────────────────────────────────┐
             │          MCP CLIENT            │
             └───────────────┬────────────────┘
                             │
                             ▼
             ┌────────────────────────────────┐
             │           MCP SERVER           │
             └───────────────┬────────────────┘
                             │
                    ┌────────┴─────────┐
                    │                  │
                    ▼                  ▼
             ┌──────────────┐   ┌──────────────┐
             │ Permissions  │   │ MCP Tools    │
             └──────────────┘   └──────┬───────┘
                                       │
                       ┌───────────────┼──────────────┐
                       ▼               ▼              ▼
                ┌───────────┐   ┌────────────┐  ┌─────────────┐
                │ CSV/Data  │   │ Documents  │  │ Databricks  │
                └───────────┘   └────────────┘  └─────────────┘
```

---

# 🧠 Agentic AI Workflow

The agent follows a structured workflow instead of directly generating an answer.

### 1. User Query

The user enters a natural-language question through Streamlit.

Example:

```text
Show me the projects assigned to a particular employee.
```

### 2. Query Understanding

The agent analyzes the request and determines what type of information is required.

### 3. Tool Selection

The agent selects an appropriate MCP tool.

For example:

```text
Employee Query
Project Query
Department Query
Policy Search
Document Search
Databricks Query
```

### 4. Permission Validation

Before executing a protected operation, the MCP server checks whether the requested operation is permitted.

### 5. Tool Execution

The selected tool retrieves the required information.

### 6. Result Processing

The result is returned to the agent.

### 7. Final Response

The agent converts the structured result into a clear response for the user.

---

# 🔌 Model Context Protocol (MCP)

MCP is used as the communication layer between the AI agent and external tools.

The architecture separates:

```text
Agent
  ↓
MCP Client
  ↓
MCP Server
  ↓
Tools
```

This makes the system modular because tools can be added or modified without redesigning the complete agent.

---

# 🛠️ MCP Tools

The project contains a dedicated MCP server responsible for exposing controlled tools.

Tools can work with:

* Employee information
* Department information
* Project information
* Company policies
* Databricks data
* Document search
* Other enterprise resources

The MCP server also contains a permission layer to control access to operations.

---

# 🔐 Permission & Security Layer

Security is an important part of the project.

The MCP server includes permission handling so that tools are not treated as unrestricted functions.

The permission system can determine:

```text
User
  ↓
Requested Action
  ↓
Permission Check
  ↓
Allowed?
 ┌───────┴───────┐
 │               │
Yes              No
 │               │
 ▼               ▼
Execute       Reject
Tool          Request
```

This approach helps prevent unauthorized tool execution.

---

# 🔍 Vector Search

The project includes a vector-search component for working with unstructured documents.

The document workflow is:

```text
Documents
   ↓
Document Processing
   ↓
Chunking
   ↓
Embeddings
   ↓
Vector Store
   ↓
Similarity Search
   ↓
Relevant Information
   ↓
Agent Response
```

This allows the application to retrieve relevant information from documents instead of relying only on keyword matching.

---

# 📄 Enterprise Documents

The project contains example company documents such as:

```text
documents/
├── company_policy.txt
├── leave_policy.txt
└── security_policy.txt
```

These documents can be used by the retrieval and search components to answer policy-related questions.

### Example queries

```text
What is the company leave policy?

What are the security requirements?

What is the company policy regarding employees?

What are the rules mentioned in the security policy?
```

---

# 📊 Data Sources

The project includes structured datasets such as:

```text
data/
├── departments.csv
├── employees.csv
└── projects.csv
```

These datasets provide structured enterprise information that can be accessed through the agent's tools.

---

# ☁️ Databricks Integration

The project includes a dedicated Databricks module:

```text
databricks/
├── __init__.py
├── client.py
├── queries.py
└── setup.sql
```

The Databricks component provides a foundation for executing enterprise data queries through the agent.

This enables the architecture to move beyond local CSV data and integrate with a cloud-based data platform.

---

# 🖥️ User Interface

The application uses **Streamlit** to provide a simple interactive interface.

The interface allows users to:

* Enter natural-language queries
* Interact with the AI agent
* View generated responses
* Access enterprise information through tools
* Search available knowledge sources

The main application components include:

```text
app.py
streamlit_app.py
```

---

# 🧩 Project Structure

```text
mcp-tool-calling-agent/
│
├── agent/
│   ├── __init__.py
│   ├── graph.py
│   ├── nodes.py
│   ├── prompts.py
│   └── state.py
│
├── databricks/
│   ├── __init__.py
│   ├── client.py
│   ├── queries.py
│   └── setup.sql
│
├── data/
│   ├── departments.csv
│   ├── employees.csv
│   └── projects.csv
│
├── documents/
│   ├── company_policy.txt
│   ├── leave_policy.txt
│   └── security_policy.txt
│
├── mcp_server/
│   ├── __init__.py
│   ├── permissions.py
│   ├── server.py
│   └── tools.py
│
├── vector_search/
│   ├── __init__.py
│   ├── ingest.py
│   └── search.py
│
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_half2.py
│   ├── test_permissions.py
│   └── test_tools.py
│
├── app.py
├── config.py
├── mcp_client.py
├── streamlit_app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Jenkinsfile
├── .dockerignore
├── .env.example
├── .gitignore
└── README.md
```

---

# ⚙️ Technologies Used

| Technology     | Purpose                      |
| -------------- | ---------------------------- |
| Python         | Core application development |
| LangGraph      | Agent workflow orchestration |
| MCP            | Tool and context integration |
| Streamlit      | Web interface                |
| Databricks     | Enterprise data platform     |
| Vector Search  | Document retrieval           |
| Docker         | Containerization             |
| Docker Compose | Application orchestration    |
| Jenkins        | CI/CD automation             |
| Pytest         | Testing                      |
| CSV            | Example structured data      |
| Git            | Version control              |
| GitHub         | Source-code management       |

---

# 🐳 Docker

The application is containerized using Docker.

### Build the image

```bash
docker build -t mcp-agent .
```

### Run the container

```bash
docker run -p 8501:8501 mcp-agent
```

The Streamlit application can then be accessed through:

```text
http://localhost:8501
```

---

# 🐳 Docker Compose

The project also contains:

```text
docker-compose.yml
```

Run:

```bash
docker compose up --build
```

To run in the background:

```bash
docker compose up -d --build
```

To stop the application:

```bash
docker compose down
```

### Check running containers

```bash
docker ps
```

---

# 🔑 Environment Variables

Sensitive configuration should not be hardcoded into the source code.

The project provides:

```text
.env.example
```

Create your local environment file:

```text
.env
```

Add the required configuration values according to the `.env.example` file.

### Important

Do not commit secrets such as:

* API keys
* Database passwords
* Access tokens
* Cloud credentials
* Private keys

The `.env` file should remain excluded through `.gitignore`.

---

# 🧪 Testing

The project includes automated tests for important components.

Test files include:

```text
tests/
├── test_agent.py
├── test_half2.py
├── test_permissions.py
└── test_tools.py
```

Run:

```bash
pytest
```

For more detailed output:

```bash
pytest -v
```

Testing helps verify:

* Agent behavior
* Tool execution
* Permission handling
* Application functionality

---

# 🔄 CI/CD with Jenkins

The project includes a:

```text
Jenkinsfile
```

The Jenkins pipeline can automate the development workflow.

Typical pipeline:

```text
Developer
    ↓
Git Push
    ↓
Jenkins
    ↓
Checkout Code
    ↓
Install Dependencies
    ↓
Run Tests
    ↓
Build Docker Image
    ↓
Deploy / Run Application
```

This reduces manual deployment steps and provides a repeatable DevOps workflow.

---

# 🔁 Complete DevOps Workflow

```text
        Developer
            │
            ▼
         Git/GitHub
            │
            ▼
         Jenkins
            │
       ┌────┴────┐
       ▼         ▼
     Build      Test
       │         │
       └────┬────┘
            ▼
       Docker Build
            │
            ▼
      Docker Container
            │
            ▼
      Streamlit App
            │
            ▼
       AI Agent
            │
            ▼
        MCP Tools
            │
       ┌────┴─────┐
       ▼          ▼
    Documents   Databricks
       │          │
       └────┬─────┘
            ▼
        Final Result
```

---

# ▶️ Local Setup

## 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
```

Move into the project:

```bash
cd mcp-tool-calling-agent
```

---

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

Then add the required credentials and configuration.

---

## 5. Run the application

Depending on the configured entry point:

```bash
streamlit run streamlit_app.py
```

or:

```bash
streamlit run app.py
```

---

# 💬 Example Queries

The agent can be used for queries such as:

```text
Show employee information.

Which department does an employee belong to?

Show available projects.

Which employees are assigned to a project?

What is the leave policy?

What does the security policy say?

Search the company policy for a specific rule.

Retrieve information from the enterprise data source.
```

The exact available queries depend on the tools and data configured in the application.

---

# 🔐 Security Considerations

The project follows several security-oriented practices:

### Environment-based secrets

Credentials are stored through environment variables instead of being hardcoded.

### Permission-controlled tools

Tool execution can be restricted through the MCP permission layer.

### Container isolation

Docker provides an isolated runtime environment for the application.

### Controlled data access

The MCP architecture provides a controlled interface between the AI agent and enterprise resources.

### No secret commits

Sensitive files should be excluded using `.gitignore`.

---

# 📈 Advantages

* Natural-language interaction with enterprise data
* Modular MCP architecture
* Tool-based agent execution
* Permission-aware operations
* Document retrieval capability
* Vector search support
* Databricks integration
* Dockerized deployment
* Automated testing
* Jenkins CI/CD support
* Easy to extend with additional tools
* Clear separation between agent, tools, data, and UI

---

# ⚠️ Limitations

* AI responses depend on the quality of the underlying data and configuration.
* External API or model credentials may be required.
* Databricks functionality requires appropriate configuration.
* Vector search requires document ingestion and embedding configuration.
* Permission rules must be correctly configured.
* Production deployment requires additional security and monitoring measures.

---

# 🔮 Future Enhancements

Possible future improvements include:

* Role-based access control
* Authentication and user management
* More enterprise data connectors
* Advanced observability
* Agent execution tracing
* Better conversation memory
* Production vector database
* Cloud deployment
* Automated security scanning
* Container registry integration
* Kubernetes deployment
* Monitoring dashboards
* Advanced audit logging
* Multi-agent collaboration
* Human approval for sensitive operations

---

# 📚 Learning Outcomes

This project demonstrates practical experience with:

### Artificial Intelligence

* Agentic AI
* Tool calling
* LLM-based workflows
* Retrieval-augmented systems

### MCP

* MCP client architecture
* MCP server architecture
* Tool exposure
* Permission-controlled execution

### Software Development

* Python
* Modular application design
* Testing
* Configuration management

### DevOps

* Git
* Docker
* Docker Compose
* Jenkins
* CI/CD

### Data Engineering

* CSV-based data processing
* Databricks
* SQL
* Vector search
* Document retrieval

---

# 👩‍💻 Project Use Cases

This architecture can be adapted for:

* Enterprise AI assistants
* HR assistants
* Internal knowledge assistants
* IT support systems
* Company policy assistants
* Data analytics assistants
* Employee information systems
* Secure AI tool execution
* Enterprise document search

---

# 🏆 Project Highlights

> **MCP + Agentic AI + LangGraph + Vector Search + Databricks + Docker + Jenkins**

The project demonstrates how an AI agent can move beyond simple question answering and interact with controlled external tools and enterprise data sources.

The combination of **MCP, permission-aware tools, agent orchestration, retrieval, containerization, testing, and CI/CD** provides a foundation for building scalable enterprise AI applications.

---

# 📌 Quick Start

For a quick Docker-based setup:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>

cd mcp-tool-calling-agent

docker compose up --build
```

Then open:

```text
http://localhost:8501
```

---

# 📄 License

This project is intended for educational, demonstration, and development purposes.

Add an appropriate open-source license such as MIT if you intend to distribute the project publicly.

---

# 👩‍💻 Author

**Lalitha Chembeti**

Computer Science Engineering Student

GitHub:
https://github.com/24wh1a0535-hash

LinkedIn:
https://www.linkedin.com/in/lalitha-chembeti

---

# ⭐ Acknowledgements

This project was developed as a practical exploration of:

* Agentic AI
* Model Context Protocol
* LangGraph
* Enterprise data integration
* Vector search
* Docker
* Jenkins
* DevOps automation

If you find this project useful, consider giving the repository a ⭐ on GitHub.
