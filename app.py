from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import openai
import re
import bleach
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest

# Load environment variables first
load_dotenv(override=True)  # Force override existing env vars

app = Flask(__name__)

# Add rate limiting - Fixed syntax
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Global variable to store extracted database content
DB_CONTENT = ""
DB_INITIALIZED = False

# Set OpenAI API key from environment variable AFTER loading .env
openai.api_key = os.getenv('OPENAI_API_KEY')

# Database configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'attendance.db')

# Debug environment variables
print(f"DEBUG: Current working directory: {os.getcwd()}")
print(f"DEBUG: .env file exists: {os.path.exists('.env')}")
print(f"DEBUG: OPENAI_API_KEY loaded: {'Yes' if openai.api_key else 'No'}")
print(f"DEBUG: DATABASE_PATH: {DATABASE_PATH}")

# Validate API key
if not openai.api_key:
    print("WARNING: OPENAI_API_KEY not found in environment variables!")
    print("Please create a .env file with your API key or set the environment variable.")
    # Try to reload environment variables
    load_dotenv(override=True, verbose=True)
    openai.api_key = os.getenv('OPENAI_API_KEY')
    if openai.api_key:
        print("SUCCESS: API key loaded after retry")
    else:
        print("FAILED: API key still not found after retry")

def reload_env_vars():
    """Reload environment variables from .env file."""
    global openai
    try:
        load_dotenv(override=True, verbose=True)
        openai.api_key = os.getenv('OPENAI_API_KEY')
        print(f"Environment variables reloaded. API key available: {'Yes' if openai.api_key else 'No'}")
        return True
    except Exception as e:
        print(f"Error reloading environment variables: {e}")
        return False

def sanitize_input(text):
    """Sanitize user input to prevent XSS and injection attacks."""
    if not text or not isinstance(text, str):
        return ""
    
    # Remove potentially dangerous characters
    sanitized = bleach.clean(text, tags=[], attributes={}, strip=True)
    
    # Limit length
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]
    
    return sanitized.strip()

def validate_table_name(table_name):
    """Validate table name to prevent SQL injection."""
    if not table_name or not isinstance(table_name, str):
        return False
    
    # Only allow alphanumeric characters and underscores
    return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name) is not None

def extract_database_content():
    """Extract all content from the database with security improvements."""
    global DB_CONTENT, DB_INITIALIZED
    
    try:
        # Check if database exists
        if not os.path.exists(DATABASE_PATH):
            return {"error": f"Database file not found: {DATABASE_PATH}"}
        
        # Connect to database with read-only mode
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            return {"error": "No tables found in database"}
        
        full_content = ""
        table_data = {}
        
        for table in tables:
            table_name = table[0]
            
            # Validate table name to prevent SQL injection
            if not validate_table_name(table_name):
                print(f"Warning: Skipping invalid table name: {table_name}")
                continue
            
            # Get table schema using parameterized query equivalent
            cursor.execute("PRAGMA table_info([{}])".format(table_name))
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Get all data from table (limit to prevent memory issues)
            cursor.execute("SELECT * FROM [{}] LIMIT 1000".format(table_name))
            rows = cursor.fetchall()
            
            # Store table data
            table_data[table_name] = {
                'columns': column_names,
                'rows': rows,
                'count': len(rows)
            }
            
            # Create text representation
            full_content += f"\n=== TABLE: {table_name.upper()} ===\n"
            full_content += f"Columns: {', '.join(column_names)}\n"
            full_content += f"Total Records: {len(rows)}\n\n"
            
            # Add sample data (first 10 rows)
            for i, row in enumerate(rows[:10]):
                row_data = dict(zip(column_names, row))
                # Sanitize row data
                sanitized_row = {k: str(v)[:100] if v else "" for k, v in row_data.items()}
                full_content += f"Record {i+1}: {sanitized_row}\n"
            
            if len(rows) > 10:
                full_content += f"... and {len(rows) - 10} more records\n"
            
            full_content += "\n" + "="*50 + "\n"
        
        conn.close()
        
        # Store extracted content globally
        DB_CONTENT = full_content
        DB_INITIALIZED = True
        
        # Don't print full content in production
        if os.getenv('FLASK_DEBUG', 'False').lower() == 'true':
            print("\n" + "="*60)
            print("EXTRACTED DATABASE CONTENT:")
            print("="*60)
            print(full_content[:500] + "..." if len(full_content) > 500 else full_content)
            print("="*60)
            print(f"Total Tables: {len(tables)}")
            print(f"Total Characters: {len(full_content)}")
            print("="*60 + "\n")
        
        return {
            "success": True,
            "database_path": DATABASE_PATH,
            "total_tables": len(table_data),
            "tables": table_data,
            "full_content": full_content,
            "total_characters": len(full_content)
        }
        
    except Exception as e:
        print(f"Database extraction error: {str(e)}")
        return {"error": "Failed to extract database content"}

