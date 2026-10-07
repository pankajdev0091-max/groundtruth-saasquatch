"""
FastAPI backend for GroundTruth.
"""
import csv
import io
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from groundtruth.csv_parser import detect_mapping, parse_csv, parse_revenue_string, ColumnMapping
from groundtruth.match import match_business, BusinessMatch
from groundtruth.signals import compute_signals, BusinessSignals

app = FastAPI(title="GroundTruth API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JOBS: dict[str, dict] = {}


class MappingOverride(BaseModel):
    field: str
    source_column: str


class MatchRequest(BaseModel):
    job_id: str
    mapping: dict[str, str] | None = None
    exclude_franchises: bool = False
    min_revenue: float | None = None
    max_revenue: float | None = None


class HealthResponse(BaseModel):
    status: str
    states_available: list[str]
    ppp_partitions: int
    sba_partitions: int


@app.get("/health", response_model=HealthResponse)
def health():
    processed = DATA_DIR / "processed"
    ppp_states = []
    ppp_count = 0
    sba_count = 0
    if (processed / "ppp").exists():
        for d in sorted((processed / "ppp").iterdir()):
            if d.is_dir() and d.name.startswith("state="):
                state = d.name.split("=")[1]
                ppp_states.append(state)
                ppp_count += len(list(d.glob("*.parquet")))
    if (processed / "sba7a").exists():
        for d in (processed / "sba7a").iterdir():
            if d.is_dir():
                sba_count += len(list(d.glob("*.parquet")))
    if (processed / "sba504").exists():
        for d in (processed / "sba504").iterdir():
            if d.is_dir():
                sba_count += len(list(d.glob("*.parquet")))

    return HealthResponse(
        status="ok",
        states_available=ppp_states,
        ppp_partitions=ppp_count,
        sba_partitions=sba_count,
    )


@app.post("/upload")
async def upload_csv(file: UploadFile):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file")

    content = (await file.read()).decode("utf-8-sig")
    rows_raw = content.strip().split("\n")
    if len(rows_raw) < 2:
        raise HTTPException(400, "CSV must have a header and at least one data row")

    reader = csv.reader(io.StringIO(content))
    headers = next(reader)
    mapping = detect_mapping(headers)

    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "content": content,
        "row_count": len(rows_raw) - 1,
        "headers": headers,
        "mapping": {k: {"source_column": v.source_column, "mapped_to": v.mapped_to, "confidence": v.confidence} for k, v in mapping.items()},
        "status": "uploaded",
        "created_at": datetime.now().isoformat(),
        "results": None,
    }

    return {
        "job_id": job_id,
        "filename": file.filename,
        "row_count": len(rows_raw) - 1,
        "headers": headers,
        "mapping": {k: {"source_column": v.source_column, "mapped_to": v.mapped_to, "confidence": v.confidence} for k, v in mapping.items()},
    }


def _serialize_match(bm: BusinessMatch, signals: BusinessSignals, row_idx: int) -> dict:
    best = bm.best_match
    result = {
        "row_index": row_idx,
        "input_name": bm.input_name,
        "input_city": bm.input_city,
        "input_state": bm.input_state,
        "match_tier": best.tier if best else "No match",
        "match_confidence": round(best.confidence, 3) if best else 0,
        "match_reasons": best.reasons if best else [],
        "matched_name": best.candidate.borrower_name if best else "",
        "matched_city": best.candidate.city if best else "",
        "matched_zip": best.candidate.zip_code if best else "",
        "matched_address": best.candidate.address if best else "",
        "naics_code": best.candidate.naics_code if best else "",
        "processing_method": best.candidate.processing_method if best else "",
        "ppp_loan_amount": best.candidate.initial_amount if best else 0,
        "annual_payroll": signals.revenue.annual_payroll,
        "payroll_formula": signals.revenue.payroll_formula,
        "revenue_point": signals.revenue.revenue_point,
        "revenue_low": signals.revenue.revenue_low,
        "revenue_high": signals.revenue.revenue_high,
        "revenue_formula": signals.revenue.revenue_formula,
        "naics_ratio": signals.revenue.naics_ratio,
        "naics_level": signals.revenue.naics_level,
        "payroll_proceed_value": signals.revenue.payroll_proceed_value,
        "payroll_proceed_note": signals.revenue.payroll_proceed_note,
        "headcount": signals.headcount,
        "business_age": signals.business_age,
        "sba_loan_count": len(signals.sba_history.loans),
        "sba_total_borrowed": signals.sba_history.total_borrowed,
        "sba_maturing": signals.sba_history.maturing_within_12mo,
        "sba_maturing_details": signals.sba_history.maturing_details,
        "sba_loans": signals.sba_history.loans,
        "franchise_flag": signals.franchise_flag,
        "franchise_name": signals.franchise_name,
        "change_of_ownership": signals.change_of_ownership,
        "recommendation": signals.recommendation,
        "recommendation_rule": signals.recommendation_rule,
    }
    return result


