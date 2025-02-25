document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const uploadButton = document.getElementById('uploadButton');
    const progressContainer = document.getElementById('progressContainer');
    const errorAlert = document.getElementById('errorAlert');
    const fileInput = document.getElementById('pdfFile');

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Validate file input
        if (!fileInput.files[0]) {
            showError('Please select a PDF file.');
            return;
        }

        if (!fileInput.files[0].type.includes('pdf')) {
            showError('Please upload a valid PDF file.');
            return;
        }

        // Hide any previous errors
        hideError();
        
        // Show progress
        showProgress();
        
        // Disable the upload button
        uploadButton.disabled = true;
        
        // Create FormData
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('language', document.getElementById('language').value);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error processing the PDF');
            }

            // Get the blob from the response
            const blob = await response.blob();
            
            // Create a download link and trigger it
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'translated.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Reset form and UI
            uploadForm.reset();
            hideProgress();
            uploadButton.disabled = false;

        } catch (error) {
            console.error('Error:', error);
            showError(error.message || 'An error occurred while processing the file.');
            hideProgress();
            uploadButton.disabled = false;
        }
    });

    function showProgress() {
        progressContainer.classList.remove('d-none');
    }

    function hideProgress() {
        progressContainer.classList.add('d-none');
    }

    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.classList.remove('d-none');
    }

    function hideError() {
        errorAlert.classList.add('d-none');
        errorAlert.textContent = '';
    }

    // Add file input validation
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file && !file.type.includes('pdf')) {
            showError('Please select a valid PDF file.');
            fileInput.value = '';
        } else {
            hideError();
        }
    });
});
