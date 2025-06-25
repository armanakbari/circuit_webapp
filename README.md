# Circuit Benchmark Sample Creator

A web interface for creating and managing circuit reasoning benchmark samples. This tool helps you create standardized sample entries for the circuit benchmark with proper formatting and validation.

## Features

- User-friendly web interface for sample creation
- Automatic file organization and naming
- Image upload with preview
- Input validation for all fields
- Automatic formatting of question text
- Support for LaTeX in derivation/solution
- Modern, responsive design

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Fill out the form with your sample information:
   - Upload a circuit image (PNG, JPG, or JPEG)
   - Enter the question text
   - Provide exactly 4 multiple choice options
   - Select the correct answer
   - Enter the derivation/solution

2. Click "Create Sample" to submit

The tool will automatically:
- Create a new folder (e.g., `q1`, `q2`, etc.)
- Save the image as `qN_image.png`
- Create all required text files with proper formatting
- Handle any necessary text transformations

## File Structure

Each sample is stored in its own folder (`qN/`) containing:
- `qN_image.png` - Circuit diagram
- `qN_question.txt` - Question text
- `qN_mc.txt` - Multiple choice options
- `qN_a.txt` - Correct answer number
- `qN_ta.txt` - Correct answer text
- `qN_der.txt` - Full derivation/solution

## Validation Rules

- Question text must be 10-1000 characters
- Each choice must be 1-200 characters
- All choices must be unique
- Derivation must be 10-5000 characters
- Image must be PNG, JPG, or JPEG format
- Maximum image size: 16MB

## Contributing

Feel free to submit issues and enhancement requests! 