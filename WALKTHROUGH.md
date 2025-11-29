# AI Paper Reviewer - Complete System Walkthrough

## 🎯 Overview

This is a **multi-agent AI system** that provides comprehensive, conference-style reviews for academic papers. The system uses Flask for the backend, Google Gemini for LLM capabilities, and Tavily for academic paper search.

---

## 🏗️ System Architecture

### Agent Workflow

```
User Upload PDF
      ↓
  Root Agent (Orchestrator)
      ↓
  Parser Agent → Parses PDF to Markdown
      ↓
  Paper Finder Agent → Searches related papers (Tavily)
      ↓
  Ranking Agent → Ranks top 5 papers
      ↓
  Reviewer Agent → Generates comprehensive review
      ↓
  Root Agent → Returns formatted review to user
```

### Component Details

#### 1. **Root Agent** (`agents/root_agent.py`)
- **Role**: Central orchestrator
- **Responsibilities**:
  - Coordinates all sub-agents
  - Manages data flow between agents
  - Formats final output
  - Error handling and logging

#### 2. **Parser Agent** (`agents/parser_agent.py`)
- **Role**: Document processor
- **Technology**: MarkItDown
- **Output**:
  - Title
  - Abstract
  - Authors
  - Keywords
  - Full content in markdown

#### 3. **Paper Finder Agent** (`agents/finder_agent.py`)
- **Role**: Research paper discovery
- **Technology**: Tavily API
- **Features**:
  - Searches academic databases
  - Filters for reputable sources (arXiv, IEEE, ACM, etc.)
  - Returns top 10 related papers

#### 4. **Ranking Agent** (`agents/ranking_agent.py`)
- **Role**: Paper evaluation
- **Scoring Criteria**:
  - **Relevance Score** (1-10): Keyword overlap with query
  - **Quality Score** (1-10): Publication venue reputation
  - **Combined Score**: Weighted average (60% relevance, 40% quality)
- **Output**: Top 5 ranked papers with justifications

#### 5. **Reviewer Agent** (`agents/reviewer_agent.py`)
- **Role**: Comprehensive review generation
- **Review Structure**:
  - ✅ **Summary** (3-5 sentences)
  - 💪 **Strengths** (4-6 points)
  - ⚠️ **Weaknesses** (4-6 points)
  - 💭 **Detailed Comments** (methodology, experiments, presentation)
  - ❓ **Questions for Authors** (3-5 questions)
  - ⭐ **Overall Assessment** (recommendation + confidence)
  - 📚 **Related Work Analysis**

---

## 🎨 Frontend Features

