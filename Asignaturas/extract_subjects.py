import os
import re
import unicodedata
import sys

# Try to import pdfplumber, suggest installation if missing
try:
    import pdfplumber
except ImportError:
    print("Error: 'pdfplumber' library is required.")
    print("Please install it running: pip install pdfplumber")
    sys.exit(1)

# Configuration
PDF_FILENAME = "fp-ensenanza-sans08-loe-curriculo-d20150179.pdf"
# We assume the script is run from the directory where the 'Asignaturas' folders and the PDF reside
BASE_DIR = os.getcwd() 
PDF_PATH = os.path.join(BASE_DIR, PDF_FILENAME)

def normalize_text(text):
    """Normalize text to lowercase and remove accents for comparison."""
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
    return text.strip()

def get_subject_directories(base_dir):
    """Get a map of normalized subject name -> full directory path."""
    dirs = {}
    if not os.path.exists(base_dir):
        return dirs
        
    for item in os.listdir(base_dir):
        full_path = os.path.join(base_dir, item)
        if os.path.isdir(full_path):
            # Name format example: "01_01 Gestion de muestras biologicas"
            # We want to use "Gestion de muestras biologicas" as key
            parts = item.split(' ', 1)
            
            # Key 1: Full name normalized (e.g. "01_01 gestion de muestras...")
            dirs[normalize_text(item)] = full_path
            
            # Key 2: Content name if numbered (e.g. "gestion de muestras...")
            if len(parts) > 1:
                potential_name = parts[1]
                dirs[normalize_text(potential_name)] = full_path

    return dirs

def extract_content(pdf_path):
    """Extract content per module from PDF."""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return {}
        
    extracted_modules = {}
    current_module = None
    buffer_text = []
    
    # Regex to find Module headers. 
    # Validates "Módulo Profesional: <Name>" (case insensitive)
    module_start_pattern = re.compile(r"Módulo Profesional\s*:\s*(.+)", re.IGNORECASE)
    
    # Optional: Stop pattern if there are sections we want to ignore after the modules?
    # For now, we assume modules run sequentially.
    
    print(f"Reading PDF: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                # Check for start of a new module
                match = module_start_pattern.search(line)
                if match:
                    # If we were collecting for a previous module, save it
                    if current_module:
                        extracted_modules[current_module] = "\n".join(buffer_text)
                        print(f"  Finished extracting: {current_module} ({len(extracted_modules[current_module])} chars)")
                        
                    # Start new module
                    current_module = match.group(1).strip()
                    # Clean up some common trailing artifacts in titles if any
                    if "Código" in current_module: 
                        current_module = current_module.split("Código")[0].strip()
                        
                    buffer_text = [f"# {current_module}\n"]
                    print(f"  Found Module: {current_module} (Page {i+1})")
                    
                # If we are inside a module, append text
                elif current_module:
                    buffer_text.append(line)
                    
        # Save the very last module
        if current_module:
             extracted_modules[current_module] = "\n".join(buffer_text)
             print(f"  Finished extracting: {current_module} ({len(extracted_modules[current_module])} chars)")
             
    return extracted_modules

def find_best_match(module_name, dir_map):
    """Find the directory that best matches the module name."""
    norm_mod = normalize_text(module_name)
    
    # 1. Exact match attempt
    if norm_mod in dir_map:
        return dir_map[norm_mod]
        
    # 2. Containment attempt (if module name contains dir name or vice versa)
    # We prioritize the dictionary keys (directory parts) being inside the module name
    # e.g. Dir: "bioquimica", Module: "Bioquímica clínica" -> Match?
    # Or reverse: Dir: "01_01 gestion...", Module: "Gestión" -> No
    
    best_match = None
    max_overlap = 0
    
    for dir_key, dir_path in dir_map.items():
        # Avoid very short matches that might be false positives
        if len(dir_key) < 4: 
            continue
            
        if dir_key in norm_mod:
            # Found a directory name inside the module name
            # e.g. dir_key="gestion de muestras", norm_mod="gestion de muestras biologicas" -> MATCH
            return dir_path
            
        if norm_mod in dir_key:
            # Found module name inside directory name
            # e.g. dir_key="01_01 gestion de muestras biologicas", norm_mod="gestion de muestras biologicas" -> MATCH
            return dir_path
            
    return None

def main():
    print("--- Starting Extraction Process ---")
    
    # 1. Map Directories
    dir_map = get_subject_directories(BASE_DIR)
    if not dir_map:
        print(f"No subdirectories found in {BASE_DIR}. Exiting.")
        return

    # 2. Extract PDF Content
    modules = extract_content(PDF_PATH)
    if not modules:
        print("No modules extracted. Check PDF content or regex.")
        return
    
    print(f"\nProcessing {len(modules)} extracted modules...")
    
    # 3. Save to Files
    files_created = 0
    for mod_name, content in modules.items():
        target_dir = find_best_match(mod_name, dir_map)
        
        if target_dir:
            # Create a safe filename
            safe_name = "".join([c for c in mod_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            filename = f"{safe_name}.md"
            file_path = os.path.join(target_dir, filename)
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[OK] Saved: {filename} -> {os.path.basename(target_dir)}")
                files_created += 1
            except Exception as e:
                print(f"[ERR] Failed to write {file_path}: {e}")
        else:
            print(f"[SKIP] No matching directory for: '{mod_name}'")

    print(f"\n--- Done. Created {files_created} markdown files. ---")

if __name__ == "__main__":
    main()
