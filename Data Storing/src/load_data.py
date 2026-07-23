import os
import json
import re
from pathlib import Path
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
}
DB_NAME = 'rinaldi_munirs_lecture_archieve_database'

def strip_instructor_titles(name):
    if not name:
        return ""
    parts = name.split(",")
    base_name = parts[0]
    
    base_name = re.sub(
        r'\b(prof|dr|eng|ir|dr-ing|st|mt|m\.t|s\.t|dr\.?|ir\.?|prof\.?|drs\.?|dra\.?|ph\.?d\.?)\b',
        ' ',
        base_name,
        flags=re.IGNORECASE
    )
    base_name = re.sub(r'[^a-zA-Z\s]', ' ', base_name)
    base_name = re.sub(r'\s+', ' ', base_name)
    return base_name.strip().title()

def is_valid_instructor_name(name):
    if not name:
        return False
    name_clean = name.strip().lower()
    if len(name_clean) <= 2:
        return False
    degrees = {"m sc", "m c", "m t", "s t", "ph d", "dr", "ir", "prof", "msc", "mt", "st", "phd"}
    if name_clean in degrees:
        return False
    return True

def get_instructor_normalization_map(raw_names):
    cleaned_to_raws = {}
    for name in raw_names:
        cleaned = strip_instructor_titles(name)
        if cleaned and is_valid_instructor_name(cleaned):
            cleaned_to_raws.setdefault(cleaned, []).append(name)
            
    sorted_cleaned = sorted(cleaned_to_raws.keys(), key=len, reverse=True)
    
    cleaned_to_normalized = {}
    for name in sorted_cleaned:
        matched_longer = None
        for longer_name in cleaned_to_normalized.values():
            words = name.lower().split()
            pattern = r'\b' + r'\b.*\b'.join(map(re.escape, words)) + r'\b'
            if re.search(pattern, longer_name.lower()):
                matched_longer = longer_name
                break
        if matched_longer:
            cleaned_to_normalized[name] = matched_longer
        else:
            cleaned_to_normalized[name] = name
            
    raw_to_normalized = {}
    for cleaned, raws in cleaned_to_raws.items():
        normalized = cleaned_to_normalized[cleaned]
        for r in raws:
            raw_to_normalized[r] = normalized
            
    return raw_to_normalized

def clean_student_name(name):
    """Clean student and assistant names: keep only alphabetic letters and spaces."""
    if not name:
        return ""
    cleaned = re.sub(r'[^a-zA-Z\s]', ' ', name)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip().title()

def map_course_title_to_subject_name(title):
    """Map any course title to one of the 3 required subjects."""
    t_lower = title.lower()
    if "aljabar" in t_lower or "geometri" in t_lower:
        return "Aljabar Linear dan Geometri"
    elif "diskrit" in t_lower:
        return "Matematika Diskrit"
    elif "strategi" in t_lower or "algoritma" in t_lower:
        return "Strategi Algoritma"
    return "Strategi Algoritma"

