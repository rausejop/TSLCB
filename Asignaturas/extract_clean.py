import os
import re
import unicodedata
import sys
import shutil

# Try to import pdfplumber
try:
    import pdfplumber
except ImportError:
    print("Error: 'pdfplumber' library is required.")
    sys.exit(1)

# Configuration
PDF_FILENAME = "fp-ensenanza-sans08-loe-curriculo-d20150179.pdf"
BASE_DIR = os.getcwd() 
PDF_PATH = os.path.join(BASE_DIR, PDF_FILENAME)

def clean_text(text):
    """Clean up PDF artifacts and formatting noise."""
    lines = text.split('\n')
    cleaned_lines = []
    
    # Patterns to remove
    noise_patterns = [
        r"B\.O\.C\.M\.", 
        r"BOLETÍN OFICIAL",
        r"Pág\.\s*\d+",
        r"\d{2}-\d{8}-MCOB",
        r"LUNES\d+DE",
        r"^\s*\d+\s*[A-Z]{3}\s*$", # artifacts like "4-A ENU"
        r"^\.14$", 
        r"^\.DOM$",
        r"^\s*4-A\s*$",
        r"^\s*ENU\s*$"
    ]
    
    for line in lines:
        is_noise = False
        for pattern in noise_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_noise = True
                break
        
        if not is_noise:
            cleaned_lines.append(line)
            
    return "\n".join(cleaned_lines)

def beautify_markdown(text, prefix, subject_name):
    """Apply GitHub-friendly formatting."""
    
    new_lines = []
    
    # Header
    new_lines.append(f"# 📘 {prefix} {subject_name}")
    new_lines.append("")
    new_lines.append("---")
    
    # Extract metadata if finding exact lines
    metadata = []
    
    lines = text.split('\n')
    content_lines = []
    
    # Normalized subject name for cleaning redundant titles
    normalized_subject = subject_name.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    
    for line in lines:
        line = line.strip()
        if not line:
            content_lines.append(line)
            continue
            
        # Metadata detection
        if line.lower().startswith("duración:"):
            val = line.split(":", 1)[1].strip()
            metadata.append(f"- **⏱️ Duración:** {val}")
            continue
        if line.lower().startswith("código:"):
            val = line.split(":", 1)[1].strip()
            metadata.append(f"- **🆔 Código:** {val}")
            continue
        if "créditos ects" in line.lower():
            val = line.split(":", 1)[1].strip()
            metadata.append(f"- **🎓 Créditos ECTS:** {val}")
            continue
            
        # Skip if line is just the title repeated (heuristic)
        # We only skip if it's very short and matches the subject name
        if len(line) < len(subject_name) + 5:
             line_norm = line.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace(".","")
             if line_norm == normalized_subject:
                 continue
            
        # Section Headers
        if re.match(r"^Contenidos\s*:?$", line, re.IGNORECASE):
            content_lines.append("")
            content_lines.append("## 📚 Contenidos")
            content_lines.append("")
            continue
            
        if re.match(r"^Resultados de aprendizaje\s*:?$", line, re.IGNORECASE):
            content_lines.append("")
            content_lines.append("## 🎯 Resultados de Aprendizaje")
            content_lines.append("")
            continue
            
        if re.match(r"^Criterios de evaluación\s*:?$", line, re.IGNORECASE):
            content_lines.append("")
            content_lines.append("## 📝 Criterios de Evaluación")
            content_lines.append("")
            continue
            
        # List formatting
        if re.match(r"^\d+\.\s", line):
            # It's a numbered list item
            content_lines.append(f"### {line}")
        elif line.startswith("-") or line.startswith("•"):
            # Standardize bullets
            content_lines.append(f"- {line.lstrip('-• ').strip()}")
        else:
            content_lines.append(line)

    # Reassemble
    if metadata:
        new_lines.append("### 📋 Información General")
        new_lines.extend(metadata)
        new_lines.append("")
        new_lines.append("---")
    
    new_lines.extend(content_lines)
    
    return "\n".join(new_lines)

