# Attendance AI Analyzer

An intelligent attendance data analysis tool that uses OpenAI's GPT-4 to analyze attendance reports and provide insights with interactive tables, charts, and visualizations.

## Features

- 📊 Attendance report analysis and insights
- 🤖 AI-powered question answering about attendance data
- 📋 Dynamic table generation for employee data
- 📈 Interactive charts for attendance visualization
- 📱 Responsive web interface
- 🔒 Secure API key management

## Use Cases

- Analyze monthly/weekly attendance reports
- Generate attendance summaries and insights
- Identify attendance patterns and trends
- Create visual reports for management
- Answer specific questions about employee attendance

## Quick Start

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

6. Start the application:
```bash
python app.py
```

7. Open your browser and navigate to `http://localhost:5000`

8. Use the chat interface to ask questions about your document:
   - General questions: "What is this document about?"
   - Request tables: "Show me the data in a table"
   - Request charts: "Create a chart of the attendance data"

## Sample Questions

- "What is the overall attendance rate?"
- "Show me employee attendance in a table"
- "Create a chart of attendance trends"
- "Which employees have perfect attendance?"
- "What are the main attendance insights?"

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `PDF_FILE_PATH` | Path to attendance report | `MonthlyAttendanceReport (1).pdf` |
| `FLASK_DEBUG` | Enable debug mode | `False` |

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
