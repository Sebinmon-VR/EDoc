from flask import Flask, request, jsonify, render_template
import PyPDF2
import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Global variable to store extracted PDF content
PDF_CONTENT = ""

# Set OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Validate API key
if not openai.api_key:
    print("WARNING: OPENAI_API_KEY not found in environment variables!")
    print("Please create a .env file with your API key or set the environment variable.")

def extract_pdf_content(pdf_path):
    """Extract all text content from a PDF file."""
    global PDF_CONTENT
    
    try:
        # Check if file exists
        if not os.path.exists(pdf_path):
            return {"error": f"PDF file not found: {pdf_path}"}
        
        # Open and read the PDF
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Get total pages
            total_pages = len(pdf_reader.pages)
            
            # Extract text from all pages
            full_text = ""
            page_contents = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        page_contents.append({
                            'page': page_num + 1,
                            'text': page_text.strip(),
                            'length': len(page_text.strip())
                        })
                        full_text += f"\n=== PAGE {page_num + 1} ===\n{page_text}\n"
                    else:
                        page_contents.append({
                            'page': page_num + 1,
                            'text': "",
                            'length': 0,
                            'status': "No text found"
                        })
                except Exception as e:
                    page_contents.append({
                        'page': page_num + 1,
                        'text': "",
                        'length': 0,
                        'error': str(e)
                    })
            
            # Store extracted content globally
            PDF_CONTENT = full_text
            
            # Print extracted content to console
            print("\n" + "="*60)
            print("EXTRACTED PDF CONTENT:")
            print("="*60)
            print(full_text)
            print("="*60)
            print(f"Total Pages: {total_pages}")
            print(f"Total Characters: {len(full_text)}")
            print("="*60 + "\n")
            
            return {
                "success": True,
                "file_path": pdf_path,
                "total_pages": total_pages,
                "full_text": full_text,
                "pages": page_contents,
                "total_characters": len(full_text)
            }
            
    except Exception as e:
        return {"error": f"Failed to extract PDF content: {str(e)}"}

def chatbot_with_pdf(user_question):
    """
    Use GPT-4o to answer questions based on extracted PDF content.
    Enhanced to provide structured responses with components only when requested.
    """
    try:
        if not PDF_CONTENT:
            return {"error": "No PDF content available. Please extract PDF first."}
        
        if not openai.api_key:
            return {"error": "OpenAI API key not configured. Please check your environment variables."}
        
        # Check if user explicitly asks for structured data
        question_lower = user_question.lower()
        wants_table = any(keyword in question_lower for keyword in ['table', 'list employees', 'show data', 'in a table'])
        wants_chart = any(keyword in question_lower for keyword in ['chart', 'graph', 'visualize', 'pie chart', 'bar chart'])
        wants_cards = any(keyword in question_lower for keyword in ['key metrics', 'summary cards', 'dashboard'])
        
        # Create prompt based on what user wants
        if wants_table or wants_chart or wants_cards:
            prompt = f"""You are an AI assistant analyzing a document. Based on the following document content, answer the user's question and provide structured data as requested.

Document Content:
{PDF_CONTENT}

User Question: {user_question}

Instructions:
1. Answer the user's question based on the document content
2. Since the user asked for structured data, provide it in the appropriate format
3. Be concise and avoid duplicating information

IMPORTANT: Only provide structured data if explicitly requested. Format as follows:

For tables:
TABLE_DATA:
headers: [Column1, Column2, Column3]
rows: [[data1, data2, data3], [data4, data5, data6]]

For charts:
CHART_DATA:
type: bar|pie|line
title: Chart Title
labels: [Label1, Label2, Label3]
values: [10, 20, 30]

For metrics:
CARDS_DATA:
[{{"title": "Metric Name", "value": "123", "description": "Description"}}]

Answer:"""
        else:
            # Simple text-only response
            prompt = f"""You are an AI assistant analyzing a document. Based on the following document content, answer the user's question accurately and comprehensively with a text response only.

Document Content:
{PDF_CONTENT}

User Question: {user_question}

Instructions:
- Answer based only on the information provided in the document
- Provide a clear, well-structured text response
- Include relevant details and reference page numbers when possible
- Do NOT provide any structured data formats (tables, charts, etc.) unless explicitly requested
- Keep the response conversational and informative

Answer:"""
        
        # Call GPT-4o
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on document content. Only provide structured data when explicitly requested."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1200,
            temperature=0.1
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Only parse for structured data if user explicitly requested it
        if wants_table or wants_chart or wants_cards:
            parsed_response = parse_structured_response(ai_response, user_question)
            final_text = parsed_response['text']
            components = parsed_response['components']
            
            # Clean up text if components exist
            if components:
                if "TABLE_DATA:" in ai_response:
                    final_text = ai_response.split("TABLE_DATA:")[0].strip()
                elif "CHART_DATA:" in ai_response:
                    final_text = ai_response.split("CHART_DATA:")[0].strip()
                elif "CARDS_DATA:" in ai_response:
                    final_text = ai_response.split("CARDS_DATA:")[0].strip()
                
                # Provide meaningful summary if text is too short
                if len(final_text) < 20:
                    if any(keyword in question_lower for keyword in ['employee', 'attendance']):
                        final_text = "Here is the employee attendance data from the monthly report:"
                    else:
                        final_text = "Here is the requested data from the document:"
        else:
            # For text-only responses, don't parse for components
            final_text = ai_response
            components = []
        
        return {
            "success": True,
            "question": user_question,
            "answer": final_text,
            "components": components,
            "model": "gpt-4o",
            "pdf_content_available": len(PDF_CONTENT) > 0
        }
        
    except Exception as e:
        return {"error": f"Chatbot error: {str(e)}"}