def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
    return text.strip()

def get_subject_directories(base_dir):
    dirs = {}
    if not os.path.exists(base_dir):
        return dirs
        
    for item in os.listdir(base_dir):
        full_path = os.path.join(base_dir, item)
        if os.path.isdir(full_path):
            parts = item.split(' ', 1)
            # Map: normalized name -> (full_path, raw_prefix, raw_name)
            
            prefix = ""
            name_part = item
            if len(parts) > 1 and re.match(r"^\d{2}_\d{2}$", parts[0]):
                prefix = parts[0]
                name_part = parts[1]
            
            info = {
                "path": full_path,
                "prefix": prefix,
                "name": name_part
            }
            
            dirs[normalize_text(item)] = info
            if len(parts) > 1:
                dirs[normalize_text(name_part)] = info
                
    return dirs

def extract_content(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return {}
        
    extracted_modules = {}
    current_module = None
    buffer_text = []
    
    module_start_pattern = re.compile(r"Módulo Profesional\s*:\s*(.+)", re.IGNORECASE)
    
    print(f"Reading PDF: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                match = module_start_pattern.search(line)
                if match:
                    if current_module:
                        extracted_modules[current_module] = "\n".join(buffer_text)
                        
                    current_module = match.group(1).strip()
                    if "Código" in current_module: 
                        current_module = current_module.split("Código")[0].strip()
                    
                    # Do NOT add title to buffer_text here, we add it in beautify
                    buffer_text = [] 
                    print(f"  Found Module: {current_module}")
                    
                elif current_module:
                    buffer_text.append(line)
                    
        if current_module:
             extracted_modules[current_module] = "\n".join(buffer_text)
             
    return extracted_modules

def find_best_match(module_name, dir_map):
    norm_mod = normalize_text(module_name)
    if norm_mod in dir_map: return dir_map[norm_mod]
    
    for dir_key, info in dir_map.items():
        if len(dir_key) < 4: continue
        if dir_key in norm_mod: return info
        if norm_mod in dir_key: return info
            
    return None

def main():
    print("--- Starting Clean Extraction Process ---")
    
    # 1. Cleanup old md files
    print("Cleaning old MD files...")
    for item in os.listdir(BASE_DIR):
        d = os.path.join(BASE_DIR, item)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".md"):
                    try:
                        os.remove(os.path.join(d, f))
                    except: pass

    # 2. Map Directories
    dir_map = get_subject_directories(BASE_DIR)

    # 3. Extract PDF Content
    modules = extract_content(PDF_PATH)
    
    print(f"\nProcessing {len(modules)} extracted modules...")
    
    files_created = 0
    for mod_name, raw_content in modules.items():
        target_info = find_best_match(mod_name, dir_map)
        
        if target_info:
            target_dir = target_info["path"]
            prefix = target_info["prefix"]
            # Use module name from PDF as it is often cleaner or at least official
            # But user wants file name to match directory?
            # "cambia el nombre de cada fichero markdown para qeu coincida con el de la asignatura"
            # It's safer to use the Directory Name (target_info['name']) to ensure match.
            sub_name = target_info['name']
            
            # 1. Clean Text
            cleaned_text = clean_text(raw_content)
            
            # 2. Beautify
            final_content = beautify_markdown(cleaned_text, prefix, sub_name)
            
            # 3. Filename
            # "incluyendo el doble digito barrabaja y segund doble digito" -> prefix + name
            filename = f"{prefix} {sub_name}.md" if prefix else f"{sub_name}.md"
            file_path = os.path.join(target_dir, filename)
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                print(f"[OK] Created: {filename}")
                files_created += 1
            except Exception as e:
                print(f"[ERR] Failed to write {file_path}: {e}")
        else:
            print(f"[SKIP] No matching directory for: '{mod_name}'")

    print(f"\n--- Done. Created {files_created} clean markdown files. ---")

if __name__ == "__main__":
    main()
