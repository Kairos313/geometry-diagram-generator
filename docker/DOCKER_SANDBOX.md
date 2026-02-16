# Sandboxed Manim Renderer

A secure Docker-based environment for executing AI-generated Manim animation code.

## Why This Exists

Your pipeline generates Python code using AI (Claude Sonnet) in Step 4, which is then executed in Step 5 to render videos. **This is a security risk** - if the AI generates malicious code (through error, prompt injection, or adversarial inputs), it could:

- Access/modify files on your system
- Exfiltrate data via network
- Install malware
- Consume system resources (DoS)

This Docker sandbox **contains the blast radius** of any malicious code by running it in an isolated environment.

---

## Quick Start

```bash
# Navigate to the docker directory
cd docker/

# 1. Build the Docker image (first time only)
./render.sh build

# 2. Copy files from the pipeline to input/
./render.sh prepare

# 3. Run the sandboxed render
./render.sh render

# Check output/
ls -la output/
```

---

## Security Architecture

### Defense in Depth

This sandbox implements **7 layers of security**:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: NETWORK ISOLATION                                 │
│  - network_mode: none                                       │
│  - No internet, no local network, no DNS                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: USER ISOLATION                                    │
│  - Runs as non-root user 'sandbox' (UID 1000)              │
│  - Cannot access root-owned files                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: FILESYSTEM ISOLATION                              │
│  - Input directory mounted READ-ONLY                        │
│  - Only output/ directory is writable                       │
│  - /tmp uses tmpfs (memory-only, auto-cleaned)              │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: RESOURCE LIMITS                                   │
│  - Max 4 CPUs, 8GB RAM                                      │
│  - Max 256 processes (prevents fork bombs)                  │
│  - 10-minute timeout per scene                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: CAPABILITY DROPPING                               │
│  - All Linux capabilities dropped (cap_drop: ALL)           │
│  - Cannot mount filesystems, change network, etc.           │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: PRIVILEGE ESCALATION PREVENTION                   │
│  - no-new-privileges:true                                   │
│  - Cannot gain elevated permissions via setuid/setgid       │
├─────────────────────────────────────────────────────────────┤
│  Layer 7: CODE VALIDATION                                   │
│  - Basic pattern matching for dangerous constructs          │
│  - Syntax validation before execution                       │
└─────────────────────────────────────────────────────────────┘
```

### What Each Layer Protects Against

| Layer | Threat | Protection |
|-------|--------|------------|
| Network Isolation | Data exfiltration, C2 communication | No network = no data leaves |
| User Isolation | Privilege escalation | Non-root can't access system files |
| Filesystem Isolation | File tampering, persistence | Read-only input, limited write |
| Resource Limits | DoS, resource exhaustion | Bounded CPU/RAM/processes |
| Capability Dropping | Kernel exploits | No dangerous syscalls |
| No New Privileges | setuid exploits | Can't escalate via binaries |
| Code Validation | Obvious malicious patterns | Early warning (not foolproof) |

---

## File Structure

```
docker/
├── Dockerfile              # Multi-stage build for minimal image
├── docker-compose.yml      # Security configuration
├── entrypoint.sh           # Container entrypoint script
├── render.sh               # Helper script for easy usage
├── requirements-docker.txt # Minimal Python dependencies
├── DOCKER_SANDBOX.md       # This documentation
├── input/                  # Mount point for input files (auto-created)
│   ├── all_scenes.py       # AI-generated Manim code
│   ├── figure.py           # Geometric function definitions
│   ├── Audio/              # Individual audio files
│   └── Scene/              # Scene-level audio files
└── output/                 # Mount point for rendered videos (auto-created)
    └── *.mp4               # Rendered scene videos
```

---

## Commands Reference

### render.sh Commands

```bash
# Build the Docker image
./render.sh build

# Copy files from pipeline to input/
./render.sh prepare

# Render all scenes (default quality: 480p)
./render.sh render

# Render at specific quality
./render.sh --quality ql render    # 480p15 (fast)
./render.sh --quality qm render    # 720p30 (balanced)
./render.sh --quality qh render    # 1080p60 (best)

# Test the Docker environment
./render.sh test

# Validate input files without rendering
./render.sh validate

# Clean output directory
./render.sh clean

# Use hardened security profile
./render.sh --hardened render
```

### Direct Docker Commands

```bash
# Using docker-compose (recommended)
cd docker/
docker-compose run --rm renderer render
docker-compose run --rm renderer test

# Using docker run directly (manual security flags)
docker run --rm \
    --network none \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --memory 8g \
    --cpus 4 \
    -v ./input:/input:ro \
    -v ./output:/output \
    manim-sandbox:latest render
```

---

## Detailed Code Explanation

### Dockerfile (Multi-Stage Build)

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder
```
**Purpose**: Install build tools and compile Python packages. This stage is discarded in the final image, reducing size and attack surface.

```dockerfile
# Stage 2: Runtime
FROM python:3.11-slim-bookworm AS runtime
```
**Purpose**: Minimal image with only runtime dependencies. No compilers or build tools.

```dockerfile
RUN groupadd --gid 1000 sandbox && \
    useradd --uid 1000 --gid sandbox --shell /bin/false --create-home sandbox
```
**Purpose**: Create non-root user. `--shell /bin/false` prevents interactive login.

```dockerfile
USER sandbox
```
**Purpose**: All subsequent commands run as unprivileged user.

### docker-compose.yml Security Options

```yaml
network_mode: none
```
**Effect**: Container has NO network interfaces. Cannot make any network connections.

