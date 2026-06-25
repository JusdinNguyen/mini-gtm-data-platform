"""
Name: Justin Nguyen
File: models.py

Description:
This file defines the shared data structures used by the GTM outreach agent.

These classes do not make business decisions, connect to the database, or draft
emails. They only describe the structure of important objects used across the
agent, including evidence facts, drafted emails, and the final agent result.

An EvidenceFact always has a source, row_id, and text.
An EmailDraft always has a subject and body.
An AgentResult always has an outreach_angle, email, and evidence.
"""

from dataclasses import dataclass


@dataclass
class EvidenceFact:
    """
    Summary:
    EvidenceFact represents one fact that the agent found from the data. The
    source stores the table name, row_id stores the record identifier, and text
    stores the readable sentence shown as supporting evidence.

    @param source: the table or data source where the fact came from
    @param row_id: the identifier for the row connected to the fact
    @param text: the readable evidence sentence

    @return: an EvidenceFact object
    """
    source: str
    row_id: str
    text: str


@dataclass
class EmailDraft:
    """
    Summary:
    EmailDraft represents the outreach email created by the agent. The subject
    stores the email subject line, and body stores the full email body.

    @param subject: the email subject line
    @param body: the full email body

    @return: an EmailDraft object
    """
    subject: str
    body: str


@dataclass
class AgentResult:
    """
    Summary:
    AgentResult represents the final output of the agent. The outreach_angle
    stores the chosen strategy, email stores the drafted message, and evidence
    stores the facts used to support the email.

    @param outreach_angle: the outreach strategy selected by rules.py
    @param email: the drafted outreach email
    @param evidence: the evidence facts used to support the draft

    @return: an AgentResult object
    """
    outreach_angle: str
    email: EmailDraft
    evidence: list[EvidenceFact]