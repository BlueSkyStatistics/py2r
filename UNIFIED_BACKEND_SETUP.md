# BlueSky Python + R Backend: Unified Setup & Usage Guide

This guide provides comprehensive setup and usage instructions for the BlueSky Python + R backend, including both Docker and manual installation options.

## System Architecture

### Local Installation:
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Electron App  │◄──►│ Python Process   │◄──►│   System R      │
│  (subprocess.js)│    │ (console.py)     │    │   + packages    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Docker Installation:
```
┌─────────────────┐    ┌────────────────────────────┐
│   Electron App  │◄──►│ Unified Container          │
│(subprocess.js)  │    │ ┌──────────┐ ┌──────────┐ │
└─────────────────┘    │ │ Python   │ │ R 4.4.3  │ │
                       │ │ Backend  ◄─► + pkgs    │ │
                       │ └──────────┘ └──────────┘ │
                       └──────────────┬─────────────┘
                                     │
                            ┌────────▼─────────┐
                            │   Shared Volume  │
                            │  (data & temp)   │
                            └──────────────────┘
```

## Overview

BlueSky's backend enables communication between Python and R for statistical analysis, data management, and integration with the BlueSkyJS frontend. The backend can be run directly or via Docker, and supports both local and remote operation.

---

## Prerequisites

- **Python 3.8+** (recommended: 3.13 or newer)
- **R (4.4.3)**
- **pip** for Python package management
- **Docker** (optional, for containerized deployment)

---

## Manual Setup (Local)

### 1. Install Python Dependencies

Navigate to the `py2rbackend` directory and install required Python packages using uv:

```zsh
cd py2rbackend

# Install uv if not already installed
pip install uv

# Create and activate virtual environment, install dependencies
uv sync
```

### 3. Configuration

- Edit `config.py` and `config.json` as needed for your environment.
- Ensure paths to R and Python executables are correct.

### 4. Running the Backend

Start the backend server:

```zsh
python console.py
# Or, for HTTP server:
python console_http.py
```

---

## Docker Setup

The Docker setup provides an isolated environment with specific R and Python versions, making deployment consistent across different systems.

### Project Structure
```
py2rbackend/
├── r-packages/          # Persistent R packages storage
├── shared/             # Shared data files between containers
├── docker-compose.yml  # Container orchestration
├── Dockerfile          # R container setup
└── packages.R         # R package installation script
```

### 1. Start Docker Environment

From the `py2rbackend` directory:

```zsh
# Build and start containers
docker compose up --build -d

# Verify containers are running
docker ps
```

### 2. Configure Electron App for Docker

Choose one of these methods:

#### Option A: Environment Variable (Temporary)
```zsh
# Set before starting Electron app
export USE_DOCKER_R=true
```

#### Option B: Permanent Configuration
Edit your `subprocess.js`:
```javascript
global.USE_DOCKER_R = true;
// Then require Docker version:
require('./subprocess_docker.js')
```

### 3. Package Management

Install additional R packages in the running container:
```zsh
# Access R console in container
docker exec -it bluesky-unified R

# Install packages
install.packages("your_package_name")
quit()
```

Packages are stored in the `r-packages` volume and persist between container restarts.

### 4. Container Management

```zsh
# Stop containers
docker compose down

# View logs
docker compose logs -f

# Restart specific service
docker compose restart bluesky-unified
```

### Environment Variables

The Python backend uses these for Docker R:
- `R_HOST`: R service hostname (default: `r-service`)
- `R_PORT`: Rserve port (default: `6311`)
- `USE_DOCKER_R`: Enable Docker mode

---

## System Integration

### Communication Flow

```
┌─────────────────┐    ┌────────────────────────────┐
│   Electron App  │◄──►│ Unified Container          │
└─────────────────┘    │ ┌──────────┐ ┌──────────┐ │
                       │ │ Python   │ │ R 4.4.3  │ │
                       │ │ Backend  ◄─► + pkgs    │ │
                       │ └──────────┘ └──────────┘ │
                       └────────────────────────────┘
```

### Process Flow

1. **Frontend → Backend**: 
   - Electron app sends commands via HTTP or WebSocket
   - Commands can be R code, Python code, or system operations

2. **Backend Processing**:
   - Python and R run in the same container
   - Direct integration between Python and R using rpy2
   - Python code runs in the backend process
   - File operations use shared volumes

3. **Data Exchange**:
   - Results returned as JSON
   - Large datasets handled via shared filesystem
   - Plots and graphics saved to shared directory

4. **Configuration**:
   - `config.py`: Backend settings
   - `config.json`: System paths and ports
   - Environment variables for Docker integration

---

## Switching Between Modes

### Local R → Docker R
```zsh
# 1. Start Docker services
cd py2rbackend
docker compose up -d

# 2. Enable Docker mode
export USE_DOCKER_R=true

# 3. Start Electron app normally
```

### Docker R → Local R
```zsh
# 1. Stop Docker services
docker compose down

# 2. Disable Docker mode
unset USE_DOCKER_R

# 3. Ensure local R is configured
```

## Troubleshooting

- **R package installation fails**:
  ```zsh
  # Access container and try manual install
  docker exec -it bluesky-unified R
  install.packages("package_name", repos="https://cran.rstudio.com/")
  ```

- **Volume permissions**:
  ```zsh
  # Fix shared volume permissions
  sudo chown -R $USER:$USER r-packages/
  docker compose restart
  ```


## Benefits of Docker Setup

✅ **Isolated Environment**: No conflicts with system R  
✅ **Version Control**: Exact R version (4.4.3) and packages  
✅ **Easy Deployment**: Single command setup  
✅ **Persistent Packages**: Stored in Docker volume  
✅ **Cross-Platform**: Works the same on all systems