def parse_structured_response(ai_response, user_question):
    """Parse AI response to extract text and structured components."""
    try:
        components = []
        text_response = ai_response
        
        # Extract table data first
        if "TABLE_DATA:" in ai_response:
            table_data = extract_table_from_response(ai_response)
            if table_data:
                components.append({
                    "type": "table",
                    "data": table_data
                })
                # Remove table data from text response
                text_parts = ai_response.split("TABLE_DATA:")
                text_response = text_parts[0].strip()
        
        # Extract chart data
        if "CHART_DATA:" in ai_response:
            chart_data = extract_chart_from_response(ai_response)
            if chart_data:
                components.append({
                    "type": "chart",
                    "data": chart_data
                })
                # Remove chart data from text response
                if "CHART_DATA:" in text_response:
                    text_response = text_response.split("CHART_DATA:")[0].strip()
        
        # Extract cards data
        if "CARDS_DATA:" in ai_response:
            cards_data = extract_cards_from_response(ai_response)
            if cards_data:
                components.append({
                    "type": "cards",
                    "data": cards_data
                })
                # Remove cards data from text response
                if "CARDS_DATA:" in text_response:
                    text_response = text_response.split("CARDS_DATA:")[0].strip()
        
        # DO NOT auto-detect components - only use explicit structured data
        
        return {
            "text": text_response,
            "components": components
        }
        
    except Exception as e:
        print(f"Error parsing structured response: {e}")
        return {
            "text": ai_response,
            "components": []
        }

