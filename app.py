import gradio as gr
import google.generativeai as genai
import json
import os
from parsers import get_text_from_file
from prompts import PROMPT
from datetime import datetime

# === CONFIGURATION ===
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
MAX_WORDS = 1000
MAX_FILE_SIZE_MB = 5  # MB

# === CUSTOM CSS (unchanged from your original) ===
custom_css = """
/* Overriding the monochrome theme's accent color and defining new colors */
:root {
    --color-accent-500: #fd7e14 !important; /* Striking Orange for CTA */
    --color-accent-600: #fd7e14 !important;
    --color-success: #1D7C31; /* Darker Green for Strengths (High Contrast) */
    --color-header-bg: #1F2937; /* Dark Charcoal for Header */
    --color-text-dark: #222222; /* Primary Body/Heading Text (Black) */
    --color-text-medium: #444444; /* Secondary/Descriptive Text (Dark Gray for contrast) */
    --color-text-light: #888888; /* Used for subtle elements like Original Bullet */
}
.gradio-button {
    background-color: transparent !important;
    border: 2px solid var(--color-accent-500) !important;
    color: var(--color-accent-500) !important;
    font-weight: 600 !important;
    transition: all 0.3s ease-in-out !important;
}
.gradio-button:hover {
    background-color: var(--color-accent-500) !important;
    color: white !important;
}
/* Ensure progress bars use the accent color */
.progress {
    background: var(--color-accent-500) !important;
}
/* Header Styling: Dark background, White text */
.header-block {
    background-color: var(--color-header-bg) !important;
    padding: 2rem 0 !important;
    margin-bottom: 2rem !important;
    border-radius: 8px !important;
}
.header-block h1 {
    color: white !important; 
    font-size: 2.8rem !important; /* Heading Size */
    font-weight: 700 !important;
    text-align: center !important;
}
.header-block p {
    color: #E5E7EB !important; /* Subheading Color */
    font-size: 1.2rem !important;
    text-align: center !important;
}
/* Ensure all labels and main text are dark on light background */
.gradio-label {
    color: var(--color-text-dark) !important;
    font-weight: 600 !important;
}
/* Output Card Styling */
.output-card {
    border-left: 5px solid var(--color-accent-500);
    padding: 1.5rem;
    border-radius: 8px;
    background-color: #fcfcfc;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px; /* Space between Sections */
}
/* General H2 Styling (Section Heading) */
.output-card h2 {
    font-size: 1.6rem !important; /* Section Heading Size */
    font-weight: 700 !important;
    color: var(--color-text-dark) !important;
    margin-bottom: 1.5rem !important; /* Space after heading */
}
/* Score Progress Bar Styling */
.score-progress {
    height: 12px;
    border-radius: 6px;
    background: #e0e0e0;
    overflow: hidden;
    margin-bottom: 1.5rem; /* Space after progress bar before next element/subheading */
}
.score-progress-fill {
    height: 100%;
    border-radius: 6px;
}
/* Specific styling for Strengths section */
.strengths-section {
    border-left-color: var(--color-success) !important;
}
.strengths-section h3 {
    color: var(--color-success) !important; /* Ensures green heading is dark and visible */
}
/* Rewritten Bullet POINTER Styling */
.bullet-pointer {
    background-color: #f7f7f7;
    border: 1px solid #e0e0e0;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem; /* Space between rewritten pointers */
}
.bullet-pointer p {
    line-height: 1.4; /* Better line spacing for dense text */
    color: var(--color-text-dark) !important; 
}
/* Ensures all list items (strengths/improvements) are dark */
.output-card ul li {
    color: var(--color-text-dark) !important;
}
.gradio-container h1, .gradio-container p {
    color: #222222 !important; /* Ensuring main text is dark */
}
/* FIX: Hides the gr.File component's label and input area, ONLY showing the download link */
.gradio-file-display {
    display: none !important;
}
.gradio-file-display > div:nth-child(2) {
    display: none !important;
}
/* Custom class for the OR text */
.or-text {
    font-weight: 700 !important; /* Make OR bold */
    text-align: center !important;
    margin: 0 10px !important;
    color: var(--color-text-dark) !important;
    align-self: center; /* Center vertically within the row */
    line-height: 5.5; /* Adjusted line height for vertical centering */
    min-width: 30px;
}
/* NEW: Input Card Group Styling - Wraps JD and Resume Sections */
.input-card-group {
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
    padding: 1.5rem !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    margin: 0 5px; /* Slight horizontal margin for separation */
}
"""

