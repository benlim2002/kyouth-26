from pydantic import BaseModel
from pathlib import Path
from bs4 import BeautifulSoup
import json

class JobListing(BaseModel):
    source_id: str
    job_title: str
    company: str
    description: str

def extract_source_id(soup: BeautifulSoup):
    og_url = soup.find("meta", property="og:url")

    if not og_url or not og_url.get("content"):
        return None

    url = og_url["content"].rstrip("/")
    return url.split("/")[-1]


def process_all_html(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    files = list(input_dir.glob("*.html"))

    total = len(files)
    processed = 0
    skipped = 0

    print("🥈 Silver:...")

    for file in files:
        html = file.read_text(encoding="utf-8", errors="ignore") #put ignore due to some files not in utf-8 format
        soup = BeautifulSoup(html, "html.parser")

        source_id = extract_source_id(soup)

        job_title_tag = soup.find(attrs={"data-automation": "job-detail-title"})
        company_tag = soup.find(attrs={"data-automation": "advertiser-name"})
        description_tag = soup.find(attrs={"data-automation": "jobAdDetails"})

        job_title = job_title_tag.get_text(strip=True) if job_title_tag else None
        company = company_tag.get_text(strip=True) if company_tag else None
        description = description_tag.get_text(" ", strip=True) if description_tag else None

        missing = []

        if not job_title:
            missing.append("job_title")
        if not company:
            missing.append("company")
        if not description:
            missing.append("description")

        if missing or not source_id:
            print(f"⚠️ Missing {', '.join(missing)} in: {file.name}")
            skipped += 1
            continue

        job = JobListing(
            source_id=source_id,
            job_title=job_title,
            company=company,
            description=description
        )

        out_file = output_dir / file.with_suffix(".json").name

        out_file.write_text(
            job.model_dump_json(indent=2),
            encoding="utf-8"
        )

        print(f"✅ Processed: {file.name}")
        processed += 1

    print("\n📊 Silver Summary:")
    print(f"Total: {total} | Processed: {processed} | Skipped: {skipped}")