import os
import re
import smtplib
from flask import Flask, render_template, request, redirect, url_for, session
from PyPDF2 import PdfReader
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


app = Flask(__name__)
app.secret_key = "secret123"
app.config['UPLOAD_FOLDER'] = "resumes"

users = {}  # email : password

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("login_page"))

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email in users and users[email] == password:
            session["user"] = email
            return redirect(url_for("submit_resume"))
        else:
            return render_template("in.html", error="Invalid email or password")
    return render_template("in.html")

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        users[email] = password
        session["user"] = email
        return redirect(url_for("submit_resume"))
    return render_template("login.html")

     #---------------- FUNCTION TO SEND EMAIL ----------------
def send_email(to_email, name, score, level):
    from_email = "komalzinjurde5224@gmail.com"
    from_password = "segk gxox kmxm xwdp"  # तुमचा पूर्ण App Password

    subject = "Resume Submission Result"

    if score >= 60:
        message_text = f"""Hi {name},

Your resume has been reviewed.

Score: {score}/100
Level: {level}

🎉 Congratulations! You have been shortlisted for the next round. We look forward to connecting with you soon.

Best regards,
Recruitment Team
"""
    else:
        message_text = f"""Hi {name},

Thank you for submitting your resume.

Score: {score}/100
Level: {level}

We appreciate your interest. We encourage you to keep improving your skills and apply again in the future.

Best wishes,
Recruitment Team
"""

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(message_text, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, from_password)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully")
    except Exception as e:
        print("❌ Email error:", e)


