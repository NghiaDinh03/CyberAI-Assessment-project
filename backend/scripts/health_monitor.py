"""Automated Continuous Monitoring & Health Verification Script for CyberAI Server.

Checks container statuses, backend API health, local models availability,
runs E2E Integration tests and logs diagnostic reports.
Optimized for Windows/Linux multi-platform execution with robust encoding handlers.
"""

import os
import sys
import json
import time
import urllib.request
import subprocess
import logging

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Setup Logging
LOG_DIR = "/data/logs" if os.path.exists("/data") else "./logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "health_monitor.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HealthMonitor")

BACKEND_HEALTH_URL = "http://localhost:8000/health"
BACKEND_TEST_COMMAND = "PYTHONPATH=/app python /app/tests/test_e2e_assessment.py"

def check_backend_api() -> bool:
    logger.info("Dang kiem tra ket noi API backend...")
    try:
        req = urllib.request.Request(BACKEND_HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                logger.info(f"Backend API Online. Health Status: {data}")
                return True
            else:
                logger.error(f"Backend API tra ve loi HTTP {response.status}")
    except Exception as e:
        logger.error(f"Khong the ket noi den Backend API ({BACKEND_HEALTH_URL}): {e}")
    return False

def check_docker_containers() -> dict:
    logger.info("Dang kiem tra trang thai cac Docker containers...")
    results = {}
    containers = ["cyberai-backend", "cyberai-frontend", "cyberai-ollama", "cyberai-searxng"]
    for container in containers:
        try:
            # Chay docker inspect de kiem tra xem container co dang chay va healthy khong
            cmd = f"docker inspect --format=\"{{{{.State.Health.Status}}}}\" {container}"
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5)
            status = proc.stdout.strip()
            if proc.returncode == 0:
                results[container] = status or "running"
                logger.info(f"Container {container}: {status or 'running'}")
            else:
                # Neu khong co healthcheck nhung container van dang chay
                cmd_running = f"docker inspect --format=\"{{{{.State.Status}}}}\" {container}"
                proc_running = subprocess.run(cmd_running, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5)
                running_status = proc_running.stdout.strip()
                if proc_running.returncode == 0:
                    results[container] = running_status
                    logger.info(f"Container {container}: {running_status}")
                else:
                    results[container] = "not found"
                    logger.error(f"Container {container} khong ton tai hoac da dung!")
        except Exception as e:
            results[container] = f"error: {e}"
            logger.error(f"Loi kiem tra container {container}: {e}")
    return results

def run_e2e_tests() -> bool:
    logger.info("Dang khoi chay E2E Integration tests tu dong...")
    try:
        # Chay test truc tiep qua docker exec de dam bao tinh co lap
        cmd = f"docker compose exec -T backend sh -c \"{BACKEND_TEST_COMMAND}\""
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=45)
        output = proc.stdout
        logger.info(f"Ket qua chay E2E Test:\n{output or ''}")
        if proc.returncode == 0 and output and "TẤT CẢ E2E TESTS ĐỀU ĐẠT!" in output:
            logger.info("Tat ca cac bai kiem thu E2E tich hop deu PASS 100%!")
            return True
        else:
            logger.error(f"Mot so bai kiem thu E2E that bai! Ma thoat: {proc.returncode}")
    except Exception as e:
        logger.error(f"Loi he thong khi khoi chay E2E tests: {e}")
    return False

def main():
    logger.info("=== BAT DAU TIEN TRINH KIEM TRA SUC KHOE TU DONG ===")
    
    # 1. Kiem tra Docker containers
    container_status = check_docker_containers()
    
    # 2. Kiem tra ket noi API
    api_ok = check_backend_api()
    
    # 3. Chay kiem thu E2E tich hop
    tests_ok = run_e2e_tests()
    
    # Danh gia tong quan
    if api_ok and tests_ok and all(s in ["healthy", "running"] for s in container_status.values()):
        logger.info(">>> DANH GIA: He thong van hanh hoan hao, an toan va toi uu! o")
        print("SYSTEM_HEALTH_OK")
    else:
        logger.warning(">>> DANH GIA: He thong phat hien canh bao hoac suy giam hieu nang! [!] ")
        print("SYSTEM_HEALTH_WARNING")
        
    logger.info("=== KET THUC TIEN TRÌNH KIEM TRA SUC KHOE ===")

if __name__ == "__main__":
    main()
