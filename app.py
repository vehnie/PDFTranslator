import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pytesseract
from pdf2image import convert_from_bytes
from googletrans import Translator
from PyPDF2 import PdfReader, PdfWriter
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Configure upload folder
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        target_lang = request.form.get('language', 'en')
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Read PDF content
        pdf_bytes = file.read()
        
        # Convert PDF to images
        images = convert_from_bytes(pdf_bytes)
        
        # Extract text using OCR
        extracted_text = ""
        for image in images:
            text = pytesseract.image_to_string(image)
            extracted_text += text + "\n"

        # Translate text
        translator = Translator()
        translated = translator.translate(extracted_text, dest=target_lang)
        
        # Create new PDF with translated text
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        y = 750  # Start from top
        
        # Split translated text into lines and add to PDF
        for line in translated.text.split('\n'):
            if y > 50:  # Check if we need a new page
                can.drawString(50, y, line)
                y -= 15
            else:
                can.showPage()
                y = 750
                can.drawString(50, y, line)
                y -= 15
        
        can.save()
        
        # Create the response PDF
        packet.seek(0)
        new_pdf = PdfReader(packet)
        
        # Create output PDF
        output = PdfWriter()
        output.add_page(new_pdf.pages[0])
        
        # Save the output to a bytes buffer
        output_buffer = io.BytesIO()
        output.write(output_buffer)
        output_buffer.seek(0)
        
        return send_file(
            output_buffer,
            as_attachment=True,
            download_name='translated.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': 'Error processing file'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