# === HELPER FUNCTIONS ===
def format_feedback_to_markdown(feedback):
    """
    Convert normalized feedback dict -> markdown string for download.
    """
    if not isinstance(feedback, dict):
        return "Error: Invalid feedback format."

    resume_score = feedback.get('resume_score', {}).get('score', 'N/A')
    match_score_100 = feedback.get('match_score', {}).get('score', 0)
    try:
        match_score_10 = (match_score_100 / 100) * 10
    except Exception:
        match_score_10 = 0

    current_date = datetime.now().strftime("%Y-%m-%d")

    md = [
        f"# Career Buddy Resume Analysis\n",
        f"**Date:** {current_date}\n",
        f"## 📊 Scores",
        f"- **Resume Score (Best Practices):** {resume_score}/100 ({feedback.get('resume_score', {}).get('bucket', 'N/A')})",
        f"- **Match Score (Against JD):** {match_score_10:.1f}/10 ({feedback.get('match_score', {}).get('bucket', 'N/A')})\n",
        f"## 💎 Strengths\n"
    ]

    strengths = feedback.get('strengths', [])
    if isinstance(strengths, (list, tuple)):
        md.extend([f"* {s}" for s in strengths])
    elif isinstance(strengths, str):
        md.append(f"* {strengths}")

    md.append("\n## 🛠️ Areas of Improvement\n")
    for a in feedback.get('improvement_areas', []):
        area = a.get('area', 'General') if isinstance(a, dict) else str(a)
        suggestion = a.get('suggestion', '') if isinstance(a, dict) else ''
        md.append(f"* **{area}**: {suggestion}")

    md.append("\n## 📝 Rewritten Resume Bullets\n")
    for b in feedback.get('rewritten_bullets', []):
        original = b.get('original', '') if isinstance(b, dict) else ''
        rewritten = b.get('rewritten', '') if isinstance(b, dict) else ''
        md.append(f"---")
        md.append(f"**Original:** {original}")
        md.append(f"**Rewritten:** {rewritten}")

    return "\n".join(md)


def ensure_list_of_dicts(data, required_keys):
    """
    Ensure `data` is a list of dicts containing required_keys. Convert simple "Key: Value" strings when possible.
    Returns cleaned list of dicts.
    """
    if not isinstance(data, list):
        return []

    cleaned = []
    for item in data:
        if isinstance(item, dict) and all(k in item for k in required_keys):
            cleaned.append(item)
        elif isinstance(item, dict):
            # Keep what's there but ensure keys exist (fill blanks)
            new_item = {k: item.get(k, "") for k in required_keys}
            cleaned.append(new_item)
        elif isinstance(item, str):
            # Try "Key: Value" parsing for two-key expected structures
            if len(required_keys) == 2 and ":" in item:
                parts = item.split(":", 1)
                cleaned.append({required_keys[0]: parts[0].strip(), required_keys[1]: parts[1].strip()})
            else:
                # For single key cases, store under first key
                cleaned.append({required_keys[0]: item})
        # else ignore non-string/non-dict entries
    return cleaned