@app.post("/match")
async def match_leads(request: MatchRequest):
    job = JOBS.get(request.job_id)
    if not job:
        raise HTTPException(404, f"Job {request.job_id} not found")

    mapping_dict = request.mapping or {k: v["source_column"] for k, v in job["mapping"].items()}

    parsed_mapping = {
        field: ColumnMapping(source_column=src_col, mapped_to=field, confidence="override")
        for field, src_col in mapping_dict.items()
    }

    rows, _ = parse_csv(job["content"], parsed_mapping)

    async def generate():
        results = []
        total = len(rows)
        for i, row in enumerate(rows):
            bm = match_business(
                name=row.company_name,
                city=row.city,
                state=row.state,
                zip_code=row.zip_code,
                address=row.address,
                industry=row.industry,
            )
            signals = compute_signals(
                match=bm.best_match,
                sba_loans=bm.sba_loans,
                exclude_franchises=request.exclude_franchises,
                min_revenue=request.min_revenue,
                max_revenue=request.max_revenue,
            )
            result = _serialize_match(bm, signals, i)
            result["saasquatch_revenue"] = parse_revenue_string(row.estimated_revenue)
            result["saasquatch_revenue_raw"] = row.estimated_revenue
            results.append(result)

            if (i + 1) % 50 == 0 or i == total - 1:
                progress = {"type": "progress", "completed": i + 1, "total": total}
                yield json.dumps(progress) + "\n"

        job["results"] = results
        job["status"] = "complete"
        done = {"type": "done", "total": total, "matched": sum(1 for r in results if r["match_tier"] != "No match")}
        yield json.dumps(done) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.get("/results/{job_id}")
def get_results(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    if not job.get("results"):
        raise HTTPException(400, "Matching not complete yet")
    return {"job_id": job_id, "results": job["results"]}


@app.get("/export/{job_id}.csv")
def export_csv(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    if not job.get("results"):
        raise HTTPException(400, "Matching not complete yet")

    output = io.StringIO()
    results = job["results"]

    export_fields = [
        "input_name", "input_city", "input_state",
        "match_tier", "match_confidence", "matched_name",
        "matched_city", "matched_zip", "naics_code",
        "ppp_loan_amount", "annual_payroll", "revenue_point",
        "revenue_low", "revenue_high", "revenue_formula",
        "saasquatch_revenue", "saasquatch_revenue_raw",
        "headcount", "business_age",
        "sba_loan_count", "sba_total_borrowed", "sba_maturing",
        "franchise_flag", "franchise_name", "change_of_ownership",
        "recommendation", "recommendation_rule",
        "match_reasons",
    ]

    writer = csv.DictWriter(output, fieldnames=export_fields, extrasaction="ignore")
    writer.writeheader()
    for r in results:
        row = {k: r.get(k, "") for k in export_fields}
        if isinstance(row.get("match_reasons"), list):
            row["match_reasons"] = "; ".join(row["match_reasons"])
        writer.writerow(row)

    csv_content = output.getvalue()
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=groundtruth_{job_id}.csv"},
    )


@app.get("/reference/naics-ratios")
def naics_ratios():
    ratios_path = DATA_DIR / "reference" / "census_ratios_2022.json"
    if not ratios_path.exists():
        raise HTTPException(404, "NAICS ratios not found")
    return json.loads(ratios_path.read_text())


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
