import os
import hashlib

EVIDENCE_DIR = os.path.abspath("evidence_final_v3")
MANIFEST_PATH = os.path.join(EVIDENCE_DIR, "manifest_sha256.txt")

files_to_hash = []

for root, _, files in os.walk(EVIDENCE_DIR):
    for f in sorted(files):
        if f in ("manifest_sha256.txt", "sha256sum_verify.log"):
            continue
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, EVIDENCE_DIR).replace("\\", "/")
        files_to_hash.append((rel_path, full_path))

files_to_hash.sort(key=lambda x: x[0])

lines = []
for rel_path, full_path in files_to_hash:
    h = hashlib.sha256()
    with open(full_path, "rb") as fp:
        while chunk := fp.read(65536):
            h.update(chunk)
    digest = h.hexdigest()
    lines.append(f"{digest}  {rel_path}\n")

with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(lines)

print(f"Generated {MANIFEST_PATH} with {len(lines)} files.")