def build_output_html(feedback, resume_score_info, match_score_info, match_score_display):
    """
    Build the final HTML string for Gradio output and return (html, markdown_content).
    Keeps your original visual structure but uses normalized data.
    """
    # Normalize strengths
    strengths = feedback.get('strengths', [])
    if isinstance(strengths, str):
        strengths = [strengths]
    strengths_list_html = ""
    for s in strengths:
        # format_strength_item behavior: split on ':' to bold the left part
        parts = s.split(":", 1)
        if len(parts) > 1:
            formatted = f"<span style='font-weight: 700; color: var(--color-success);'>{parts[0]}:</span> <span style='font-weight: 500; color: var(--color-text-dark);'>{parts[1].strip()}</span>"
        else:
            formatted = f"<span style='font-weight: 500; color: var(--color-text-dark);'>{s}</span>"
        strengths_list_html += f"<li style='margin-bottom: 0.75rem;'>💎 {formatted}</li>"

    # Improvements
    improvements_list = ""
    for a in feedback.get('improvement_areas', []):
        area = a.get('area', '') if isinstance(a, dict) else str(a)
        suggestion = a.get('suggestion', '') if isinstance(a, dict) else ""
        improvements_list += f"<li style='margin-bottom: 0.75rem; font-weight: 500; color: var(--color-text-dark);'>🛠️ <span style='font-weight: 600; color: var(--color-accent-500);'>{area}</span>: {suggestion}</li>"

    # Rewritten bullets
    rewritten_pointers_html = ""
    for b in feedback.get('rewritten_bullets', []):
        original = b.get('original', '') if isinstance(b, dict) else ""
        rewritten = b.get('rewritten', '') if isinstance(b, dict) else ""
        rewritten_pointers_html += f"""
            <div class='bullet-pointer'>
                <p style='margin-bottom: 0.5rem; font-size: 0.95rem; line-height: 1.4;'>
                    <span style='font-weight: 700; color: var(--color-accent-500);'>📝 Original:</span>
                    <span style='font-weight: 500; color: var(--color-text-dark);'>{original}</span>
                </p>
                <p style='font-size: 1.0rem; line-height: 1.4;'>
                    <span style='font-weight: 700; color: var(--color-success);'>💡 Rewritten:</span>
                    <span style='font-weight: 500; color: var(--color-text-dark);'>{rewritten}</span>
                </p>
            </div>
        """

    # Scores HTML (safe defaults if missing)
    resume_score_val = resume_score_info.get('score', 0) if isinstance(resume_score_info, dict) else 0
    resume_score_bucket = resume_score_info.get('bucket', 'N/A') if isinstance(resume_score_info, dict) else 'N/A'
    match_score_bucket = match_score_info.get('bucket', 'N/A') if isinstance(match_score_info, dict) else 'N/A'
    match_score_pct = match_score_info.get('score', 0) if isinstance(match_score_info, dict) else 0

    scores_html = f"""
    <div class='output-card'>
        <h2>📊 Performance Scores</h2>
        <hr style='border: 0; border-top: 1px solid #e0e0e0; margin-bottom: 1.5rem;'/>
        <div style='margin-bottom: 1.5rem;'>
            <h3 style='font-weight: 700; color: var(--color-text-dark); margin-bottom: 0.5rem;'>🎯 Resume Score:
                <span style='color: var(--color-accent-500); font-size: 1.4rem;'>{resume_score_val}/100 ({resume_score_bucket})</span>
            </h3>
            <div class='score-progress'><div class='score-progress-fill' style='width:{resume_score_val}%; background:var(--color-accent-500);'></div></div>
        </div>
        <div>
            <h3 style='font-weight: 700; color: var(--color-text-dark); margin-bottom: 0.5rem;'>🎯 Match Score:
                <span style='color: var(--color-accent-500); font-size: 1.4rem;'>{match_score_display:.1f}/10 ({match_score_bucket})</span>
            </h3>
            <div class='score-progress'><div class='score-progress-fill' style='width:{match_score_pct}%; background:var(--color-accent-500);'></div></div>
        </div>
    </div>
    """

    strengths_html = f"""
    <div class='output-card strengths-section'>
        <h3 style='font-weight: 700; color: var(--color-success); margin-bottom: 1.5rem;'>💎 Strengths</h3>
        <ul style='list-style-type: none; padding-left: 0; margin-top: 1rem;'>{strengths_list_html}</ul>
    </div>
    """

    improvements_html = f"""
    <div class='output-card'>
        <h3 style='font-weight: 700; color: var(--color-accent-500); margin-bottom: 1.5rem;'>🛠️ Key Areas for Improvement</h3>
        <ul style='color: var(--color-text-dark); list-style-type: none; padding-left: 0; margin-top: 1rem;'>{improvements_list}</ul>
    </div>
    """

    rewritten_section_html = f"""
    <div class='output-card'>
        <h2 style='color: var(--color-text-dark); margin-top: 0; font-size: 1.6rem; font-weight: 700;'>📝 Rewritten Resume Bullets</h2>
        <p style='margin-bottom: 1.5rem; color: var(--color-text-medium); font-size: 1rem;'>Use these suggestions to immediately improve your resume's impact.</p>
        {rewritten_pointers_html}
    </div>
    """

    output_html = f"<div>{scores_html}{strengths_html}{improvements_html}{rewritten_section_html}</div>"

    markdown_content = format_feedback_to_markdown(feedback)

    return output_html, markdown_content


