# KOREV AI - Attendance Management System

An intelligent attendance management system powered by AI that analyzes attendance data and provides insights through interactive dashboards, charts, and reports.

## 🚀 Features

- 🤖 **AI-Powered Analysis**: Uses OpenAI GPT-4 for intelligent data analysis
- 📊 **Interactive Dashboards**: Dynamic tables, charts, and metrics
- 🌐 **Bilingual Support**: Full English and Arabic language support
- 🔒 **Security First**: Rate limiting, input sanitization, and secure database access
- 📱 **Responsive Design**: Desktop application-style interface
- 📈 **Real-time Insights**: Instant attendance pattern analysis

## 🛡️ Security Features

- Rate limiting on all endpoints
- Input sanitization and validation
- SQL injection protection
- Security headers implementation
- Environment variable protection
- Read-only database access

## 🏗️ Architecture

- **Backend**: Flask with OpenAI API integration
- **Frontend**: Vanilla JavaScript with Chart.js
- **Database**: SQLite with secure access patterns
- **Security**: Flask-Limiter, Bleach sanitization

## 📋 Prerequisites

- Python 3.8+
- OpenAI API key
- SQLite database

## ⚡ Quick Start

1. **Clone and Setup**
```bash
git clone <repository-url>
cd KOREV
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

3. **Run Application**
```bash
python app.py
```

4. **Access Dashboard**
```
http://localhost:5000
```

## 🌍 Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | ✅ | - |
| `DATABASE_PATH` | SQLite database path | ❌ | `attendance.db` |
| `FLASK_DEBUG` | Debug mode | ❌ | `False` |
| `HOST` | Server host | ❌ | `127.0.0.1` |
| `PORT` | Server port | ❌ | `5000` |

## 🎯 Usage Examples

### English Queries
- "Show me attendance summary in a table"
- "Create a chart of department attendance"
- "Give me key attendance metrics"
- "Analyze attendance trends"

### Arabic Queries  
- "أظهر لي ملخص الحضور في جدول"
- "أنشئ مخطط لحضور الأقسام"
- "أعطني مؤشرات الحضور الرئيسية"
- "حلل اتجاهات الحضور"

## 🚀 Production Deployment

### Using Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Security Checklist for Production
- [ ] Set `FLASK_DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure HTTPS/SSL
- [ ] Set up proper logging
- [ ] Configure database backups
- [ ] Monitor rate limits
- [ ] Regular security updates

## 🔧 API Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/` | GET | Main dashboard | - |
| `/chat` | POST | AI chat interface | 30/min |
| `/analyze-database` | POST | Database analysis | 5/min |
| `/generate-sample-data` | POST | Sample data | 10/min |
| `/test-database` | GET | Database test | - |

## 🛠️ Development

### Project Structure
```
KOREV/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Frontend interface
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please contact the development team or create an issue in the repository.

## 🔄 Version History

- **v1.0.0** - Initial release with bilingual support
- **v1.1.0** - Added security improvements and rate limiting
- **v1.2.0** - Enhanced UI and production readiness
