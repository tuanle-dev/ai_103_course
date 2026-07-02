# =============================================================================
# INTENT CLASSIFICATION
# =============================================================================


def classify_intent(user_question):
    """
    Determine whether a question is simple or complex.
    Returns: "simple" or "complex"
    """
    question_lower = user_question.lower()

    # Complex patterns (require deeper reasoning)
    complex_patterns = [
        "compare",
        "contrast",
        "analyze",
        "evaluate",
        "why should",
        "what if",
        "how would",
        "plan",
        "strategy",
        "recommend",
        "suggest",
    ]

    for pattern in complex_patterns:
        if pattern in question_lower:
            return "complex"

    # Simple patterns (greetings and basic facts)
    simple_patterns = [
        "hello",
        "hi",
        "hey",
        "greetings",
        "what is",
        "who is",
        "when is",
        "where is",
        "how are you",
        "thanks",
        "thank you",
    ]

    for pattern in simple_patterns:
        if pattern in question_lower:
            return "simple"

    # Long questions (over 20 words) are likely complex
    if len(user_question.split()) > 20:
        return "complex"

    return "simple"


def classify_intent_via_slm(
    openai_client,
    slm_deployment_name,
    user_question,
    max_tokens,
    temperature,
    top_p,
):
    """
    Use the SLM (Phi-4) to classify intent as simple or complex.
    This is more accurate than keyword matching but adds latency and cost.
    Returns: "simple" or "complex"
    """
    system_instruction = """
    You classify questions or user prompts as either "simple" or "complex":

    A "simple" question is a straightforward query that can be answered with a fact, definition, or short response. Examples include greetings, basic facts, and simple instructions.

    A "complex" question requires deeper reasoning, analysis, comparison, planning, or multi-step thinking. Examples include "compare product A and B", "what if scenarios", and "recommend a strategy".

    Respond with only one word: "simple" or "complex".
    """

    system_message = {"role": "system", "content": system_instruction}
    user_message = {"role": "user", "content": user_question}
    messages = [system_message, user_message]

    response = openai_client.chat.completions.create(
        model=slm_deployment_name,
        messages=messages,
        max_tokens=max_tokens,  # Set the maximum length of the response
        temperature=temperature,  # Control the creativity of the response
        top_p=top_p,  # Control the diversity of the token selection
    )

    classification = response.choices[0].message.content.strip().lower()
    if classification not in ["simple", "complex"]:
        print(
            f"Unexpected classification result: '{classification}'. Defaulting to 'complex'."
        )
        return "complex"

    return classification