# === CORE LOGIC ===
def get_coaching_feedback(jd_text_input, jd_file_input, resume_input_file, domain, years_experience):
    """
    Returns a tuple for Gradio outputs: (html_string, markdown_file_path_or_None, gr.update(visible=True/False))
    """
    print("--- New Request ---")
    jd_text = jd_text_input.strip() if jd_text_input else ""
    resume_text = ""

    # === File reading helper with clear errors ===
    def read_file_safely(file_path, label):
        if not file_path:
            return ""
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                return f"ERROR__TOO_LARGE__{label}"
            text = get_text_from_file(file_path)
            if text == "PDF_PARSING_ERROR":
                return f"ERROR__PDF_PARSE__{label}"
            return text
        except Exception as e:
            print(f"Error reading {label}: {e}")
            return f"ERROR__READ__{label}"

    if not jd_text and jd_file_input:
        jd_text = read_file_safely(jd_file_input, "JD")
        if isinstance(jd_text, str) and jd_text.startswith("ERROR__"):
            return (f"❌ {jd_text.replace('ERROR__','').replace('__',' ')}", None, gr.update(visible=False))

    if resume_input_file:
        resume_text = read_file_safely(resume_input_file, "Resume")
        if isinstance(resume_text, str) and resume_text.startswith("ERROR__"):
            return (f"❌ {resume_text.replace('ERROR__','').replace('__',' ')}", None, gr.update(visible=False))

    # Mandatory validation
    if not jd_text or not resume_text:
        return ("⚠️ Please provide both JD and Resume.", None, gr.update(visible=False))

    if len(jd_text.split()) > MAX_WORDS:
        return (f"⚠️ Job Description exceeds {MAX_WORDS} words.", None, gr.update(visible=False))
    if len(resume_text.split()) > MAX_WORDS:
        return (f"⚠️ Resume exceeds {MAX_WORDS} words.", None, gr.update(visible=False))

    # Build prompt
    full_prompt = (
        PROMPT.replace("<JD_TEXT>", jd_text)
        .replace("<RESUME_TEXT>", resume_text)
        .replace("<DOMAIN>", domain or "General")
        .replace("<YEARS_OF_EXPERIENCE>", str(years_experience))
    )

    model = genai.GenerativeModel("gemini-2.5-pro")

    try:
        response = model.generate_content(full_prompt, generation_config={"temperature": 0.2})
        # Access text safely
        raw_text = getattr(response, "text", None)
        if raw_text is None:
            raw_text = str(response)

        raw_text = raw_text.strip()

        # Strip common markdown code fences if present
        if "```" in raw_text:
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        # Attempt to parse JSON
        try:
            feedback = json.loads(raw_text)
        except json.JSONDecodeError:
            # Log raw text for debugging
            print("⚠️ JSON decode failed. Raw model output:")
            print(raw_text[:10000])  # print up to 10k chars
            return ("⚠️ AI returned invalid JSON. Retry.", None, gr.update(visible=False))

        if not isinstance(feedback, dict):
            print("⚠️ Model returned JSON that is not an object/dict:")
            print(type(feedback), feedback)
            return ("⚠️ AI returned unexpected structure. Retry.", None, gr.update(visible=False))

        # Normalize expected fields
        feedback.setdefault("strengths", feedback.get("strengths", []))
        feedback["improvement_areas"] = ensure_list_of_dicts(feedback.get("improvement_areas", []), ["area", "suggestion"])
        # Normalize rewritten bullets with fallback keys
        rewritten_raw = feedback.get("rewritten_bullets", [])
        normalized_rewritten = []
        
        if isinstance(rewritten_raw, list):
            for item in rewritten_raw:
                if isinstance(item, dict):
                    original = (
                        item.get("original")
                        or item.get("old")
                        or item.get("before")
                        or item.get("previous")
                        or item.get("existing")
                        or item.get("old_bullet")
                        or item.get("original_pointer")
                    )
                    rewritten = (
                        item.get("rewritten")
                        or item.get("new")
                        or item.get("after")
                        or item.get("improved")
                        or item.get("suggestion")
                        or item.get("new_bullet")
                        or item.get("improved_pointer")
                    )
                    if original or rewritten:
                        normalized_rewritten.append({"original": original or "", "rewritten": rewritten or ""})
                elif isinstance(item, str) and "→" in item:
                    parts = item.split("→", 1)
                    normalized_rewritten.append({"original": parts[0].strip(), "rewritten": parts[1].strip()})
        feedback["rewritten_bullets"] = normalized_rewritten

        # Safely get score dicts
        resume_score_info = feedback.get("resume_score", {"score": 0, "bucket": "N/A"})
        match_score_info = feedback.get("match_score", {"score": 0, "bucket": "N/A"})
        try:
            match_score_display = (match_score_info.get("score", 0) / 100) * 10
        except Exception:
            match_score_display = 0.0

        # Build HTML + markdown
        output_html, markdown_content = build_output_html(feedback, resume_score_info, match_score_info, match_score_display)

        # Save markdown to a temporary path that Gradio File component can serve
        temp_file_path = "career_buddy_feedback.md"
        try:
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        except Exception as e:
            print(f"Failed to write markdown file: {e}")
            temp_file_path = None

        visible_update = gr.update(visible=bool(temp_file_path))
        return (output_html, temp_file_path, visible_update)

    except Exception as e:
        # Catch-all to avoid crashes; log for debugging
        print(f"❌ Unexpected error in get_coaching_feedback: {type(e).__name__}: {e}")
        return (f"❌ Unexpected error: {e}", None, gr.update(visible=False))