### Modern UI Design
- **Dark Theme**: Easy on the eyes (#0f0f23 background)
- **Gradient Accents**: Purple-blue gradients (#667eea → #764ba2)
- **Smooth Animations**: Micro-interactions for better UX
- **Responsive Layout**: Works on desktop and mobile

### User Flow

1. **Upload Section**
   - Drag & drop or click to upload
   - Real-time file validation (10MB max, PDF only)
   - Displays file name and size

2. **Status Check**
   - Paste review token
   - Real-time status updates (Processing → Completed)
   - Auto-refresh capability

3. **Review Display**
   - Sidebar navigation for easy section jumping
   - Collapsible sections
   - Syntax-highlighted code/formulas (if applicable)
   - Export options (Markdown/HTML)

---

## 📡 API Endpoints

### `POST /api/upload`
**Upload paper for review**

**Request**:
```bash
curl -X POST -F "file=@paper.pdf" http://localhost:5000/api/upload
```

**Response**:
```json
{
  "success": true,
  "token": "uuid-token-here",
  "message": "Paper uploaded successfully"
}
```

---

### `GET /api/status/<token>`
**Check review processing status**

**Request**:
```bash
curl http://localhost:5000/api/status/uuid-token-here
```

**Response**:
```json
{
  "token": "uuid-token-here",
  "status": "processing",  // or "completed", "failed"
  "progress": "Ranking papers...",
  "uploaded_at": "2025-11-28T10:00:00"
}
```

---

### `GET /api/review/<token>`
**Retrieve completed review**

**Request**:
```bash
curl http://localhost:5000/api/review/uuid-token-here
```

**Response**:
```json
{
  "token": "uuid-token-here",
  "status": "completed",
  "result": {
    "paper": {
      "title": "...",
      "abstract": "...",
      "authors": [...]
    },
    "related_papers": [...],
    "review": {
      "summary": "...",
      "strengths": [...],
      "weaknesses": [...],
      ...
    }
  }
}
```

---

## 🚀 Getting Started

### Prerequisites
```bash
# Python 3.8+
python3 --version

# pip
pip --version
```

### Quick Start

1. **Navigate to project**:
```bash
cd paper_reviewer
```

2. **Run setup script**:
```bash
./start.sh
```

3. **Add API keys to `.env`**:
```env
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
```

4. **Start the application**:
```bash
python app.py
```

5. **Open browser**:
```
http://localhost:5000
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI API key for Gemini | ✅ Yes | `TAVILY_API_KEY` | Tavily API key for search | ✅ Yes |

### Application Settings (`app.py`)

```python
# Maximum file size
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

# Allowed file extensions
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Upload and review directories
app.config['UPLOAD_FOLDER'] = 'uploads'
```

---

## 📊 Example Output

### Sample Review Structure

```json
{
  "summary": "This paper proposes...",
  "strengths": [
    "Novel approach to problem X",
    "Comprehensive experimental evaluation",
    "Clear presentation and well-structured"
  ],
  "weaknesses": [
    "Limited comparison with baseline Y",
    "Scalability concerns not addressed",
    "Some notation is unclear"
  ],
  "detailed_comments": {
    "methodology": "The proposed method...",
    "experiments": "The experimental setup...",
    "presentation": "Overall well-written..."
  },
  "questions": [
    "How does the method scale to larger datasets?",
    "What is the computational complexity?"
  ],
  "overall_assessment": {
    "recommendation": "Weak Accept",
    "confidence": "Medium",
    "justification": "The paper makes solid contributions..."
  }
}
```

---

## 🐛 Troubleshooting

### Common Issues

**❌ PDF Parsing Fails**
```
Solution: Ensure PDF is text-based, not scanned images
```

**❌ No Related Papers Found**
```
Solution: 
1. Check TAVILY_API_KEY is correct
2. Verify internet connection
3. Try broader search terms
```

**❌ Review Generation Timeout**
```
Solution:
1. Check GOOGLE_API_KEY quota
2. Reduce paper complexity
3. Check network connectivity
```

---

## 🚀 Production Deployment

### Recommended Stack

1. **Web Server**: Gunicorn + Nginx
2. **Database**: PostgreSQL (replace in-memory storage)
3. **Task Queue**: Celery + Redis
4. **Storage**: AWS S3 / Google Cloud Storage
5. **Logging**: ELK Stack or CloudWatch
6. **Monitoring**: Prometheus + Grafana

### Deployment Checklist

- [ ] Set `DEBUG=False`
- [ ] Use production WSGI server
- [ ] Configure database
- [ ] Set up task queue for async processing
- [ ] Add rate limiting
- [ ] Implement authentication
- [ ] Set up SSL/TLS
- [ ] Configure logging
- [ ] Add monitoring/alerts
- [ ] Regular backups

---

## 📈 Future Enhancements

### Planned Features

1. **Multi-format Support**
   - Word documents (.docx)
   - LaTeX files (.tex)
   - Plain text (.txt)

2. **Advanced Review Options**
   - Select review style (conference/journal)
   - Choose review depth (quick/comprehensive)
   - Custom reviewer instructions

3. **Collaboration Features**
   - Share reviews with team
   - Collaborative editing
   - Review comparison

4. **Analytics Dashboard**
   - Review statistics
   - Common weaknesses trends
   - Citation analysis

5. **Export Options**
   - PDF export
   - LaTeX export
   - Email delivery

---

## 📚 Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Flask (Python) |
| **LLM** | Google Gemini 2.5 Flash |
| **Search** | Tavily API |
| **PDF Parser** | MarkItDown |
| **Frontend** | HTML5, CSS3, Vanilla JS |
| **Styling** | Custom CSS (Dark Theme) |

---

## 📄 License

MIT License - Feel free to use and modify

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

---

## 📞 Support

For issues or questions:
- Check the README.md
- Review troubleshooting section
- Open GitHub issue

---

**Built with ❤️ using Google Gemini and Flask**