```yaml
cap_drop:
  - ALL
```
**Effect**: Drops all 38+ Linux capabilities. Container cannot:
- `CAP_NET_ADMIN`: Modify network configuration
- `CAP_SYS_ADMIN`: Mount filesystems, load kernel modules
- `CAP_DAC_OVERRIDE`: Bypass file permissions
- etc.

```yaml
security_opt:
  - no-new-privileges:true
```
**Effect**: Prevents privilege escalation via setuid/setgid binaries or capabilities.

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```
**Effect**: Hard limits on CPU and memory usage.

```yaml
ulimits:
  nproc: 256
```
**Effect**: Max 256 processes. Prevents fork bombs like `:(){ :|:& };:`

```yaml
volumes:
  - type: bind
    source: ./input
    target: /input
    read_only: true
```
**Effect**: Input directory is read-only. Malicious code cannot modify the source files.

### entrypoint.sh Safety Features

```bash
validate_python_safety() {
    local dangerous_patterns=(
        "import os"
        "import subprocess"
        "eval("
        "exec("
        ...
    )
}
```
**Purpose**: Detect obviously dangerous code patterns. This is a **warning system**, not a security boundary (Docker provides the real isolation).

```bash
timeout "$MAX_RENDER_TIME" manim ...
```
**Purpose**: Kill renders that take too long. Prevents infinite loops from hanging the system.

---

## Integration with Pipeline

### Modified Workflow

**Before (Insecure)**:
```
Steps 1-4: Run on host
Step 5: Execute AI code on host ← DANGEROUS
```

**After (Sandboxed)**:
```
Steps 1-4: Run on host (API calls only - safe)
Step 5: Execute AI code in Docker sandbox ← ISOLATED
```

### Example Integration

Modify `terminal_pipeline.py` to use the sandbox for Step 5:

```python
import subprocess
import shutil
from pathlib import Path

def run_sandboxed_render(quality="ql"):
    """Run Step 5 in Docker sandbox instead of directly on host."""

    docker_dir = Path(__file__).parent / "docker"
    input_dir = docker_dir / "input"
    output_dir = docker_dir / "output"

    # Prepare input directory
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # Copy required files
    pipeline_dir = Path(__file__).parent
    shutil.copy(pipeline_dir / "all_scenes.py", input_dir)
    shutil.copy(pipeline_dir / "figure.py", input_dir)

    if (pipeline_dir / "Audio").exists():
        shutil.copytree(pipeline_dir / "Audio", input_dir / "Audio", dirs_exist_ok=True)
    if (pipeline_dir / "Scene").exists():
        shutil.copytree(pipeline_dir / "Scene", input_dir / "Scene", dirs_exist_ok=True)

    # Run sandboxed render
    result = subprocess.run(
        ["./render.sh", "--quality", quality, "render"],
        cwd=docker_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Sandboxed render failed: {result.stderr}")

    # Copy output back
    for video in output_dir.glob("*.mp4"):
        shutil.copy(video, pipeline_dir)

    return True
```

---

## About PyPy

Your supervisor mentioned PyPy for sandboxing. Here's the context:

### PyPy Sandbox Mode
PyPy had an experimental `pypy-sandbox` feature that created a restricted Python interpreter. However:
- It's **deprecated and unmaintained** since ~2015
- It's **not compatible** with Manim's dependencies (numpy, scipy, etc.)
- Docker provides **stronger isolation** than PyPy sandbox ever did

### Why This Solution Uses CPython + Docker
1. **Compatibility**: Manim requires numpy, cairo bindings, etc. that don't work with PyPy
2. **Stronger Isolation**: Docker's kernel-level isolation > PyPy's interpreter-level restrictions
3. **Production Ready**: Docker is battle-tested; PyPy sandbox was experimental
4. **Maintainability**: Standard Docker tooling vs. abandoned sandbox mode

### If You Must Use PyPy
You could create a PyPy-based image for simple Python code, but Manim rendering requires:
- NumPy (limited PyPy support)
- Cairo/Pango (C bindings)
- OpenGL (for 3D scenes)

These have poor or no PyPy compatibility.

---

## Hardened Mode

For maximum security, use the hardened profile:

```bash
./render.sh --hardened render
```

This adds:
- **Read-only root filesystem**: `/` is immutable
- **tmpfs everywhere**: All writable paths are memory-only
- **Stricter limits**: 2 CPUs, 4GB RAM

Trade-offs:
- Slightly slower (tmpfs overhead)
- May fail on very large renders (memory limits)

---

## Troubleshooting

### "Docker image not found"
```bash
./render.sh build
```

### "No input files found"
```bash
./render.sh prepare
```

### Render timeout
Increase timeout:
```bash
./render.sh --timeout 1200 render  # 20 minutes
```

### Out of memory
The default 8GB limit should be sufficient. If not:
```bash
# Edit docker-compose.yml
memory: 16G
```

### Permission denied on output
```bash
# Fix output directory permissions
sudo chown -R $(whoami) docker/output/
```

---

## Security Considerations

### What This Protects Against
- ✅ File system access/modification
- ✅ Network access/data exfiltration
- ✅ Resource exhaustion (DoS)
- ✅ Privilege escalation
- ✅ Persistence (container is ephemeral)

### What This Does NOT Protect Against
- ❌ Kernel exploits (container escape via kernel bug)
- ❌ Docker daemon exploits
- ❌ Side-channel attacks (timing, cache)
- ❌ Output file manipulation (rendered videos could be malicious)

### For Higher Security
Consider:
1. **gVisor**: Google's container runtime with kernel syscall interception
2. **Kata Containers**: VM-level isolation with container UX
3. **Separate server**: Physical/VM isolation (your supervisor's first suggestion)

---

## License

This sandbox configuration is provided as part of the geometry-video-generator project.
