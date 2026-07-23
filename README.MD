## Rinaldi Munir's Lecture Archive ETL Project
###
<h1 align="center">
  <br>
  Seleksi Warga Basdat 2026 <br>
  ETL Project
  <br>
  <br>
</h1>

## Author
Nama : Irvin Tandiarrang Sumual <br>
NIM  : 13524030

## Deskripsi
Proyek ETL ini menggunakan data arsip (khusus mata kuliah Matematika Diskrit, Aljabar Linear dan Geometri,
dan Strategi Algoritam pada tahun 2020-2026) dari website Pak Rinaldi Munir yang merupakan dosen STEI ITB, di mana
website tersebut sangat kaya akan bahan belajar yang digunakan oleh mahasiswa dan juga terdapat makalah-makalah yang
pernah ditulis oleh mahasiswa yang mengambil mata kuliah Pak Rinaldi Munir. Selain itu, terdapat juga hasil belajar yang
berupa nilai dari mahasiswa-mahasiswa tersebut. Oleh karena itu, data tersebut dipilih untuk discraping, meskipun dalam
prosesnya tidak semudah itu karena banyaknya ketidakonsistenan format data. Namun, pada akhirnya, setelah berhasil discraping,
data akan dibersihkan dan dipersiapkan untuk dapat dimasukkan ke dalam basis data relasional Maria DB.

MariaDB dipilih sebagai RDBMS karena memiliki performa tinggi, sifatnya open-source, dan juga saya pribadi cukup familiar.

Alasan topik ini saya pilih adalah karena data ini cukup bermanfaat, khususnya sebagai anak Teknik Informatika ITB, di mana
ketika ingin melihat data-data terdahulu, tidak perlu untuk gonta-ganti page terus-menerus dan juga banyak kenangan indah
di mata kuliah - mata kuliah yang diampuh Pak Rinaldi :)

---

## Struktur File JSON
Arsip data scraping disimpan dalam format JSON berikut di direktori `Data Scraping/src/data/`:

### 1. `courses_info.json`
Menyimpan metadata dasar suatu mata kuliah beserta pembagian dosen pengajar dan kelas (section) yang diampu.
```json
{
  "course_code": "IF2211",
  "course_name": "Strategi Algoritma",
  "course_credits": 3,
  "semester": 2,
  "academic_year": {
    "start_year": 2025,
    "end_year": 2026
  },
  "instructors": [
    {
      "name": "Rila Mandala",
      "sections": [
        "K2"
      ]
    }
  ]
}
```
* **Penjelasan Field:**
  * `course_code` / `course_name` / `course_credits`: Identitas kode mata kuliah, nama, dan beban SKS.
  * `semester`: Nomor semester (1 = Ganjil, 2 = Genap).
  * `academic_year`: Tahun ajaran perkuliahan.
  * `instructors`: Daftar dosen pengajar serta pemetaan kelas (*sections*) yang diampunya.

### 2. `course_materials.json`
Menyimpan materi kuliah (slide presentasi, catatan kuliah) yang diunduh dari situs web.
```json
{
  "course_code": "IF2211",
  "course_name": "Strategi Algoritma",
  "title": "Pengantar Strategi Algoritma",
  "url": "https://informatika.stei.itb.ac.id/~rinaldi.munir/Stmik/2025-2026/01-Pengantar-Strategi-Algoritma-(2026).pdf",
  "academic_year": {
    "start_year": 2025,
    "end_year": 2026
  }
}
```
* **Penjelasan Field:**
  * `title`: Judul slide atau nama topik materi kuliah.
  * `url`: Tautan berkas unduhan PDF materi.
  * `course_code` / `course_name` : Identitas kode mata kuliah dan nama
  * `academic_year`: Tahun ajaran perkuliahan.

### 3. `assignments.json`
Menyimpan soal/tugas kuliah (Tugas Kecil, Tugas Besar, Ujian, Kuis).
```json
{
  "course_code": "IF2211",
  "course_name": "Strategi Algoritma",
  "title": "Tugas kecil 1: Penyelesaian Permainan Queens Linkedin",
  "url": "https://informatika.stei.itb.ac.id/~rinaldi.munir/Stmik/2025-2026/Tucil1-IF2211-2026.pdf",
  "academic_year": {
    "start_year": 2025,
    "end_year": 2026
  }
}
```
* **Penjelasan Field:**
  * `title`: Nama/deskripsi tugas kuliah.
  * `url`: Tautan unduhan soal tugas format PDF.
  * `course_code` / `course_name` : Identitas kode mata kuliah dan nama
  * `academic_year`: Tahun ajaran perkuliahan.

