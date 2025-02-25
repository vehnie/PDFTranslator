import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pytesseract
from pdf2image import convert_from_bytes
from googletrans import Translator, LANGUAGES
from PyPDF2 import PdfReader, PdfWriter
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import asyncio

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

        # Validate target language
        if target_lang not in LANGUAGES:
            return jsonify({'error': f'Unsupported target language: {target_lang}'}), 400

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Read PDF content
        pdf_bytes = file.read()
        logger.debug(f"Processing PDF for translation to {target_lang}")

        # Convert PDF to images
        images = convert_from_bytes(pdf_bytes)

        # Extract text using OCR for each page
        pages_text = []
        for image in images:
            text = pytesseract.image_to_string(image)
            pages_text.append(text)

        logger.debug(f"Extracted text from {len(pages_text)} pages")

        # Create translator instance
        translator = Translator()

        # Create event loop for async translation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Translate each page
        translated_pages = []
        try:
            for page_text in pages_text:
                # Split text into smaller chunks if it's too long
                max_chunk_size = 5000
                text_chunks = [page_text[i:i+max_chunk_size] 
                             for i in range(0, len(page_text), max_chunk_size)]

                translated_chunks = []
                for chunk in text_chunks:
                    translation = loop.run_until_complete(
                        translator.translate(chunk, dest=target_lang))
                    translated_chunks.append(translation.text)

                translated_pages.append(' '.join(translated_chunks))

            logger.debug(f"Translated {len(translated_pages)} pages")

        except Exception as translation_error:
            logger.error(f"Translation error: {str(translation_error)}")
            return jsonify({'error': f'Translation failed: {str(translation_error)}'}), 500
        finally:
            loop.close()

        # Create output PDF with translated text
        output = PdfWriter()

        # Create each page
        for translated_text in translated_pages:
            # Create new PDF page
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            y = 750  # Start from top

            # Split translated text into lines and add to PDF
            for line in translated_text.split('\n'):
                if y > 50:  # Check if we have space on current page
                    can.drawString(50, y, line)
                    y -= 15
                else:
                    # If we run out of space, create a new page
                    can.showPage()
                    y = 750
                    can.drawString(50, y, line)
                    y -= 15

            can.save()

            # Add page to output PDF
            packet.seek(0)
            new_pdf = PdfReader(packet)
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)