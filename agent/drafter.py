"""
Name: Justin Nguyen
File: drafter.py

Description:
This file creates the outreach email after rules.py chooses the outreach angle
and supporting evidence. The drafter does not query the database and does not
decide the business logic. It turns the selected outreach angle and evidence
into a readable email subject and body.

The drafter first tries to use an LLM when an OpenAI API key is available. If
there is no API key, it falls back to a deterministic template-based email.
This makes the agent more useful while still allowing it to run locally during
demos or grading.
"""

import os

from openai import OpenAI

from agent.models import EmailDraft, EvidenceFact


# evidence_to_text turns a list of EvidenceFact objects into readable bullet points.
# This gives the email drafter grounded facts from the data.
def evidence_to_text(evidence: list[EvidenceFact]) -> str:
    evidence_lines = []

    for fact in evidence:
        evidence_lines.append(f"- {fact.text}")

    return "\n".join(evidence_lines)


# get_tone_instruction returns a short tone description based on the outreach angle.
# The LLM uses this tone to make the generated email fit the situation.
def get_tone_instruction(outreach_angle: str) -> str:
    if outreach_angle == "open opportunity follow-up":
        return "direct and action-oriented"

    if outreach_angle == "expansion":
        return "confident and value-focused"

    if outreach_angle == "adoption support":
        return "helpful and supportive"

    if outreach_angle == "re-engagement":
        return "friendly and low-pressure"

    if outreach_angle == "warm prospect outreach":
        return "personalized and curious"

    return "professional and lightweight"


# parse_llm_email separates the LLM response into a subject and body.
# The prompt asks the LLM to return:
# Subject: ...
# Body: ...
def parse_llm_email(email_text: str) -> EmailDraft:
    default_subject = "Following up"
    default_body = email_text.strip()

    if "Subject:" not in email_text or "Body:" not in email_text:
        return EmailDraft(
            subject=default_subject,
            body=default_body,
        )

    subject_part, body_part = email_text.split("Body:", 1)
    subject = subject_part.replace("Subject:", "").strip()
    body = body_part.strip()

    return EmailDraft(
        subject=subject,
        body=body,
    )


# draft_email_with_llm uses an LLM to write a personalized outreach email.
# The business logic already happened in rules.py, so the LLM should only write
# from the outreach angle and evidence provided here.
def draft_email_with_llm(
    account_name: str,
    outreach_angle: str,
    evidence: list[EvidenceFact],
) -> EmailDraft:
    client = OpenAI()
    tone = get_tone_instruction(outreach_angle)
    evidence_text = evidence_to_text(evidence)

    prompt = f"""
You are writing a concise, human-sounding B2B sales email.

Account:
{account_name}

Outreach angle:
{outreach_angle}

Tone:
{tone}

Internal GTM evidence:
{evidence_text}

Write an email that sounds like a real account executive wrote it after reading
this account context. Use the evidence naturally, but do not paste the evidence
as bullet points.

Email structure:
- Start the body with a simple greeting, such as "Hi there,".
- Use short paragraphs with blank lines between them.
- Mention the opportunity stage or next step if it appears in the evidence.
- End with a clear and specific call to action.
- Sign off as Justin.

Important writing rules:
- Keep the email under 120 words.
- Do not mention internal ARR, account value, or revenue numbers.
- Do not invent facts, names, dates, metrics, or product details.
- Do not use the phrase "I wanted to follow up".
- Do not use the phrase "I thought it would be helpful".
- Do not use the sentence "Would you be open to a quick conversation this week?".
- Do not sound like a generic template.

Return the answer in exactly this format:

Subject: ...
Body: ...
"""

    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1")
    print(f"Using OpenAI model: {model_name}")

    response = client.responses.create(
        model=model_name,
        input=prompt,
    )

    return parse_llm_email(response.output_text)


# make_phrase_lower turns short CRM next-step text into a phrase that sounds
# natural inside an email sentence.
def make_phrase_lower(text: str) -> str:
    cleaned_text = text.strip()

    if len(cleaned_text) == 0:
        return cleaned_text

    next_step_lower = cleaned_text.lower()

    if next_step_lower == "reference call":
        return "a reference call"

    if next_step_lower == "send proposal":
        return "sending over the proposal"

    return cleaned_text[0].lower() + cleaned_text[1:]


# get_opportunity_details pulls the opportunity name, stage, and next step
# out of the structured opportunity evidence text.
def get_opportunity_details(evidence: list[EvidenceFact]) -> dict[str, str]:
    for fact in evidence:
        if fact.source != "marts.fct_opportunities":
            continue

        text = fact.text

        try:
            opportunity_name = text.split("called ", 1)[1].split(" in the ", 1)[0]
            stage = text.split(" in the ", 1)[1].split(" stage", 1)[0]
            next_step = text.split("The next step is: ", 1)[1].strip(".")

            return {
                "opportunity_name": opportunity_name,
                "stage": stage,
                "next_step": next_step,
            }

        except IndexError:
            return {
                "opportunity_name": "",
                "stage": "",
                "next_step": "",
            }

    return {
        "opportunity_name": "",
        "stage": "",
        "next_step": "",
    }


