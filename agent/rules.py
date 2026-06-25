"""
Name: Justin Nguyen
File: rules.py

Description:
This file decides the outreach strategy for a given account based on the
business context gathered in context.py. It does not query the database and it
does not write the final email. Instead, it looks at account context,
opportunities, calls, funnel activity, and product usage to choose the most
useful outreach angle.

The rules should stay simple and explainable. The goal is to identify the
strongest reason to contact the account right now, not to use every column from
every table.

Functions in this file:
- has_open_opportunity: checks whether the account has an active sales deal
- get_latest_product_usage: gets the most recent usage record for the account
- choose_outreach_angle: chooses the best outreach angle based on priority rules
- build_evidence: turns selected context into readable evidence facts
- apply_rules: returns the chosen angle and evidence for the email drafter
"""

from typing import Any

from agent.models import EvidenceFact


WARM_LEAD_SCORE_THRESHOLD = 75


def has_open_opportunity(opportunities: list[dict[str, Any]]) -> bool:
    """
    Summary:
    has_open_opportunity checks whether the account has an active opportunity.
    An opportunity is considered open when the is_closed field is False.

    @param opportunities: a list of opportunity rows connected to the account

    @return: True if the account has an open opportunity, otherwise False
    """
    for opportunity in opportunities:
        is_closed = opportunity.get("is_closed")

        if is_closed is False:
            return True

    return False


def get_latest_product_usage(product_usage: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Summary:
    get_latest_product_usage returns the most recent product usage row. If
    there is no product usage data, it returns None. The max function returns
    the usage row with the biggest usage month.

    @param product_usage: a list of product usage rows connected to the account

    @return: the latest product usage row, or None if no usage data exists
    """
    if len(product_usage) == 0:
        return None

    return max(
        product_usage,
        key=lambda usage: usage.get("usage_month"),
    )


def choose_outreach_angle(account_context: dict[str, Any]) -> str:
    """
    Summary:
    choose_outreach_angle chooses the best outreach angle using simple priority
    rules. The goal is to pick the strongest reason to contact the account
    right now.

    Priority order:
    1. Open opportunity follow-up
    2. Expansion
    3. Re-engagement
    4. Adoption support
    5. Warm prospect outreach
    6. General account outreach

    @param account_context: the full account context built by context.py

    @return: the selected outreach angle
    """
    opportunities = account_context.get("opportunities", [])
    product_usage = account_context.get("product_usage", [])
    funnel_activity = account_context.get("funnel_activity", [])

    latest_usage = get_latest_product_usage(product_usage)

    if has_open_opportunity(opportunities):
        return "open opportunity follow-up"

    if latest_usage is not None:
        engagement_tier = latest_usage.get("engagement_tier")
        usage_trend_pct = latest_usage.get("usage_trend_pct")

        if isinstance(engagement_tier, str):
            engagement_tier = engagement_tier.lower()

        if engagement_tier == "high":
            return "expansion"

        if usage_trend_pct is not None and usage_trend_pct < 0:
            return "re-engagement"

        if engagement_tier == "low":
            return "adoption support"

    for lead in funnel_activity:
        lead_score = lead.get("lead_score")

        if lead_score is not None and lead_score >= WARM_LEAD_SCORE_THRESHOLD:
            return "warm prospect outreach"

    return "general account outreach"


def build_evidence(
    account_context: dict[str, Any],
    outreach_angle: str,
) -> list[EvidenceFact]:
    """
    Summary:
    build_evidence turns selected account context into readable evidence facts.
    These facts explain why the agent chose a certain outreach angle.

    @param account_context: the full account context built by context.py
    @param outreach_angle: the outreach angle selected by choose_outreach_angle

    @return: a list of EvidenceFact objects used by the email drafter
    """
    evidence = []

    account = account_context.get("account")
    opportunities = account_context.get("opportunities", [])
    product_usage = account_context.get("product_usage", [])
    funnel_activity = account_context.get("funnel_activity", [])

    if account is not None:
        evidence.append(
            EvidenceFact(
                source="marts.dim_accounts",
                row_id=str(account.get("account_id")),
                text=(
                    f"{account.get('name')} is a {account.get('segment')} "
                    f"account in {account.get('industry')} with "
                    f"${account.get('arr')} ARR."
                ),
            )
        )

    if outreach_angle == "open opportunity follow-up":
        for opportunity in opportunities:
            if opportunity.get("is_closed") is False:
                evidence.append(
                    EvidenceFact(
                        source="marts.fct_opportunities",
                        row_id=str(opportunity.get("opp_id")),
                        text=(
                            f"There is an open opportunity called "
                            f"{opportunity.get('opp_name')} in the "
                            f"{opportunity.get('stage')} stage worth "
                            f"${opportunity.get('amount')}. "
                            f"The next step is: {opportunity.get('next_step')}."
                        ),
                    )
                )
                break

    latest_usage = get_latest_product_usage(product_usage)

    if latest_usage is not None and outreach_angle in [
        "expansion",
        "adoption support",
        "re-engagement",
    ]:
        evidence.append(
            EvidenceFact(
                source="marts.fct_product_usage",
                row_id=str(latest_usage.get("account_id")),
                text=(
                    f"The latest product usage month is "
                    f"{latest_usage.get('usage_month')} with "
                    f"{latest_usage.get('active_users')} active users, "
                    f"{latest_usage.get('total_events')} total events, and "
                    f"{latest_usage.get('engagement_tier')} engagement."
                ),
            )
        )

    if outreach_angle == "warm prospect outreach":
        for lead in funnel_activity:
            lead_score = lead.get("lead_score")

            if lead_score is not None and lead_score >= WARM_LEAD_SCORE_THRESHOLD:
                evidence.append(
                    EvidenceFact(
                        source="marts.fct_funnel",
                        row_id=str(lead.get("lead_id")),
                        text=(
                            f"A related lead has a lead score of "
                            f"{lead.get('lead_score')} from "
                            f"{lead.get('lead_source')}."
                        ),
                    )
                )
                break

    return evidence


def apply_rules(account_context: dict[str, Any]) -> dict[str, Any]:
    """
    Summary:
    apply_rules runs the full rules step. It chooses the outreach angle and
    builds the supporting evidence.

    @param account_context: the full account context built by context.py

    @return: a dictionary containing the outreach angle and evidence
    """
    outreach_angle = choose_outreach_angle(account_context)
    evidence = build_evidence(account_context, outreach_angle)

    return {
        "outreach_angle": outreach_angle,
        "evidence": evidence,
    }