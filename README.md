# EDoc AI Document Analyzer

An intelligent document analysis tool that uses OpenAI's GPT-4 to analyze PDF documents and provide interactive responses with tables, charts, and visualizations.

## Features

- 📄 PDF text extraction and analysis
- 🤖 AI-powered question answering
- 📊 Dynamic table generation (when requested)
- 📈 Interactive charts and visualizations (when requested)
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
   - Create a `.env` file in the project root
   - Add your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
PDF_FILE_PATH=MonthlyAttendanceReport (1).pdf
FLASK_DEBUG=False
```

5. Place your PDF file in the project directory

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

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `PDF_FILE_PATH` | Path to your PDF file | `MonthlyAttendanceReport (1).pdf` |
| `FLASK_DEBUG` | Enable debug mode | `False` |
| `PORT` | Server port | `5000` |
| `HOST` | Server host | `127.0.0.1` |

## Security Notes

- Never commit your `.env` file
- Keep your OpenAI API key secure
- The application only generates structured components when explicitly requested

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.