### 4. `courses_grades.json`
Menyimpan transkrip nilai lengkap mahasiswa di suatu kelas (*section*) beserta asisten kelasnya.
```json
{
  "course_code": "IF2211",
  "course_title": "Strategi Algoritma",
  "section_semester": 2,
  "academic_year": {
    "start_year": 2025,
    "end_year": 2026
  },
  "assistant": [
    "Zulfaqar Nayaka"
  ],
  "students": [
    {
      "student_number": "10122043",
      "name": "Beni Lesmana",
      "section_code": "K1",
      "final_grade": "B",
      "components": {
        "TUCIL Tucil1": 95,
        "TUBES Tubes1": 97,
        "UTS": 32.5,
        "UAS": 67,
        "Nilai Akhir": 70.03
      }
    }
  ]
}
```
* **Penjelasan Field:**
  * `assistant`: Daftar nama asisten kelas (TA) yang bertugas.
  * `students`: List mahasiswa pengambil kelas, berisi NIM (`student_number`), nama, nilai indeks (`final_grade`), serta breakdown nilai tiap komponen tugas/ujian (`components`).

### 5. `paper_files.json`
Menyimpan metadata lengkap makalah mahasiswa hasil ekstraksi PDF.
```json
{
  "title": "Implementasi Algoritma Greedy untuk Pengambilan Keputusan Optimal Jangka Pendek pada Papan Congklak",
  "abstract": "Congklak adalah permainan papan tradisional yang membutuhkan strategi untuk mengumpulkan jumlah biji terbanyak di lumbung...",
  "url": "https://informatika.stei.itb.ac.id/~rinaldi.munir/Stmik/2025-2026/Makalah2026/10122043_Beni%20Lesmana_Implementasi%20Algoritma%20Greedy%20untukCongklak.pdf",
  "language": "id",
  "student": {
    "name": "Beni Lesmana",
    "student_number": "10122043",
    "emails": [
      "benilesmana48@gmail.com",
      "10122043@mahasiswa.itb.ac.id"
    ]
  },
  "course_code": "IF2211",
  "section_semester": 1,
  "academic_year": {
    "start_year": 2025,
    "end_year": 2026
  },
  "course_name": "Strategi Algoritma"
}
```
* **Penjelasan Field:**
  * `title` / `abstract` / `language`: Judul makalah, kutipan abstrak, dan kode bahasa terdeteksi (`id` untuk Indonesia, `en` untuk Inggris, dan sebagainya).
  * `student`: Data profil penulis mencakup nama, NIM, dan email yang berhasil diekstrak dari dokumen PDF.

---

## Scraper
### Cara Menggunakan Scraper:
1. Pastikan Python >= 3.0 telah terpasang.
2. Pasang dependensi yang diperlukan:
   ```bash
   pip install -r "Data Scraping/requirements.txt"
   ```
3. Masuk ke direktori source scraper dan jalankan skrip:
   ```bash
   cd "Data Scraping/src"
   python main.py
   ```
4. Output JSON akan otomatis diperbarui dan disimpan di `Data Scraping/src/data/`.

---

## ERD
![ERD of Rinaldi Munir's Lecture Archive](Data%20Storing/design/ERD%20of%20Rinaldi%20Munir's%20Lecture%20Archive.png)
    
## Diagram Relasional RDMBS
![Relational Model Diagram of Rinaldi Munir's Lecture Archive](Data%20Storing/design/Relational%20Model%20Diagram%20of%20Rinaldi%20Munir's%20Lecture%20Archive.png)

## Translasi ERD ke Diagram Relasional
1. Setiap entitas kuat (*strong entity*) dipetakan menjadi tabel tersendiri (`students`, `subjects`, `courses`, `instructors`, `assignments`, `materials`, `academic_years`).
2. Atribut bernilai banyak (*multi-valued attribute*) dipetakan menjadi tabel baru dengan foreign key ke entitas induk (`student_emails`).
3. Hubungan *many-to-many* dipetakan menjadi tabel asosiatif dengan gabungan foreign key sebagai primary key (`section_instructors`, `student_sections`, `section_materials`, `section_assignments`, `student_assignments`, `section_teaching_assistants`).
4. Weak entity (`teaching_assistants` dan `papers`) direlasikan ke entitas induknya menggunakan foreign key.
5. Translasi hierarki student `is-a` teaching_assistant dilakukan dengan cara meletakkan student_id di tabel teaching_assitant

---

## Struktur Tabel Relasional

