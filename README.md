# EDoc AI Document Analyzer

An intelligent document analysis tool that uses OpenAI's GPT-4 to analyze PDF documents and provide interactive responses with tables, charts, and visualizations.

## Features

- 📄 PDF text extraction and analysis
- 🤖 AI-powered question answering
- 📊 Dynamic table generation
- 📈 Interactive charts and visualizations
- 📱 Responsive web interface
- 🔒 Secure API key management

## Prerequisites

- Python 3.8 or higher
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/edoc-ai-analyzer.git
cd edoc-ai-analyzer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to the `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

5. Place your PDF file in the project directory or update the `PDF_FILE_PATH` in `.env`

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Use the chat interface to ask questions about your document:
   - General questions: "What is this document about?"
   - Request tables: "Show me the data in a table"
   - Request charts: "Create a chart of the attendance data"

## Environment Variables

Create a `.env` file with the following variables:

```bash
OPENAI_API_KEY=your_openai_api_key_here
PDF_FILE_PATH=your_pdf_file.pdf
FLASK_DEBUG=False
PORT=5000
HOST=127.0.0.1
```

## API Endpoints

- `GET /` - Main interface
- `POST /chat` - Chat with the document
- `GET /extract` - Extract PDF content
- `POST /test-openai` - Test API connection
- `GET /check-dependencies` - Check system dependencies

## Deployment

### Heroku

1. Create a Heroku app
2. Set environment variables in Heroku dashboard
3. Deploy using Git:

```bash
git push heroku main
```

### Docker

```bash
docker build -t edoc-analyzer .
docker run -p 5000:5000 --env-file .env edoc-analyzer
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Security

- Never commit API keys or sensitive data
- Use environment variables for all configuration
- Follow the `.gitignore` patterns

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues, please create an issue on GitHub or contact [your-email@example.com].
