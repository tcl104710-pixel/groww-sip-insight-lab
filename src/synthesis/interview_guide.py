"""
SIP Insight Lab — Interview Validation Guide Generator (Task 4.8)
=================================================================
Generates 5–8 qualitative, non-leading interview validation questions
for each ranked opportunity. Used by User Researchers to test hypotheses
directly with real mutual fund investors.
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger("synthesis.interview_guide")


class InterviewGuideGenerator:
    """
    Generates tailored, empathetic, and rigorous user interview guides.
    """

    GUIDE_TEMPLATES = {
        "RC-01": [
            "Can you walk me through what happened when your SIP installment didn't go through as scheduled?",
            "Did you receive any prior notification or alert from Groww or your bank before the payment was missed? How clear was it?",
            "When the mandate failed or the SIP was cancelled after consecutive misses, what was your initial reaction?",
            "Did you intend to stop investing, or were you hoping the app would retry automatically or give you an option to pay manually?",
            "What specific assistance or automated grace period would have enabled you to keep your SIP active?",
            "Did you attempt to reach customer support or look on Reddit/YouTube for a solution? What was that experience like?",
        ],
        "RC-02": [
            "When you first wanted to adjust, pause, or check your SIP in the app, how easy or difficult was it to locate that option?",
            "Did you encounter any error codes, confusing payment gateway screens, or delays during the process?",
            "How clear was the explanation given for why a transaction could not be modified or completed?",
            "If you decided to stop or pause, was that your original plan or did the friction in the app cause you to give up?",
            "What changes to the interface or navigation would have made managing your ongoing SIP seamless?",
            "Have you tried managing similar automated investments on other apps? How did the experience compare?",
        ],
        "RC-03": [
            "When you first set up your SIP, what return or outcome were you expecting over your first 3 to 6 months?",
            "Where did that initial expectation come from (e.g., an in-app calculator, social media, a friend, or past experience)?",
            "When you logged in and saw your portfolio flat or in the negative, how did that make you feel about your strategy?",
            "Did you look for context within the app explaining why short-term market dips occur during long-term compounding?",
            "What kind of progress indicator or milestone tracking would help you stay committed even when returns fluctuate?",
            "What ultimately triggered your decision to pause or withdraw your investment?",
        ],
        "RC-04": [
            "Around the time you stopped or paused your SIP, what changes occurred in your monthly cash flow or financial commitments?",
            "Did you want to permanently cancel the investment, or did you simply need temporary breathing room for 1–2 months?",
            "If Groww offered a one-click 'Skip This Month' or 'Reduce Amount for 60 Days' feature, would you have used it instead of cancelling?",
            "How did having fixed automated debits impact your sense of financial security during unexpected expenses?",
            "Under what conditions or financial recovery milestone would you consider resuming your regular SIP?",
            "What features would make an investment platform feel supportive during temporary cash crunches?",
        ],
        "RC-05": [
            "What was the specific goal or milestone you had in mind when you started this mutual fund investment?",
            "When you stopped the SIP, was it because you successfully reached that goal, or did your target change?",
            "Did you redeem your funds to re-invest elsewhere (such as another fund, fixed deposit, or platform), or to make a planned purchase?",
            "How did your experience with Groww influence where you chose to allocate your money next?",
            "What would make it easier to transition a completed SIP directly into your next long-term financial objective on the same platform?",
            "Looking back, how satisfied were you with the disciplined habit you built over the investment period?",
        ],
        "RC-06": [
            "When you first started investing, how confident did you feel about concepts like NAV, units, and rupee-cost averaging?",
            "When markets fell and your NAV went down, did it feel like you were losing money permanently or buying units at a discount?",
            "Did you search for educational explanations within the app, or look externally (e.g. YouTube, Google, Reddit)?",
            "What kind of visual or bite-sized explanation would have made you feel secure during market corrections?",
            "What role did daily portfolio checking play in your decision to exit?",
            "How could the platform help first-time investors understand that volatility is normal in equity mutual funds?",
        ],
        "RC-07": [
            "What discussions, recommendations, or social media videos influenced your decision to start or stop this SIP?",
            "When finfluencers or peers suggested changing strategies or stopping investments, how did you verify that advice?",
            "Did you feel peer pressure or social comparison when others around you talked about high-return trading or quick profits?",
            "What trusted benchmark comparison or transparent data could Groww have shown to help you evaluate the advice objectively?",
            "Who do you trust most when making decisions about your mutual fund portfolio?",
            "What would help you feel confident staying the course despite noisy market commentary?",
        ],
        "RC-99": [
            "Can you tell us about your overall experience investing via SIP on Groww?",
            "What was the most challenging or confusing moment during your investment journey?",
            "Was your decision to discontinue deliberate, or did an unexpected issue get in the way?",
            "What information or feature was missing that could have helped you stay invested?",
            "If you could change one thing about how SIPs work on the app, what would it be?",
        ],
    }

    def generate_guide(
        self,
        root_cause: str,
        opportunity_label: Optional[str] = None,
        custom_prompts: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Generate 5–8 targeted, non-leading questions for the given root cause.
        """
        questions = self.GUIDE_TEMPLATES.get(root_cause, self.GUIDE_TEMPLATES["RC-99"])

        if custom_prompts:
            combined = questions + custom_prompts
            return combined[:8]

        return list(questions)