Basis data terdiri dari 17 tabel utama:
1. **`students`**: Menyimpan identitas dasar mahasiswa (ID, nama, NIM). NIM bersifat unik dan dibatasi panjang 8-12 karakter.
2. **`subjects`**: Menyimpan daftar subjek/topik mata kuliah.
3. **`courses`**: Menyimpan metadata mata kuliah (kode matkul, judul, SKS) dengan relasi ke subjeknya.
4. **`instructors`**: Menyimpan data nama dosen pengajar.
5. **`academic_years`**: Menyimpan daftar tahun akademik (tahun mulai, tahun selesai).
6. **`sections`**: Representasi kelas perkuliahan (kode kelas seperti K1/K2, ID matkul, tahun akademik, semester).
7. **`student_emails`**: Menyimpan alamat email mahasiswa (serta satu student dapat memiliki sejumlah email).
8. **`materials`**: Menyimpan daftar materi kuliah dan tautan berkasnya.
9. **`assignments`**: Menyimpan daftar tugas kuliah dan tautan soalnya.
10. **`teaching_assistants`**: Menandai mahasiswa yang menjadi asisten dosen.
11. **`papers`**: Menyimpan metadata makalah mahasiswa (judul, abstrak, bahasa, tautan berkas) yang terhubung ke tugas makalah dan data mahasiswa.
12. **`student_assignments`**: Pencatatan nilai tugas mahasiswa.
13. **`student_sections`**: Pencatatan nilai akhir mahasiswa untuk kelas tertentu.
14. **`section_instructors`**: Relasi dosen pengajar dengan kelas yang diampu.
15. **`section_teaching_assistants`**: Relasi asisten dosen dengan kelas yang dibantu.
16. **`section_materials`**: Tautan materi kuliah yang diberikan pada kelas tertentu.
17. **`section_assignments`**: Tautan tugas kuliah yang diberikan pada kelas tertentu.

---

## Cara Mengakses & Query Database

### 1. Inisialisasi Database (Ingest)
Pastikan layanan MariaDB/MySQL lokal Anda sudah aktif pada port 3306. Jalankan perintah berikut untuk menginisialisasi skema tabel dan memuat semua data JSON ke MariaDB:
```bash
cd "Data Storing/src"
python load_data.py
```

### 2. Mengakses Database via CLI
Hubungkan ke MariaDB langsung lewat terminal Anda:
```bash
mysql -u root rinaldi_munirs_lecture_archieve_database
```

## Screenshots

![1](Data%20Storing/screenshot/Screenshot%202026-07-23%20232635.png)
![2](Data%20Storing/screenshot/Screenshot%202026-07-23%20232650.png)
![3](Data%20Storing/screenshot/Screenshot%202026-07-23%20232831.png)
![4](Data%20Storing/screenshot/Screenshot%202026-07%20232847.png)

---

## Referensi
### Libraries
- `beautifulsoup4` (Parsing dokumen HTML perkuliahan)
- `requests` (Mengunduh halaman arsip & berkas PDF)
- `pypdf` (Mengekstrak teks halaman makalah dan juga informasi kuliah)
- `langdetect` (Mendeteksi bahasa makalah secara otomatis)
- `pydantic` (Validasi tipe data hasil scraping)
- `mysql-connector-python` (Ingestion data ke basis data MariaDB)

### Data source
- Primary source: https://informatika.stei.itb.ac.id/~rinaldi.munir/

## Penggunaan AI
### Bagian-bagian yang dibantu AI
AI sangat membantu author dalam menghadapi keterbatasan author dalam proses pembuatan code,
di mana dalam hal scraping, AI sangat membantu dalam menyusun regex yang diperlukan untuk memperoleh
data-data dari sumber yang wujudnya berupa PDF ataupun live office dan juga .htm. Dalam hal storing,
AI membantu penulis dalam proses akselerasi penulisan kode di mana membantu penulis dalam berfokus
pada batasan-batasan database yang seharusnya dibandingkan pada syntax penulisan.

### Bagian-bagian yang tetap dikerjakan sendiri
Author tetap mengerjakan sendiri mulai dari memilih sumber, merancang ERD, merancang Relational Model dan juga DDL.
Author juga tetap berperan untuk mengarahkan AI agar tidak keluar dari jalur yang diharapkan dan juga author
tetap melakukan testing

### Refleksi dari penggunaan AI
Author merasa AI sangat membantu dalam mewujudnyatakan ide author dalam
menyusun database ini, tetapi di balik kenyamanan tersebut author tetap
harus belajar untuk dapat menguasai fundamental basisdata dan juga
mengimplementasikannya secara mandiri agar tidak ketergantungan :D