"""HOOK PATTERNS — the hook-writer-sms translation (batch-2 skills,
2026-10-27).

The hook-writer library names nine proven hook patterns. This channel's
hook pools were strong but MONO-PATTERN: almost every hook is a bold
observation ("X isn't love — it's Y"). Pattern variety is retention
variety — a viewer who has heard three contrarian claims in a row stops
leaning in; a question hook after two statements re-opens them.

One new hook per concept, each written in a DIFFERENT pattern from the
library (labeled per entry), in the channel's plain-words voice:

  contrarian   challenges what the viewer already believes
  question     specific, non-obvious, personally addressed
  statistic    a real, hedged research finding (never invented —
               the channel's no-fabrication rule is the moat)
  empathy      opens on the viewer's felt pain, not the message
  before/after the transformation gap, with a timeframe
  negation     "Stop doing X" / "Stop calling it X"
  open loop    names the gap, delays the answer
  list preview promises discrete, countable value
  bold claim   a declarative that demands agreement or argument

Writing rules (asserted by scripts/test_batch2_skills.py):
  * 8-30 words — a hook is one breath, not a paragraph
  * never contains the concept's TERM (the reveal keeps its payoff)
  * never duplicates an existing pool entry (original or variant)
  * passes the story_engine safety audit (no banned framing)
  * no {a}/{b}/{day}/{time}/{place} slots (hooks are slot-free)
"""
from __future__ import annotations