# === GRADIO UI ===
with gr.Blocks(theme=gr.themes.Monochrome(), css=custom_css) as demo:

    with gr.Column():

        # Header
        with gr.Row(elem_classes=["header-block"]):
            gr.Markdown("# Career Buddy\nYour personal AI job coach to land your dream job.")

        # Inputs
        with gr.Row():
            with gr.Column(scale=2, min_width=300, elem_classes=["input-card-group"]):
                gr.Markdown("## 📋 Job Description (JD)")
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1):
                        jd_input_text = gr.Textbox(label="Paste JD Text", lines=5, placeholder="Paste JD here (max 1000 words)")
                    gr.Markdown("<div class='or-text'>OR</div>")
                    with gr.Column(scale=1):
                        jd_input_file = gr.File(label="Upload JD (PDF/DOCX)", type="filepath")

            with gr.Column(scale=1, min_width=200, elem_classes=["input-card-group"]):
                gr.Markdown("## 📝 Your Resume")
                resume_input_file = gr.File(label="Upload Resume (PDF/DOCX) (Mandatory)", type="filepath")

        with gr.Accordion("Additional Details", open=True):
            domain_input = gr.Textbox(label="Professional Domain", placeholder="e.g., Product Management")
            years_exp_input = gr.Number(label="Years of Experience", minimum=0, maximum=50, value=0)

        gr.Examples(
            [
                [
                    "Product Manager for FinTech role requiring A/B testing and Agile.",
                    None, "Product Management", 2,
                ],
                [
                    "Senior Software Engineer, Python/Django, 5+ years, requiring AWS and CI/CD.",
                    None, "Software Engineering", 5,
                ],
                [
                    "Marketing Analyst focusing on SEO performance and Google Analytics reporting.",
                    None, "Digital Marketing", 3,
                ]
            ],
            inputs=[jd_input_text, jd_input_file, domain_input, years_exp_input],
        )

        # Outputs
        output_text = gr.HTML(elem_classes=["markdown-output"])
        download_file = gr.File(label="Download Feedback", visible=False)

        # Buttons
        with gr.Row():
            analyze_button = gr.Button("🔍 Analyze My Resume", scale=3)
            reset_button = gr.Button("🔄 Try Again (Reset)", scale=1)
            download_button_ui = gr.Button("⬇️ Download Feedback (.md)", scale=2, visible=False)

        # Reset outputs list
        reset_outputs = [
            jd_input_text, jd_input_file, resume_input_file,
            domain_input, years_exp_input, output_text, download_file,
        ]

        # Hook up analyze button
        analyze_button.click(
            fn=get_coaching_feedback,
            inputs=[jd_input_text, jd_input_file, resume_input_file, domain_input, years_exp_input],
            outputs=[output_text, download_file, download_button_ui],
            show_progress=True,
        )

        # Reset logic: clear inputs and hide download button
        def _reset_all():
            # Return None for each UI element to clear, and hide the download button
            return [None] * len(reset_outputs) + [gr.update(visible=False)]

        reset_button.click(
            fn=_reset_all,
            inputs=[],
            outputs=reset_outputs + [download_button_ui],
            queue=False
        )

        # Download button simply triggers the file component to be visible/downlaodable; keep as UI affordance
        # We keep it clickable with no extra effect (file is already created and bound to download_file)
        download_button_ui.click(
            fn=lambda: None,
            inputs=[],
            outputs=[],
            queue=False
        )

# Enable queue for scalability
demo.queue(max_size=3)

if __name__ == "__main__":
    demo.launch()
