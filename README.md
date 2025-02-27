# CrewAI Production Ready Template

A production-ready template for building multi-agent systems with [CrewAI](https://github.com/joaomdmoura/crewAI). This project provides a scalable, modular foundation for developing AI-driven workflows with multiple agents and tools, designed for real-world deployment. Currently includes Slack integration as an example, with an architecture designed to support multiple integrations.

## Overview

This template showcases a production-ready CrewAI implementation, featuring a research and writing crew as an example. It's built with best practices to support:
- **Multi-Agent Development**: Easily add new agents and tools via modular design.
- **Production Readiness**: Robust error handling, structured logging, and configuration management.
- **Scalability**: Abstract crew base class and dependency injection for flexibility.
- **Containerization**: Docker support with multi-stage builds and production-grade process management.
- **Extensible Integrations**: Modular design supporting multiple integration channels (Slack provided as example).
- **Conversation History**: Redis-backed conversation tracking with automatic expiration.
- **Retrieval-Augmented Generation (RAG)**: Vector database integration for knowledge base creation and querying.

## Features

- Multi-agent system with CrewAI (v0.102.0)
- Slack integration via `slack-bolt` (v1.22.0) as an example integration
- Agents powered by OpenAI (v1.63.2) and Anthropic (v0.34.1) LLMs
- Conversation history with Redis persistence (1-day retention)
- Configuration via `.env` with `python-dotenv` (v1.0.1)
- Structured JSON logging with `structlog` (v24.4.0)
- Dependency management with `pyproject.toml`
- Comprehensive unit tests using `pytest` (v8.3.2) and `pytest-asyncio` (v0.23.8)
- Python 3.12+ compatibility with modern type hints
- Docker support with multi-stage builds
- Process management with Supervisor
- Health checks and monitoring
- Production-grade logging configuration
- Message serialization with msgpack for efficient storage
- Automatic conversation cleanup with TTL
- **RAG Functionality**:
  - Vector database integration (Pinecone and Chroma)
  - Document processing pipeline with chunking and caching
  - Multiple embedding models (OpenAI and Sentence Transformers)
  - Document loaders for various sources (Web, Files, Slack)
  - Query processing and context enhancement
  - Document management tools

## Setup

### Prerequisites
- Python 3.12+ (for local development)
- Docker and Docker Compose (for containerized deployment)
- OpenAI and Anthropic API keys
- Slack app with Bot Token (`xoxb-...`) and App Token (`xapp-...`) (if using Slack integration)
- Redis (provided via Docker Compose for production)
- Vector database access (Pinecone API key or local Chroma DB)

### Local Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/raju-deriv/crewai-production-ready-template
   cd crewai-production-ready-template
   ```

2. **Set Up Environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your configuration including RAG settings
   ```

3. **Install Dependencies**:
   ```bash
   pip install -e .
   ```

4. **Vector Database Setup**:
   - For Pinecone: Create an account, create an index, and add your API key to `.env`
   - For Chroma: The local directory will be created automatically

### Docker Deployment

1. **Environment Setup**:
   ```bash
   cp .env.template .env
   # Edit .env with your production configuration including:
   # - API keys
   # - Redis password
   # - Other service configurations
   ```

2. **Build and Start Services**:
   ```bash
   docker compose up -d --build
   ```

3. **View Logs**:
   ```bash
   # View service logs
   docker compose logs -f crewai-agent-service
   
   # View specific log files
   docker compose exec crewai-agent-service tail -f /app/logs/crewai.log
   ```

4. **Health Check**:
   ```bash
   # Check application status
   docker compose exec crewai-agent-service supervisorctl status
   
   # Check Redis status
   docker compose exec redis redis-cli -a "${REDIS_PASSWORD}" ping
   ```

### Production Deployment Considerations

1. **Resource Management**:
   - CrewAI Agent: 2GB max with 1GB reservation
   - Redis: 512MB max with 256MB reservation
   - Adjust `deploy.resources` in `docker-compose.yml` based on your needs

2. **Logging**:
   - JSON logging enabled for structured log aggregation
   - Log rotation configured for both application and Docker logs
   - Logs directory mounted as volume for persistence
   - Configure log aggregation based on your infrastructure (e.g., ELK, Splunk)

3. **Process Management**:
   - Supervisor manages the application process
   - Automatic restart on failure
   - Health checks ensure service availability
   - Process logs are rotated to prevent disk space issues

4. **Security**:
   - Multi-stage Docker builds for minimal attack surface
   - Non-root user for running the application
   - Environment variables for sensitive configuration
   - Supervisor socket protected with permissions
   - Redis password protection enabled
   - SSL/TLS support for Redis connections

5. **Monitoring**:
   - Health check endpoints for container orchestration
   - Supervisor status for process monitoring
   - Redis monitoring for conversation storage
   - JSON-formatted logs for easy parsing
   - Configure additional monitoring based on your infrastructure

6. **Data Management**:
   - Conversation history stored in Redis with 1-day TTL
   - Automatic cleanup of expired conversations
   - Redis persistence enabled with appendonly
   - Volume mounting for Redis data persistence
   - Efficient message serialization with msgpack

### Adding New Integrations

The template is designed to be extensible. To add a new integration:

1. Create a new module in `src/` for your integration
2. Implement the integration using the existing patterns
3. Update the configuration in `src/config/settings.py`
4. Add any new environment variables to `.env.template`
5. Update tests as needed

### RAG Configuration

The template includes a comprehensive RAG system:

1. **Vector Databases**:
   - Pinecone: Cloud-based vector database (requires API key)
   - Chroma: Local vector database (no API key required)
   - Configurable via environment variables

2. **Embedding Models**:
   - OpenAI: High-quality embeddings (requires API key)
   - Sentence Transformers: Local embeddings (no API key required)
   - Configurable and switchable at runtime

3. **Document Processing**:
   - Automatic chunking with configurable size and overlap
   - Document caching to avoid reprocessing
   - Support for various file types (PDF, DOCX, TXT, images)

4. **Document Sources**:
   - Web pages: Load and process content from URLs
   - Files: Load and process local files
   - Slack: Load and process messages and files from Slack

5. **Query Processing**:
   - Query expansion for better retrieval
   - Context enhancement for better responses
   - Integration with LLMs for natural language responses

6. **Document Management**:
   - List, get, and delete documents
   - View statistics about the knowledge base
   - Filter and search documents

### Redis Configuration

The template uses Redis for storing conversation history. Key features:

1. **Storage Format**:
   - Conversations are stored by channel and thread
   - Messages include timestamp, type, and content
   - Data is serialized using msgpack for efficiency

2. **TTL Management**:
   - Default 1-day retention for conversations
   - TTL is extended on conversation access
   - Automatic cleanup of expired data

3. **Error Handling**:
   - Graceful degradation on Redis failures
   - Continued operation without history if Redis is unavailable
   - Automatic reconnection attempts

4. **Production Setup**:
   - Password protection enabled
   - SSL/TLS support
   - Persistence with appendonly
   - Resource limits and monitoring
   - Health checks

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
