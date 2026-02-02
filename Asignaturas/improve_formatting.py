import os
import re
import shutil

BASE_DIR = r"c:\_CONFIANZA23\PERSONAL\PERSONAS 00 LUDA\01_Estudios_TSLCB\Asignaturas"

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
    
    # Remove redundant title line that matches subject name loosely
    # e.g. "Tecnicas de analisis hematologico." inside the body
    normalized_subject = subject_name.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    
    for line in lines:
        line = line.strip()
        if not line:
            content_lines.append(line)
            continue

        # Skip if line is just the title repeated (heuristic)
        # Check if line content is very similar to subject name
        if len(line) < 100 and normalized_subject in line.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u"):
             # If it looks like a header (starts with # or just text), skip it
             if line.startswith("#") or line.endswith("."):
                 # But don't skip if it's a sentence.
                 # Heuristic: mostly match
                 pass # Actually, safest to just let the user delete if wrong, but let's try to remove exact matches of "Subject Name."
        
        if line.strip(" #.") == subject_name:
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
        # If line starts with "1.", "2." etc, bold it?
        # Or numeric list.
        if re.match(r"^\d+\.\s", line):
            # It's a numbered list item, likely a main topic in contents
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

def process_directories():
    print(f"Scanning {BASE_DIR}...")
    
    for item in os.listdir(BASE_DIR):
        dir_path = os.path.join(BASE_DIR, item)
        
        if os.path.isdir(dir_path):
            # Check for pattern like "01_01 Name"
            match = re.match(r"^(\d{2}_\d{2})\s+(.+)$", item)
            if match:
                prefix = match.group(1)
                subject_raw_name = match.group(2)
                
                # Look for .md files inside
                md_files = [f for f in os.listdir(dir_path) if f.endswith(".md")]
                
                for md_file in md_files:
                    full_md_path = os.path.join(dir_path, md_file)
                    
                    # Read original content
                    with open(full_md_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    
                    # 1. Clean
                    cleaned_content = clean_text(raw_content)
                    
                    # 2. Beautify
                    # Use the file name as subject name hint
                    subject_name_from_file = os.path.splitext(md_file)[0]
                    
                    # Remove existing prefix if present to avoid duplication "01_01 01_01 ..."
                    # We remove any leading "XX_XX " pattern (one or more times)
                    subject_name_clean = re.sub(r"^(\d{2}_\d{2}\s+)+", "", subject_name_from_file).strip()
                    
                    final_content = beautify_markdown(cleaned_content, prefix, subject_name_clean)
                    
                    # 3. Rename
                    # Desired: "01_01 Subject Name.md"
                    new_filename = f"{prefix} {subject_name_clean}.md"
                    new_full_path = os.path.join(dir_path, new_filename)
                    
                    # Save
                    with open(new_full_path, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                        
                    print(f"[UPDATED] {new_filename}")
                    
                    # Remove old file if name is different
                    if new_filename != md_file:
                        os.remove(full_md_path)
                        print(f"  (Removed old: {md_file})")

if __name__ == "__main__":
    process_directories()