# draft_email_with_template creates a basic email without calling an LLM.
# This is the fallback version used when there is no API key.
def draft_email_with_template(
    account_name: str,
    outreach_angle: str,
    evidence: list[EvidenceFact],
) -> EmailDraft:
    subject = f"Following up with {account_name}"

    if outreach_angle == "open opportunity follow-up":
        opportunity_details = get_opportunity_details(evidence)

        opportunity_name = opportunity_details["opportunity_name"]
        stage = opportunity_details["stage"]
        next_step = opportunity_details["next_step"]
        next_step_phrase = make_phrase_lower(next_step)

        subject = f"Next steps for {account_name}"

        if stage != "" and next_step != "":
            body = (
                f"Hi there,\n\n"
                f"I wanted to follow up on the {opportunity_name} opportunity now that "
                f"it is in the {stage} stage.\n\n"
                f"Since the next step is {next_step_phrase}, I thought it would be helpful "
                f"to connect and make sure we are aligned on priorities, timing, and what "
                f"your team needs before moving forward.\n\n"
                f"Would you be open to a quick conversation this week?\n\n"
                f"Best,\n"
                f"Justin"
            )

        else:
            body = (
                f"Hi there,\n\n"
                f"I wanted to follow up on the opportunity with {account_name} and make sure "
                f"we are aligned on the next step.\n\n"
                f"Would you be open to a quick conversation this week?\n\n"
                f"Best,\n"
                f"Justin"
            )

    elif outreach_angle == "expansion":
        subject = f"Exploring broader usage at {account_name}"
        body = (
            f"Hi there,\n\n"
            f"I noticed {account_name} has been showing strong product engagement recently, "
            f"so I wanted to reach out.\n\n"
            f"Given that momentum, it may be worth exploring whether there are additional "
            f"teams or workflows that could benefit from broader usage.\n\n"
            f"Would you be open to a quick conversation this week?\n\n"
            f"Best,\n"
            f"Justin"
        )

    elif outreach_angle == "adoption support":
        subject = f"Helping {account_name} get more value"
        body = (
            f"Hi there,\n\n"
            f"I wanted to check in and see if there is anything we can do to help "
            f"{account_name} get more value from the product.\n\n"
            f"If there are any onboarding gaps, workflow questions, or adoption blockers, "
            f"I would be happy to help talk through them.\n\n"
            f"Would it be helpful to connect this week?\n\n"
            f"Best,\n"
            f"Justin"
        )

    elif outreach_angle == "re-engagement":
        subject = f"Checking in on {account_name}"
        body = (
            f"Hi there,\n\n"
            f"I wanted to check in because it looks like engagement from {account_name} "
            f"may have slowed recently.\n\n"
            f"If priorities have shifted or there are any blockers, I would be happy to "
            f"help figure out the best path forward.\n\n"
            f"Would you be open to a quick conversation?\n\n"
            f"Best,\n"
            f"Justin"
        )

    elif outreach_angle == "warm prospect outreach":
        subject = f"Following up with {account_name}"
        body = (
            f"Hi there,\n\n"
            f"I noticed some recent interest from {account_name} and wanted to reach out.\n\n"
            f"I would love to learn more about what your team is exploring and whether "
            f"there is a useful way we can help.\n\n"
            f"Would it be worth connecting briefly this week?\n\n"
            f"Best,\n"
            f"Justin"
        )

    else:
        subject = f"Connecting with {account_name}"
        body = (
            f"Hi there,\n\n"
            f"I wanted to reach out because {account_name} looks like a relevant account "
            f"to connect with.\n\n"
            f"I would be interested in learning more about your team’s current priorities "
            f"and whether there is a useful way we can help.\n\n"
            f"Would you be open to a quick conversation this week?\n\n"
            f"Best,\n"
            f"Justin"
        )

    return EmailDraft(
        subject=subject,
        body=body,
    )


# draft_email is the main function used by the rest of the agent.
# If an OPENAI_API_KEY exists, the agent uses the LLM to draft the email.
# If there is no API key, it falls back to the template version so the project
# can still run locally during demos or grading.
def draft_email(
    account_name: str,
    outreach_angle: str,
    evidence: list[EvidenceFact],
) -> EmailDraft:
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key is None:
        print("No OPENAI_API_KEY found, using template draft.")
        return draft_email_with_template(
            account_name,
            outreach_angle,
            evidence,
        )

    print("Using LLM draft.")
    return draft_email_with_llm(
        account_name,
        outreach_angle,
        evidence,
    )