# Each entry: (pattern, hook). The pattern label lives in code so the
# pool stays honest about its spread — the test asserts every pattern
# appears at least once and no pattern owns more than a third of the
# pool.
PATTERN_HOOKS: dict[str, list[tuple[str, str]]] = {
    "intermittent_reinforcement": [
        ("open loop",
         "There's a reason you can't stop checking for their reply — and it "
         "has nothing to do with how much you like them."),
    ],
    "anxious_avoidant_trap": [
        ("question",
         "Why does calm love feel boring to you, but chaos feels like "
         "chemistry?"),
    ],
    "attachment_styles": [
        ("before/after",
         "Six months of the right person can quietly rewrite what love felt "
         "like your whole life."),
    ],
    "anxious_attachment": [
        ("empathy",
         "If you've ever counted the minutes between texts, this one will "
         "feel uncomfortably familiar."),
    ],
    "avoidant_attachment": [
        ("negation",
         "Stop calling it commitment issues. Some people just wired "
         "distance into their idea of safety."),
    ],
    "secure_attachment": [
        ("contrarian",
         "If a relationship feels like relief instead of a rush, you may "
         "have finally gotten it right."),
    ],
    "self_expansion": [
        ("question",
         "Ever notice you miss who you were around them more than you "
         "miss them?"),
    ],
    "misattribution_arousal": [
        ("statistic",
         "Psychologists once sent men across a shaky bridge to prove a "
         "point — the fear itself got mislabeled as attraction."),
    ],
    "mere_exposure": [
        ("statistic",
         "Psychologists can make you like someone just by showing you "
         "their face more often. It's that simple."),
    ],
    "dopamine_novelty": [
        ("bold claim",
         "The butterflies you're chasing aren't a sign of love. They're a "
         "subscription you forgot you signed up for."),
    ],
    "oxytocin_bonding": [
        ("statistic",
         "Skin contact releases the same bonding chemical that glues "
         "parents to newborns — you were built to need it."),
    ],
    "cortisol_bonding": [
        ("negation",
         "Stop mistaking anxiety around someone for chemistry. Stress and "
         "attraction use the same doorway."),
    ],
    "heartbreak_brain": [
        ("empathy",
         "Missing them feels like coming down with something because, "
         "chemically, that's exactly what it is."),
    ],
    "rose_glasses": [
        ("before/after",
         "Six months in, you'll finally meet the actual person — your eyes "
         "had been finishing the portrait for you."),
    ],
    "negativity_bias": [
        ("question",
         "Why does one insult from them erase a month of compliments?"),
    ],
    "rejection_sensitivity": [
        ("open loop",
         "Your brain has a smoke detector for rejection — and somewhere "
         "along the way it got set to maximum."),
    ],
    "loss_aversion": [
        ("open loop",
         "There's a reason you want them back more after losing them than "
         "you ever wanted them while you had them."),
    ],
    "scarcity_effect": [
        ("question",
         "Why does everyone suddenly look better the moment they become "
         "unavailable?"),
    ],
    "ghosting_psych": [
        ("empathy",
         "You deserved two honest sentences. Instead you got a read "
         "receipt — and this is why."),
    ],
    "silence_amplification": [
        ("open loop",
         "Silence has a volume setting, and yours climbs every hour the "
         "reply doesn't come."),
    ],
    "on_off_cycles": [
        ("negation",
         "Stop calling it fate when you keep finding your way back. "
         "Cycles have gravity, not destiny."),
    ],
    "love_bombing": [
        ("contrarian",
         "Too much too soon isn't romance moving fast. It's a sales "
         "pitch with a deadline."),
    ],
    "breadcrumbing": [
        ("question",
         "If they only ever give you the minimum, why does the minimum "
         "feel like a jackpot?"),
    ],
    "mixed_signals_cost": [
        ("question",
         "What if the mixed signal isn't confusion at all — what if it's "
         "the clearest thing they've ever told you?"),
    ],
    "no_contact_effect": [
        ("question",
         "What actually changes in your brain after three weeks of not "
         "hearing from them?"),
    ],
    "rumination_loop": [
        ("question",
         "Why does replaying the ending feel like progress, when it "
         "quietly eats the whole afternoon?"),
    ],
    "unfinished_ending": [
        ("open loop",
         "Your brain keeps one browser tab open that no amount of time "
         "seems to close."),
    ],
    "nostalgia_filter": [
        ("before/after",
         "The memory gets warmer every month you're away — and none of "
         "that warmth was ever in the room."),
    ],
    "rebound_psych": [
        ("before/after",
         "The rebound feels like moving on. Six months later, you meet "
         "the same lesson wearing a new face."),
    ],
    "self_worth_reset": [
        ("empathy",
         "If you keep explaining away the bare minimum, the problem isn't "
         "your standards — it's your set point."),
    ],
    "closure_myth": [
        ("negation",
         "Stop waiting for the final conversation. You've been writing "
         "both sides of it for months."),
    ],
    "apology_languages": [
        ("bold claim",
         "An actual apology names what it did, owns it without excuses, "
         "and changes — anything less is theater."),
    ],
    "repair_attempts": [
        ("open loop",
         "After a fight, one small move predicts whether a couple lasts — "
         "and it takes under a minute."),
    ],
    "four_horsemen": [
        ("list preview",
         "Count the eye-rolls at dinner tonight. Psychologists did — and "
         "the number told them which marriages would survive."),
    ],
    "bids_for_connection": [
        ("question",
         "When was the last time someone asked for your attention without "
         "actually asking?"),
    ],
    "trust_equation": [
        ("open loop",
         "There's a reason you trust some people whose words are clumsy — "
         "and distrust some whose words are perfect."),
    ],
    "jealousy_signal": [
        ("negation",
         "Stop measuring love by how jealous you feel. Jealousy is a "
         "pointer — follow it to the fear underneath."),
    ],
    "boundaries_attract": [
        ("before/after",
         "Say one clear no and watch half your relationship problems sort "
         "themselves into people."),
    ],
    "green_flags": [
        ("empathy",
         "You've been trained to spot red flags so well that the good "
         "ones now look suspicious. Let's fix that."),
    ],
    "slow_love": [
        ("before/after",
         "Fast love shows you the highlight reel. Going slow introduces "
         "you to the actual human."),
    ],
}
