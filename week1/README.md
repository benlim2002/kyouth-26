## Week 1 : Data Component
This project builds a local ETL (Extract, Transform, Load) pipeline that processes raw job listing data from HTML/MHTML files into a clean, structured SQLite database. The pipeline follows a medallion-style approach (Bronze → Silver → Gold), progressively cleaning and structuring data while ensuring quality validation and profiling.
Final output is a jobs.db database containing structured job listings ready for downstream analytics and modeling.

---

### Setup Instructions
1. Install uv
- Open PowerShell (Admin or normal) and run:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
- Verify:
```bash
uv --version
```

2. Clone and enter project
```bash
git clone <https://github.com/benlim2002/kyouth-26.git>
cd week1
```

3. Set up environment
- ```uv python install ``` **(make sure to install 3.14)**
- ```uv venv```  **(to run the local environment from uv)
- ```.venv\Scripts\activate```  **(activate the environment)**

4. Add source data
Place all raw job listing .mhtml files into:
```bash
data/0_source/
```

--- 

### Usage
1) After cloning the repository, make sure to open it on VS Code or other IDE.
2) By default, your terminal will land you on the main root file ```kyouth-26```
3) Make sure the change the directory to ./week1 by typing ``` cd week1 ```
4) Run the individual pipelines in the following order:
```bash
a) python main.py ingest
b) python main.py process 
c) python main.py load
d) python main.py profile 
```
Or run everything:
```bash
python main.py all
```

## Technical Reflections
---
### Module 1: The Extractor (Medallion & Lakehouses)
Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?
- Answer: Keeping raw .mhtml files is useful because it preserves the original source data. If something breaks later in processing, there is no need to re-process or re-collect the data from the start. It also makes the pipeline more flexible since transformations can be improved without needing to restart the whole project. It is a common practice in my humble opinion to always store each stage of the data for safe keeping.

### Module 2: Treatment Plant (ETL vs ELT & Scale)
Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?
- Answer: ELT is preferred in cloud systems because raw data is stored first, then transformed later according to each projects depending needs. This gives more flexibility compared to doing all cleaning upfront as doing all cleaning upfront might also not be as efficient if there is problem found later on. Sequential processing is slower and doesn’t scale well, especially with large datasets or failures in the middle. Distributed systems solve this by splitting work across multiple machines, making processing faster and more efficient.

### Module 3: The Blueprint & The Vault (Storage & Contracts)
What should happen if an important field like job_title disappears? Why fail early instead of silently inserting nulls into DB? How does INSERT OR IGNORE help prevent duplicate records?
- Answer: Missing critical fields like job_title should be handled early instead of storing null values, because it can break later analysis or produce irrelevant results. It’s better to fail or filter early to keep data clean than to do a whole lot of processing and then finding that it yields no results. INSERT OR IGNORE prevents duplicate entries by using source_id, making the database safe to rerun without creating repeated copies.

### Module 4: The QA Inspector & Orchestrator (Orchestration & DAGs)
What happens if ```processor.py``` crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?
- Answer: For this project itself, I built a manual orchestrator using main.py, where the all command runs the full pipeline in order from ingest to profiling as requested for Module 1. If processor.py crashes halfway, the pipeline stops at that stage, then some data may already be transformed while the rest is not, leading to an incomplete or inconsistent datasets. Re-running the script without restarting the environment can also cause repeated work or require careful handling to avoid issues.
