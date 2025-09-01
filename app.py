import os
from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, abort
from werkzeug.utils import secure_filename
from forms import SampleForm
import re
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'samples'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# List of CSV files to load with their corresponding folders
CSV_FILE_MAPPING = {
    'results_gemini25_Mei_nonlinear.csv': 'Mei_nonlinear',
    'results_gemini25_Mei_samples.csv': 'Mei_samples',
    'results_gemini25_Jinru_samples.csv': 'Jinru_samples',
    'results_gemini25_synthetic_dataset.csv': 'synthetic_dataset',
    'results_gemini25_synthetic_dataset_2.csv': 'synthetic_dataset_2'
}

# New CSV file for judge-based evaluations
JUDGE_CSV_FILES = [
    'results_gemini25_judge_Mei_samples.csv'
]

# Judge samples CSV file
JUDGE_SAMPLES_CSV_FILES = [
    'results_gemini25_judge_samples.csv'
]

# Equation derivation CSV file
EQUATION_DERIVATION_CSV_FILES = [
    'results_gemini25_equation_derivation_full.csv'
]

# Analysis folder which contains question folders like q1, q2, ...
ANALYSIS_FOLDER = 'Analysis'

# Load and combine all CSV files, filtering for failed cases only
results_data = []
for csv_file, folder_name in CSV_FILE_MAPPING.items():
    if os.path.exists(csv_file):
        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Check both 'is_correct' and 'judge_is_correct' columns
                is_correct_value = row.get('is_correct', '') or row.get('judge_is_correct', '')
                # Only include failed cases (where is_correct is False)
                if is_correct_value.strip().lower() == 'false':
                    # Normalize column names for synthetic dataset
                    if csv_file == 'results_gemini25_synthetic_dataset.csv':
                        # Map synthetic dataset columns to expected template variables
                        row['model_answer'] = row.get('solver_final_answer', '')
                        row['explanation'] = row.get('solver_explanation', '')
                        row['correct_answer'] = row.get('ground_truth_answer', '')
                        row['is_correct'] = row.get('judge_is_correct', '')
                    
                    # Add source file and folder information
                    row['source_file'] = csv_file
                    row['results_folder'] = folder_name
                    results_data.append(row)

# Load and combine all CSV files, filtering for successful cases only
success_data = []
for csv_file, folder_name in CSV_FILE_MAPPING.items():
    if os.path.exists(csv_file):
        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Check both 'is_correct' and 'judge_is_correct' columns
                is_correct_value = row.get('is_correct', '') or row.get('judge_is_correct', '')
                # Only include successful cases (where is_correct is True)
                if is_correct_value.strip().lower() == 'true':
                    # Normalize column names for synthetic dataset
                    if csv_file == 'results_gemini25_synthetic_dataset.csv':
                        # Map synthetic dataset columns to expected template variables
                        row['model_answer'] = row.get('solver_final_answer', '')
                        row['explanation'] = row.get('solver_explanation', '')
                        row['correct_answer'] = row.get('ground_truth_answer', '')
                        row['is_correct'] = row.get('judge_is_correct', '')
                    
                    # Add source file and folder information
                    row['source_file'] = csv_file
                    row['results_folder'] = folder_name
                    success_data.append(row)

