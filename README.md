# 💰 Financial ChatBot

A multilingual, AI-powered financial assistant that can:
- Analyze financial trends from Excel/CSV data
- Summarize and compare documents
- Perform statistical and table analysis
- Answer financial queries with context
- Conduct web research
- Handle user/session-based conversations with chat history
- Support document uploads per session
- Generate and download financial charts

Backend: **Python (≥3.10)**  
Frontend: **Node.js + React**

---

## 🚀 Quick Start

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Drashti7312/FinancialChatBot.git
cd FinancialChatBot
````

---

### 2️⃣ Backend Setup (Python)

1. **Create Python Environment** using `uv`:

   ```bash
   uv venv
   uv pip install -r requirements.txt
   # OR install from lock file
   uv pip sync uv.lock
   ```

2. **Run Backend**:

   ```bash
   python app/main.py
   ```

---

### 3️⃣ Frontend Setup (React)

1. **Install Node.js** (LTS recommended)
   [Download here](https://nodejs.org/)

2. **Install Dependencies**:

   ```bash
   npm install uuid
   npm install react-markdown remark-gfm
   ```

3. **Run Frontend**:

   ```bash
   npm run dev
   ```

---

### 4️⃣ Environment Variables

1. Copy `.env.example` → `.env`:

   ```bash
   cp .env.example .env
   ```

2. Set your Google Gemini API key:

   ```env
   GOOGLE_API_KEY=Your_Gemini_API_Key
   MONGODB_URL = "mongodb://localhost:27017"
   NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
   NEXT_PUBLIC_DEFAULT_USER_ID=demo_user
   ```

---

## 📂 Repository Structure

```
app/
 ├── config/            # App configuration
 │    └── settings.py
 ├── core/              # Core AI logic
 │    ├── chat_history.py
 │    ├── intent_classifier.py
 │    ├── multilingual.py
 │    ├── response_processor.py
 │    ├── tool_orchestrator.py
 │    ├── tool_orchestrator_utils.py
 │    └── tools_utils.py
 ├── database/
 │    └── database.py
 ├── mcp/
 │    └── mcp_server.py
 ├── schema/
 │    └── models.py
 ├── service/           # Business logic services
 │    ├── chat_service.py
 │    ├── document_service.py
 │    └── link_service.py
 ├── tools/             # Tool implementations
 │    ├── base_tool.py
 │    ├── comparative_analyser.py
 │    ├── document_summarizer.py
 │    ├── financial_trend_analyser.py
 │    ├── general_query.py
 │    ├── statistical_analyzer.py
 │    ├── table_extractor.py
 │    └── web_researcher.py
 ├── logger.py
 ├── main.py
 └── utility.py

Documents/              # Sample financial docs
pages/                  # Frontend pages
solutions/              # Architecture images
styles/                 # CSS
utils/                  # API helper
```

---

## 🔧 MCP Tool Overview

The **Model-Controller-Protocol (MCP)** system powers the chatbot’s tool orchestration.
Defined in `mcp.json`:

| Tool Name                      | Purpose                                                                                              |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **financial\_trend\_analysis** | Analyze financial data from Excel/CSV; supports quarter & metric selection; outputs visual insights. |
| **document\_summarizer**       | Summarize PDF/DOCX documents using Google Generative AI.                                             |
| **extract\_table\_data**       | Extract, filter, search, or aggregate table data from Excel/CSV.                                     |
| **comparative\_analysis**      | Compare financial tables across multiple PDF/DOCX files.                                             |
| **web\_research**              | Fetch and analyze content from a URL to answer queries.                                              |
| **statistical\_analysis**      | Perform statistical computations on Excel/CSV datasets.                                              |
| **general\_query**             | Handle general financial queries with conversation context.                                          |

---

## 🌍 Multilingual Support

* Implemented via `app/core/multilingual.py`
* Detects and translates user queries/responses in multiple languages
* Works with both text and extracted data insights

---

## 💬 Chat Features

* **User & Session-based Conversations** — Track conversations per user and session
* **View Previous Chats** — History stored via `chat_history.py`
* **Upload Documents Per Session** — Upload PDFs, DOCX, Excel, CSV for analysis
* **Download Charts** — Export generated visualizations from trend/comparative analysis tools

---

## 🧩 Tech Stack

**Backend**:

* Python ≥3.10
* FastAPI / custom services
* Google Generative AI

**Frontend**:

* React + Next.js
* TailwindCSS (if styled)
* `react-markdown` + `remark-gfm` for rich chat responses

---