def chatbot_with_database(user_question, language='en'):
    """
    Use GPT-4o to answer questions with security improvements.
    """
    try:
        # Sanitize user input
        user_question = sanitize_input(user_question)
        
        if not user_question:
            error_msg = "Invalid or empty question provided"
            if language == 'ar':
                error_msg = "تم تقديم سؤال غير صحيح أو فارغ"
            return {"error": error_msg}
        
        # Check question length
        if len(user_question) > 500:
            error_msg = "Question too long. Please limit to 500 characters."
            if language == 'ar':
                error_msg = "السؤال طويل جداً. يرجى تقييده بـ 500 حرف."
            return {"error": error_msg}
        
        if not DB_CONTENT or not DB_INITIALIZED:
            # Try to initialize database
            result = extract_database_content()
            if not result.get("success"):
                error_msg = "KOREV AI: Attendance database not available."
                if language == 'ar':
                    error_msg = "KOREV AI: قاعدة بيانات الحضور غير متوفرة."
                return {"error": error_msg}
        
        if not openai.api_key:
            error_msg = "KOREV AI: Service temporarily unavailable."
            if language == 'ar':
                error_msg = "KOREV AI: الخدمة غير متوفرة مؤقتاً."
            return {"error": error_msg}
        
        # Check if user explicitly asks for structured data
        question_lower = user_question.lower()
        wants_table = any(keyword in question_lower for keyword in ['table', 'list employees', 'show data', 'in a table', 'جدول', 'عرض البيانات', 'قائمة الموظفين'])
        wants_chart = any(keyword in question_lower for keyword in ['chart', 'graph', 'visualize', 'pie chart', 'bar chart', 'رسم بياني', 'مخطط', 'تصور'])
        wants_cards = any(keyword in question_lower for keyword in ['key metrics', 'summary cards', 'dashboard', 'مؤشرات رئيسية', 'بطاقات ملخص', 'لوحة التحكم'])
        
        # Language-specific instructions
        language_instructions = {
            'en': {
                'system_role': "You are KOREV AI, an intelligent assistant for attendance management systems. You analyze attendance database content and provide insights. Only provide structured data when explicitly requested.",
                'response_instruction': "Answer based only on the attendance information provided in the database",
                'text_only_instruction': "Provide a clear, well-structured text response in English about attendance data",
                'structured_instruction': "Answer the user's attendance question and provide structured data as requested in English"
            },
            'ar': {
                'system_role': "أنت KOREV AI، مساعد ذكي لأنظمة إدارة الحضور. تحلل محتوى قاعدة بيانات الحضور وتقدم الرؤى. قدم البيانات المنظمة فقط عند الطلب صراحة.",
                'response_instruction': "أجب بناءً فقط على معلومات الحضور المقدمة في قاعدة البيانات",
                'text_only_instruction': "قدم إجابة نصية واضحة ومنظمة باللغة العربية حول بيانات الحضور",
                'structured_instruction': "أجب على سؤال المستخدم حول الحضور وقدم البيانات المنظمة كما هو مطلوب باللغة العربية"
            }
        }
        
        lang_config = language_instructions.get(language, language_instructions['en'])
        
        # Create prompt based on what user wants and language
        if wants_table or wants_chart or wants_cards:
            if language == 'ar':
                prompt = f"""أنت KOREV AI، مساعد ذكي متخصص في تحليل أنظمة إدارة الحضور. بناءً على محتوى قاعدة بيانات الحضور التالية، أجب على سؤال المستخدم وقدم البيانات المنظمة كما هو مطلوب.

محتوى قاعدة بيانات الحضور:
{DB_CONTENT}

سؤال المستخدم: {user_question}

التعليمات:
1. أجب على سؤال المستخدم بناءً على بيانات الحضور باللغة العربية
2. بما أن المستخدم طلب بيانات منظمة، قدمها بالتنسيق المناسب
3. ركز على إحصائيات الحضور والاتجاهات والرؤى
4. استخدم اللغة العربية فقط في الإجابة

مهم: قدم البيانات المنظمة فقط إذا طُلبت صراحة. استخدم التنسيق التالي:

للجداول:
TABLE_DATA:
headers: [العمود1, العمود2, العمود3]
rows: [[بيانات1, بيانات2, بيانات3], [بيانات4, بيانات5, بيانات6]]

للمخططات:
CHART_DATA:
type: bar|pie|line
title: عنوان المخطط
labels: [تسمية1, تسمية2, تسمية3]
values: [10, 20, 30]

للمؤشرات:
CARDS_DATA:
[{{"title": "اسم المؤشر", "value": "123", "description": "الوصف"}}]

الإجابة:"""
            else:
                prompt = f"""You are KOREV AI, an intelligent assistant specialized in attendance management system analysis. Based on the following attendance database content, answer the user's question and provide structured data as requested.

Attendance Database Content:
{DB_CONTENT}

User Question: {user_question}

Instructions:
1. Answer the user's question based on the attendance data in English
2. Since the user asked for structured data, provide it in the appropriate format
3. Focus on attendance statistics, trends, and insights
4. Be concise and avoid duplicating information

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
            if language == 'ar':
                prompt = f"""أنت KOREV AI، مساعد ذكي متخصص في تحليل أنظمة إدارة الحضور. بناءً على محتوى قاعدة بيانات الحضور التالية، أجب على سؤال المستخدم بدقة وشمولية مع إجابة نصية فقط.