def extract_table_from_response(response):
    """Extract table data from AI response with safer parsing."""
    try:
        # Find the TABLE_DATA section
        if "TABLE_DATA:" not in response:
            return None
            
        table_section = response.split("TABLE_DATA:")[1]
        
        # Clean up the section by removing other data types that might follow
        if "CHART_DATA:" in table_section:
            table_section = table_section.split("CHART_DATA:")[0]
        if "CARDS_DATA:" in table_section:
            table_section = table_section.split("CARDS_DATA:")[0]
        
        # Handle multiline array parsing
        table_section = table_section.strip()
        
        # Try to extract headers and rows from the text
        headers = None
        rows = []
        
        lines = table_section.split('\n')
        collecting_rows = False
        row_buffer = ""
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Look for headers
            if line.startswith('headers:') and not headers:
                headers_str = line.replace('headers:', '').strip()
                try:
                    import ast
                    headers = ast.literal_eval(headers_str)
                except:
                    # Fallback: try to extract manually
                    if '[' in headers_str and ']' in headers_str:
                        headers_str = headers_str.strip('[]')
                        headers = [h.strip().strip('"\'') for h in headers_str.split(',')]
                continue
            
            # Look for rows
            if line.startswith('rows:') or collecting_rows:
                if line.startswith('rows:'):
                    row_buffer = line.replace('rows:', '').strip()
                    collecting_rows = True
                else:
                    row_buffer += " " + line
                
                # Check if we have a complete array
                if row_buffer.count('[') > 0 and row_buffer.count('[') == row_buffer.count(']'):
                    try:
                        import ast
                        rows = ast.literal_eval(row_buffer)
                        break
                    except:
                        # Continue collecting if parsing fails
                        continue
        
        # Fallback: try to parse the entire section as JSON-like structure
        if not headers or not rows:
            try:
                import re
                
                # Extract headers array
                headers_pattern = r'headers:\s*\[(.*?)\]'
                headers_match = re.search(headers_pattern, table_section, re.DOTALL)
                if headers_match:
                    headers_str = headers_match.group(1)
                    headers = [h.strip().strip('"\'') for h in headers_str.split(',')]
                
                # Extract rows array - handle multiline
                rows_pattern = r'rows:\s*\[(.*?)\](?:\s*$|\s*\n|$)'
                rows_match = re.search(rows_pattern, table_section, re.DOTALL | re.MULTILINE)
                if rows_match:
                    rows_content = '[' + rows_match.group(1) + ']'
                    try:
                        import ast
                        rows = ast.literal_eval(rows_content)
                    except:
                        # Manual parsing as last resort
                        rows = parse_rows_manually(rows_content)
                        
            except Exception as e:
                print(f"Fallback parsing failed: {e}")
        
        if headers and rows:
            return {
                "headers": headers,
                "rows": rows
            }
        
        return None
        
    except Exception as e:
        print(f"Error extracting table: {e}")
        return None

def parse_rows_manually(rows_content):
    """Manually parse rows when ast.literal_eval fails."""
    try:
        import re
        
        # Remove outer brackets
        rows_content = rows_content.strip('[]')
        
        # Split by row patterns - look for nested arrays
        row_pattern = r'\[(.*?)\]'
        row_matches = re.findall(row_pattern, rows_content)
        
        rows = []
        for row_match in row_matches:
            # Split by comma and clean each item
            items = []
            parts = row_match.split(',')
            current_item = ""
            in_quotes = False
            
            for part in parts:
                part = part.strip()
                
                # Handle quoted strings that might contain commas
                if (part.startswith('"') and part.endswith('"')) or (part.startswith("'") and part.endswith("'")):
                    items.append(part.strip('"\''))
                elif part.startswith('"') or part.startswith("'"):
                    current_item = part
                    in_quotes = True
                elif part.endswith('"') or part.endswith("'"):
                    current_item += "," + part
                    items.append(current_item.strip('"\''))
                    current_item = ""
                    in_quotes = False
                elif in_quotes:
                    current_item += "," + part
                else:
                    # Try to convert to appropriate type
                    try:
                        # Check if it's a number
                        if part.isdigit():
                            items.append(int(part))
                        elif '.' in part and part.replace('.', '').isdigit():
                            items.append(float(part))
                        else:
                            items.append(part.strip('"\''))
                    except:
                        items.append(part.strip('"\''))
            
            if items:
                rows.append(items)
        
        return rows
        
    except Exception as e:
        print(f"Manual parsing failed: {e}")
        return []

