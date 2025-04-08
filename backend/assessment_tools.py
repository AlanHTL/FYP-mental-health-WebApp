"""
Mental health assessment tools and their scoring functions.
This module contains standardized assessment tools like DASS-21, GAD-7, PHQ-9, etc.
Each assessment has a function to calculate the result based on patient responses.
"""

from typing import Dict, List, Any, Tuple

# DASS-21 Assessment Tool
DASS21_QUESTIONS = [
    "I found it hard to wind down",  # Stress
    "I was aware of dryness of my mouth",  # Anxiety
    "I couldn't seem to experience any positive feeling at all",  # Depression
    "I experienced breathing difficulty",  # Anxiety
    "I found it difficult to work up the initiative to do things",  # Depression
    "I tended to over-react to situations",  # Stress
    "I experienced trembling (e.g., in the hands)",  # Anxiety
    "I felt that I was using a lot of nervous energy",  # Stress
    "I was worried about situations in which I might panic and make a fool of myself",  # Anxiety
    "I felt that I had nothing to look forward to",  # Depression
    "I found myself getting agitated",  # Stress
    "I found it difficult to relax",  # Stress
    "I felt down-hearted and blue",  # Depression
    "I was intolerant of anything that kept me from getting on with what I was doing",  # Stress
    "I felt I was close to panic",  # Anxiety
    "I was unable to become enthusiastic about anything",  # Depression
    "I felt I wasn't worth much as a person",  # Depression
    "I felt that I was rather touchy",  # Stress
    "I was aware of the action of my heart in the absence of physical exertion",  # Anxiety
    "I felt scared without any good reason",  # Anxiety
    "I felt that life was meaningless"  # Depression
]

DASS21_SEVERITY = {
    "Depression": {
        "Normal": (0, 9),
        "Mild": (10, 13),
        "Moderate": (14, 20),
        "Severe": (21, 27),
        "Extremely Severe": (28, 42)
    },
    "Anxiety": {
        "Normal": (0, 7),
        "Mild": (8, 9),
        "Moderate": (10, 14),
        "Severe": (15, 19),
        "Extremely Severe": (20, 42)
    },
    "Stress": {
        "Normal": (0, 14),
        "Mild": (15, 18),
        "Moderate": (19, 25),
        "Severe": (26, 33),
        "Extremely Severe": (34, 42)
    }
}

def calculate_dass21_scores(responses: List[int]) -> Dict[str, Any]:
    """
    Calculate DASS-21 scores from patient responses.
    
    Args:
        responses: List of integers (0-3) corresponding to responses
                  0 = Did not apply to me at all
                  1 = Applied to me to some degree, or some of the time
                  2 = Applied to me to a considerable degree, or a good part of time
                  3 = Applied to me very much, or most of the time
    
    Returns:
        Dict containing scores and severity ratings for depression, anxiety, and stress
    """
    if len(responses) != 21:
        raise ValueError("DASS-21 requires exactly 21 responses")
    
    # Indices for each scale (0-indexed)
    depression_indices = [2, 4, 9, 12, 15, 16, 20]
    anxiety_indices = [1, 3, 6, 8, 14, 18, 19]
    stress_indices = [0, 5, 7, 10, 11, 13, 17]
    
    # Calculate raw scores
    depression_score = sum(responses[i] for i in depression_indices) * 2
    anxiety_score = sum(responses[i] for i in anxiety_indices) * 2
    stress_score = sum(responses[i] for i in stress_indices) * 2
    
    # Determine severity for each scale
    def get_severity(score: int, scale: str) -> str:
        for severity, (lower, upper) in DASS21_SEVERITY[scale].items():
            if lower <= score <= upper:
                return severity
        return "Unknown"
    
    depression_severity = get_severity(depression_score, "Depression")
    anxiety_severity = get_severity(anxiety_score, "Anxiety")
    stress_severity = get_severity(stress_score, "Stress")
    
    return {
        "depression": {
            "score": depression_score,
            "severity": depression_severity
        },
        "anxiety": {
            "score": anxiety_score,
            "severity": anxiety_severity
        },
        "stress": {
            "score": stress_score,
            "severity": stress_severity
        },
        "total_score": depression_score + anxiety_score + stress_score
    }

# GAD-7 Assessment Tool (Generalized Anxiety Disorder)
GAD7_QUESTIONS = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it's hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid as if something awful might happen"
]

GAD7_SEVERITY = {
    "Minimal": (0, 4),
    "Mild": (5, 9),
    "Moderate": (10, 14),
    "Severe": (15, 21)
}

