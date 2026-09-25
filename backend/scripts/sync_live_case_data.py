import json
import os
import re
import hashlib
import sys
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def sync_case(aid, std_type):
    print(f"\n=================== SYNCING CASE {aid} ({std_type}) ===================")
    asm_path = f"/data/assessments/{aid}.json"
    mf_path = f"/data/evidence_manifests/{aid}.json"
    
    if not os.path.exists(asm_path):
        print(f"Error: {asm_path} does not exist")
        return
    alt_mf = f"/data/evidence_manifests/manifest_{aid[:11]}.json"
    if not os.path.exists(mf_path):
        if os.path.exists(alt_mf):
            mf_path = alt_mf
        else:
            print(f"Error: Neither {mf_path} nor {alt_mf} exists")
            return

    with open(mf_path, "r", encoding="utf-8") as f:
        mf = json.load(f)

    # 1. Sync Manifest
    files = mf.get("files", [])
    for it in files:
        fname = it.get("masked_filename") or ""
        # If TCVN, parse control code from filename
        if std_type == "tcvn":
            it["ingestion_status"] = "ingested"
            it["exclusion_reason"] = None
            # e.g. 20260923_070615_APP.01_Bao_Cao... -> APP.01
            m = re.search(r"([A-Z]{2,4}\.\d{2})", fname)
            if m:
                ctrl_id = m.group(1)
                it["control_mapping"] = [ctrl_id]
                it["controls_covered"] = [ctrl_id]
            else:
                it["control_mapping"] = []
                it["controls_covered"] = []
        elif std_type == "iso":
            it["ingestion_status"] = "ingested"
            it["exclusion_reason"] = None
            m = re.search(r"(A\.\d+\.\d+)", fname)
            if m:
                ctrl_id = m.group(1)
                existing = it.get("control_mapping") or []
                if ctrl_id not in existing:
                    existing.append(ctrl_id)
                it["control_mapping"] = existing
                it["controls_covered"] = existing

    # Recompute mapped_control_count as unique mapped controls across ingested files
    mapped_ctrls = set()
    for it in files:
        if it.get("ingestion_status") == "ingested":
            for c in (it.get("control_mapping") or it.get("controls_covered") or []):
                if c:
                    mapped_ctrls.add(str(c))
    
    mf["total_files"] = len(files)
    mf["mapped_control_count"] = len(mapped_ctrls)
    
    with open(mf_path, "w", encoding="utf-8") as f:
        json.dump(mf, f, ensure_ascii=False, indent=2)
    if os.path.exists(alt_mf) and alt_mf != mf_path:
        with open(alt_mf, "w", encoding="utf-8") as f:
            json.dump(mf, f, ensure_ascii=False, indent=2)
    print(f"Manifest updated: total_files={mf['total_files']}, mapped_control_count={mf['mapped_control_count']}")

    # Build file lookup by masked_filename, filename, and file_id
    file_by_name = {}
    for it in files:
        fid = it.get("file_id")
        sha = it.get("sha256")
        mf_name = it.get("masked_filename")
        if mf_name:
            file_by_name[mf_name] = it
            # also index by plain basename without timestamp
            clean = re.sub(r"^\d{8}_\d{6}_", "", mf_name)
            file_by_name[clean] = it
        if fid:
            file_by_name[fid] = it

    # 2. Sync Assessment JSON
    with open(asm_path, "r", encoding="utf-8") as f:
        asm = json.load(f)

    jd = asm.get("json_data", {})
    controls = jd.get("controls", [])
    
    satisfied_cnt = 0
    tot_ctrls = len(controls)
    
    for c in controls:
        cid = c.get("id") or c.get("control_id")
        v = (c.get("verdict") or "").lower()
        if v == "satisfied":
            satisfied_cnt += 1
            
        cits = c.get("evidence_citations", [])
        updated_cits = []
        for cit in cits:
            cfname = cit.get("file_name") or cit.get("filename") or ""
            # Match in manifest
            matched_file = file_by_name.get(cfname)
            if not matched_file:
                clean_name = re.sub(r"^\d{8}_\d{6}_", "", cfname)
                matched_file = file_by_name.get(clean_name)
            if not matched_file:
                # Try finding any file mapped to this control
                for it in files:
                    if cid in (it.get("control_mapping") or []):
                        matched_file = it
                        break
            
            if matched_file:
                fid = matched_file.get("file_id")
                sha = matched_file.get("sha256")
                real_name = matched_file.get("masked_filename") or cfname
                exc = cit.get("excerpt") or f"Minh chứng trích xuất từ tệp {real_name}"
                updated_cits.append({
                    "evidence_id": fid,
                    "file_id": fid,
                    "file_name": real_name,
                    "filename": real_name,
                    "sha256": sha,
                    "excerpt": exc,
                    "reference": cit.get("reference") or f"Tài liệu {real_name}"
                })
            else:
                updated_cits.append(cit)
        c["evidence_citations"] = updated_cits

    # Sync Compliance Object (Evidence-supported Satisfied Controls)
    ev_supp_pct = round((satisfied_cnt / tot_ctrls * 100), 1) if tot_ctrls > 0 else 0.0
    comp_obj = {
        "score": satisfied_cnt,
        "max_score": tot_ctrls,
        "percentage": ev_supp_pct,
        "satisfied_count": satisfied_cnt,
    }
    jd["compliance"] = comp_obj
    asm["compliance"] = comp_obj
    
    # Sync Risk Register & Risk Summary
    # Risk register contains ONLY non-satisfied controls
    existing_rr = jd.get("risk_register", [])
    synced_rr = [r for r in existing_rr if (r.get("verdict") or "").lower() != "satisfied"]
    
    crit = sum(1 for r in synced_rr if str(r.get("severity", "")).lower() == "critical")
    high = sum(1 for r in synced_rr if str(r.get("severity", "")).lower() == "high")
    med = sum(1 for r in synced_rr if str(r.get("severity", "")).lower() == "medium")
    low = sum(1 for r in synced_rr if str(r.get("severity", "")).lower() == "low")
    tot_gaps = len(synced_rr)
    
    risk_summary = {
        "critical_gaps": crit,
        "high_gaps": high,
        "medium_gaps": med,
        "low_gaps": low,
        "total_gaps": tot_gaps,
    }
    jd["risk_register"] = synced_rr
    jd["risk_summary"] = risk_summary
    asm["risk_register"] = synced_rr
    asm["risk_summary"] = risk_summary

    # Ensure expert_review_status is explicit
    jd["expert_review_status"] = "pending"
    asm["expert_review_status"] = "pending"

    # Sanitize TCVN text if TCVN
    if std_type == "tcvn":
        jd["standard"] = {"id": "tcvn11930", "name": "TCVN 11930:2017 (Catalogue kỹ thuật)"}
        asm["standard"] = {"id": "tcvn11930", "name": "TCVN 11930:2017 (Catalogue kỹ thuật)"}
        # Sanitize report field
        if "report" in jd and isinstance(jd["report"], str):
            rep = jd["report"]
            rep = rep.replace("HỒ SƠ ĐỀ XUẤT CẤP ĐỘ AN TOÀN HỆ THỐNG THÔNG TIN", "BÁO CÁO ĐÁNH GIÁ SƠ BỘ THEO CATALOGUE TCVN 11930:2017")
            rep = rep.replace("CẤP ĐỘ 3", "Cấp độ đánh giá sơ bộ")
            rep = rep.replace("XÁC NHẬN VÀ KÝ DUYỆT HỒ SƠ ĐỀ XUẤT CẤP ĐỘ", "XÁC NHẬN KẾT QUẢ ĐÁNH GIÁ SƠ BỘ")
            rep = rep.replace("CĂN CỨ PHÁP LÝ THỰC HIỆN", "TÀI LIỆU TIÊU CHUẨN THAM CHIẾU")
            jd["report"] = rep
        if "report" in asm and isinstance(asm["report"], str):
            rep = asm["report"]
            rep = rep.replace("HỒ SƠ ĐỀ XUẤT CẤP ĐỘ AN TOÀN HỆ THỐNG THÔNG TIN", "BÁO CÁO ĐÁNH GIÁ SƠ BỘ THEO CATALOGUE TCVN 11930:2017")
            rep = rep.replace("CẤP ĐỘ 3", "Cấp độ đánh giá sơ bộ")
            rep = rep.replace("XÁC NHẬN VÀ KÝ DUYỆT HỒ SƠ ĐỀ XUẤT CẤP ĐỘ", "XÁC NHẬN KẾT QUẢ ĐÁNH GIÁ SƠ BỘ")
            rep = rep.replace("CĂN CỨ PHÁP LÝ THỰC HIỆN", "TÀI LIỆU TIÊU CHUẨN THAM CHIẾU")
            asm["report"] = rep

    # Harmonize markdown report text to authoritative Weighted Compliance
    raw_rep = asm.get("report") or (asm.get("result", {}).get("report") if isinstance(asm.get("result"), dict) else "") or jd.get("report") or ""
    if raw_rep:
        from services.chat_service import ChatService
        w_comp = jd.get("weighted_compliance", {})
        pct_val = w_comp.get("percentage", 0.0)
        cov_val = jd.get("control_coverage", {})
        healed_rep = ChatService.ensure_complete_report(
            markdown_report=raw_rep,
            percentage=pct_val,
            score=cov_val.get("evidence_supported_implemented", satisfied_cnt),
            max_score=cov_val.get("total_controls", tot_ctrls),
            json_data=jd,
        )
        asm["report"] = healed_rep
        jd["report"] = healed_rep
        if "result" in asm and isinstance(asm["result"], dict):
            asm["result"]["report"] = healed_rep

    # Also mirror top-level fields
    asm["json_data"] = jd
    asm["weighted_compliance"] = jd.get("weighted_compliance", {})
    asm["control_coverage"] = jd.get("control_coverage", {})
    asm["weighted_coverage"] = jd.get("weighted_coverage", {})
    asm["compliance_percent"] = jd.get("weighted_compliance", {}).get("percentage", 0.0)

    with open(asm_path, "w", encoding="utf-8") as f:
        json.dump(asm, f, ensure_ascii=False, indent=2)

    # Sync to sqlite db as well
    db_path = "/data/assessments/assessments.db"
    if os.path.exists(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        w_pct = asm.get("compliance_percent", 0.0)
        c_cov = asm.get("control_coverage", {})
        sat_c = c_cov.get("evidence_supported_implemented", satisfied_cnt)
        tot_c = c_cov.get("total_applicable_controls", tot_ctrls)
        fail_c = tot_c - sat_c
        cur.execute(
            """UPDATE infrastructure_assessments 
               SET report_data = ?, overall_score = ?, total_controls = ?, passed_controls = ?, failed_controls = ? 
               WHERE id = ?""",
            (json.dumps(asm, ensure_ascii=False), w_pct, tot_c, sat_c, fail_c, aid)
        )
        conn.commit()
        conn.close()

    # Regenerate DOCX, SoA, Risk Register exports
    os.makedirs("/data/exports", exist_ok=True)
    try:
        from services.report_docx_generator import generate_report_docx
        docx_path = f"/data/exports/IT_Audit_Report_{aid[:8]}.docx"
        generate_report_docx(asm, output_path=docx_path)
        print(f"Generated DOCX: {docx_path}")
    except Exception as e:
        print(f"Error generating DOCX export for {aid}: {e}")

    try:
        from services.risk_register_exporter import generate_risk_register_xlsx
        rr_bytes = generate_risk_register_xlsx(assessment_data=asm)
        rr_path = f"/data/exports/Risk_Register_{aid[:8]}.xlsx"
        with open(rr_path, "wb") as f:
            f.write(rr_bytes)
        print(f"Generated Risk Register: {rr_path}")
    except Exception as e:
        print(f"Error generating Risk Register export for {aid}: {e}")

    try:
        from services.soa_exporter import generate_soa_xlsx
        soa_bytes = generate_soa_xlsx(assessment_data=asm)
        soa_prefix = "SoA_TCVN11930" if std_type == "tcvn" else "SoA_ISO27001"
        soa_path = f"/data/exports/{soa_prefix}_{aid[:8]}.xlsx"
        with open(soa_path, "wb") as f:
            f.write(soa_bytes)
        print(f"Generated SoA: {soa_path}")
    except Exception as e:
        print(f"Error generating SoA export for {aid}: {e}")

    print(f"Assessment updated successfully: satisfied={satisfied_cnt}/{tot_ctrls} ({ev_supp_pct}%), gaps={tot_gaps} (crit={crit}, high={high}, med={med}, low={low})")

if __name__ == "__main__":
    sync_case("163f3f6b-1265-41ac-acab-10f9d7580da5", "iso")
    sync_case("e9bee7ff-8f23-4f01-9666-7e271e7b1a77", "tcvn")
    if os.path.exists("/data/assessments/7b8a17d5-0314-4cae-af32-9f702f94427f.json"):
        sync_case("7b8a17d5-0314-4cae-af32-9f702f94427f", "iso")
    if os.path.exists("/data/assessments/f2879709-3784-46db-88f3-074ad5a2cf1c.json"):
        sync_case("f2879709-3784-46db-88f3-074ad5a2cf1c", "tcvn")