def extract_chart_from_response(response):
    """Extract chart data from AI response with safer parsing."""
    try:
        if "CHART_DATA:" not in response:
            return None
            
        chart_section = response.split("CHART_DATA:")[1]
        if "CARDS_DATA:" in chart_section:
            chart_section = chart_section.split("CARDS_DATA:")[0]
        
        lines = chart_section.strip().split('\n')
        chart_data = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key in ['labels', 'values']:
                    try:
                        import ast
                        # Try to parse as a Python literal
                        chart_data[key] = ast.literal_eval(value)
                    except (ValueError, SyntaxError) as e:
                        print(f"Error parsing {key}: {e}")
                        # Try manual parsing for common formats
                        if value.startswith('[') and value.endswith(']'):
                            try:
                                # Remove brackets and split by comma
                                items_str = value.strip('[]')
                                items = []
                                for item in items_str.split(','):
                                    item = item.strip().strip('"\'')
                                    # Try to convert to number if possible
                                    try:
                                        if '.' in item:
                                            items.append(float(item))
                                        else:
                                            items.append(int(item))
                                    except ValueError:
                                        items.append(item)
                                chart_data[key] = items
                            except Exception:
                                print(f"Failed to manually parse {key}: {value}")
                                continue
                        else:
                            continue
                elif key in ['type', 'title']:
                    chart_data[key] = value.strip('"\'')
                else:
                    chart_data[key] = value
        
        # Validate that we have the minimum required data
        if 'labels' in chart_data and 'values' in chart_data:
            # Ensure both arrays have the same length
            if len(chart_data['labels']) == len(chart_data['values']):
                return chart_data
            else:
                print(f"Chart data length mismatch: labels={len(chart_data['labels'])}, values={len(chart_data['values'])}")
        
        return None
        
    except Exception as e:
        print(f"Error extracting chart: {e}")
        return None

def extract_cards_from_response(response):
    """Extract cards data from AI response with safer parsing."""
    try:
        cards_section = response.split("CARDS_DATA:")[1].strip()
        
        # Remove any trailing text after the JSON
        lines = cards_section.split('\n')
        json_lines = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('[') or line.startswith('{') or '":' in line or line.endswith(']') or line.endswith('}')):
                json_lines.append(line)
            elif json_lines:  # Stop if we've started collecting JSON and hit non-JSON
                break
        
        if json_lines:
            json_str = ' '.join(json_lines)
            # Use json.loads instead of eval for safety
            import json
            cards_data = json.loads(json_str)
            return cards_data
        
        return None
        
    except Exception as e:
        print(f"Error extracting cards: {e}")
        return None