محتوى قاعدة بيانات الحضور:
{DB_CONTENT}

سؤال المستخدم: {user_question}

التعليمات:
- أجب بناءً فقط على معلومات الحضور المقدمة في قاعدة البيانات
- قدم إجابة واضحة ومنظمة باللغة العربية حول بيانات الحضور
- اذكر التفاصيل ذات الصلة بالحضور وأشر إلى أسماء الجداول عند الضرورة
- ركز على الإحصائيات والاتجاهات والرؤى المتعلقة بالحضور
- لا تقدم أي تنسيقات بيانات منظمة ما لم يُطلب صراحة
- حافظ على الإجابة تحاورية ومفيدة
- استخدم اللغة العربية فقط

الإجابة:"""
            else:
                prompt = f"""You are KOREV AI, an intelligent assistant specialized in attendance management system analysis. Based on the following attendance database content, answer the user's question accurately and comprehensively with a text response only.

Attendance Database Content:
{DB_CONTENT}

User Question: {user_question}

Instructions:
- Answer based only on the attendance information provided in the database
- Provide a clear, well-structured text response in English about attendance data
- Include relevant attendance details and reference table names when possible
- Focus on attendance statistics, trends, and insights
- Do NOT provide any structured data formats (tables, charts, etc.) unless explicitly requested
- Keep the response conversational and informative about attendance management