def main():
    print("Connecting to MariaDB...")
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print(f"Creating database '{DB_NAME}' if not exists...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

    ddl_dir = Path(__file__).parent / "ddl"
    ddl_files = sorted(ddl_dir.glob("*.sql"))
    print(f"Found {len(ddl_files)} DDL files. Initializing schema...")

    for ddl_file in ddl_files:
        print(f"Executing {ddl_file.name}...")
        with open(ddl_file, "r", encoding="utf-8") as f:
            content = f.read()

        if "DELIMITER //" in content:
            content = content.replace("DELIMITER //", "").replace("DELIMITER ;", "")
            statements = content.split("//")
            for stmt in statements:
                stmt_clean = stmt.strip()
                if stmt_clean:
                    cursor.execute(stmt_clean)
        else:
            statements = content.split(";")
            for stmt in statements:
                stmt_clean = stmt.strip()
                if stmt_clean:
                    cursor.execute(stmt_clean)

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    print("Schema initialized successfully.")

    scraping_data_dir = Path(__file__).parent.parent.parent / "Data Scraping" / "src" / "data"
    
    courses_info_path = scraping_data_dir / "courses_info.json"
    assignments_path = scraping_data_dir / "assignments.json"
    materials_path = scraping_data_dir / "course_materials.json"
    grades_path = scraping_data_dir / "courses_grades.json"
    papers_path = scraping_data_dir / "paper_files.json"

    all_raw_instructors = set()
    if courses_info_path.exists():
        with open(courses_info_path, "r", encoding="utf-8") as f:
            courses_info_data = json.load(f)
        for cinfo in courses_info_data:
            for inst in cinfo.get("instructors", []):
                all_raw_instructors.add(inst["name"])
    instructor_norm_map = get_instructor_normalization_map(all_raw_instructors)
    print(f"Instructor normalization mapping built for {len(all_raw_instructors)} instructors.")

    def get_or_create_academic_year(start_year, end_year):
        cursor.execute("SELECT id FROM academic_years WHERE start_year = %s AND end_year = %s", (start_year, end_year))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO academic_years (start_year, end_year) VALUES (%s, %s)", (start_year, end_year))
        return cursor.lastrowid

    def get_or_create_subject(name):
        cursor.execute("SELECT id FROM subjects WHERE name = %s", (name,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO subjects (name) VALUES (%s)", (name,))
        return cursor.lastrowid

    def get_or_create_course(subject_id, title, code, credits):
        cursor.execute("SELECT id FROM courses WHERE code = %s", (code,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO courses (subject_id, title, code, credits) VALUES (%s, %s, %s, %s)",
                    (subject_id, title, code, credits))
        return cursor.lastrowid

    def get_or_create_instructor(name):
        norm_name = instructor_norm_map.get(name, strip_instructor_titles(name))
        if not is_valid_instructor_name(norm_name):
            return None
        cursor.execute("SELECT id FROM instructors WHERE name = %s", (norm_name,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO instructors (name) VALUES (%s)", (norm_name,))
        return cursor.lastrowid

    def get_or_create_section(code, course_id, academic_year_id, semester):
        cursor.execute("""
            SELECT 1 FROM sections 
            WHERE code = %s AND course_id = %s AND academic_year_id = %s AND semester = %s
        """, (code, course_id, academic_year_id, semester))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT INTO sections (code, course_id, academic_year_id, semester) 
                VALUES (%s, %s, %s, %s)
            """, (code, course_id, academic_year_id, semester))

    def insert_section_instructor(instructor_id, section_code, course_id, academic_year_id, semester):
        cursor.execute("""
            SELECT 1 FROM section_instructors 
            WHERE instructor_id = %s AND section_code = %s AND course_id = %s AND academic_year_id = %s AND section_semester = %s
        """, (instructor_id, section_code, course_id, academic_year_id, semester))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT INTO section_instructors (instructor_id, section_code, course_id, academic_year_id, section_semester) 
                VALUES (%s, %s, %s, %s, %s)
            """, (instructor_id, section_code, course_id, academic_year_id, semester))

    def get_or_create_student(name, student_number):
        cleaned_name = clean_student_name(name) if name else None
        cursor.execute("SELECT id FROM students WHERE student_number = %s", (student_number,))
        row = cursor.fetchone()
        if row:
            student_id = row[0]
            if cleaned_name:
                cursor.execute("UPDATE students SET name = %s WHERE id = %s AND name IS NULL", (cleaned_name, student_id))
            return student_id
        cursor.execute("INSERT INTO students (name, student_number) VALUES (%s, %s)", (cleaned_name, student_number))
        return cursor.lastrowid

    def insert_student_email(student_id, email):
        email_clean = email.lower().strip()
        cursor.execute("SELECT 1 FROM student_emails WHERE student_id = %s AND email = %s", (student_id, email_clean))
        row = cursor.fetchone()
        if not row:
            try:
                cursor.execute("INSERT INTO student_emails (student_id, email) VALUES (%s, %s)", (student_id, email_clean))
            except mysql.connector.Error:
                pass

    def get_or_create_ta_student(ta_name):
        cleaned_ta_name = clean_student_name(ta_name)
        if not cleaned_ta_name:
            cleaned_ta_name = "Unknown TA"
            
        cursor.execute("SELECT id FROM students WHERE name = %s", (cleaned_ta_name,))
        row = cursor.fetchone()
        if row:
            return row[0]
            
        cursor.execute("SELECT id, name FROM students WHERE name IS NOT NULL")
        all_students = cursor.fetchall()
        
        ta_words = [w for w in cleaned_ta_name.lower().split() if len(w) > 1]
        best_match_id = None
        best_score = 0.0
        
        for s_id, s_name in all_students:
            s_words = [w for w in s_name.lower().split() if len(w) > 1]
            if not s_words or not ta_words:
                continue
                
            matched_words = 0
            for tw in ta_words:
                found_match = False
                for sw in s_words:
                    if tw == sw:
                        found_match = True
                        break
                    if abs(len(tw) - len(sw)) <= 2:
                        common_chars = sum(1 for c in tw if c in sw)
                        if common_chars >= max(len(tw), len(sw)) - 2:
                            if tw[:3] == sw[:3] or tw[-3:] == sw[-3:]:
                                found_match = True
                                break
                if found_match:
                    matched_words += 1
                    
            score = matched_words / max(len(ta_words), len(s_words))
            if score > best_score:
                best_score = score
                best_match_id = s_id
                
        if best_score >= 0.6:
            return best_match_id
            
        cursor.execute("SELECT student_number FROM students WHERE student_number LIKE 'UNKNOWN%'")
        rows = cursor.fetchall()
        max_num = 0
        for r in rows:
            num_part = r[0].replace("UNKNOWN", "")
            if num_part.isdigit():
                max_num = max(max_num, int(num_part))
        
        new_num = f"UNKNOWN{max_num + 1:04d}"
        cursor.execute("INSERT INTO students (name, student_number) VALUES (%s, %s)", (cleaned_ta_name, new_num))
        return cursor.lastrowid

    def get_or_create_teaching_assistant(student_id):
        cursor.execute("SELECT student_id FROM teaching_assistants WHERE student_id = %s", (student_id,))
        row = cursor.fetchone()
        if row:
            return student_id
        cursor.execute("INSERT INTO teaching_assistants (student_id) VALUES (%s)", (student_id,))
        return student_id

    def insert_section_teaching_assistant(ta_student_id, section_code, course_id, academic_year_id, semester):
        cursor.execute("""
            SELECT 1 FROM section_teaching_assistants 
            WHERE teaching_assistant_id = %s AND section_code = %s AND course_id = %s AND academic_year_id = %s AND section_semester = %s
        """, (ta_student_id, section_code, course_id, academic_year_id, semester))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT IGNORE INTO section_teaching_assistants (teaching_assistant_id, section_code, course_id, academic_year_id, section_semester) 
                VALUES (%s, %s, %s, %s, %s)
            """, (ta_student_id, section_code, course_id, academic_year_id, semester))

    def insert_student_section(student_id, section_code, course_id, academic_year_id, semester, final_grade):
        cursor.execute("""
            SELECT 1 FROM student_sections 
            WHERE student_id = %s AND section_code = %s AND course_id = %s AND academic_year_id = %s AND section_semester = %s
        """, (student_id, section_code, course_id, academic_year_id, semester))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT IGNORE INTO student_sections (student_id, section_code, course_id, academic_year_id, section_semester, final_grade) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (student_id, section_code, course_id, academic_year_id, semester, final_grade))

    def get_or_create_material(url, title):
        cursor.execute("SELECT id FROM materials WHERE url = %s", (url,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO materials (url, title) VALUES (%s, %s)", (url, title))
        return cursor.lastrowid

    def insert_section_material(material_id, section_code, course_id, academic_year_id, semester):
        cursor.execute("""
            SELECT 1 FROM section_materials 
            WHERE material_id = %s AND section_code = %s AND course_id = %s AND academic_year_id = %s AND section_semester = %s
        """, (material_id, section_code, course_id, academic_year_id, semester))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT IGNORE INTO section_materials (material_id, section_code, course_id, academic_year_id, section_semester) 
                VALUES (%s, %s, %s, %s, %s)
            """, (material_id, section_code, course_id, academic_year_id, semester))

    def get_or_create_assignment(url, title):
        cursor.execute("SELECT id FROM assignments WHERE url = %s", (url,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("INSERT INTO assignments (url, title) VALUES (%s, %s)", (url, title))
        return cursor.lastrowid

    def insert_section_assignment(assignment_id, section_code, course_id, academic_year_id, semester):
        cursor.execute("""
            SELECT 1 FROM section_assignments 
            WHERE assignment_id = %s AND section_code = %s AND course_id = %s AND academic_year_id = %s AND section_semester = %s
        """, (assignment_id, section_code, course_id, academic_year_id, semester))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT IGNORE INTO section_assignments (assignment_id, section_code, course_id, academic_year_id, section_semester) 
                VALUES (%s, %s, %s, %s, %s)
            """, (assignment_id, section_code, course_id, academic_year_id, semester))

    def find_assignment_id(course_id, academic_year_id, semester, component_name):
        comp_lower = component_name.lower().strip()
        
        is_ignored = any(kw in comp_lower for kw in ["rerata", "rata-rata", "kehadiran", "hadir", "akhir", "prediksi"])
        if is_ignored:
            return None

        cursor.execute("""
            SELECT a.id, a.title, a.url FROM assignments a
            JOIN section_assignments sa ON a.id = sa.assignment_id
            WHERE sa.course_id = %s 
              AND sa.academic_year_id = %s 
              AND sa.section_semester = %s
        """, (course_id, academic_year_id, semester))
        candidates = cursor.fetchall()

        if "uts" in comp_lower or "ujian tengah semester" in comp_lower:
            for a_id, title, url in candidates:
                t_low = title.lower()
                if "uts" in t_low or "ujian tengah semester" in t_low or "tengah" in t_low:
                    return a_id
        elif "uas" in comp_lower or "ujian akhir semester" in comp_lower:
            for a_id, title, url in candidates:
                t_low = title.lower()
                if "uas" in t_low or "ujian akhir semester" in t_low or "akhir" in t_low:
                    return a_id
        elif "kuis" in comp_lower:
            match = re.search(r'kuis\s*(\d+)', comp_lower)
            if match:
                k_num = match.group(1)
                for a_id, title, url in candidates:
                    t_low = title.lower()
                    if "kuis" in t_low and (k_num in t_low or f"kuis-{k_num}" in t_low):
                        return a_id
        elif "tubes" in comp_lower or "tugas besar" in comp_lower:
            match = re.search(r'(?:tubes|tugas besar)\s*(\d+)', comp_lower)
            if match:
                t_num = match.group(1)
                for a_id, title, url in candidates:
                    t_low = title.lower()
                    if ("tubes" in t_low or "tugas besar" in t_low) and (t_num in t_low or f"besar-{t_num}" in t_low or f"tubes-{t_num}" in t_low):
                        return a_id
        elif "tucil" in comp_lower or "tugas kecil" in comp_lower:
            match = re.search(r'(?:tucil|tugas kecil)\s*(\d+)', comp_lower)
            if match:
                t_num = match.group(1)
                for a_id, title, url in candidates:
                    t_low = title.lower()
                    if ("tucil" in t_low or "tugas kecil" in t_low) and (t_num in t_low or f"kecil-{t_num}" in t_low or f"tucil-{t_num}" in t_low):
                        return a_id
        elif "makalah" in comp_lower:
            for a_id, title, url in candidates:
                t_low = title.lower()
                if "makalah" in t_low:
                    return a_id

        return None

    def insert_student_assignment(assignment_id, student_id, grade):
        cursor.execute("""
            SELECT 1 FROM student_assignments 
            WHERE assignment_id = %s AND student_id = %s
        """, (assignment_id, student_id))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT IGNORE INTO student_assignments (assignment_id, student_id, grade) 
                VALUES (%s, %s, %s)
            """, (assignment_id, student_id, grade))

    print("Seeding subjects table...")
    required_subjects = ["Matematika Diskrit", "Aljabar Linear dan Geometri", "Strategi Algoritma"]
    for sname in required_subjects:
        get_or_create_subject(sname)
    conn.commit()

    if courses_info_path.exists():
        print("Loading courses_info.json...")
        with open(courses_info_path, "r", encoding="utf-8") as f:
            courses_info = json.load(f)
        
        for cinfo in courses_info:
            ay_id = get_or_create_academic_year(cinfo["academic_year"]["start_year"], cinfo["academic_year"]["end_year"])
            
            subject_name = map_course_title_to_subject_name(cinfo["course_name"])
            sub_id = get_or_create_subject(subject_name)
            
            course_id = get_or_create_course(sub_id, cinfo["course_name"], cinfo["course_code"], cinfo["course_credits"])
            
            for inst in cinfo.get("instructors", []):
                inst_name = inst["name"]
                cleaned_name = strip_instructor_titles(inst_name)
                if cleaned_name and is_valid_instructor_name(cleaned_name):
                    inst_id = get_or_create_instructor(inst_name)
                    if inst_id:
                        for sect_code in inst["sections"]:
                            get_or_create_section(sect_code, course_id, ay_id, cinfo["semester"])
                            insert_section_instructor(inst_id, sect_code, course_id, ay_id, cinfo["semester"])
        conn.commit()

    if materials_path.exists():
        print("Loading course_materials.json...")
        with open(materials_path, "r", encoding="utf-8") as f:
            materials_list = json.load(f)
        
        for mat in materials_list:
            cursor.execute("SELECT id FROM courses WHERE code = %s", (mat["course_code"],))
            c_row = cursor.fetchone()
            if not c_row:
                continue
            course_id = c_row[0]
            
            ay_id = get_or_create_academic_year(mat["academic_year"]["start_year"], mat["academic_year"]["end_year"])
            
            cursor.execute("SELECT code, semester FROM sections WHERE course_id = %s AND academic_year_id = %s", (course_id, ay_id))
            sections_list = cursor.fetchall()
            
            mat_id = get_or_create_material(mat["url"], mat["title"])
            for sect_code, semester in sections_list:
                insert_section_material(mat_id, sect_code, course_id, ay_id, semester)
        conn.commit()

    if assignments_path.exists():
        print("Loading assignments.json...")
        with open(assignments_path, "r", encoding="utf-8") as f:
            assignments_list = json.load(f)
            
        for ass in assignments_list:
            cursor.execute("SELECT id FROM courses WHERE code = %s", (ass["course_code"],))
            c_row = cursor.fetchone()
            if not c_row:
                continue
            course_id = c_row[0]
            
            ay_id = get_or_create_academic_year(ass["academic_year"]["start_year"], ass["academic_year"]["end_year"])
            
            cursor.execute("SELECT code, semester FROM sections WHERE course_id = %s AND academic_year_id = %s", (course_id, ay_id))
            sections_list = cursor.fetchall()
            
            ass_id = get_or_create_assignment(ass["url"], ass["title"])
            for sect_code, semester in sections_list:
                insert_section_assignment(ass_id, sect_code, course_id, ay_id, semester)
        conn.commit()

    if grades_path.exists():
        print("Loading courses_grades.json...")
        with open(grades_path, "r", encoding="utf-8") as f:
            grades_list = json.load(f)
            
        for grade_record in grades_list:
            cursor.execute("SELECT id FROM courses WHERE code = %s", (grade_record["course_code"],))
            c_row = cursor.fetchone()
            if not c_row:
                continue
            course_id = c_row[0]
            
            ay_id = get_or_create_academic_year(grade_record["academic_year"]["start_year"], grade_record["academic_year"]["end_year"])
            semester = grade_record["section_semester"]
            
            tAs = grade_record.get("assistant") or []
            students_list = grade_record.get("students") or []
            unique_sections = set(stud["section_code"] for stud in students_list)
            
            for ta_name in tAs:
                cleaned_ta_name = clean_student_name(ta_name)
                if not cleaned_ta_name:
                    continue
                ta_student_id = get_or_create_ta_student(cleaned_ta_name)
                get_or_create_teaching_assistant(ta_student_id)
                for sect_code in unique_sections:
                    get_or_create_section(sect_code, course_id, ay_id, semester)
                    insert_section_teaching_assistant(ta_student_id, sect_code, course_id, ay_id, semester)
            
            for stud in students_list:
                s_num = stud["student_number"]
                s_name = clean_student_name(stud["name"])
                sect_code = stud["section_code"]
                f_grade = stud["final_grade"]
                
                student_id = get_or_create_student(s_name, s_num)
                get_or_create_section(sect_code, course_id, ay_id, semester)
                insert_student_section(student_id, sect_code, course_id, ay_id, semester, f_grade)
                
                components = stud.get("components", {})
                for comp_name, comp_val in components.items():
                    comp_name_lower = comp_name.lower()
                    is_ignored = any(kw in comp_name_lower for kw in ["rerata", "rata-rata", "kehadiran", "hadir", "akhir", "prediksi"])
                    if not is_ignored:
                        if isinstance(comp_val, (int, float)):
                            grade_val = int(comp_val)
                        elif isinstance(comp_val, str) and comp_val.strip().replace('.', '', 1).isdigit():
                            grade_val = int(float(comp_val))
                        else:
                            continue
                            
                        ass_id = find_assignment_id(course_id, ay_id, semester, comp_name)
                        if ass_id:
                            insert_student_assignment(ass_id, student_id, grade_val)
                            
        conn.commit()

    if papers_path.exists():
        print("Loading paper_files.json...")
        with open(papers_path, "r", encoding="utf-8") as f:
            papers_list = json.load(f)
            
        for paper in papers_list:
            c_code = paper["course_code"]
            cursor.execute("SELECT id FROM courses WHERE code = %s", (c_code,))
            c_row = cursor.fetchone()
            if not c_row:
                continue
            course_id = c_row[0]
            
            ay_id = get_or_create_academic_year(paper["academic_year"]["start_year"], paper["academic_year"]["end_year"])
            
            stud_info = paper["student"]
            s_num = stud_info["student_number"]
            s_name = clean_student_name(stud_info["name"])
            
            if not s_num:
                s_id = get_or_create_ta_student(s_name or "Unknown Student")
                cursor.execute("SELECT student_number FROM students WHERE id = %s", (s_id,))
                s_num = cursor.fetchone()[0]
            else:
                s_id = get_or_create_student(s_name, s_num)
                
            for email in stud_info.get("emails", []):
                insert_student_email(s_id, email)
                
            ass_id = None
            cursor.execute("""
                SELECT a.id FROM assignments a
                JOIN section_assignments sa ON a.id = sa.assignment_id
                WHERE sa.course_id = %s AND a.title LIKE '%makalah%'
                LIMIT 1
            """, (course_id,))
            a_row = cursor.fetchone()
            if a_row:
                ass_id = a_row[0]
            else:
                cursor.execute("INSERT INTO assignments (url, title) VALUES (%s, %s)",
                            (f"https://placeholder.url/course/{c_code}/makalah-assignment", "Tugas makalah"))
                ass_id = cursor.lastrowid
                cursor.execute("SELECT code, semester FROM sections WHERE course_id = %s AND academic_year_id = %s", (course_id, ay_id))
                sections_list = cursor.fetchall()
                for sect_code, sem in sections_list:
                    insert_section_assignment(ass_id, sect_code, course_id, ay_id, sem)
            
            cursor.execute("""
                SELECT grade FROM student_assignments 
                WHERE assignment_id = %s AND student_id = %s
            """, (ass_id, s_id))
            sa_row = cursor.fetchone()
            
            paper_title_trunc = paper["title"][:255]
            paper_url = paper["url"]
            paper_abstract = paper["abstract"]
            paper_lang = paper["language"]
            
            if not sa_row:
                cursor.execute("""
                    INSERT IGNORE INTO student_assignments (assignment_id, student_id, grade)
                    VALUES (%s, %s, NULL)
                """, (ass_id, s_id))
                
            cursor.execute("SELECT 1 FROM papers WHERE url = %s", (paper_url,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT IGNORE INTO papers (assignment_id, student_id, title, abstract, url, language) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (ass_id, s_id, paper_title_trunc, paper_abstract, paper_url, paper_lang))
                
        conn.commit()

    print("Data loading completed successfully!")
    conn.close()

if __name__ == "__main__":
    main()