# Initialize PDF extraction when app starts
def initialize_pdf():
    """Extract PDF content when the application starts."""
    # Default PDF file - can be made configurable via environment variable
    pdf_file = os.getenv('PDF_FILE_PATH', 'MonthlyAttendanceReport (1).pdf')
    
    if not os.path.exists(pdf_file):
        print(f"WARNING: Attendance report file '{pdf_file}' not found!")
        print("Please ensure the attendance report exists or update the PDF_FILE_PATH environment variable.")
        return
    
    print("Loading attendance data...")
    result = extract_pdf_content(pdf_file)
    if result.get("success"):
        print("Attendance data successfully loaded!")
    else:
        print(f"Failed to load attendance data: {result.get('error')}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/extract')
def extract():
    """Extract content from default PDF file."""
    pdf_file = 'MonthlyAttendanceReport (1).pdf'
    result = extract_pdf_content(pdf_file)
    return jsonify(result)

@app.route('/chat', methods=['POST'])
def chat():
    """Enhanced chat endpoint with responsive components."""
    try:
        data = request.get_json()
        user_question = data.get('message', '') or data.get('question', '')

        if not user_question:
            return jsonify({"error": "No question provided"}), 400

        result = chatbot_with_pdf(user_question)
        if result.get("success"):
            return jsonify({
                "response": result["answer"],
                "components": result.get("components", []),
                "source": "ai_analysis"
            })
        else:
            return jsonify({
                "error": result.get("error"),
                "response": result.get("error"),
                "components": []
            })
    except Exception as e:
        return jsonify({
            "error": f"Chat error: {str(e)}",
            "components": []
        }), 500

@app.route('/test-pdf', methods=['GET'])
def test_pdf():
    """Test PDF extraction."""
    pdf_file = 'MonthlyAttendanceReport (1).pdf'
    result = extract_pdf_content(pdf_file)
    if result.get("success"):
        return jsonify({
            'pdf_path': pdf_file,
            'total_pages': result['total_pages'],
            'extraction_successful': True,
            'first_page_text_length': len(result['pages'][0]['text']) if result['pages'] else 0,
            'first_100_chars': result['full_text'][:100]
        })
    else:
        return jsonify({
            'error': result.get('error'),
            'extraction_successful': False
        })

@app.route('/pdf-info', methods=['GET'])
def pdf_info():
    """Get PDF file information."""
    pdf_file = 'MonthlyAttendanceReport (1).pdf'
    
    if os.path.exists(pdf_file):
        file_size = os.path.getsize(pdf_file)
        return jsonify({
            'file_exists': True,
            'file_size_mb': round(file_size / (1024 * 1024), 2)
        })
    else:
        return jsonify({
            'file_exists': False,
            'error': 'PDF file not found'
        })

@app.route('/simple-test', methods=['POST'])
def simple_test():
    """Simple AI test without PDF."""
    try:
        data = request.get_json()
        question = data.get('question', 'What is 2+2?')
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": question}],
            max_tokens=100
        )
        
        return jsonify({
            'response': response.choices[0].message.content.strip(),
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-openai', methods=['POST'])
def test_openai():
    """Test OpenAI API connection."""
    try:
        if not openai.api_key:
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured'
            }), 500
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello and confirm you're working!"}],
            max_tokens=50
        )
        
        return jsonify({
            'success': True,
            'response': response.choices[0].message.content.strip(),
            'model_used': 'gpt-3.5-turbo',
            'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else 'unknown'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/generate-sample-data', methods=['POST'])
def generate_sample_data():
    """Generate sample data for testing UI components."""
    try:
        data = request.get_json()
        component_type = data.get('type', 'all')
        
        components = []
        
        if component_type in ['all', 'table']:
            components.append({
                "type": "table",
                "data": {
                    "title": "Sample Data Table",
                    "headers": ["Name", "Value", "Status"],
                    "rows": [
                        ["Total Users", "1,234", "Active"],
                        ["New Signups", "56", "Growing"],
                        ["Revenue", "$12,345", "Up 15%"],
                        ["Support Tickets", "23", "Resolved"]
                    ]
                }
            })
        
        if component_type in ['all', 'chart']:
            components.append({
                "type": "chart",
                "data": {
                    "type": "pie",
                    "title": "Sample Chart",
                    "labels": ["Chrome", "Firefox", "Safari", "Edge"],
                    "values": [65, 20, 10, 5]
                }
            })
        
        if component_type in ['all', 'cards']:
            components.append({
                "type": "cards",
                "data": [
                    {"title": "Total", "value": "1,234", "description": "Total count"},
                    {"title": "Average", "value": "87.5", "description": "Average score"},
                    {"title": "Growth", "value": "+15%", "description": "This month"}
                ]
            })
        
        return jsonify({
            "text": "Sample components generated for testing:",
            "components": components
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze-document', methods=['POST'])
def analyze_document():
    """Analyze the attendance document."""
    try:
        if not PDF_CONTENT:
            return jsonify({"error": "No attendance data available"}), 400
        
        # Use chatbot function to analyze attendance document
        result = chatbot_with_pdf("Provide a comprehensive analysis of this attendance report including key statistics, attendance rates, and important insights.")
        
        if result.get("success"):
            return jsonify({
                "analysis": result["answer"],
                "components": result.get("components", [])
            })
        else:
            return jsonify({"error": result.get("error")}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/extract-text', methods=['GET'])
def extract_text():
    """Extract and return attendance data information."""
    try:
        if not PDF_CONTENT:
            return jsonify({"error": "No attendance data available"}), 400
        
        # Split into chunks for analysis
        chunks = PDF_CONTENT.split('\n')
        meaningful_chunks = [chunk.strip() for chunk in chunks if chunk.strip() and len(chunk.strip()) > 10]
        
        return jsonify({
            "text_length": len(PDF_CONTENT),
            "total_chunks": len(meaningful_chunks),
            "first_500_chars": PDF_CONTENT[:500] + "..." if len(PDF_CONTENT) > 500 else PDF_CONTENT,
            "data_type": "attendance_report"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Extract PDF content when app starts
initialize_pdf()

if __name__ == '__main__':
    # Use environment variables for Flask configuration
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')  # Changed to 0.0.0.0 for hosting compatibility
    
    app.run(debug=debug_mode, host=host, port=port)