# Load judge-based evaluation data
judge_data = []
for csv_file in JUDGE_CSV_FILES:
    if os.path.exists(csv_file):
        try:
            with open(csv_file, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Add source file information
                    row['source_file'] = csv_file
                    judge_data.append(row)
        except Exception as e:
            print(f"Error loading judge CSV file {csv_file}: {e}")
    else:
        print(f"Judge CSV file not found: {csv_file}")

# Separate judge data into correct and incorrect cases
judge_correct_data = [row for row in judge_data if row.get('judge_is_correct', '').strip().lower() == 'true']
judge_incorrect_data = [row for row in judge_data if row.get('judge_is_correct', '').strip().lower() == 'false']

# Load judge samples evaluation data
judge_samples_data = []
for csv_file in JUDGE_SAMPLES_CSV_FILES:
    if os.path.exists(csv_file):
        try:
            with open(csv_file, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Add source file information
                    row['source_file'] = csv_file
                    judge_samples_data.append(row)
        except Exception as e:
            print(f"Error loading judge samples CSV file {csv_file}: {e}")
    else:
        print(f"Judge samples CSV file not found: {csv_file}")

# Separate judge samples data into correct and incorrect cases
judge_samples_correct_data = [row for row in judge_samples_data if row.get('judge_is_correct', '').strip().lower() == 'true']
judge_samples_incorrect_data = [row for row in judge_samples_data if row.get('judge_is_correct', '').strip().lower() == 'false']

# Load equation derivation evaluation data
equation_derivation_data = []
for csv_file in EQUATION_DERIVATION_CSV_FILES:
    if os.path.exists(csv_file):
        try:
            with open(csv_file, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Add source file information
                    row['source_file'] = csv_file
                    equation_derivation_data.append(row)
        except Exception as e:
            print(f"Error loading equation derivation CSV file {csv_file}: {e}")
    else:
        print(f"Equation derivation CSV file not found: {csv_file}")

# Separate equation derivation data into correct and incorrect cases
equation_derivation_correct_data = [row for row in equation_derivation_data if row.get('judge_is_correct', '').strip().lower() == 'true']
equation_derivation_incorrect_data = [row for row in equation_derivation_data if row.get('judge_is_correct', '').strip().lower() == 'false']

analysis_qids = None  # list of qids like 'q1', 'q2', ...
analysis_cache = {}   # qid -> item dict
ANALYSIS_CACHE_MAX = 16

def _build_analysis_index():
    global analysis_qids
    if analysis_qids is not None:
        return
    analysis_qids = []
    if not os.path.exists(ANALYSIS_FOLDER):
        return
    try:
        for entry in sorted(os.listdir(ANALYSIS_FOLDER)):
            q_dir = os.path.join(ANALYSIS_FOLDER, entry)
            if os.path.isdir(q_dir) and re.match(r'^q\d+$', entry):
                analysis_qids.append(entry)
        print(f"Indexed Analysis questions: {len(analysis_qids)}")
    except Exception as e:
        print(f"Error indexing Analysis folder: {e}")

def count_analysis_questions() -> int:
    _build_analysis_index()
    return len(analysis_qids or [])

def get_analysis_item(qid: str):
    if qid in analysis_cache:
        return analysis_cache[qid]

    q_dir = os.path.join(ANALYSIS_FOLDER, qid)
    # Some datasets use singular 'question' and others 'questions'
    question_path = os.path.join(q_dir, f"{qid}_questions.txt")
    if not os.path.exists(question_path):
        question_path = os.path.join(q_dir, f"{qid}_question.txt")
    gt_path = os.path.join(q_dir, f"{qid}_ta.txt")
    claude_path = os.path.join(q_dir, f"{qid}_claude.txt")
    gemini_path = os.path.join(q_dir, f"{qid}_gemini.txt")

    # Determine if an image exists
    image_exists = False
    for ext in ('png', 'jpg', 'jpeg'):
        candidate = os.path.join(q_dir, f"{qid}_image.{ext}")
        if os.path.exists(candidate):
            image_exists = True
            break

    if not os.path.exists(question_path):
        return None

    try:
        with open(question_path, 'r', encoding='utf-8') as f:
            question_text = f.read().strip()
    except Exception:
        question_text = ''

    ground_truth = None
    if os.path.exists(gt_path):
        try:
            with open(gt_path, 'r', encoding='utf-8') as f:
                ground_truth = f.read().strip()
        except Exception:
            ground_truth = None

    # Prefer Claude answer; fallback to Gemini if Claude missing
    model_answer = None
    if os.path.exists(claude_path):
        try:
            with open(claude_path, 'r', encoding='utf-8') as f:
                model_answer = f.read().strip()
        except Exception:
            model_answer = None
    elif os.path.exists(gemini_path):
        try:
            with open(gemini_path, 'r', encoding='utf-8') as f:
                model_answer = f.read().strip()
        except Exception:
            model_answer = None

    item = {
        'qid': qid,
        'question_text': question_text,
        'ground_truth': ground_truth,
        'gemini_answer': model_answer,
        'image_exists': image_exists,
        'results_folder': ANALYSIS_FOLDER
    }

    try:
        if len(analysis_cache) >= ANALYSIS_CACHE_MAX:
            analysis_cache.pop(next(iter(analysis_cache)))
        analysis_cache[qid] = item
    except Exception:
        pass

    return item

def auto_latex(text):
    """Automatically wrap mathematical expressions with LaTeX delimiters for MathJax rendering."""
    if not text:
        return text
    
    try:
        # Convert text to string if it's not already
        text = str(text)
        
        # Add proper formatting for better readability
        # Add line breaks after major sections
        text = re.sub(r'---\s*', '<hr class="my-3">\n', text)
        text = re.sub(r'###\s+([^:]+):', r'<h5 class="text-primary mt-3">\1</h5>', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        
        # Format step markers
        text = re.sub(r'\*\*Step (\d+):\s*([^*]+)\*\*', r'<h6 class="text-info mt-3">Step \1: \2</h6>', text)
        
        # Format bullet points (simpler approach)
        text = re.sub(r'^\s*\*\s+([^\n]+)', r'• \1', text, flags=re.MULTILINE)
        
        # Add better line breaks for readability
        text = re.sub(r'(\.\s+)([A-Z])', r'\1\n\n\2', text)  # Break after sentences
        text = re.sub(r'(\s+where\s+)', r'\n\nwhere ', text)  # Break before "where" clauses
        
        # Enhanced patterns for mathematical expressions
        patterns = [
            # Complex variables like V_top_0, V_bottom_0
            (r'\b([VIR])_([a-zA-Z0-9_]+)\b', r'$\1_{\2}$'),
            # Variables like I9, I6, V1, U4, etc. (word boundaries)
            (r'\b([IUVPRCL][0-9]+)\b', r'$\1$'),
            # Transfer function H(s)
            (r'\bH\(s\)', r'$H(s)$'),
            # Functions with variables like V(s), I(s)
            (r'\b([VIZ])\(s\)', r'$\1(s)$'),
            # Impedance notation Z_C1
            (r'\bZ_([a-zA-Z0-9]+)', r'$Z_{\1}$'),
            # Mathematical operations and equations (more selective)
            (r'H\(s\)\s*=\s*([^=\n,;]+?)(?=\s*[,;\n]|where|$)', r'$H(s) = \1$'),
            # Fractions and complex expressions
            (r'\b([A-Za-z0-9_]+)\s*/\s*\(([^)]+)\)', r'$\\frac{\1}{\2}$'),
            (r'\(([^()]+)\s*/\s*([^()]+)\)', r'$\\left(\\frac{\1}{\2}\\right)$'),
            # Units like Ω, A, V  
            (r'\b([0-9]+(?:\.[0-9]+)?)\s*(Ω|A|V|μ|m|k|M|F|H)\b', r'$\1\,\\mathrm{\2}$'),
            # Mathematical equations in backticks
            (r'`([^`]+)`', r'$\1$'),
            # Simple subscripts like I_25, R_AP
            (r'\b([IUVPRCL])_([a-zA-Z0-9]+)\b', r'$\1_{\2}$'),
            # Greek letters
            (r'\b(alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|rho|sigma|tau|phi|omega)\b', r'$\\\1$'),
            # Clean up circuit node references
            (r'\bnode\s+([0-9]+)', r'node $\1$'),
        ]
        
        # Apply patterns safely
        for pattern, replacement in patterns:
            try:
                text = re.sub(pattern, replacement, text)
            except Exception:
                # Skip problematic patterns
                continue
        
        # Clean up duplicate $ signs
        text = re.sub(r'\$\$+', '$', text)
        text = re.sub(r'\$\s*\$', '', text)
        
        # Add proper paragraph breaks for long text
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            text = '</p><p>'.join(paragraphs)
            text = '<p>' + text + '</p>'
        
        return text
    except Exception:
        # If anything goes wrong, return the original text
        return str(text) if text else ""

# Register the filter with Jinja2
app.jinja_env.filters['auto_latex'] = auto_latex

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_next_question_number():
    """Get the next available question number by checking existing folders."""
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        return 1
    
    existing_folders = [d for d in os.listdir(app.config['UPLOAD_FOLDER']) 
                       if os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], d))]
    
    if not existing_folders:
        return 1
    
    numbers = []
    for folder in existing_folders:
        try:
            num = int(folder.replace('q', ''))
            numbers.append(num)
        except ValueError:
            continue
    
    return max(numbers, default=0) + 1

def create_sample_files(q_num, form_data, image_file):
    """Create all required files for a sample."""
    # Create question directory
    q_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'q{q_num}')
    os.makedirs(q_dir, exist_ok=True)
    
    # Save image
    if image_file and allowed_file(image_file.filename):
        image_filename = f'q{q_num}_image.png'
        image_path = os.path.join(q_dir, image_filename)
        image_file.save(image_path)
    
    # Process question text
    question_text = form_data['question'].strip()
    question_text = re.sub(r'^\d+\.\s*', '', question_text)  # Remove leading number
    question_text = re.sub(r'Figure\s+\d+', 'provided circuit image', question_text, flags=re.IGNORECASE)
    
    # Save question text
    with open(os.path.join(q_dir, f'q{q_num}_question.txt'), 'w') as f:
        f.write(question_text)
    
    # Save source in structured format
    with open(os.path.join(q_dir, f'q{q_num}_source.txt'), 'w') as f:
        source_lines = []
        
        # Add source book (required)
        if form_data.get('source_book') and form_data['source_book'].strip():
            source_lines.append(form_data['source_book'].strip())
        
        # Add page reference if provided
        if form_data.get('source_page') and form_data['source_page'].strip():
            source_lines.append(form_data['source_page'].strip())
        
        # Add problem/example reference if provided
        if form_data.get('source_problem') and form_data['source_problem'].strip():
            source_lines.append(form_data['source_problem'].strip())
        
        # Add additional source info if provided
        if form_data.get('source') and form_data['source'].strip():
            source_lines.append(form_data['source'].strip())
        
        # Fallback to old source field for backward compatibility
        if not source_lines and form_data.get('source') and form_data['source'].strip():
            source_lines.append(form_data['source'].strip())
        
        f.write('\n'.join(source_lines))
    
    # Save text answer if provided
    if form_data['text_answer'] and form_data['text_answer'].strip():
        with open(os.path.join(q_dir, f'q{q_num}_ta.txt'), 'w') as f:
            f.write(form_data['text_answer'].strip())
    
    # Save derivation if provided
    if form_data['derivation'] and form_data['derivation'].strip():
        with open(os.path.join(q_dir, f'q{q_num}_der.txt'), 'w') as f:
            f.write(form_data['derivation'].strip())
    
    # Save level
    with open(os.path.join(q_dir, f'q{q_num}_level.txt'), 'w') as f:
        f.write(str(form_data['difficultiness']))

    # Save multiple choice options if provided
    if form_data.get('mc_choices') and form_data['mc_choices'].strip():
        with open(os.path.join(q_dir, f'q{q_num}_mc.txt'), 'w') as f:
            f.write(form_data['mc_choices'].strip())

    # Save correct answer if provided
    if form_data.get('correct_choice') and form_data['correct_choice'].strip():
        with open(os.path.join(q_dir, f'q{q_num}_a.txt'), 'w') as f:
            f.write(form_data['correct_choice'].strip())