def calculate_gad7_score(responses: List[int]) -> Dict[str, Any]:
    """
    Calculate GAD-7 score from patient responses.
    
    Args:
        responses: List of integers (0-3) corresponding to responses
                  0 = Not at all
                  1 = Several days
                  2 = More than half the days
                  3 = Nearly every day
    
    Returns:
        Dict containing total score and severity rating
    """
    if len(responses) != 7:
        raise ValueError("GAD-7 requires exactly 7 responses")
    
    total_score = sum(responses)
    
    # Determine severity
    severity = "Unknown"
    for sev, (lower, upper) in GAD7_SEVERITY.items():
        if lower <= total_score <= upper:
            severity = sev
    
    return {
        "score": total_score,
        "severity": severity
    }

# PHQ-9 Assessment Tool (Patient Health Questionnaire for Depression)
PHQ9_QUESTIONS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself - or that you are a failure or have let yourself or your family down",
    "Trouble concentrating on things, such as reading the newspaper or watching television",
    "Moving or speaking so slowly that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual",
    "Thoughts that you would be better off dead or of hurting yourself in some way"
]

PHQ9_SEVERITY = {
    "None-Minimal": (0, 4),
    "Mild": (5, 9),
    "Moderate": (10, 14),
    "Moderately Severe": (15, 19),
    "Severe": (20, 27)
}

def calculate_phq9_score(responses: List[int]) -> Dict[str, Any]:
    """
    Calculate PHQ-9 score from patient responses.
    
    Args:
        responses: List of integers (0-3) corresponding to responses
                  0 = Not at all
                  1 = Several days
                  2 = More than half the days
                  3 = Nearly every day
    
    Returns:
        Dict containing total score and severity rating
    """
    if len(responses) != 9:
        raise ValueError("PHQ-9 requires exactly 9 responses")
    
    total_score = sum(responses)
    
    # Determine severity
    severity = "Unknown"
    for sev, (lower, upper) in PHQ9_SEVERITY.items():
        if lower <= total_score <= upper:
            severity = sev
    
    return {
        "score": total_score,
        "severity": severity,
        "suicide_risk": responses[8] > 0  # Check if the last question has a non-zero response
    }

# Assessment database
ASSESSMENTS = {
    "DASS-21": {
        "name": "Depression Anxiety Stress Scales",
        "questions": DASS21_QUESTIONS,
        "options": [
            "Did not apply to me at all",
            "Applied to me to some degree, or some of the time",
            "Applied to me to a considerable degree, or a good part of time",
            "Applied to me very much, or most of the time"
        ],
        "scoring_function": calculate_dass21_scores,
        "description": "The DASS-21 is a set of three self-report scales designed to measure the emotional states of depression, anxiety and stress."
    },
    "GAD-7": {
        "name": "Generalized Anxiety Disorder Assessment",
        "questions": GAD7_QUESTIONS,
        "options": [
            "Not at all",
            "Several days",
            "More than half the days",
            "Nearly every day"
        ],
        "scoring_function": calculate_gad7_score,
        "description": "The GAD-7 is a self-reported questionnaire for screening and severity measuring of generalized anxiety disorder."
    },
    "PHQ-9": {
        "name": "Patient Health Questionnaire",
        "questions": PHQ9_QUESTIONS,
        "options": [
            "Not at all",
            "Several days",
            "More than half the days",
            "Nearly every day"
        ],
        "scoring_function": calculate_phq9_score,
        "description": "The PHQ-9 is a multipurpose instrument for screening, diagnosing, monitoring and measuring the severity of depression."
    }
}

def get_assessment(assessment_id: str) -> Dict[str, Any]:
    """
    Get assessment details by ID.
    
    Args:
        assessment_id: The ID of the assessment to retrieve
    
    Returns:
        Assessment details including questions, options, and scoring function
    """
    if assessment_id not in ASSESSMENTS:
        raise ValueError(f"Assessment {assessment_id} not found")
    
    return ASSESSMENTS[assessment_id]

def get_assessment_list() -> List[Dict[str, Any]]:
    """
    Get a list of all available assessments.
    
    Returns:
        List of assessment details excluding the scoring functions
    """
    result = []
    for assessment_id, details in ASSESSMENTS.items():
        assessment_info = {k: v for k, v in details.items() if k != 'scoring_function'}
        assessment_info['id'] = assessment_id
        result.append(assessment_info)
    
    return result

def calculate_assessment_result(assessment_id: str, responses: List[int]) -> Dict[str, Any]:
    """
    Calculate the result of an assessment based on the responses.
    
    Args:
        assessment_id: The ID of the assessment
        responses: List of integer responses corresponding to the assessment questions
    
    Returns:
        Assessment results including scores and severity ratings
    """
    assessment = get_assessment(assessment_id)
    scoring_function = assessment['scoring_function']
    
    return scoring_function(responses) 