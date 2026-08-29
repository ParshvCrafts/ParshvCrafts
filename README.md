<!--
  ============================================================================
  ParshvCrafts - GitHub Profile README
  ----------------------------------------------------------------------------
  Palette: the GitHub contribution-graph greens, so the page reads as native to
  the site it lives on.
      #39d353 bright   #26a641 mid    #006d32 deep   #0e4429 darkest
      #0d1117 dark bg  #ffffff light bg  #c9d1d9 dark text  #24292f light text

  Two rules this file follows:
    1. Every card that carries colour ships a light AND a dark variant through
       <picture> + prefers-color-scheme, because GitHub renders READMEs in both.
    2. Tech is shown as logos only, never logo-plus-text, so the grid stays even.
       Icons come from go-skill-icons (uniform 48px tiles, theme-aware).
  Portrait: assets/portrait-{dark,light}.svg, regenerate with
       python scripts/dotify.py scripts/source-portrait.jpg -o assets/portrait \
              --cols 96 --detail 0.65 --key 60 --zoom 0.86
  ============================================================================
-->

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="assets/portrait-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/portrait-light.svg">
  <img src="assets/portrait-dark.svg" width="230" alt="Parshv Patel, rendered as a contribution-graph dot matrix">
</picture>

<br>

<a href="https://www.portfolio.parshvpatel.com/">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=25&duration=2800&pause=900&color=39D353&center=true&vCenter=true&width=620&lines=Parshv+Patel;Data+Science+%40+UC+Berkeley;Machine+Learning+Engineer;Agentic+AI+Systems+Builder;Prev.+SWE+Intern+%40+Amazon" alt="Parshv Patel - Data Science, Machine Learning, Agentic AI">
</a>

<br>

<a href="https://www.linkedin.com/in/parshv-patel-65a90326b/"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
<a href="mailto:parshvpatel_0910@berkeley.edu"><img src="https://img.shields.io/badge/Email-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"></a>
<a href="https://www.portfolio.parshvpatel.com/"><img src="https://img.shields.io/badge/Portfolio-39D353?style=for-the-badge&logo=vercel&logoColor=0D1117" alt="Portfolio"></a>
<a href="https://github.com/ParshvCrafts?tab=repositories"><img src="https://img.shields.io/badge/Repositories-F97316?style=for-the-badge&logo=github&logoColor=white" alt="Repositories"></a>

<br><br>

<img src="https://img.shields.io/badge/UC%20Berkeley-B.A.%20Data%20Science%20'29-216E39?style=flat-square&logo=googlescholar&logoColor=white" alt="UC Berkeley, B.A. Data Science 2029">
<img src="https://img.shields.io/badge/GPA-4.00%20%C2%B7%20Dean's%20List%20%C3%972-26A641?style=flat-square&logo=academia&logoColor=white" alt="4.00 GPA, Dean's List twice">
<img src="https://img.shields.io/badge/Berkeley,%20CA-39D353?style=flat-square&logo=googlemaps&logoColor=0D1117" alt="Berkeley, California">

</div>

---

## About

I build systems that turn messy data into decisions — and increasingly, into agents that act on them.

- **Studying** Data Science at **UC Berkeley** (College of Computing, Data Science and Society), 4.00 GPA, Dean's List every graded term.
- **Last summer** I was a **Software Engineer Intern at Amazon**, where I redesigned how a batch ML inference platform resolves model configuration and migrated it live with zero production incidents.
- **I work across** data engineering, machine learning, and agentic AI: retrieval systems over tens of thousands of products, multi-agent LangGraph workflows running as a paid product, ETL over 15M+ records, and fine-tuned transformers behind production APIs.
- **I care most** about the unglamorous parts — schema design, failover paths, evaluation, and the tests that let you ship on a Friday.
- **Outside the code**, I'm an AI4ALL Ignite Fellow and MLT Ascend Scholar, and I've written two papers on fairness in automated decision-making.

> **Open to Summer 2027 internships** in Data Science, Data Engineering, Machine Learning, and AI / Agentic Engineering — and to collaborating on open-source AI tooling.

---

## Experience

### Software Engineer Intern · Amazon

`Jun 2026 – Aug 2026` &nbsp;·&nbsp; Classification and Policy Platforms &nbsp;·&nbsp; Seattle, WA

I owned a platform-level redesign of how a batch ML inference system resolves model configuration, then migrated it live behind a fallback architecture so no customer ever saw the switch.

