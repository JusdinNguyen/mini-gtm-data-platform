"""
Name: Justin Nguyen
File: models.py

Description: This file will define the shared data structures used by the agent.
These classes will not make business decisions or connect to the database. They will describe 
and show the model of the structures that will be used in the code like account context,
evidence facts, drafted emails, and the final agent result and report.

An EvidenceFact always has source, row_id, and text.
An EmailDraft always has subject and body.
An AgentResult always has outreach_angle, email, and evidence.

"""

# dataclass is a Python helper that creates simple data containers.
# It automatically builds the setup code needed to store class fields.

from dataclasses import dataclass




# EvidenceFact represents one fact that the agent found from the data.
# source stores the table name, row_id stores the record identifier, and
# text stores the readable sentence that can be shown as supporting evidence.

@dataclass

class EvidenceFact:

    source: str

    row_id: str

    text: str




# EmailDraft represents the outreach email created by the agent.
# subject stores the email subject line, and body stores the full email body.

@dataclass

class EmailDraft:

    subject: str

    body: str




# AgentResult represents the final output of the agent. outreach_angle stores
# the chosen strategy, email stores the drafted message, and evidence stores the
# facts used to support the email.

@dataclass

class AgentResult:

    outreach_angle: str

    email: EmailDraft

    evidence: list[EvidenceFact]