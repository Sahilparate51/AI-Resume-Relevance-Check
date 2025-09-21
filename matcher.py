import os
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from thefuzz import fuzz
import spacy
from dotenv import load_dotenv

# Load environment variables for API keys
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# List of keywords for a more reliable check
KEYWORD_LIST = ["Python", "SQL", "Machine Learning", "Data Analysis", "Tableau", "Power BI", "R", "pandas", "numpy"]

# Load NLP model (download with 'python -m spacy download en_core_web_sm')
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print("Downloading spaCy model. This will happen only once.")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def extract_keywords_with_spacy(text):
    """A simple function to extract skills and keywords."""
    doc = nlp(text)
    keywords = [ent.text for ent in doc.ents if ent.label_ in ['SKILL', 'PROFESSION', 'LANGUAGE']]
    return list(set(keywords))

def hard_match_score(resume_text, jd_text):
    """Calculates a score based on keyword and skill matching."""
    jd_text_lower = jd_text.lower()
    resume_text_lower = resume_text.lower()
    
    found_jd_keywords = [kw.lower() for kw in KEYWORD_LIST if kw.lower() in jd_text_lower]
    found_resume_keywords = [kw.lower() for kw in KEYWORD_LIST if kw.lower() in resume_text_lower]
    
    match_count = 0
    missing_skills = []
    
    for kw in found_jd_keywords:
        if any(fuzz.partial_ratio(kw, res_kw) > 85 for res_kw in found_resume_keywords):
            match_count += 1
        else:
            missing_skills.append(kw)

    if not found_jd_keywords:
        return 0, []
        
    score = (match_count / len(found_jd_keywords)) * 100
    return score, missing_skills

def semantic_match_score(resume_text, jd_text):
    """Calculates a semantic similarity score using embeddings and FAISS."""
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_store = FAISS.from_texts([jd_text], embeddings)
        
        docs = vector_store.similarity_search_with_score(resume_text, k=1)
        score = docs[0][1] # Get the similarity score
        
        return score * 100
    except Exception as e:
        print(f"Error during semantic matching: {e}")
        return 0

def generate_llm_feedback(resume_text, jd_text, verdict, missing_skills):
    """Generates personalized feedback using an LLM."""
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.5)

        prompt_template = PromptTemplate.from_template(
            """
            You are an AI assistant providing feedback on a resume based on a job description.
            Here is the resume:
            <RESUME_TEXT>
            {resume_text}
            </RESUME_TEXT>
            
            Here is the job description:
            <JD_TEXT>
            {jd_text}
            </JD_TEXT>

            The resume has a verdict of "{verdict}" with the following missing skills: {missing_skills_str}.
            
            Provide constructive feedback to the student in a professional and encouraging tone.
            Focus on how they can improve their resume for this specific job.
            """
        )

        formatted_prompt = prompt_template.format(
            resume_text=resume_text,
            jd_text=jd_text,
            verdict=verdict,
            missing_skills_str=", ".join(missing_skills)
        )

        response = llm.invoke(formatted_prompt)
        return response.content
    except Exception as e:
        return f"Could not generate feedback. Check your API key. Error: {e}"

def calculate_final_score(hard_score, semantic_score):
    """Calculates a weighted final score."""
    final_score = (hard_score * 0.6) + (semantic_score * 0.4)
    return final_score

def get_verdict(score):
    """Assigns a verdict based on the final score."""
    if score >= 80:
        return "High suitability"
    elif score >= 50:
        return "Medium suitability"
    else:
        return "Low suitability"