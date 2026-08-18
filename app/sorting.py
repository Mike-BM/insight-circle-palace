def assign_path(q5_answer: str) -> str:
    """
    Assigns the user to a path based on their answer to Question 5.
    Defaults to Explorer Path for "not sure" or unrecognized answers.
    """
    ans = q5_answer.lower()
    
    if "discipline" in ans or "structure" in ans or "builder" in ans:
        return "Builder Path"
    elif "emotional" in ans or "mindset" in ans or "healing" in ans or "reflector" in ans:
        return "Reflector Path"
    elif "guidance" in ans or "mentorship" in ans or "direction" in ans:
        return "Mentorship Path"
    
    # Defaults to Explorer for "self-discovery", "not sure", or anything else
    return "Explorer Path"
