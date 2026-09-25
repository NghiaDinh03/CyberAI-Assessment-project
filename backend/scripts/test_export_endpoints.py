import urllib.request
import urllib.error
import json

def test_endpoint(name, url, method="POST"):
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            cd = resp.headers.get("Content-Disposition")
            ct = resp.headers.get("Content-Type")
            print(f"[{name}] SUCCESS: status={resp.status}, cd={cd}, ct={ct}, bytes={len(data)}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[{name}] HTTP ERROR {e.code}: {body}")
    except Exception as e:
        print(f"[{name}] ERROR: {e}")

if __name__ == "__main__":
    full_id = "163f3f6b-1265-41ac-acab-10f9d7580da5"
    short_id = "163f3f6b"
    old_id = "102ad2b1-2ff8-48d6-9613-2a59d0bd78cd"

    print("=== TESTING FULL ID (163f3f6b...) ===")
    test_endpoint("DOCX FULL", f"http://127.0.0.1:8000/api/iso27001/assessments/{full_id}/export-docx")
    test_endpoint("RISK FULL", f"http://127.0.0.1:8000/api/iso27001/assessments/{full_id}/export-risk-register")
    test_endpoint("PDF FULL",  f"http://127.0.0.1:8000/api/iso27001/assessments/{full_id}/export-pdf")

    print("\n=== TESTING SHORT ID (163f3f6b) ===")
    test_endpoint("DOCX SHORT", f"http://127.0.0.1:8000/api/iso27001/assessments/{short_id}/export-docx")
    test_endpoint("RISK SHORT", f"http://127.0.0.1:8000/api/iso27001/assessments/{short_id}/export-risk-register")
    test_endpoint("PDF SHORT",  f"http://127.0.0.1:8000/api/iso27001/assessments/{short_id}/export-pdf")

    print("\n=== TESTING OLD ID (102ad2b1...) ===")
    test_endpoint("DOCX OLD", f"http://127.0.0.1:8000/api/iso27001/assessments/{old_id}/export-docx")
    test_endpoint("RISK OLD", f"http://127.0.0.1:8000/api/iso27001/assessments/{old_id}/export-risk-register")
    test_endpoint("PDF OLD",  f"http://127.0.0.1:8000/api/iso27001/assessments/{old_id}/export-pdf")