def get_question_assets(qid: str, results_folder: str):
    """Return dict with paths for image, mc_choices, derivation, netlist, and source for a question id (e.g., 'q248') in the specified folder."""
    q_folder = os.path.join(results_folder, qid)
    image_path = None
    choices = []
    derivation = None
    source_info = None
    netlist = None
    
    # Special handling for equations_2 folder with different structure
    if results_folder == 'equations_2':
        # Remove 'q' prefix and look for files like 1_39.jpg directly in equations_2 folder
        clean_qid = qid.replace('q', '') if qid.startswith('q') else qid
        for ext in ('jpg', 'png', 'jpeg'):
            candidate = os.path.join(results_folder, f"{clean_qid}.{ext}")
            if os.path.exists(candidate):
                image_path = candidate
                break
    else:
        # Look for image in the results folder (standard structure)
        for ext in ('png', 'jpg', 'jpeg'):
            candidate = os.path.join(q_folder, f"{qid}_image.{ext}")
            if os.path.exists(candidate):
                image_path = candidate
                break
            # Also try without the qid prefix (just image.png)
            candidate = os.path.join(q_folder, f"image.{ext}")
            if os.path.exists(candidate):
                image_path = candidate
                break
    
    # Look for multiple choice options
    mc_path = os.path.join(q_folder, f"{qid}_mc.txt")
    if os.path.exists(mc_path):
        with open(mc_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Split by numbered lines and process
            # Split by pattern like "1.", "2.", etc. at the beginning of lines
            choice_parts = re.split(r'\n(?=\d+\.)', content)
            for part in choice_parts:
                if part.strip():
                    # Remove the leading number and period
                    cleaned_choice = re.sub(r'^\d+\.\s*', '', part.strip())
                    if cleaned_choice:
                        # Apply auto_latex filter instead of wrapping everything
                        latex_choice = auto_latex(cleaned_choice)
                        choices.append(latex_choice)
    else:
        # Also try without the qid prefix (just mc.txt)
        mc_path = os.path.join(q_folder, "mc.txt")
        if os.path.exists(mc_path):
            with open(mc_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                # Split by numbered lines and process
                # Split by pattern like "1.", "2.", etc. at the beginning of lines
                choice_parts = re.split(r'\n(?=\d+\.)', content)
                for part in choice_parts:
                    if part.strip():
                        # Remove the leading number and period
                        cleaned_choice = re.sub(r'^\d+\.\s*', '', part.strip())
                        if cleaned_choice:
                            # Apply auto_latex filter instead of wrapping everything
                            latex_choice = auto_latex(cleaned_choice)
                            choices.append(latex_choice)
    
    # Look for derivation/solution
    der_path = os.path.join(q_folder, f"{qid}_der.txt")
    if os.path.exists(der_path):
        with open(der_path, 'r', encoding='utf-8') as f:
            derivation = f.read().strip()
    else:
        # Also try without the qid prefix (just der.txt)
        der_path = os.path.join(q_folder, "der.txt")
        if os.path.exists(der_path):
            with open(der_path, 'r', encoding='utf-8') as f:
                derivation = f.read().strip()
    
    # Look for netlist file (specifically for synthetic_dataset_2)
    if results_folder == 'synthetic_dataset_2':
        netlist_path = os.path.join(q_folder, f"{qid}_netlist.txt")
        print(f"DEBUG: Looking for netlist at: {netlist_path}")
        if os.path.exists(netlist_path):
            print(f"DEBUG: Found netlist file!")
            with open(netlist_path, 'r', encoding='utf-8') as f:
                netlist = f.read().strip()
                print(f"DEBUG: Netlist content length: {len(netlist)}")
        else:
            # Also try without the qid prefix (just netlist.txt)
            netlist_path = os.path.join(q_folder, "netlist.txt")
            print(f"DEBUG: Trying alternative netlist path: {netlist_path}")
            if os.path.exists(netlist_path):
                print(f"DEBUG: Found alternative netlist file!")
                with open(netlist_path, 'r', encoding='utf-8') as f:
                    netlist = f.read().strip()
            else:
                print(f"DEBUG: No netlist file found")
    else:
        print(f"DEBUG: Not synthetic_dataset_2, results_folder is: {results_folder}")
    
    # Look for source information
    source_path = os.path.join(q_folder, f"{qid}_source.txt")
    if os.path.exists(source_path):
        with open(source_path, 'r', encoding='utf-8') as f:
            source_lines = f.read().strip().split('\n')
            if source_lines:
                source_info = {
                    'book': source_lines[0] if len(source_lines) > 0 else '',
                    'page': source_lines[1] if len(source_lines) > 1 else '',
                    'problem': source_lines[2] if len(source_lines) > 2 else '',
                    'additional': '\n'.join(source_lines[3:]) if len(source_lines) > 3 else '',
                    'raw': '\n'.join(source_lines)
                }
    else:
        # Also try without the qid prefix (just source.txt)
        source_path = os.path.join(q_folder, "source.txt")
        if os.path.exists(source_path):
            with open(source_path, 'r', encoding='utf-8') as f:
                source_content = f.read().strip()
                source_info = {
                    'book': source_content,
                    'page': '',
                    'problem': '',
                    'additional': '',
                    'raw': source_content
                }
    
    return {"image_path": image_path, "choices": choices, "derivation": derivation, "netlist": netlist, "source_info": source_info}

@app.route('/', methods=['GET', 'POST'])
def index():
    form = SampleForm()
    if form.validate_on_submit():
        try:
            q_num = get_next_question_number()
            create_sample_files(q_num, form.data, request.files['image'])
            flash(f'Successfully added question {q_num}!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error creating sample: {str(e)}', 'error')
    
    # Calculate statistics for failed cases
    failed_stats = {
        'total_failed': len(results_data),
        'by_source': {}
    }
    
    for row in results_data:
        source = row.get('source_file', 'Unknown')
        if source not in failed_stats['by_source']:
            failed_stats['by_source'][source] = 0
        failed_stats['by_source'][source] += 1
    
    # Calculate statistics for successful cases
    success_stats = {
        'total_success': len(success_data),
        'by_source': {}
    }
    
    for row in success_data:
        source = row.get('source_file', 'Unknown')
        if source not in success_stats['by_source']:
            success_stats['by_source'][source] = 0
        success_stats['by_source'][source] += 1
    
    # Calculate statistics for judge evaluations
    judge_stats = {
        'total_judge': len(judge_data),
        'total_correct': len(judge_correct_data),
        'total_incorrect': len(judge_incorrect_data),
        'by_source': {}
    }
    
    for row in judge_data:
        source = row.get('source_file', 'Unknown')
        if source not in judge_stats['by_source']:
            judge_stats['by_source'][source] = {'total': 0, 'correct': 0, 'incorrect': 0}
        judge_stats['by_source'][source]['total'] += 1
        if row.get('judge_is_correct', '').strip().lower() == 'true':
            judge_stats['by_source'][source]['correct'] += 1
        else:
            judge_stats['by_source'][source]['incorrect'] += 1

    # Calculate statistics for judge samples evaluations
    judge_samples_stats = {
        'total_judge_samples': len(judge_samples_data),
        'total_correct': len(judge_samples_correct_data),
        'total_incorrect': len(judge_samples_incorrect_data),
        'by_source': {}
    }
    
    for row in judge_samples_data:
        source = row.get('source_file', 'Unknown')
        if source not in judge_samples_stats['by_source']:
            judge_samples_stats['by_source'][source] = {'total': 0, 'correct': 0, 'incorrect': 0}
        judge_samples_stats['by_source'][source]['total'] += 1
        if row.get('judge_is_correct', '').strip().lower() == 'true':
            judge_samples_stats['by_source'][source]['correct'] += 1
        else:
            judge_samples_stats['by_source'][source]['incorrect'] += 1

    # Calculate statistics for equation derivation evaluations
    equation_derivation_stats = {
        'total_equation_derivation': len(equation_derivation_data),
        'total_correct': len(equation_derivation_correct_data),
        'total_incorrect': len(equation_derivation_incorrect_data),
        'by_source': {}
    }
    
    for row in equation_derivation_data:
        source = row.get('source_file', 'Unknown')
        if source not in equation_derivation_stats['by_source']:
            equation_derivation_stats['by_source'][source] = {'total': 0, 'correct': 0, 'incorrect': 0}
        equation_derivation_stats['by_source'][source]['total'] += 1
        if row.get('judge_is_correct', '').strip().lower() == 'true':
            equation_derivation_stats['by_source'][source]['correct'] += 1
        else:
            equation_derivation_stats['by_source'][source]['incorrect'] += 1
    
    return render_template(
        'index.html',
        form=form,
        failed_stats=failed_stats,
        success_stats=success_stats,
        judge_stats=judge_stats,
        judge_samples_stats=judge_samples_stats,
        equation_derivation_stats=equation_derivation_stats,
        analysis_count=count_analysis_questions()
    )

@app.route('/image/<folder>/<qid>')
def serve_question_image(folder, qid):
    assets = get_question_assets(qid, folder)
    img_path = assets.get("image_path")
    if not img_path:
        abort(404)
    directory, filename = os.path.split(img_path)
    return send_from_directory(directory, filename)

@app.route('/results/')
@app.route('/results/<int:idx>')
def view_results(idx: int = 0):
    if not results_data:
        flash('Results CSV not found or empty.', 'error')
        return redirect(url_for('index'))

    total = len(results_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = results_data[idx]

    qid = row.get('question_number', '').strip()
    assets = get_question_assets(qid, row.get('results_folder', ''))
    
    # Use derivation from file if available, otherwise fallback to CSV ground truth
    ground_truth = assets.get('derivation') or row.get('ground_truth_explanation', '')

    return render_template(
        'result.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        ground_truth=ground_truth,
        source_info=assets.get('source_info'),
    )

@app.route('/success/')
@app.route('/success/<int:idx>')
def view_success(idx: int = 0):
    if not success_data:
        flash('No successful results found.', 'info')
        return redirect(url_for('index'))

    total = len(success_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = success_data[idx]

    qid = row.get('question_number', '').strip()
    assets = get_question_assets(qid, row.get('results_folder', ''))
    
    # Use derivation from file if available, otherwise fallback to CSV ground truth
    ground_truth = assets.get('derivation') or row.get('ground_truth_explanation', '')

    return render_template(
        'success.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        ground_truth=ground_truth,
        source_info=assets.get('source_info'),
    )

@app.route('/minimal-test/')
def minimal_test():
    return """
    <html><body>
    <h1>MINIMAL TEST</h1>
    <p>If you can see this, the server works.</p>
    <a href="/judge/">CLICK THIS SIMPLE LINK</a>
    </body></html>
    """

@app.route('/judge-test/')
def test_judge():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Judge Test</title></head>
    <body style="font-family: Arial; margin: 20px;">
    <h1>Judge Test Page - Working Links</h1>
    
    <h3>Judge Mei Samples:</h3>
    <p>Total judge records: {len(judge_data)}</p>
    <p>Judge correct: {len(judge_correct_data)}</p>
    <p>Judge incorrect: {len(judge_incorrect_data)}</p>
    <p>First question: {judge_data[0].get('question_number', 'N/A') if judge_data else 'No data'}</p>
    
    <div style="margin: 10px 0;">
        <a href='/judge/' style="display: inline-block; padding: 10px 20px; background: blue; color: white; text-decoration: none; margin: 5px;">All Judge Results ({len(judge_data)})</a>
    </div>
    <div style="margin: 10px 0;">
        <a href='/judge-correct/' style="display: inline-block; padding: 10px 20px; background: green; color: white; text-decoration: none; margin: 5px;">Correct Only ({len(judge_correct_data)})</a>
    </div>
    <div style="margin: 10px 0;">
        <a href='/judge-incorrect/' style="display: inline-block; padding: 10px 20px; background: red; color: white; text-decoration: none; margin: 5px;">Incorrect Only ({len(judge_incorrect_data)})</a>
    </div>
    
    <h3>Judge Samples:</h3>
    <p>Total judge samples records: {len(judge_samples_data)}</p>
    <p>Judge samples correct: {len(judge_samples_correct_data)}</p>
    <p>Judge samples incorrect: {len(judge_samples_incorrect_data)}</p>
    <p>First question: {judge_samples_data[0].get('question_number', 'N/A') if judge_samples_data else 'No data'}</p>
    
    <div style="margin: 10px 0;">
        <a href='/judge-samples/' style="display: inline-block; padding: 10px 20px; background: purple; color: white; text-decoration: none; margin: 5px;">All Judge Samples Results ({len(judge_samples_data)})</a>
    </div>
    <div style="margin: 10px 0;">
        <a href='/judge-samples-correct/' style="display: inline-block; padding: 10px 20px; background: darkgreen; color: white; text-decoration: none; margin: 5px;">Samples Correct Only ({len(judge_samples_correct_data)})</a>
    </div>
    <div style="margin: 10px 0;">
        <a href='/judge-samples-incorrect/' style="display: inline-block; padding: 10px 20px; background: darkred; color: white; text-decoration: none; margin: 5px;">Samples Incorrect Only ({len(judge_samples_incorrect_data)})</a>
    </div>
    
    <h3>Equation Derivation:</h3>
    <p>Total equation derivation records: {len(equation_derivation_data)}</p>
    <p>Equation derivation correct: {len(equation_derivation_correct_data)}</p>
    <p>Equation derivation incorrect: {len(equation_derivation_incorrect_data)}</p>
    <p>First question: {equation_derivation_data[0].get('question_number', 'N/A') if equation_derivation_data else 'No data'}</p>
    
    <div style="margin: 10px 0;">
        <a href='/equation-derivation/' style="display: inline-block; padding: 10px 20px; background: orange; color: white; text-decoration: none; margin: 5px;">All Equation Derivation Results ({len(equation_derivation_data)})</a>
    </div>
    <div style="margin: 10px 0;">
        <a href='/equation-derivation-correct/' style="display: inline-block; padding: 10px 20px; background: darkgreen; color: white; text-decoration: none; margin: 5px;">Derivation Correct Only ({len(equation_derivation_correct_data)})</a>
    </div>
    <div style="margin: 10px 0;">
        <a href='/equation-derivation-incorrect/' style="display: inline-block; padding: 10px 20px; background: darkred; color: white; text-decoration: none; margin: 5px;">Derivation Incorrect Only ({len(equation_derivation_incorrect_data)})</a>
    </div>
    
    <h4>Direct Access:</h4>
    <ul>
        <li><a href='/judge/0'>First Judge Result</a></li>
        <li><a href='/judge-correct/0'>First Correct Result</a></li>
        <li><a href='/judge-incorrect/0'>First Incorrect Result</a></li>
        <li><a href='/judge-samples/0'>First Judge Samples Result</a></li>
        <li><a href='/judge-samples-correct/0'>First Samples Correct Result</a></li>
        <li><a href='/judge-samples-incorrect/0'>First Samples Incorrect Result</a></li>
        <li><a href='/equation-derivation/0'>First Equation Derivation Result</a></li>
        <li><a href='/equation-derivation-correct/0'>First Derivation Correct Result</a></li>
        <li><a href='/equation-derivation-incorrect/0'>First Derivation Incorrect Result</a></li>
    </ul>
    
    <p><a href='/'>← Back to Home</a></p>
    </body>
    </html>
    """

@app.route('/judge-text/')
@app.route('/judge-text/<int:idx>')
def view_judge_text(idx: int = 0):
    if not judge_data:
        return "No judge data available"
    
    total = len(judge_data)
    idx = max(0, min(idx, total - 1))
    row = judge_data[idx]
    qid = row.get('question_number', '').strip()
    
    return f"""
    <html><body style="font-family: monospace; margin: 20px;">
    <h2>Judge Result {idx+1}/{total} - Question {qid}</h2>
    <h3>Question:</h3>
    <p>{row.get('question_text', 'N/A')[:200]}...</p>
    <h3>Solver Answer:</h3>
    <p>{row.get('solver_final_answer', 'N/A')[:200]}...</p>
    <h3>Judge Decision:</h3>
    <p><b>{row.get('judge_judgment', 'N/A')}</b> (Correct: {row.get('judge_is_correct', 'N/A')})</p>
    <h3>Ground Truth:</h3>
    <p>{row.get('ground_truth_answer', 'N/A')[:200]}...</p>
    <p>
    <a href="/judge-text/{max(0, idx-1)}">Previous</a> | 
    <a href="/judge-text/{min(total-1, idx+1)}">Next</a> |
    <a href="/">Home</a>
    </p>
    </body></html>
    """

@app.route('/judge/')
@app.route('/judge/<int:idx>')
def view_judge(idx: int = 0):
    if not judge_data:
        flash('No judge evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(judge_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = judge_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from Mei_samples folder
    assets = get_question_assets(qid, 'Mei_samples')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        nav_route='view_judge',
        image_folder='Mei_samples'
    )

@app.route('/judge-correct/')
@app.route('/judge-correct/<int:idx>')
def view_judge_correct(idx: int = 0):
    if not judge_correct_data:
        flash('No correct judge evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(judge_correct_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = judge_correct_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from Mei_samples folder
    assets = get_question_assets(qid, 'Mei_samples')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        view_type='correct',
        nav_route='view_judge_correct',
        image_folder='Mei_samples'
    )

@app.route('/judge-incorrect/')
@app.route('/judge-incorrect/<int:idx>')
def view_judge_incorrect(idx: int = 0):
    if not judge_incorrect_data:
        flash('No incorrect judge evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(judge_incorrect_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = judge_incorrect_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from Mei_samples folder
    assets = get_question_assets(qid, 'Mei_samples')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        view_type='incorrect',
        nav_route='view_judge_incorrect',
        image_folder='Mei_samples'
    )

@app.route('/judge-samples/')
@app.route('/judge-samples/<int:idx>')
def view_judge_samples(idx: int = 0):
    if not judge_samples_data:
        flash('No judge samples evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(judge_samples_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = judge_samples_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from judge_samples folder
    assets = get_question_assets(qid, 'judge_samples')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        dataset_name='Judge Samples',
        nav_route='view_judge_samples',
        image_folder='judge_samples'
    )

@app.route('/judge-samples-correct/')
@app.route('/judge-samples-correct/<int:idx>')
def view_judge_samples_correct(idx: int = 0):
    if not judge_samples_correct_data:
        flash('No correct judge samples evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(judge_samples_correct_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = judge_samples_correct_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from judge_samples folder
    assets = get_question_assets(qid, 'judge_samples')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        view_type='correct',
        dataset_name='Judge Samples',
        nav_route='view_judge_samples_correct',
        image_folder='judge_samples'
    )

@app.route('/judge-samples-incorrect/')
@app.route('/judge-samples-incorrect/<int:idx>')
def view_judge_samples_incorrect(idx: int = 0):
    if not judge_samples_incorrect_data:
        flash('No incorrect judge samples evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(judge_samples_incorrect_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = judge_samples_incorrect_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from judge_samples folder
    assets = get_question_assets(qid, 'judge_samples')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        view_type='incorrect',
        dataset_name='Judge Samples',
        nav_route='view_judge_samples_incorrect',
        image_folder='judge_samples'
    )

@app.route('/equation-derivation/')
@app.route('/equation-derivation/<int:idx>')
def view_equation_derivation(idx: int = 0):
    if not equation_derivation_data:
        flash('No equation derivation evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(equation_derivation_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = equation_derivation_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from equations_2 folder
    assets = get_question_assets(qid, 'equations_2')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        dataset_name='Equation Derivation',
        nav_route='view_equation_derivation',
        image_folder='equations_2'
    )

@app.route('/equation-derivation-correct/')
@app.route('/equation-derivation-correct/<int:idx>')
def view_equation_derivation_correct(idx: int = 0):
    if not equation_derivation_correct_data:
        flash('No correct equation derivation evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(equation_derivation_correct_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = equation_derivation_correct_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from equations_2 folder
    assets = get_question_assets(qid, 'equations_2')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        view_type='correct',
        dataset_name='Equation Derivation',
        nav_route='view_equation_derivation_correct',
        image_folder='equations_2'
    )

@app.route('/equation-derivation-incorrect/')
@app.route('/equation-derivation-incorrect/<int:idx>')
def view_equation_derivation_incorrect(idx: int = 0):
    if not equation_derivation_incorrect_data:
        flash('No incorrect equation derivation evaluation results found.', 'info')
        return redirect(url_for('index'))

    total = len(equation_derivation_incorrect_data)
    idx = max(0, min(idx, total - 1))  # clamp
    row = equation_derivation_incorrect_data[idx]

    qid = row.get('question_number', '').strip()
    # Get image assets from equations_2 folder
    assets = get_question_assets(qid, 'equations_2')
    
    return render_template(
        'judge_working.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        derivation=assets.get('derivation'),
        source_info=assets.get('source_info'),
        view_type='incorrect',
        dataset_name='Equation Derivation',
        nav_route='view_equation_derivation_incorrect',
        image_folder='equations_2'
    )

@app.route('/analysis/')
@app.route('/analysis/<int:idx>')
def view_analysis(idx: int = 0):
    _build_analysis_index()
    if not analysis_qids:
        flash('No Analysis questions found.', 'info')
        return redirect(url_for('index'))

    total = len(analysis_qids)
    idx = max(0, min(idx, total - 1))
    qid = analysis_qids[idx]
    item = get_analysis_item(qid)
    if not item:
        flash(f'Question {qid} not found.', 'warning')
        return redirect(url_for('index'))

    # Use existing asset resolver to locate the image inside Analysis/q#
    assets = get_question_assets(qid, ANALYSIS_FOLDER)

    return render_template(
        'analysis.html',
        idx=idx,
        total=total,
        qid=qid,
        question_text=item.get('question_text', ''),
        ground_truth=item.get('ground_truth'),
        gemini_answer=item.get('gemini_answer'),
        image_exists=bool(assets.get('image_path')),
        image_folder=ANALYSIS_FOLDER
    )

@app.route('/synthetic/')
@app.route('/synthetic/<int:idx>')
def view_synthetic(idx: int = 0):
    # Filter synthetic dataset results
    synthetic_results = [row for row in results_data if row.get('results_folder') == 'synthetic_dataset']
    
    if not synthetic_results:
        flash('No synthetic dataset results found.', 'info')
        return redirect(url_for('index'))

    total = len(synthetic_results)
    idx = max(0, min(idx, total - 1))  # clamp
    row = synthetic_results[idx]

    qid = row.get('question_number', '').strip()
    assets = get_question_assets(qid, row.get('results_folder', ''))
    
    # Use derivation from file if available, otherwise fallback to CSV ground truth
    ground_truth = assets.get('derivation') or row.get('ground_truth_explanation', '')

    return render_template(
        'result.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        ground_truth=ground_truth,
        source_info=assets.get('source_info'),
        dataset_name='Synthetic Dataset',
        nav_route='view_synthetic',
        nav_type='failed'
    )

@app.route('/synthetic-success/')
@app.route('/synthetic-success/<int:idx>')
def view_synthetic_success(idx: int = 0):
    # Filter synthetic dataset successful results
    synthetic_success = [row for row in success_data if row.get('results_folder') == 'synthetic_dataset']
    
    if not synthetic_success:
        flash('No successful synthetic dataset results found.', 'info')
        return redirect(url_for('index'))

    total = len(synthetic_success)
    idx = max(0, min(idx, total - 1))  # clamp
    row = synthetic_success[idx]

    qid = row.get('question_number', '').strip()
    assets = get_question_assets(qid, row.get('results_folder', ''))
    
    # Use derivation from file if available, otherwise fallback to CSV ground truth
    ground_truth = assets.get('derivation') or row.get('correct_answer', '')
    
    return render_template(
        'success.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        ground_truth=ground_truth,
        nav_route='view_synthetic_success',
        nav_type='success',
        dataset_name='Synthetic Dataset'
    )

@app.route('/synthetic2/')
@app.route('/synthetic2/<int:idx>')
def view_synthetic2(idx: int = 0):
    # Filter synthetic dataset 2 results
    synthetic_results = [row for row in results_data if row.get('results_folder') == 'synthetic_dataset_2']
    
    if not synthetic_results:
        flash('No synthetic dataset 2 results found.', 'info')
        return redirect(url_for('index'))

    total = len(synthetic_results)
    idx = max(0, min(idx, total - 1))  # clamp
    row = synthetic_results[idx]

    qid = row.get('question_number', '').strip()
    assets = get_question_assets(qid, row.get('results_folder', ''))
    
    # Use derivation from file if available, otherwise fallback to CSV ground truth
    ground_truth = assets.get('derivation') or row.get('ground_truth_explanation', '') or row.get('correct_answer', '')
    
    return render_template(
        'synthetic2_result.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        ground_truth=ground_truth,
        netlist=assets.get('netlist'),
        source_info=assets.get('source_info'),
        nav_route='view_synthetic2',
        nav_type='failed',
        dataset_name='Synthetic Dataset 2'
    )

@app.route('/synthetic2-success/')
@app.route('/synthetic2-success/<int:idx>')
def view_synthetic2_success(idx: int = 0):
    # Filter synthetic dataset 2 successful results
    synthetic_success = [row for row in success_data if row.get('results_folder') == 'synthetic_dataset_2']
    
    if not synthetic_success:
        flash('No successful synthetic dataset 2 results found.', 'info')
        return redirect(url_for('index'))

    total = len(synthetic_success)
    idx = max(0, min(idx, total - 1))  # clamp
    row = synthetic_success[idx]

    qid = row.get('question_number', '').strip()
    assets = get_question_assets(qid, row.get('results_folder', ''))
    
    # Use derivation from file if available, otherwise fallback to CSV ground truth
    ground_truth = assets.get('derivation') or row.get('ground_truth_explanation', '') or row.get('correct_answer', '')
    
    return render_template(
        'synthetic2_success.html',
        row=row,
        idx=idx,
        total=total,
        qid=qid,
        image_exists=bool(assets.get('image_path')),
        choices=assets.get('choices', []),
        ground_truth=ground_truth,
        netlist=assets.get('netlist'),
        source_info=assets.get('source_info'),
        nav_route='view_synthetic2_success',
        nav_type='success',
        dataset_name='Synthetic Dataset 2'
    )

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5002, debug=False) 