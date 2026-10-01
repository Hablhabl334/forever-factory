"""The love-psychology content banks — the machine's knowledge.

Every long video and every Short is assembled from these atoms by the
generative grammar in story_engine.py. The banks are large on purpose:
a daily factory burns 9 concepts a day (8 long segments + 4 shorts
drawn from the day's concepts), so the space must feel fresh for
years. Combination space (orderings, subsets, framings, hooks) is in
the tens of billions — the no-repeat hash ledger guards the rest.

Tone rules baked into the writing:
  * real psychology, plain language — name the mechanism, then show it
  * relatable two-person scenarios (the "that's literally me" moment)
  * healthy framing: awareness and self-respect, never manipulation
  * no diagnosis, no absolutes, no medical claims (audited in engine)
"""
from __future__ import annotations

SERIES_NAME = "Psychology of Love"
CTA_LINE = "Subscribe for more tips like this."

# ── topics: the daily umbrella (video title + Shorts top band) ──────
# id -> (long title phrase, shorts band label, opener hook, [concept keys])
TOPICS: dict[str, dict] = {
    "attraction": {
        "title": "Why We Fall for Certain People",
        "band": "psychology of attraction",
        "opener": "Attraction feels like magic, but it follows rules — and once you see them, you can never unsee them.",
        "concepts": ["misattribution_arousal", "mere_exposure", "dopamine_novelty",
                     "scarcity_effect", "self_expansion", "rose_glasses",
                     "oxytocin_bonding", "attachment_styles"],
    },
    "attachment": {
        "title": "Attachment Styles, Finally Explained",
        "band": "psychology of attachment",
        "opener": "The way you love was shaped before you could even talk — here is how to spot it, and how to steady it.",
        "concepts": ["attachment_styles", "anxious_attachment", "avoidant_attachment",
                     "secure_attachment", "anxious_avoidant_trap", "bids_for_connection",
                     "repair_attempts", "self_worth_reset"],
    },
    "breakup": {
        "title": "How to Get Over a Breakup",
        "band": "psychology of breakups",
        "opener": "Heartbreak is not weakness — your brain is going through something very real, and there is a way out.",
        "concepts": ["heartbreak_brain", "cortisol_bonding", "rumination_loop",
                     "unfinished_ending", "nostalgia_filter", "no_contact_effect",
                     "closure_myth", "self_worth_reset"],
    },
    "ghosting": {
        "title": "The Psychology of Ghosting",
        "band": "psychology of ghosting",
        "opener": "The silence says more about them than it ever said about you — here's the science of why people disappear.",
        "concepts": ["ghosting_psych", "silence_amplification", "rejection_sensitivity",
                     "breadcrumbing", "mixed_signals_cost", "loss_aversion",
                     "intermittent_reinforcement", "self_worth_reset"],
    },
    "mixed_signals": {
        "title": "Mixed Signals, Decoded",
        "band": "psychology of mixed signals",
        "opener": "Hot then cold, present then gone — mixed signals aren't confusion, they're information. Here's how to read them.",
        "concepts": ["mixed_signals_cost", "breadcrumbing", "intermittent_reinforcement",
                     "scarcity_effect", "avoidant_attachment", "rejection_sensitivity",
                     "silence_amplification", "boundaries_attract"],
    },
    "red_flags": {
        "title": "Red Flags People Ignore",
        "band": "psychology of red flags",
        "opener": "Red flags rarely look red in the beginning — they look like butterflies. Here's what the butterflies hide.",
        "concepts": ["love_bombing", "four_horsemen", "on_off_cycles",
                     "breadcrumbing", "negativity_bias", "jealousy_signal",
                     "mixed_signals_cost", "boundaries_attract"],
    },
    "green_flags": {
        "title": "Green Flags Everyone Misses",
        "band": "psychology of green flags",
        "opener": "Green flags are quiet — they never announce themselves. But once you can spot them, you'll never settle again.",
        "concepts": ["green_flags", "secure_attachment", "repair_attempts",
                     "bids_for_connection", "trust_equation", "boundaries_attract",
                     "slow_love", "apology_languages"],
    },
    "love_bombing": {
        "title": "The Love Bombing Trap",
        "band": "psychology of love bombing",
        "opener": "Too much too soon is not a compliment — it's a pattern. Here's how intensity gets mistaken for destiny.",
        "concepts": ["love_bombing", "dopamine_novelty", "intermittent_reinforcement",
                     "on_off_cycles", "scarcity_effect", "rose_glasses",
                     "negativity_bias", "boundaries_attract"],
    },
    "jealousy": {
        "title": "Why We Get Jealous",
        "band": "psychology of jealousy",
        "opener": "Jealousy is not proof of love — it's a security system with a broken alarm. Let's look at what it's actually guarding.",
        "concepts": ["jealousy_signal", "anxious_attachment", "rejection_sensitivity",
                     "negativity_bias", "on_off_cycles", "attachment_styles",
                     "boundaries_attract", "secure_attachment"],
    },
    "trust": {
        "title": "How Trust Is Actually Built",
        "band": "psychology of trust",
        "opener": "Trust isn't a grand gesture — it's a boring pattern repeated a thousand times. Here's how it really compounds.",
        "concepts": ["trust_equation", "bids_for_connection", "repair_attempts",
                     "green_flags", "slow_love", "secure_attachment",
                     "apology_languages", "four_horsemen"],
    },
    "communication": {
        "title": "Communication That Actually Works",
        "band": "psychology of communication",
        "opener": "Most couples don't have a communication problem — they have a translation problem. Here's how to fix the translator.",
        "concepts": ["bids_for_connection", "four_horsemen", "repair_attempts",
                     "apology_languages", "negativity_bias", "anxious_avoidant_trap",
                     "jealousy_signal", "trust_equation"],
    },
    "arguments": {
        "title": "Why Couples Really Fight",
        "band": "psychology of arguments",
        "opener": "The argument is never about the dishes. Here's what the fight is actually protecting.",
        "concepts": ["four_horsemen", "repair_attempts", "negativity_bias",
                     "anxious_avoidant_trap", "bids_for_connection", "apology_languages",
                     "jealousy_signal", "attachment_styles"],
    },
    "apology": {
        "title": "The Science of a Real Apology",
        "band": "psychology of apologies",
        "opener": "'I'm sorry you feel that way' is not an apology — it's an escape hatch. Real repair follows a recipe.",
        "concepts": ["apology_languages", "repair_attempts", "four_horsemen",
                     "trust_equation", "negativity_bias", "green_flags",
                     "secure_attachment", "bids_for_connection"],
    },
    "love_languages": {
        "title": "Love Languages, Without the Hype",
        "band": "psychology of love languages",
        "opener": "You can love someone fluently and still speak the wrong language. Here's why the translation matters more than the feeling.",
        "concepts": ["bids_for_connection", "self_expansion", "green_flags",
                     "apology_languages", "secure_attachment", "repair_attempts",
                     "trust_equation", "slow_love"],
    },
    "chemistry": {
        "title": "Chemistry vs Compatibility",
        "band": "chemistry vs compatibility",
        "opener": "Chemistry gets you in the door. Compatibility decides whether you'll still be inside in five years. Here's the difference.",
        "concepts": ["dopamine_novelty", "misattribution_arousal", "rose_glasses",
                     "slow_love", "self_expansion", "scarcity_effect",
                     "green_flags", "secure_attachment"],
    },
    "self_love": {
        "title": "Self-Love Before Love",
        "band": "psychology of self love",
        "opener": "You will accept the love you think you deserve — so the bar you set for yourself becomes the bar for everyone else.",
        "concepts": ["self_worth_reset", "boundaries_attract", "secure_attachment",
                     "anxious_attachment", "rejection_sensitivity", "green_flags",
                     "attachment_styles", "slow_love"],
    },
    "boundaries": {
        "title": "Boundaries in Love",
        "band": "psychology of boundaries",
        "opener": "A boundary isn't a wall — it's a filter. And the people it filters out were never going to stay anyway.",
        "concepts": ["boundaries_attract", "self_worth_reset", "green_flags",
                     "on_off_cycles", "mixed_signals_cost", "secure_attachment",
                     "jealousy_signal", "trust_equation"],
    },
    "ex_thinking": {
        "title": "Why You Can't Stop Thinking About Your Ex",
        "band": "why you can't forget your ex",
        "opener": "If they live in your head rent-free, it's not because they earned it — it's because your brain kept the file open.",
        "concepts": ["rumination_loop", "unfinished_ending", "nostalgia_filter",
                     "intermittent_reinforcement", "cortisol_bonding", "loss_aversion",
                     "heartbreak_brain", "no_contact_effect"],
    },
    "no_contact": {
        "title": "Does No Contact Actually Work?",
        "band": "psychology of no contact",
        "opener": "Silence isn't a game — it's a reset button for a nervous system that forgot how to be calm without them.",
        "concepts": ["no_contact_effect", "cortisol_bonding", "rumination_loop",
                     "intermittent_reinforcement", "nostalgia_filter", "unfinished_ending",
                     "self_worth_reset", "closure_myth"],
    },
    "moving_on": {
        "title": "Dating After Heartbreak",
        "band": "psychology of moving on",
        "opener": "Ready is not a feeling you wait for — it's a skill you rebuild. Here's what the research says about starting again.",
        "concepts": ["rebound_psych", "self_worth_reset", "nostalgia_filter",
                     "slow_love", "green_flags", "attachment_styles",
                     "misattribution_arousal", "boundaries_attract"],
    },
    "long_distance": {
        "title": "The Psychology of Long Distance",
        "band": "psychology of long distance",
        "opener": "Distance doesn't kill relationships — ambiguity does. Here's what keeps far-apart love alive.",
        "concepts": ["bids_for_connection", "trust_equation", "silence_amplification",
                     "attachment_styles", "rejection_sensitivity", "repair_attempts",
                     "slow_love", "green_flags"],
    },
    "lasting": {
        "title": "What Keeps Love Alive",
        "band": "psychology of lasting love",
        "opener": "Passion fades on schedule — but attraction was never the engine. Here's what actually drives long love.",
        "concepts": ["slow_love", "self_expansion", "bids_for_connection",
                     "repair_attempts", "oxytocin_bonding", "green_flags",
                     "trust_equation", "dopamine_novelty"],
    },
    "secure": {
        "title": "Becoming Emotionally Secure",
        "band": "becoming secure in love",
        "opener": "Security isn't something you find in a person — it's something you build in a nervous system. Here's the blueprint.",
        "concepts": ["secure_attachment", "self_worth_reset", "boundaries_attract",
                     "repair_attempts", "anxious_avoidant_trap", "green_flags",
                     "rumination_loop", "slow_love"],
    },
    "heartache_science": {
        "title": "What Heartbreak Does to Your Brain",
        "band": "psychology of heartbreak",
        "opener": "Heartbreak lights up the same brain regions as physical pain — that's not poetry, that's a scan. Here's what's happening to you.",
        "concepts": ["heartbreak_brain", "cortisol_bonding", "rumination_loop",
                     "loss_aversion", "unfinished_ending", "no_contact_effect",
                     "nostalgia_filter", "self_worth_reset"],
    },
}