Answer:"""
        
        # Call GPT-4o
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": lang_config['system_role']},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,  # Reduced for production
            temperature=0.1,
            timeout=30  # Add timeout
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
                    if language == 'ar':
                        if any(keyword in question_lower for keyword in ['employee', 'attendance', 'موظف', 'حضور']):
                            final_text = "إليك بيانات حضور الموظفين من قاعدة البيانات:"
                        else:
                            final_text = "إليك البيانات المطلوبة من قاعدة البيانات:"
                    else:
                        if any(keyword in question_lower for keyword in ['employee', 'attendance']):
                            final_text = "Here is the employee attendance data from the database:"
                        else:
                            final_text = "Here is the requested data from the database:"
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
            "language": language,
            "system": "KOREV AI",
            "database_content_available": len(DB_CONTENT) > 0
        }
        
    except openai.error.RateLimitError:
        error_msg = "KOREV AI: Rate limit exceeded. Please try again later."
        if language == 'ar':
            error_msg = "KOREV AI: تم تجاوز حد المعدل. يرجى المحاولة مرة أخرى لاحقاً."
        return {"error": error_msg}
    except openai.error.InvalidRequestError:
        error_msg = "KOREV AI: Invalid request. Please try a different question."
        if language == 'ar':
            error_msg = "KOREV AI: طلب غير صحيح. يرجى تجربة سؤال مختلف."
        return {"error": error_msg}
    except Exception as e:
        print(f"Chatbot error: {str(e)}")  # Log for debugging
        error_msg = "KOREV AI: Service error. Please try again."
        if language == 'ar':
            error_msg = "KOREV AI: خطأ في الخدمة. يرجى المحاولة مرة أخرى."
        return {"error": error_msg}

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

# Initialize database extraction when app starts
def initialize_database():
    """Extract database content when the application starts."""
    global DB_INITIALIZED
    
    print("Initializing attendance database...")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"WARNING: Database file '{DATABASE_PATH}' not found!")
        print("Creating sample database...")
        # Try to create sample database
        try:
            # Import and create sample database
            import setup_database
            setup_database.create_sample_database()
            print("Sample database created successfully!")
        except ImportError:
            print("ERROR: setup_database.py not found. Please create it or provide a database file.")
            return
        except Exception as e:
            print(f"Failed to create sample database: {e}")
            print("Please ensure you have a valid attendance.db file or create one manually.")
            return
    
    print("Loading database content...")
    result = extract_database_content()
    if result.get("success"):
        print("Database content successfully loaded!")
        DB_INITIALIZED = True
    else:
        print(f"Failed to load database content: {result.get('error')}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/extract')
def extract():
    """Extract content from database."""
    result = extract_database_content()
    return jsonify(result)

@app.route('/chat', methods=['POST'])
@limiter.limit("30 per minute")  # Rate limit chat endpoint
def chat():
    """Enhanced chat endpoint with security improvements."""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        user_question = data.get('message', '') or data.get('question', '')
        language = data.get('language', 'en')
        
        # Validate language parameter
        if language not in ['en', 'ar']:
            language = 'en'
        
        if not user_question:
            error_msg = "No question provided"
            if language == 'ar':
                error_msg = "لم يتم تقديم سؤال"
            return jsonify({"error": error_msg}), 400

        result = chatbot_with_database(user_question, language)
        if result.get("success"):
            return jsonify({
                "response": result["answer"],
                "components": result.get("components", []),
                "language": language,
                "source": "ai_analysis"
            })
        else:
            return jsonify({
                "error": result.get("error"),
                "response": result.get("error"),
                "components": [],
                "language": language
            })
    except BadRequest:
        return jsonify({"error": "Invalid request format"}), 400
    except Exception as e:
        print(f"Chat endpoint error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "components": [],
            "language": language if 'language' in locals() else 'en'
        }), 500

@app.route('/test-database', methods=['GET'])
def test_database():
    """Test database extraction."""
    result = extract_database_content()
    if result.get("success"):
        return jsonify({
            'database_path': DATABASE_PATH,
            'total_tables': result['total_tables'],
            'extraction_successful': True,
            'tables': list(result['tables'].keys()),
            'first_100_chars': result['full_content'][:100]
        })
    else:
        return jsonify({
            'error': result.get('error'),
            'extraction_successful': False
        })

@app.route('/database-info', methods=['GET'])
def database_info():
    """Get database file information."""
    
    if os.path.exists(DATABASE_PATH):
        file_size = os.path.getsize(DATABASE_PATH)
        return jsonify({
            'file_exists': True,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'database_path': DATABASE_PATH,
            'initialized': DB_INITIALIZED,
            'content_available': len(DB_CONTENT) > 0
        })
    else:
        return jsonify({
            'file_exists': False,
            'error': 'Database file not found',
            'database_path': DATABASE_PATH,
            'initialized': False,
            'content_available': False
        })

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
@limiter.limit("10 per minute")  # Rate limit sample data generation
def generate_sample_data():
    """Generate sample data with rate limiting."""
    try:
        data = request.get_json() or {}
        component_type = data.get('type', 'all')
        language = data.get('language', 'en')
        
        # Validate inputs
        if component_type not in ['all', 'table', 'chart', 'cards']:
            component_type = 'all'
        if language not in ['en', 'ar']:
            language = 'en'
        
        components = []
        
        if component_type in ['all', 'table']:
            if language == 'ar':
                components.append({
                    "type": "table",
                    "data": {
                        "title": "جدول بيانات الحضور التجريبي",
                        "headers": ["اسم الموظف", "القسم", "حالة الحضور", "الساعات"],
                        "rows": [
                            ["أحمد علي", "تقنية المعلومات", "حاضر", "8.5"],
                            ["فاطمة محمد", "الموارد البشرية", "حاضر", "7.0"],
                            ["خالد أحمد", "المالية", "غائب", "0.0"],
                            ["سارة عبدالله", "التسويق", "حاضر", "8.0"]
                        ]
                    }
                })
            else:
                components.append({
                    "type": "table",
                    "data": {
                        "title": "Sample Attendance Data",
                        "headers": ["Employee Name", "Department", "Status", "Hours"],
                        "rows": [
                            ["Ahmed Ali", "IT", "Present", "8.5"],
                            ["Fatima Mohammed", "HR", "Present", "7.0"],
                            ["Khalid Ahmed", "Finance", "Absent", "0.0"],
                            ["Sarah Abdullah", "Marketing", "Present", "8.0"]
                        ]
                    }
                })
        
        if component_type in ['all', 'chart']:
            if language == 'ar':
                components.append({
                    "type": "chart",
                    "data": {
                        "type": "pie",
                        "title": "توزيع الحضور حسب القسم",
                        "labels": ["تقنية المعلومات", "الموارد البشرية", "المالية", "التسويق"],
                        "values": [85, 90, 75, 88]
                    }
                })
            else:
                components.append({
                    "type": "chart",
                    "data": {
                        "type": "pie",
                        "title": "Attendance Distribution by Department",
                        "labels": ["IT", "HR", "Finance", "Marketing"],
                        "values": [85, 90, 75, 88]
                    }
                })
        
        if component_type in ['all', 'cards']:
            if language == 'ar':
                components.append({
                    "type": "cards",
                    "data": [
                        {"title": "إجمالي الموظفين", "value": "120", "description": "العدد الكلي للموظفين"},
                        {"title": "معدل الحضور", "value": "84.5%", "description": "هذا الشهر"},
                        {"title": "ساعات العمل", "value": "2,340", "description": "إجمالي الساعات"}
                    ]
                })
            else:
                components.append({
                    "type": "cards",
                    "data": [
                        {"title": "Total Employees", "value": "120", "description": "Total workforce"},
                        {"title": "Attendance Rate", "value": "84.5%", "description": "This month"},
                        {"title": "Work Hours", "value": "2,340", "description": "Total hours"}
                    ]
                })
        
        text_message = "KOREV AI: Sample attendance data generated for testing:" if language == 'en' else "KOREV AI: تم إنشاء بيانات حضور تجريبية للاختبار:"
        
        return jsonify({
            "text": text_message,
            "components": components
        })
        
    except Exception as e:
        print(f"Sample data generation error: {str(e)}")
        error_msg = "Error generating sample data" if language == 'en' else "خطأ في إنشاء البيانات التجريبية"
        return jsonify({"error": error_msg}), 500

@app.route('/analyze-database', methods=['POST'])
@limiter.limit("5 per minute")  # Rate limit analysis endpoint
def analyze_database():
    """Analyze database with rate limiting."""
    try:
        data = request.get_json() or {}
        language = data.get('language', 'en')
        
        if language not in ['en', 'ar']:
            language = 'en'
        
        if not DB_CONTENT:
            error_msg = "KOREV AI: No attendance database content available" if language == 'en' else "KOREV AI: لا يوجد محتوى قاعدة بيانات حضور متاح"
            return jsonify({"error": error_msg}), 400
        
        # Use chatbot function to analyze database content
        analysis_question = "Provide a comprehensive analysis of this attendance database including key statistics, attendance patterns, employee insights, and important findings." if language == 'en' else "قدم تحليلاً شاملاً لقاعدة بيانات الحضور هذه بما في ذلك الإحصائيات الرئيسية وأنماط الحضور ورؤى الموظفين والنتائج المهمة."
        
        result = chatbot_with_database(analysis_question, language)
        
        if result.get("success"):
            return jsonify({
                "analysis": result["answer"],
                "components": result.get("components", [])
            })
        else:
            return jsonify({"error": result.get("error")}), 500
            
    except Exception as e:
        print(f"Database analysis error: {str(e)}")
        error_msg = "Error analyzing database" if language == 'en' else "خطأ في تحليل قاعدة البيانات"
        return jsonify({"error": error_msg}), 500

# Security headers
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data:; connect-src 'self';"
    return response

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

# Extract database content when app starts
initialize_database()

if __name__ == '__main__':
    # Production configuration
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')  # Changed from 0.0.0.0 for security
    
    # Validate required environment variables
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {missing_vars}")
        exit(1)
    
    if debug_mode:
        print("WARNING: Running in debug mode. Not suitable for production!")
    
    app.run(debug=debug_mode, host=host, port=port)