- Merged **5 separate ML model configuration stores into 2 unified schemas**, removing **20+ hardcoded service-layer dependencies** and making model onboarding self-service — integration time went from weeks to hours.
- Designed a fallback path across **3 distributed service layers** so the live migration could not take the platform down.

<div align="center">

| Code changes merged | Lines added | Packages shipped | Production incidents |
| :-----------------: | :---------: | :--------------: | :------------------: |
| **44** | **61,565** | **19** | **0** |

</div>

---

## Featured Projects

Six projects, newest first. Each one opens to the same four things: what it does, what it's built on, what it measurably achieved, and the one engineering decision that mattered.

<details open>
<summary><b>&nbsp;Interlace — Multimodal Fashion Search Engine</b> &nbsp;·&nbsp; <i>ML · Information Retrieval · Full-Stack</i></summary>

<br>

Search **29,000+ ASOS products** by text, by image, or by both at once. Fashion-specific CLIP embeddings feed two FAISS indexes, which are fused with keyword search so a query like *"something like this jacket but in linen"* matches on both the picture and the words.

| | |
| :--- | :--- |
| **Built with** | Python · FashionCLIP · FAISS · BM25 · FastAPI · Next.js 15 · TypeScript · Docker |
| **Scale** | 29,000+ products · two vector indexes · text, image and combined queries |
| **How search works** | Vector search and keyword search are merged by Reciprocal Rank Fusion, then reranked on what the query was actually asking for |
| **Reliability** | Filters relax step by step, so a search never comes back empty |
| **Live** | HuggingFace Spaces (model) + Vercel (site) |
| **Links** | [Repository](https://github.com/ParshvCrafts/Multimodal_Search_Engine) · [Live Demo](https://interlace-fashion.vercel.app/) · [Video](https://www.youtube.com/watch?v=1bLxOZ0QqVs) |

The hard part was not embedding quality. Real shoppers write queries that no single search method handles: vector search misses exact brand and size words, keyword search misses visual intent entirely. Running both and merging them is what made results usable rather than merely relevant.

</details>

<details>
<summary><b>&nbsp;AtlasMind — Agentic AI Trip Planner</b> &nbsp;·&nbsp; <i>Agentic AI · Production SaaS</i></summary>

<br>

A paid AI travel platform where **six LangGraph agents** research, draft, critique and finalise an itinerary. Requests are routed across 10 LLM API keys with health scoring and automatic failover, so one provider going down never reaches a paying user.

| | |
| :--- | :--- |
| **Built with** | Python · FastAPI · LangGraph · LangChain · React · PostgreSQL · Stripe |
| **Architecture** | 6-agent LangGraph state machine · LLM routing across 10 keys |
| **Uptime** | 99.9%, held up by health-scored automatic failover |
| **Payments** | Stripe Free / Pro tiers · usage tracking · webhooks · automatic quota enforcement |
| **Security** | Google OAuth · JWT · CSRF tokens · rate limiting |
| **Speed** | Lighthouse 95+ progressive web app |
| **Links** | [Repository](https://github.com/ParshvCrafts/AtlasMind) · [Live Demo](https://atlasmind-ai-trip-planner.vercel.app/) · [Video](https://youtu.be/WWb9e_y1B40) |

Agent demos are easy; agent *products* are not. Most of the work went into the parts users never see — quota enforcement that survives a replayed webhook, routing that degrades instead of failing, and a graph where a bad generation is caught by a critic agent rather than by a customer.

</details>

<details>
<summary><b>&nbsp;Vendor Performance Analysis — Retail Analytics at Scale</b> &nbsp;·&nbsp; <i>Data Engineering · Analytics</i></summary>

<br>

An end-to-end ETL and analytics pipeline over **15.6M+ transaction records**, built to answer a question the business could not previously ask: which vendors are quietly tying up working capital?

| | |
| :--- | :--- |
| **Built with** | Python · SQL · Pandas · Power BI |
| **Scale** | 15.6M+ transaction records ingested and modelled |
| **Speed** | Query time cut from **9 minutes to 44 seconds** (~12x) through indexing and query rewrites |
| **Finding** | **$3.7M** of unsold inventory capital sitting with underperforming vendors |
| **Delivered** | An executive Power BI dashboard showing margin and turnover per vendor |
| **Links** | [Repository](https://github.com/ParshvCrafts/Vendor-Performance-Analysis) |

The 12x speedup mattered more than it sounds. At nine minutes a query, analysts asked one question a day. At forty-four seconds, they explored. Making the pipeline fast enough to be interactive changed what the data was used for.

</details>

<details>
<summary><b>&nbsp;AI Text Summarizer — Fine-Tuned FLAN-T5</b> &nbsp;·&nbsp; <i>NLP · MLOps · Full-Stack</i></summary>

<br>

A dialogue summarisation service built on **FLAN-T5 fine-tuned over 16,000+ SAMSum conversations**, using a training loop written from scratch in PyTorch with mixed precision and resumable checkpoints.

| | |
| :--- | :--- |
| **Built with** | Python · PyTorch · FLAN-T5 · FastAPI · Groq · React · Vite · Tailwind |
| **Training** | 16,000+ dialogues · fp16 mixed precision · resumable checkpoints · 4 training profiles |
| **Quality** | **ROUGE-1 = 43.53** |
| **Speed** | Sub-second inference through Groq |
| **Testing** | 35 tests, all passing |
| **Links** | [Repository](https://github.com/ParshvCrafts/Text-Summarizer) · [Live Demo](https://text-summarizer-lilac.vercel.app/) · [Video](https://youtu.be/RNVwHcDpYfc) |

Writing the training loop by hand instead of reaching for a prebuilt `Trainer` was deliberate. Checkpoint resumption and profile switching are exactly what break when you cannot see the loop — and they are what let the model train on free compute that can be interrupted at any moment.

</details>

<details>
<summary><b>&nbsp;SpaceX Falcon 9 Landing Predictor</b> &nbsp;·&nbsp; <i>Data Science · Predictive Modelling</i></summary>

<br>

A full data-science pipeline — collection, cleaning, exploration, mapping and modelling — that predicts whether a Falcon 9 first stage will land successfully, then turns that into launch-cost economics.

| | |
| :--- | :--- |
| **Built with** | Python · Pandas · scikit-learn · Matplotlib · Seaborn · Folium · Plotly Dash |
| **Pipeline** | API and web-scraped data · feature engineering · interactive maps and dashboard |
| **Modelling** | 4 classifiers compared under GridSearchCV; SVM won |
| **Accuracy** | **94.4%** on held-out test data |
| **Why it matters** | Quantified a **$103M** cost difference per launch depending on stage recovery |
| **Links** | [Repository](https://github.com/ParshvCrafts/SpaceX-Landing-Predictor) |

The modelling was the short part. The value came from the ingestion layer — reconciling an inconsistent public API against scraped launch tables, which is where the real-world errors lived.

</details>

<details>
<summary><b>&nbsp;CFD Navier–Stokes Solver</b> &nbsp;·&nbsp; <i>Scientific Computing · Numerical Methods</i></summary>

<br>

A 2D fluid-dynamics solver written from first principles for UC Berkeley Physics 77, used to sweep airfoil shapes for the best lift-to-drag ratio.

| | |
| :--- | :--- |
| **Built with** | Python · NumPy · Matplotlib · finite-difference methods |
| **Method** | 2D incompressible Navier–Stokes, solved on a finite-difference grid |
| **Result** | Best **lift-to-drag = 1.479** (NACA 5315 airfoil at 0.1 m/s) |
| **Recognition** | **Charlene Conrad Liebau Library Prize — Honorable Mention**, the only STEM paper among lower-division finalists from 51 applicants |
| **Archived** | UC eScholarship |
| **Links** | [Repository](https://github.com/ParshvCrafts/CFD_Navier-Stokes_Solver) |

Implementing the pressure coupling by hand rather than calling a solver library is why this one is here. It is the project where numerical stability stopped being a debugging problem and became a design constraint.

</details>

---

## Tech Stack

<div align="center">

**Languages**

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="https://go-skill-icons.vercel.app/api/icons?i=python,java,typescript,javascript,html,css&theme=dark&titles=true">
  <img src="https://go-skill-icons.vercel.app/api/icons?i=python,java,typescript,javascript,html,css&theme=light&titles=true" height="48" alt="Python, Java, TypeScript, JavaScript, HTML, CSS">
</picture>

<br><br>

**Machine Learning &amp; AI**

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="https://go-skill-icons.vercel.app/api/icons?i=pytorch,tensorflow,sklearn,opencv,huggingface,langchain&theme=dark&titles=true">
  <img src="https://go-skill-icons.vercel.app/api/icons?i=pytorch,tensorflow,sklearn,opencv,huggingface,langchain&theme=light&titles=true" height="48" alt="PyTorch, TensorFlow, scikit-learn, OpenCV, Hugging Face, LangChain">
</picture>

<br><br>

**Data &amp; Analytics**

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="https://go-skill-icons.vercel.app/api/icons?i=pandas,numpy,spark,postgresql,mysql,sqlite,plotly,seaborn,matplotlib,jupyter&theme=dark&titles=true">
  <img src="https://go-skill-icons.vercel.app/api/icons?i=pandas,numpy,spark,postgresql,mysql,sqlite,plotly,seaborn,matplotlib,jupyter&theme=light&titles=true" height="48" alt="Pandas, NumPy, Spark, PostgreSQL, MySQL, SQLite, Plotly, Seaborn, Matplotlib, Jupyter">
</picture>

<br><br>

**Backend, Cloud &amp; Tooling**

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="https://go-skill-icons.vercel.app/api/icons?i=fastapi,flask,react,nextjs,nodejs,tailwindcss,docker,aws,vercel,git,github,vscode&theme=dark&titles=true">
  <img src="https://go-skill-icons.vercel.app/api/icons?i=fastapi,flask,react,nextjs,nodejs,tailwindcss,docker,aws,vercel,git,github,vscode&theme=light&titles=true" height="48" alt="FastAPI, Flask, React, Next.js, Node.js, Tailwind CSS, Docker, AWS, Vercel, Git, GitHub, VS Code">
</picture>

</div>

---

## What I Can Actually Do

Each row names the system that proves it, so nothing here rests on a job title or a buzzword.

| Area | Level | The system that backs it |
| :--- | :--- | :--- |
| **Agentic AI / multi-agent systems** | Production | 6-agent LangGraph workflow serving paying users, with failover across 10 LLM providers — *AtlasMind* |
| **Search &amp; retrieval (RAG)** | Production | Vector + keyword retrieval over 29K products, two FAISS indexes fused by rank fusion — *Interlace* |
| **Fine-tuning transformers** | Proficient | FLAN-T5 on 16K dialogues, hand-written fp16 PyTorch loop, ROUGE-1 43.53 — *Text Summarizer* |
| **Classical ML &amp; model selection** | Proficient | GridSearchCV across SVM / Random Forest / CNN; 94.4% and 99% accuracy on two separate problems |
| **Data engineering &amp; ETL** | Proficient | 15.6M-record pipeline with a 12x query-time cut; schema consolidation in production at Amazon |
| **Deployment &amp; MLOps** | Working | Dockerised services on HuggingFace, Vercel, Render and Railway; checkpointed training; full test suites |

---

## Achievements

<div align="center">

| Recognition | What it is |
| :--- | :--- |
| **4.00 GPA · Dean's List ×2** | UC Berkeley, B.A. Data Science — every graded term |
| **Amazon Future Engineer Scholar** | National scholarship that includes the Amazon software engineering internship |
| **Greenhouse Scholar** | Whole College Program — selected at a 1-in-1,780 rate |
| **RSM US Foundation First Generation Scholar** | 2026 cohort — 1 of 5 selected nationwide |
| **Charlene Conrad Liebau Library Prize** | Honorable Mention — the only STEM paper among lower-division finalists from 51 applicants |
| **Valedictorian** | Ranked #1 of 455 · AP Scholar with Distinction |

</div>

<details>
<summary><b>&nbsp;More honours and fellowships</b></summary>

<br>

| Recognition | What it is |
| :--- | :--- |
| **MLT Ascend Scholar** | Management Leadership for Tomorrow career-development fellowship |
| **AI4ALL Ignite Fellow** | Applied AI accelerator for underrepresented technologists |
| **CAA Leadership Scholar** | Cal Alumni Association multi-year leadership award |
| **QuestBridge National College Match Finalist** | Also a College Prep Scholar |
| **Berkeley competitive prizes** | Leslie Lipson Essay Prize · Elizabeth Mills Crothers Prize · Dorothy Rosenberg Memorial Prize · Lili Fabilli &amp; Eric Hoffer Essay Prize |
| **IMO Gold Medal** | International Mathematics Olympiad, Level 1 |
| **GFWC National 1st Place** | National youth writing competition |

</details>

---

## Certifications

<div align="center">

<img src="https://img.shields.io/badge/AWS%20Certified%20AI%20Practitioner-FF9900?style=for-the-badge&logo=amazonwebservices&logoColor=white" alt="AWS Certified AI Practitioner">

<br><br>

<img src="https://img.shields.io/badge/Berkeley%20Student%20Leadership%20Academy-003262?style=flat-square&logo=googlescholar&logoColor=FDB515" alt="Berkeley Student Leadership Academy">
<img src="https://img.shields.io/badge/Berkeley%20Changemaker-003262?style=flat-square&logo=googlescholar&logoColor=FDB515" alt="Berkeley Changemaker">
<img src="https://img.shields.io/badge/CodePath%20AI%20Engineering-26A641?style=flat-square&logo=codeforces&logoColor=white" alt="CodePath Foundations of AI Engineering">

<br>

<img src="https://img.shields.io/badge/IBM%20Data%20Analytics-052FAD?style=flat-square&logo=ibm&logoColor=white" alt="IBM Introduction to Data Analytics">
<img src="https://img.shields.io/badge/SQL%20for%20Data%20Science-002855?style=flat-square&logo=postgresql&logoColor=white" alt="SQL for Data Science, UC Davis">
<img src="https://img.shields.io/badge/Python%20for%20Everybody-00274C?style=flat-square&logo=python&logoColor=FFCB05" alt="Python for Everybody, University of Michigan">

<br>

<img src="https://img.shields.io/badge/Deloitte%20Data%20Analytics-86BC25?style=flat-square&logo=deloitte&logoColor=white" alt="Deloitte Data Analytics, Forage">
<img src="https://img.shields.io/badge/Commonwealth%20Bank%20Data%20Science-FFCC00?style=flat-square&logo=commonwealthbank&logoColor=black" alt="Commonwealth Bank Data Science, Forage">

</div>

---

## GitHub Activity

<div align="center">

<!-- These cards are generated in this repository by scripts/cards.py and refreshed
     twice a day by .github/workflows/cards.yml. They used to come from the shared
     public github-readme-stats and streak-stats instances, which went down. -->

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="assets/card-stats-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/card-stats-light.svg">
  <img src="assets/card-stats-dark.svg" width="440" alt="GitHub statistics">
</picture>
<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="assets/card-langs-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/card-langs-light.svg">
  <img src="assets/card-langs-dark.svg" width="440" alt="Most used languages">
</picture>

<br>

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="assets/card-streak-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/card-streak-light.svg">
  <img src="assets/card-streak-dark.svg" width="440" alt="Contribution streaks">
</picture>

<br><br>

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="assets/card-activity-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/card-activity-light.svg">
  <img src="assets/card-activity-dark.svg" width="100%" alt="Contribution activity over the past year">
</picture>

<br><br>

<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="https://raw.githubusercontent.com/ParshvCrafts/ParshvCrafts/output/github-snake-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ParshvCrafts/ParshvCrafts/output/github-snake.svg">
  <img src="https://raw.githubusercontent.com/ParshvCrafts/ParshvCrafts/output/github-snake.svg" width="100%" alt="Snake eating the contribution graph">
</picture>

</div>

---

## Right Now

```yaml
studying:  "Data Science @ UC Berkeley - Class of 2029"
shipped:   "Batch-inference config redesign at Amazon - 0 production incidents"

building:
  - "Agentic systems in LangGraph: planner, critic and tool-use topologies"
  - "Hybrid search - vector and keyword retrieval fused for one domain"
  - "Data pipelines that stay interactive past 10M rows"

learning:
  - "Distributed data engineering: Spark, streaming, warehouse modelling"
  - "Evaluation for LLM systems - the part everyone skips"
  - "Transformer internals, past the point of fine-tuning"

open_to:
  - "Summer 2027 internships - Data Science, Data Engineering, ML, AI Engineering"
  - "Open-source collaboration on AI tooling and evaluation"
```

---

## Let's Talk

<div align="center">

If you are hiring, building something adjacent, or just want to compare notes on agent evaluation — I answer every message.

<br>

<a href="https://www.linkedin.com/in/parshv-patel-65a90326b/"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
<a href="mailto:parshvpatel_0910@berkeley.edu"><img src="https://img.shields.io/badge/Email-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"></a>
<a href="https://www.portfolio.parshvpatel.com/"><img src="https://img.shields.io/badge/Portfolio-39D353?style=for-the-badge&logo=vercel&logoColor=0D1117" alt="Portfolio"></a>
<a href="https://github.com/ParshvCrafts?tab=repositories"><img src="https://img.shields.io/badge/Repositories-F97316?style=for-the-badge&logo=github&logoColor=white" alt="Repositories"></a>

<br><br>

<i>Good models are cheap. Good data, good schemas, and good failure modes are what actually ship.</i>

</div>

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&height=110&section=footer&color=0:0D1117,50:0E4429,100:39D353" alt="">