# ── the concepts: one bank entry = one long segment + one Short ─────
# scene: (emotion_a, pose_a, emotion_b, pose_b) for the flat couple art
CONCEPTS: dict[str, dict] = {
    "intermittent_reinforcement": {
        "term": "intermittent reinforcement",
        "hook": "If they only reply when you're about to give up, that's not bad luck — that's a slot machine.",
        "explain": (
            "Psychologists call this intermittent reinforcement, and it's the same schedule that keeps people glued to slot machines. "
            "When affection arrives unpredictably, your brain releases more dopamine than it would for affection that arrives reliably. "
            "The uncertainty itself becomes the hook, because a maybe demands constant attention. "
            "That's why an inconsistent person can feel more intense than a consistent one."
        ),
        "example": (
            "You text on Monday, they answer on Thursday — warm, funny, perfect. Then silence again for a week. "
            "You're not addicted to them; you're addicted to the unpredictability, and the relief when the coin finally drops."
        ),
        "takeaway": (
            "Consistency is the real green flag. If calm feels boring to you right now, that's a sign about your nervous system, not about the person offering it."
        ),
        "scene": ("anxious", "phone", "detached", "phone"),
    },
    "anxious_avoidant_trap": {
        "term": "the anxious-avoidant trap",
        "hook": "The person who chases and the person who retreats always find each other — that's not chemistry, it's a circuit.",
        "explain": (
            "Psychologists call this the anxious-avoidant trap. One partner seeks closeness to feel safe, the other seeks space to feel safe. "
            "Each one's coping style triggers the other's fear, so the distance keeps resetting itself. "
            "The pursuit feels like passion at first, but it's actually two alarm systems taking turns. "
            "Breaking the loop means one person has to hold steady while the other practices trusting."
        ),
        "example": (
            "The closer you reach, the further they step. The further they step, the harder you chase. "
            "Neither of you is the villain — you're just running opposite rescue missions for the same fire."
        ),
        "takeaway": (
            "Notice the pattern, not the person. The trap loosens the moment one of you says out loud: 'I need closeness' or 'I need space' — calmly, without blame."
        ),
        "scene": ("anxious", "stand", "detached", "away"),
    },
    "attachment_styles": {
        "term": "attachment styles",
        "hook": "The way you love was decided before you could talk — and it's running quietly in the background of every relationship.",
        "explain": (
            "Attachment research splits love habits into four broad styles: secure, anxious, avoidant, and fearful. "
            "They're not personalities, they're strategies your younger self built to stay close to the people it depended on. "
            "Your style decides what feels normal: closeness, or distance, or a nervous mix of both. "
            "And here's the hopeful part — styles can change with safe people and honest practice."
        ),
        "example": (
            "One person hears 'I need space' and thinks, fine. Another hears the same words and feels abandoned. "
            "Same sentence, two different childhoods behind the ears."
        ),
        "takeaway": (
            "Learn your default before you blame your partner. When you know what your nervous system expects, you stop mistaking your history for their behavior."
        ),
        "scene": ("neutral", "stand", "surprised", "stand"),
    },
    "anxious_attachment": {
        "term": "anxious attachment",
        "hook": "Rereading a text for the ninth time isn't love — it's your nervous system searching for evidence it's safe.",
        "explain": (
            "Anxious attachment works like an overly sensitive smoke detector. It detects distance early and often correctly, but it can't measure how serious the fire is. "
            "So a delayed reply becomes a possible breakup, and a short answer becomes a possible ending. "
            "The exhaustion you feel isn't from caring too much — it's from monitoring without rest. "
            "Reassurance helps for a moment; predictability is what actually heals it."
        ),
        "example": (
            "They said 'good morning' yesterday but not today, and now you're building a case from silence. "
            "Your brain isn't broken — it just learned early that love can vanish without warning."
        ),
        "takeaway": (
            "Ask directly instead of investigating. 'Are we okay?' costs one sentence. Detective mode costs your whole evening."
        ),
        "scene": ("anxious", "phone", "tired", "stand"),
    },
    "avoidant_attachment": {
        "term": "avoidant attachment",
        "hook": "Some people don't leave the room to hurt you — they leave because closeness starts to feel like losing themselves.",
        "explain": (
            "Avoidant attachment isn't a lack of feeling; it's a shutdown under pressure. "
            "For this style, intimacy and independence can feel like a trade — the closer someone gets, the more alarms go off about being controlled. "
            "So they create distance exactly when things deepen, then genuinely miss you once the pressure lifts. "
            "It looks like mixed signals from the outside, but inside it's one long balancing act."
        ),
        "example": (
            "An amazing weekend together, and suddenly they're distant for days. "
            "It's not regret — it's their system restoring air pressure after being seen up close."
        ),
        "takeaway": (
            "If this is you, try naming the exit before taking it. 'I need some space tonight, and I'll reach out tomorrow' keeps the bond alive while you breathe."
        ),
        "scene": ("sad", "stand", "detached", "away"),
    },
    "secure_attachment": {
        "term": "secure attachment",
        "hook": "Secure love feels underwhelming at first — because there's no adrenaline where the anxiety used to be.",
        "explain": (
            "Securely connected people do something quietly radical: they take words at face value. "
            "'I'm busy' means busy. 'I love you' means they'll act like it on Tuesday, not just on anniversaries. "
            "Their calm isn't a lack of depth — it's the absence of a constant threat detector. "
            "Research keeps finding the same thing: security is the style that makes every other relationship skill actually work."
        ),
        "example": (
            "You say you're upset, and they don't defend, attack, or vanish. They just get curious. "
            "That's not a personality — that's thousands of hours of feeling safe enough to stay soft."
        ),
        "takeaway": (
            "If stable love feels flat to you, don't chase chaos back. Excitement you can add. Safety is the foundation you can't."
        ),
        "scene": ("happy", "stand", "happy", "stand"),
    },
    "self_expansion": {
        "term": "the self-expansion model",
        "hook": "We don't fall for people — we fall for the version of ourselves we become around them.",
        "explain": (
            "Psychologists call this the self-expansion model of love. We're drawn to people who make our world bigger: new ideas, new courage, new experiences. "
            "That's why shared adventures bond couples faster than shared sofas. "
            "It also explains why relationships feel stale when growth stops — the expansion was the fuel, not just the bonus. "
            "Couples who keep learning together keep choosing each other."
        ),
        "example": (
            "Remember how alive you felt that first trip, that first project, that first disaster you survived as a team? "
            "You weren't high on the person only — you were high on your own growth, with them beside it."
        ),
        "takeaway": (
            "To keep love alive, expand together. A new skill, a trip, a hobby that scares you both — novelty repairs what routine erodes."
        ),
        "scene": ("happy", "stand", "happy", "arms_crossed"),
    },
    "misattribution_arousal": {
        "term": "misattribution of arousal",
        "hook": "A racing heart can't tell the difference between terror and chemistry — so it files everything under 'in love'.",
        "explain": (
            "In a famous study, men who crossed a shaky suspension bridge described the woman waiting on the other side as far more attractive than men who crossed a stable one. "
            "Their hearts were pounding from the height, but their brains labeled the arousal as attraction. "
            "This is misattribution of arousal — excitement from any source can be billed to the person standing nearest. "
            "It's why first dates work better with rollercoasters than with coffee."
        ),
        "example": (
            "You met during chaos — a deadline, a night out, a crisis — and it felt destined. "
            "Some of that spark was real. Some of it was adrenaline looking for someone to thank."
        ),
        "takeaway": (
            "Feel the spark, then re-test it on a quiet Tuesday. Attraction that survives boredom is the kind that survives marriage."
        ),
        "scene": ("surprised", "stand", "happy", "stand"),
    },
    "mere_exposure": {
        "term": "the mere exposure effect",
        "hook": "Familiarity doesn't breed contempt — it quietly breeds attraction. Every single time.",
        "explain": (
            "The mere exposure effect says we grow to like what we see repeatedly, even if nothing about it changes. "
            "The brain reads repetition as safety, and safety reads as likable. "
            "It's why the coworker you ignored in March is suddenly cute in October, and why songs grow on us by the fifth listen. "
            "It's attraction that compounds like interest."
        ),
        "example": (
            "You never noticed them at first. Then the same face, week after week, class after class, and one day the smile landed differently. "
            "Nothing about them changed — your brain just learned to feel safe around their pattern."
        ),
        "takeaway": (
            "Give decent people a second exposure. The spark-at-first-sight rule deletes slow burners — who are often the keepers."
        ),
        "scene": ("neutral", "stand", "happy", "stand"),
    },
    "dopamine_novelty": {
        "term": "the dopamine novelty effect",
        "hook": "The first six months of love are literally a drug phase — and withdrawal is scheduled, not personal.",
        "explain": (
            "Early romance floods the brain's reward circuit with dopamine, the same chemistry that powers craving and focus. "
            "That's why new love feels obsessive: you think about them constantly because the brain treats them as a reward it must pursue. "
            "But novelty fades on a schedule, and the intensity drops whether the love is real or not. "
            "Couples who know this stop panicking when the fire settles into warmth."
        ),
        "example": (
            "The butterflies faded around month seven, and you wondered if the love did too. "
            "It didn't. The chemicals stopped paying for the high — now the relationship pays for itself."
        ),
        "takeaway": (
            "Don't measure love by intensity; measure it by interest. Real love survives the chemistry drop and gets interesting again on purpose."
        ),
        "scene": ("happy", "stand", "tired", "phone"),
    },
    "oxytocin_bonding": {
        "term": "oxytocin bonding",
        "hook": "Cuddling is not a bonus feature of love — it's the maintenance schedule.",
        "explain": (
            "Oxytocin, released through touch and closeness, is the bonding chemical that turns attraction into attachment. "
            "Holding, hugging, and long quiet contact literally re-glue the connection between two nervous systems. "
            "That's why distance after a fight feels physical, not just emotional — the bond's maintenance got interrupted. "
            "Ten minutes of contact a day quietly outranks a bouquet every month."
        ),
        "example": (
            "You haven't hugged properly in weeks — quick pecks, passing taps, screens between you. "
            "The relationship isn't dying of drama; it's starving for its chemistry."
        ),
        "takeaway": (
            "Repair with touch before words when you can. A real hug lowers the guard that an argument raised."
        ),
        "scene": ("happy", "stand", "happy", "stand"),
    },
    "cortisol_bonding": {
        "term": "cortisol bonding",
        "hook": "A relationship that keeps you stressed can still keep you attached — stress itself builds the glue.",
        "explain": (
            "Cortisol, the stress hormone, doesn't just wreck you — it also deepens memory and attachment under the right conditions. "
            "Unpredictable partners spike it constantly, and the relief that follows each good moment gets bonded to them. "
            "This is how up-down relationships tattoo themselves into your mind while calm ones barely leave a note. "
            "The intensity isn't proof of a deeper love — it's proof of a stressed system doing its job."
        ),
        "example": (
            "The fights, the make-ups, the not knowing — and somehow they occupy your whole mind. "
            "You're not more bonded; you're more chemically booked."
        ),
        "takeaway": (
            "Rate the relationship by your weekday calm, not by the intensity of the reunions. Peace is data."
        ),
        "scene": ("anxious", "stand", "detached", "phone"),
    },
    "heartbreak_brain": {
        "term": "heartbreak withdrawal",
        "hook": "Breakup pain isn't poetry — brain scans put it next to physical pain and drug withdrawal.",
        "explain": (
            "When researchers scanned the recently rejected, the regions that lit up overlapped with those of physical pain and of craving during withdrawal. "
            "Your brain built its routines around a person who is now gone, and it protests like any addicted system. "
            "The appetite loss, the obsessive replay, the waves at night — they're symptoms, not weakness. "
            "And like withdrawal, the intensity is time-limited if you stop relapsing."
        ),
        "example": (
            "Day nine, and you feel it in your chest like a flu. That's not dramatic — that's neural recalibration. "
            "Your days were dosed with them, and the dose just stopped."
        ),
        "takeaway": (
            "Treat heartbreak like recovery, not sadness: routine, movement, sleep, and no relapse-checking their profile. The craving is the drug leaving."
        ),
        "scene": ("sad", "hands_face", "detached", "away"),
    },
    "rose_glasses": {
        "term": "positive illusion",
        "hook": "Being in love is a mild hallucination — and it's supposed to be.",
        "explain": (
            "Psychologists call it positive illusion: committed partners rate each other more kindly than reality strictly supports, and studies find mildly idealizing couples are actually more satisfied. "
            "The glasses help you forgive small flaws and invest long-term. "
            "The failure mode is the fog version — ignoring values, character, and consistency because the halo is bright. "
            "See the person clearly enough to know their behavior, kindly enough to forgive their humanity."
        ),
        "example": (
            "Your friends list the red flags; you list the exceptions. "
            "Some of that is love — some of it is a project, funded by hope."
        ),
        "takeaway": (
            "Keep the kindness, drop the blindness. Ask: 'Would I respect this behavior if I saw it in a stranger?'"
        ),
        "scene": ("happy", "stand", "neutral", "phone"),
    },
    "negativity_bias": {
        "term": "negativity bias",
        "hook": "One cruel sentence outweighs ten kind ones — your brain is built to remember the knife, not the gift.",
        "explain": (
            "Negativity bias is the mind's ancient accounting: bad moments get recorded in ink, good ones in pencil. "
            "It kept our ancestors alive, but it quietly bankrupts relationships, because partners feel underpaid no matter how much they give. "
            "This is why contempt is the single strongest predictor of breakup — contempt is negativity bias with a voice. "
            "Awareness of the bias is most of the battle."
        ),
        "example": (
            "You cooked, planned, showed up all month — and one sharp comment at dinner owns the whole evening. "
            "Your partner remembers the comment. Their brain isn't ungrateful; it's prehistoric."
        ),
        "takeaway": (
            "Balance the ledger out loud: name what they did right, especially when your brain only wants to file what they did wrong."
        ),
        "scene": ("annoyed", "arms_crossed", "sad", "stand"),
    },
    "rejection_sensitivity": {
        "term": "rejection sensitivity",
        "hook": "If 'K' feels like a door slamming, your threat detector is calibrated to a war that's over.",
        "explain": (
            "Rejection sensitivity means your nervous system flags possible exclusion faster and harder than average. "
            "It often comes from early experiences where approval vanished without explanation. "
            "The cost is heavy: you detect rejection that isn't there, react to protect yourself, and sometimes create the distance you feared. "
            "It's a self-fulfilling alarm."
        ),
        "example": (
            "They reply with one word, and you feel fired from the relationship. "
            "Nothing happened — but your system answered a question nobody asked."
        ),
        "takeaway": (
            "Separate the trigger from the evidence. Two deep breaths and one honest question beat a three-hour silent investigation."
        ),
        "scene": ("anxious", "phone", "tired", "phone"),
    },
    "loss_aversion": {
        "term": "loss aversion",
        "hook": "You don't miss them — you miss not losing them. The brain fights harder to keep what's leaving.",
        "explain": (
            "Loss aversion is the finding that losses hurt roughly twice as much as equivalent gains feel good. "
            "Apply it to love and the math turns dark: the moment someone withdraws, keeping them becomes the mission, regardless of whether they were right for you. "
            "The relationship's value inflates exactly as its probability drops. "
            "That's why people chase harder after the breakup than before it."
        ),
        "example": (
            "For months you had doubts you could name. They left, and suddenly the doubts evaporated and they became the one. "
            "Scarcity upgraded them; it never evaluated them."
        ),
        "takeaway": (
            "Write down why it ended while it still hurts. Loss aversion edits memory fast — the list keeps the truth."
        ),
        "scene": ("sad", "stand", "detached", "away"),
    },
    "scarcity_effect": {
        "term": "the scarcity effect",
        "hook": "Hard-to-get isn't hotter. It's just mispriced.",
        "explain": (
            "The scarcity effect makes anything seem more valuable as it becomes less available — including attention. "
            "Someone who gives you Tuesday might genuinely be worth less to your week than someone who gives you every day. "
            "But the brain sees 'limited availability' and slaps on a collector's price. "
            "The fix is pricing the person's actual behavior, not their availability schedule."
        ),
        "example": (
            "They fit you in when it's convenient, and you plan your life around the slot. "
            "You're not valuing a relationship; you're bidding on a rare item."
        ),
        "takeaway": (
            "Value consistency over scarcity. Available people aren't cheap — they're fairly priced."
        ),
        "scene": ("anxious", "stand", "smug", "phone"),
    },
    "ghosting_psych": {
        "term": "ghosting",
        "hook": "Ghosting isn't a mystery — it's conflict avoidance wearing an invisibility cloak.",
        "explain": (
            "People who ghost are rarely at war with you; they're at war with discomfort. "
            "Ending things requires a moment of being the villain, and some people will pay any price to skip that moment. "
            "The disappearing act buys them peace and bills you the confusion. "
            "It's not a reflection of your worth — it's a receipt of their conflict skills, printed in silence."
        ),
        "example": (
            "Two months of daily talk, then a read receipt and nothing. "
            "You're left holding a half-story — because finishing it required a courage they didn't have."
        ),
        "takeaway": (
            "Stop auditioning for an answer. A person who vanishes has answered — in the only language they're fluent in."
        ),
        "scene": ("sad", "phone", "detached", "away"),
    },
    "silence_amplification": {
        "term": "the silence effect",
        "hook": "An unanswered text gets louder the longer it stays unanswered. That's not you — that's a vacuum.",
        "explain": (
            "The mind abhors an information vacuum, so it fills silence with its loudest available fear. "
            "A read receipt without a reply is an open loop, and open loops demand closure like an itch demands scratching. "
            "The longer the silence, the more storylines your brain scripts, and rarely the kind ones. "
            "The message's power comes from the gap, not from the sender."
        ),
        "example": (
            "Three hours quiet, and you've already been dumped, promoted to enemy, and mourned — all inside one afternoon. "
            "The silence wrote all of it."
        ),
        "takeaway": (
            "Answer the vacuum with reality: 'They might be busy, and I'll know soon.' Say it out loud. Silence shrinks under daylight."
        ),
        "scene": ("anxious", "phone", "tired", "phone"),
    },
    "on_off_cycles": {
        "term": "on-off cycles",
        "hook": "Every breakup with the same person gets easier to start — and harder to count.",
        "explain": (
            "Research on on-again, off-again couples finds the pattern usually feeds on ambiguity rather than love. "
            "Each reunion is powered by relief, and relief is a terrible judge of compatibility. "
            "The cycle also normalizes itself: the third breakup simply doesn't scare anyone the way the first one did. "
            "The question isn't 'do we love each other' — cyclical couples usually do — it's 'do we ever solve anything between reunions'."
        ),
        "example": (
            "You've broken up twice, and both times the comeback felt like fate. "
            "Notice that the actual problems have been in the room all three times, quietly outliving the drama."
        ),
        "takeaway": (
            "If you restart, restart with changes, not just with feelings. A reunion without a new plan is a rerun with spoilers."
        ),
        "scene": ("sad", "stand", "neutral", "phone"),
    },
    "love_bombing": {
        "term": "love bombing",
        "hook": "If week two feels like a movie, ask who's holding the script — and why the pacing is so fast.",
        "explain": (
            "Love bombing is overwhelming affection deployed early: constant messages, grand gifts, future plans by day ten. "
            "Genuine intensity exists, but healthy intensity leaves room for your pace — bombing doesn't. "
            "The tell isn't the size of the gesture; it's what happens when you slow down even slightly. "
            "Bombing creates a debt: you owe enthusiasm, and the interest rate rises."
        ),
        "example": (
            "By the second week they've said you're their soulmate and picked your song. By the third, a slow reply from you got a dramatic response. "
            "The affection was never about you — it was about speed."
        ),
        "takeaway": (
            "Pace is a filter: 'I want to slow down' is a sentence, and their reaction to it is a full personality preview."
        ),
        "scene": ("surprised", "stand", "smug", "arms_crossed"),
    },
    "breadcrumbing": {
        "term": "breadcrumbing",
        "hook": "A crumb is not bread. A text at 11 p.m. is not a relationship.",
        "explain": (
            "Breadcrumbing is feeding someone the minimum attention required to keep them interested — never enough to build anything. "
            "The breadcrumber enjoys being wanted more than they want the wanting. "
            "For the person receiving it, each crumb restarts hope and resets the clock, which is exactly the design. "
            "The pattern runs on your optimism, not on their potential."
        ),
        "example": (
            "Every ten days: a compliment, a meme, a 'we should hang out soon' that never becomes a plan. "
            "You've been full on hope and starving on facts for months."
        ),
        "takeaway": (
            "Test with a concrete invitation — place, day, hour. Breadcrumbers vanish at specifics; interested people negotiate them."
        ),
        "scene": ("anxious", "phone", "smug", "phone"),
    },
    "mixed_signals_cost": {
        "term": "the cost of ambiguity",
        "hook": "Mixed signals aren't confusion. They're the most expensive clarity you'll ever buy.",
        "explain": (
            "When someone runs hot and cold, most people try to decode the signal — but the signal IS the message. "
            "Ambivalence communicates: 'I want the benefits of your presence without the obligations of my consistency.' "
            "The hidden cost is months of your attention spent auditing someone instead of living. "
            "Certainty may be boring, but it's the only soil where anything actually grows."
        ),
        "example": (
            "They call you 'baby' but cancel the plans; they post you but hide the label. "
            "You've become a translator for a language that only ever says one thing: maybe."
        ),
        "takeaway": (
            "Replace 'what do they feel' with 'what do they do'. Behavior is the only signal that never mixes."
        ),
        "scene": ("anxious", "stand", "detached", "phone"),
    },
    "no_contact_effect": {
        "term": "the no-contact reset",
        "hook": "No contact isn't a strategy to get them back — it's the only setting where your brain starts repairing.",
        "explain": (
            "Contact with a person you're withdrawing from works like a drink for an alcoholic: one message resets the craving clock. "
            "The pain you feel in silence isn't proof you belong together; it's the withdrawal curve doing its steep part. "
            "After a few weeks, the same memories start arriving with less voltage, because the bond is finally un-maintained. "
            "Space doesn't change them — it changes your chemistry."
        ),
        "example": (
            "You broke it off but kept watching the stories, 'just to see.' "
            "That's not strength — that's dosing yourself with exactly enough to stay sick."
        ),
        "takeaway": (
            "Full silence, including the profile. The healing you're buying costs 30 honest days — checking extends the invoice."
        ),
        "scene": ("anxious", "phone", "away", "away"),
    },
    "rumination_loop": {
        "term": "rumination",
        "hook": "Replaying the breakup isn't processing — it's a loop pretending to be one.",
        "explain": (
            "Rumination feels like problem-solving, but it re-runs the same scene without producing any new answers. "
            "Each replay strengthens the memory path, so the thoughts get easier to think, not easier to drop. "
            "That's why 'I just need to figure out what went wrong' can last a year — the brain is chewing, never swallowing. "
            "Actual processing produces decisions; rumination only produces more replays."
        ),
        "example": (
            "Hour three of the same montage: the message, the silence, the conversation you'd rewrite. "
            "You know every line. You've learned nothing new since hour one."
        ),
        "takeaway": (
            "Interrupt the loop with your body: walk, lift, call someone, cook — anything with a physical score the brain has to follow."
        ),
        "scene": ("sad", "hands_face", "detached", "away"),
    },
    "unfinished_ending": {
        "term": "the Zeigarnik effect",
        "hook": "Your ex stays memorable because the story stayed unfinished — open files get no archive.",
        "explain": (
            "The Zeigarnik effect is the mind's habit of holding open tasks in active memory while completed ones get filed away. "
            "A relationship that ended with silence or chaos stays 'open', so the brain keeps it loaded like a browser tab. "
            "It's not love keeping them accessible — it's the lack of an ending sentence. "
            "People who write their own closure report the tab finally closing."
        ),
        "example": (
            "If they'd said a real goodbye, you'd miss them like a finished book. "
            "Instead you miss them like a cliffhanger — because that's exactly what your memory filed it as."
        ),
        "takeaway": (
            "Write the ending yourself: one page — what it was, why it ended, what you're taking with you. Sign it. The mind respects a signature."
        ),
        "scene": ("sad", "stand", "detached", "away"),
    },
    "nostalgia_filter": {
        "term": "rosy retrospection",
        "hook": "You're not missing the person. You're missing the highlight reel your memory edited for you.",
        "explain": (
            "Rosy retrospection is the documented tendency to remember the past more fondly than it was lived. "
            "Pain fades first from memory, which is merciful for trauma and treacherous for breakups. "
            "Six months out, your mind replays the trip and the laughing — the silent car rides and the Sunday dread rarely make the cut. "
            "The person in your head is a curated version; the real one had scenes you paid to forget."
        ),
        "example": (
            "You miss 'how it was' — but you texted your best friend from the bathroom at your happiest dinner together. "
            "The memory and the diary rarely agree."
        ),
        "takeaway": (
            "When nostalgia hits, read the diary, not the montage. Missing the good parts is human; rebuilding your week around them is optional."
        ),
        "scene": ("sad", "stand", "happy", "phone"),
    },
    "rebound_psych": {
        "term": "the rebound effect",
        "hook": "A rebound isn't unfair to the new person only — it's a mirror, and mirrors make terrible partners.",
        "explain": (
            "Rebounds work as painkillers: the new attention suppresses the withdrawal at full speed. "
            "The problem is dosage — the relief you feel gets attributed to the new person, inflating what they actually mean to you. "
            "Studies suggest people who rebound while still processing often pick for contrast, not compatibility: whoever feels most opposite of the ex. "
            "Some rebounds do last; those usually started after the grief had already done most of its work."
        ),
        "example": (
            "They're nothing like your ex — calm where the other was chaos. That's real relief. "
            "Just check whether you're dating them, or the absence of someone else."
        ),
        "takeaway": (
            "Ask one honest question before committing: 'Would I choose this person if I weren't bleeding?' If unsure, date slowly — it's allowed."
        ),
        "scene": ("neutral", "stand", "happy", "stand"),
    },
    "self_worth_reset": {
        "term": "the worth baseline",
        "hook": "You don't attract what you deserve — you attract what you believe you deserve. The math is brutal.",
        "explain": (
            "Psychologists find that self-esteem acts like a price floor: it sets the minimum treatment you'll quietly tolerate. "
            "Raise the floor and bad offers stop being affordable; lower it and mistreatment starts looking like luck. "
            "That's why the same person can leave a terrible relationship and walk straight into a similar one — the filter, not the market, carried over. "
            "Working on worth isn't vanity; it's relationship economics."
        ),
        "example": (
            "After the breakup you swore 'never again' — and six months later you're explaining the same red flags to a new best friend. "
            "The pattern followed the price floor, not the person."
        ),
        "takeaway": (
            "Do the boring work: sleep, build, achieve, keep promises to yourself. Worth rises with kept commitments, and standards follow it."
        ),
        "scene": ("neutral", "stand", "neutral", "stand"),
    },
    "closure_myth": {
        "term": "the closure myth",
        "hook": "Closure isn't delivered. It's decided. Waiting for the explanation is just the wound voting to stay open.",
        "explain": (
            "Most people waiting for closure already know what happened — they're waiting for the other person to co-sign the paperwork. "
            "The reason it never arrives is that a clean explanation would require the other person to be more organized than their exit was. "
            "Acceptance research is clear: meaning can be self-authored; permission cannot be outsourced. "
            "The explanation you want is real — you're just asking the wrong supplier."
        ),
        "example": (
            "You rehearsed the conversation a hundred times: the apology, the reasons, the dignity. "
            "You could write it yourself, almost word for word. That's the tell — the file is complete; only your signature is missing."
        ),
        "takeaway": (
            "Write the ending letter you're waiting for — from them, then sign it yourself. It sounds silly. It works."
        ),
        "scene": ("sad", "stand", "away", "away"),
    },
    "apology_languages": {
        "term": "real apology",
        "hook": "'I'm sorry you feel that way' is an apology-shaped object. It contains no apology.",
        "explain": (
            "A real apology has four load-bearing parts: the specific action, the acknowledgment of the impact, the absence of excuses, and the change plan. "
            "'If' and 'but' cancel the whole thing — 'I'm sorry if I hurt you' files the hurt as hypothetical. "
            "The strongest predictor of repair isn't the apology's warmth; it's the change that follows within a week. "
            "Words settle the moment; behavior settles the pattern."
        ),
        "example": (
            "Compare: 'Sorry, but I was exhausted' versus 'I snapped at dinner. It wasn't fair to you. Tonight I'll tell you when I'm at my limit.' "
            "One is a speech. The other is a promise with a timestamp."
        ),
        "takeaway": (
            "Audit apologies the way banks audit promises: name, amount, date. Anything vaguer than that is a coupon, not a commitment."
        ),
        "scene": ("sad", "stand", "neutral", "stand"),
    },
    "repair_attempts": {
        "term": "repair attempts",
        "hook": "Strong couples don't fight less — they repair faster. The exit matters more than the entrance.",
        "explain": (
            "In Gottman's long-term studies of couples, the single best predictor of staying together wasn't the absence of conflict — it was the speed and warmth of repair attempts. "
            "A repair attempt is any move that lowers the temperature: a joke, a touch, 'this is hard for me too'. "
            "The healthiest couples repair mid-fight, not after the verdict. "
            "What kills relationships is not the spark but the fire's inability to hear an extinguisher."
        ),
        "example": (
            "Mid-argument, one of you breaks eye contact and says, 'can we sit closer?' "
            "Nothing got solved — but the war got a ceasefire, and that's where solutions live."
        ),
        "takeaway": (
            "Learn one repair phrase by heart and use it before you're ready. 'We're on the same team' works even when it's the last thing you feel."
        ),
        "scene": ("annoyed", "arms_crossed", "sad", "stand"),
    },
    "four_horsemen": {
        "term": "the four horsemen",
        "hook": "Four habits predict divorce with scary accuracy — and three of them look like normal arguing.",
        "explain": (
            "Gottman's research named the four horsemen of relationship collapse: criticism of the person instead of the behavior, contempt — eye-rolls, mockery, superiority — defensiveness, and stonewalling. "
            "Of the four, contempt is the heaviest single predictor, because it communicates disgust rather than disagreement. "
            "The antidotes are learnable: complain without blaming, describe feelings, own your share, and ask for a pause instead of going silent. "
            "Every horseman has an exit ramp."
        ),
        "example": (
            "'The dishes aren't done' is a complaint. 'Of course not — you're just like your mother' is a cavalry charge. "
            "The first starts a conversation; the second starts a countdown."
        ),
        "takeaway": (
            "Catch the eye-roll — it's contempt's signature move. Swap 'you always' for 'when X happens, I feel Y'. Same fire, no arson."
        ),
        "scene": ("annoyed", "arms_crossed", "detached", "away"),
    },
    "bids_for_connection": {
        "term": "bids for connection",
        "hook": "'Look at that dog' is not about the dog. It never was.",
        "explain": (
            "Gottman's team found couples make tiny bids for connection constantly — a comment, a question, a pointed finger at a sunset. "
            "Partners either turn toward the bid, turn away, or turn against it, and the ratio predicts the relationship's future with unsettling accuracy. "
            "Masters of relationship turn toward roughly nine times out of ten, even when the bid is boring. "
            "Love isn't maintained on anniversaries; it's maintained on Tuesdays, one small 'yes' at a time."
        ),
        "example": (
            "They said 'look at the moon' from the kitchen. You said 'mm' and kept scrolling. "
            "Nothing happened — and a small withdrawal was just made from an account neither of you checks often enough."
        ),
        "takeaway": (
            "For one day, answer every bid: look up, laugh, respond. It's the cheapest relationship upgrade with the highest return."
        ),
        "scene": ("happy", "stand", "tired", "phone"),
    },
    "trust_equation": {
        "term": "the trust equation",
        "hook": "Trust isn't built by promises — it's built by boring predictability, delivered over time.",
        "explain": (
            "Trust researchers describe it as consistency plus integrity divided by self-interest: people trust those whose words, actions, and motives line up, repeatedly. "
            "Grand gestures can't compensate for broken patterns — trust compounds like a savings account, in small identical deposits. "
            "This is also why recovery after a betrayal is slow: the account must be rebuilt at the same boring rate it was drained. "
            "There is no lottery version of trust."
        ),
        "example": (
            "One partner promised change with fireworks and relapsed. The other quietly texted 'landing now' at every arrival for two years. "
            "Guess whose word is now currency?"
        ),
        "takeaway": (
            "Make fewer promises, keep more of them. If you say 7, be there at 7 — that's a deposit. 7:15 with flowers is still a withdrawal."
        ),
        "scene": ("neutral", "stand", "happy", "stand"),
    },
    "jealousy_signal": {
        "term": "jealousy as information",
        "hook": "Jealousy isn't proof of love. It's an alarm — and your job is to figure out what tripped it.",
        "explain": (
            "Jealousy has two possible sources: a real threat in the situation, or an insecurity in the alarm system itself. "
            "The first deserves a conversation; the second deserves self-work — but they can feel identical from inside. "
            "Unchecked jealousy becomes control, and control is the fastest known killer of desire. "
            "The skill isn't feeling less — it's investigating the signal before obeying it."
        ),
        "example": (
            "Their coworker got a laugh, and your chest tightened. Was something actually happening — or did an old wound hear its favorite song? "
            "One answer needs a talk. The other needs a journal. Choose correctly and the night survives."
        ),
        "takeaway": (
            "Ask the alarm one question: 'what exactly did I see?' Facts first, story second. Then decide whether the conversation is with them — or with yourself."
        ),
        "scene": ("annoyed", "arms_crossed", "surprised", "phone"),
    },
    "boundaries_attract": {
        "term": "the boundary filter",
        "hook": "A boundary isn't a wall to keep love out — it's a filter that makes love possible.",
        "explain": (
            "Boundaries define where you end and another person begins: your time, your body, your money, your yes and no. "
            "Psychologically, clear boundaries do something counterintuitive — they make people feel safer, because rules you can see are rules you can trust. "
            "People who resent your boundaries were only ever compatible with your absence of them. "
            "The filter isn't losing you people; it's pricing them accurately."
        ),
        "example": (
            "You said 'I can't do late-night calls on workdays' — simple, kind, final. "
            "The person who respected it stayed. The person who called at 2 a.m. anyway just self-selected out."
        ),
        "takeaway": (
            "State boundaries early, kindly, without apology. You're not asking permission — you're publishing the map."
        ),
        "scene": ("neutral", "stand", "neutral", "phone"),
    },
    "green_flags": {
        "term": "green flags",
        "hook": "Green flags are quiet — consistency never makes noise, and noise is all we're trained to notice.",
        "explain": (
            "Green flags are unsexy: they remember small things, they're on time, they apologize specifically, they're kind to waiters and exes alike. "
            "Our attention systems are trained by drama, so steadiness registers as flat — the psychological version of a quiet engine. "
            "The trick is to actively look for the boring signals, because they're the ones carrying the relationship's actual weight. "
            "A person whose presence calms you is doing something biochemically rare."
        ),
        "example": (
            "No fireworks — but they text when they say, they ask how your mom's test went, and you sleep better when they're around. "
            "Your nervous system noticed before your heart did."
        ),
        "takeaway": (
            "Score people on how you feel two hours after seeing them, not two minutes. Calm is a green flag wearing a disguise."
        ),
        "scene": ("happy", "stand", "happy", "stand"),
    },
    "slow_love": {
        "term": "slow love",
        "hook": "Slow love isn't less intense — it's better funded. Fast love runs on credit.",
        "explain": (
            "Sociologists call it slow love: building the relationship before the fantasy, letting intimacy develop over months of real information instead of weeks of projection. "
            "Fast love happens in the dark — you fall for the montage and meet the person later. "
            "Slow love keeps the pace of actual knowledge, so affection grows on facts instead of imagination. "
            "It's less cinematic and dramatically more durable."
        ),
        "example": (
            "No labels by date three, no weekend trips by week two — but six months in, you know their money habits, their temper, their mother. "
            "You're not less in love. You're in love with a verified account."
        ),
        "takeaway": (
            "Let the timeline be a feature, not a bug. Depth is slow by design — anything moving too fast is skipping the inspections."
        ),
        "scene": ("happy", "stand", "neutral", "stand"),
    },
}