# ---------------- SUBMIT RESUME ----------------
@app.route("/submit", methods=["GET", "POST"])
def submit_resume():
    if "user" not in session:
        return redirect(url_for("login_page"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        job_description = request.form.get("job_description", "").lower()
        file = request.files.get("resume")

        if not file:
            return render_template("s.html", error="No file uploaded")

        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        filename = f"{name}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # -------- PDF TEXT EXTRACTION --------
        reader = PdfReader(filepath)
        resume_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                resume_text += text + "\n"

        cleaned_text = resume_text.replace("\n", " ").lower()

        # -------- SKILL DETECTION --------
        SKILLS_LIST = [
            "python", "java", "sql", "excel", "machine learning",
            "data analysis", "pandas", "numpy", "matplotlib",
            "power bi", "tableau", "html", "css", "javascript"
        ]
        detected_skills = [skill for skill in SKILLS_LIST if re.search(r"\b" + re.escape(skill) + r"\b", cleaned_text)]

        # -------- JOB ROLE DETECTION --------
        JOB_ROLES = [
            "data scientist", "data analyst", "machine learning engineer",
            "business analyst", "software engineer", "full stack developer",
            "backend developer", "frontend developer", "python developer",
            "java developer"
        ]
        detected_roles = [role for role in JOB_ROLES if re.search(r"\b" + re.escape(role) + r"\b", cleaned_text)]

        # -------- EXPERIENCE DETECTION --------
        EXPERIENCE_KEYWORDS = [
            "experience", "worked", "intern", "internship",
            "project", "projects", "company", "organization",
            "role", "responsibility", "employment"
        ]
        experience_lines = []
        for line in resume_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            for word in EXPERIENCE_KEYWORDS:
                if word in line.lower():
                    if len(line.split()) > 3 and not any(noise in line.lower() for noise in ["summary", "profile", "contact", "education", "skills"]):
                        experience_lines.append(line)
                        break

        # -------- EXPERIENCE DURATION --------
        duration_pattern = r"\d+(?:\.\d+)?\s*(?:year|years|month|months)"
        experience_duration = [match.group() for match in re.finditer(duration_pattern, cleaned_text)]

        # -------- RESUME SCORING --------
        score = 0
        SKILL_SCORES = {
            "python": 10, "java": 8, "sql": 7, "machine learning": 12,
            "data analysis": 12, "excel": 5, "power bi": 6, "tableau": 6,
            "html": 4, "css": 3, "javascript": 5
        }
        for skill in detected_skills:
            score += SKILL_SCORES.get(skill, 3)

        for line in experience_lines:
            if any(word in line.lower() for word in ["intern", "internship", "project"]):
                score += 10
                break

        for duration in experience_duration:
            if "year" in duration:
                years = float(re.findall(r"\d+(?:\.\d+)?", duration)[0])
                if years >= 1: score += 15
                if years >= 2: score += 10
            elif "month" in duration:
                months = float(re.findall(r"\d+(?:\.\d+)?", duration)[0])
                if months >= 6: score += 5

        # -------- JD BASED SCORING --------
        jd_matched_skills = [skill for skill in detected_skills if skill in job_description]
        score += len(jd_matched_skills) * 5
        score = min(score, 100)

        # -------- CANDIDATE LEVEL --------
        if score >= 80:
            level = "Excellent Candidate ⭐⭐⭐"
        elif score >= 60:
            level = "Good Candidate ⭐⭐"
        elif score >= 40:
            level = "Average Candidate ⭐"
        else:
            level = "Needs Improvement"

        # -------- SAVE DATA --------
        with open("resumes/resume_list.txt", "a", encoding="utf-8") as f:
            f.write(f"{name},{email},{phone},{filename},{score},{level}\n")

        # -------- SEND EMAIL --------
        send_email(email, name, score, level)

        # -------- RETURN OUTPUT WITH DASHBOARD LINK --------
        return f"""
<!DOCTYPE html>
<html>
<head>
<title>Resume Result</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #f4f6f9;
}}
.card {{
    width: 700px;
    margin: 40px auto;
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
}}
h2 {{
    text-align: center;
    color: #2ecc71;
}}
.section {{
    margin-top: 20px;
}}
.label {{
    font-weight: bold;
    color: #555;
}}
.tags span {{
    display: inline-block;
    background: #e3f2fd;
    color: #0d47a1;
    padding: 6px 12px;
    margin: 4px;
    border-radius: 20px;
    font-size: 14px;
}}
.score-box {{
    margin-top: 25px;
    padding: 20px;
    background: #f1f8e9;
    border-radius: 10px;
    text-align: center;
}}
.score {{
    font-size: 32px;
    font-weight: bold;
    color: #2e7d32;
}}
.links {{
    display: flex;
    justify-content: space-between;
    margin-top: 30px;
}}
a {{
    text-decoration: none;
    color: #1976d2;
    font-weight: bold;
}}
</style>
</head>

<body>
<div class="card">

<h2>✅ Resume Uploaded Successfully</h2>

<div class="section">
    <p><span class="label">Name:</span> {name}</p>
    <p><span class="label">Email:</span> {email}</p>
</div>

<div class="section">
    <p class="label">Skills</p>
    <div class="tags">
        {" ".join(f"<span>{skill}</span>" for skill in detected_skills) if detected_skills else "None"}
    </div>
</div>

<div class="section">
    <p class="label">Detected Job Role(s)</p>
    <p>{", ".join(detected_roles) if detected_roles else "Not detected"}</p>
</div>


<div class="section">
    <p class="label">Experience</p>
    <p>{"<br>".join(experience_lines) if experience_lines else "None"}</p>
</div>

<div class="section">
    <p class="label">Experience Duration</p>
    <p>{", ".join(experience_duration) if experience_duration else "Not mentioned"}</p>
</div>

<div class="section">
    <p class="label">JD Matched Skills</p>
    <p>{", ".join(jd_matched_skills) if jd_matched_skills else "None"}</p>
</div>

<div class="score-box">
    <div class="score">{score}/100</div>
    <div>{level}</div>
</div>

<div class="links">
    <a href="/submit">➕ Upload Another Resume</a>
    <a href="/dashboard">📊 View Dashboard</a>
</div>

</div>
</body>
</html>
"""


    return render_template("s.html")

# ---------------- VIEW & RANKING ----------------
@app.route("/view")
def view_resumes():
    if "user" not in session:
        return redirect(url_for("login_page"))

    resumes = []
    if os.path.exists("resumes/resume_list.txt"):
        with open("resumes/resume_list.txt", "r", encoding="utf-8") as f:
            for line in f:
                name, email, phone, filename, score, level = line.strip().split(",")
                resumes.append({
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "file": filename,
                    "score": int(score),
                    "level": level
                })

    resumes.sort(key=lambda x: x["score"], reverse=True)
    return render_template("view.html", resumes=resumes)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login_page"))

    SKILLS_LIST = [
        "python", "java", "sql", "excel", "machine learning",
        "data analysis", "pandas", "numpy", "matplotlib",
        "power bi", "tableau", "html", "css", "javascript"
    ]
    total_resumes = 0
    skill_count = {skill: 0 for skill in SKILLS_LIST}
    scores = []

    resume_file = "resumes/resume_list.txt"
    if os.path.exists(resume_file):
        with open(resume_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) != 6:
                    continue
                name, email, phone, filename, score_str, level = parts
                scores.append(int(score_str))
                total_resumes += 1

                # Count skills from PDF
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(pdf_path) and filename.lower().endswith(".pdf"):
                    try:
                        reader = PdfReader(pdf_path)
                        text = ""
                        for page in reader.pages:
                            txt = page.extract_text()
                            if txt:
                                text += txt.lower() + " "
                        for skill in skill_count:
                            if skill in text:
                                skill_count[skill] += 1
                    except:
                        pass

    avg_score = sum(scores) // len(scores) if scores else 0

    return render_template(
        "dashboard.html",
        total=total_resumes,
        avg=avg_score,
        skills=skill_count
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(port=9500, debug=True)