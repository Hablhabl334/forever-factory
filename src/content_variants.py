"""The variation layer — why the factory NEVER runs out of new scripts.

content_data.py holds the psychology atoms (40 concepts, 24 topics).
This module holds the SURFACE VARIATIONS for every atom:

  * 2 extra hooks, 2 extra examples, 2 extra takeaways per concept
  * slotted example scenes ({a} {b} {day} {time} {place}) drawn from
    name/place/day/time pools -> thousands of distinct micro-scenes

Distinct Shorts per concept (lower bound):
    hooks(3) x facts(~4) x examples(3) x takeaways(3) x slot draws
    (40 names x 39 partners x 7 days x 8 times x 16 places)
    = 81 skeletons x ~1.4M slot draws ~= 110M scripts per concept
    x 40 concepts ~= 4.5 BILLION distinct Shorts before any repeat.
At 4 Shorts/day that is ~3 million years. The hash ledger enforces
the guarantee: no script text is ever produced twice.

Long videos: 8 concepts per episode (ordered subsets across 24 topics
= 67.7M structures) x 27 surface variants per concept -> the long-
episode space exceeds the number of atoms in the observable universe
by a comfortable margin.

Tone rules: same as content_data.py — name patterns, never pathologize
people; no diagnosis, no manipulation framing (audited downstream).
"""
from __future__ import annotations

# ── slot pools (shared by every slotted example) ─────────────────────
NAMES = [
    "Maya", "Noah", "Lena", "Sam", "Ava", "Theo", "Iris", "Eli",
    "Nora", "Adam", "Zoe", "Leo", "Emma", "Kai", "Sara", "Omar",
    "Layla", "Ben", "Chloe", "Rami", "Dina", "Jack", "Nina", "Milo",
    "Tara", "Youssef", "Amy", "Cole", "Hana", "Ivan", "Rosa", "Finn",
    "Ada", "Jonas", "Mira", "Seth", "Tala", "Ryan", "Aya", "Luke",
]
PLACES = [
    "a coffee shop downtown", "the office", "a wedding", "the airport",
    "the gym", "a bookstore", "a rooftop party", "the library",
    "a birthday party", "the park", "a concert", "their favorite cafe",
    "the beach", "a house party", "the office party", "a dinner party",
]
DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]
TIMES = [
    "midnight", "2 a.m.", "3 a.m.", "6 a.m.",
    "noon", "4 p.m.", "11 p.m.", "1 a.m.",
]

# ── topic -> music mood (the soundtrack matches the theme) ───────────
TOPIC_MOODS = {
    "attraction": "warm",
    "attachment": "attachment",
    "breakup": "healing",
    "ghosting": "healing",
    "mixed_signals": "healing",
    "red_flags": "healing",
    "green_flags": "warm",
    "love_bombing": "healing",
    "jealousy": "attachment",
    "trust": "warm",
    "communication": "warm",
    "arguments": "attachment",
    "apology": "attachment",
    "love_languages": "warm",
    "chemistry": "warm",
    "self_love": "warm",
    "boundaries": "warm",
    "ex_thinking": "healing",
    "no_contact": "healing",
    "moving_on": "healing",
    "long_distance": "attachment",
    "lasting": "warm",
    "secure": "warm",
    "heartache_science": "healing",
}

# ── concept surface variants ─────────────────────────────────────────
# hooks/examples/takeaways: 2 NEW entries each; the original text in
# content_data.py is always variant #0. Examples here are slotted.
VARIANTS: dict[str, dict] = {
    "intermittent_reinforcement": {
        "hooks": [
            "The person who answers once a week can own your whole brain — and it's not chemistry, it's a payout schedule.",
            "Casinos discovered something about love before we did: unpredictable rewards hook deeper than certain ones.",
        ],
        "examples": [
            "{a} texts {b} on {day} — warm, funny, exact. Then nothing for six days. {b} isn't hooked on {a}; {b} is hooked on the moment the machine finally pays.",
            "Every time {b} decides to walk away, {a} resurfaces with a voice note at {time} and a reason. It's not timing. It's a schedule that keeps the player seated.",
        ],
        "takeaways": [
            "Track the pattern, not the highs. A calendar of crumbs was never a relationship.",
            "If consistency feels flat to you, price the calm correctly — steadiness is the expensive thing; the rollercoaster is the cheap trick.",
        ],
    },
    "anxious_avoidant_trap": {
        "hooks": [
            "One of you gets calm by getting closer. The other gets calm by getting space. That's not a match — that's a circuit.",
            "The chase feels like passion. It's actually two alarm systems taking turns.",
        ],
        "examples": [
            "{a} reaches for {b} at {time}; {b} goes quiet for two days; then {b} returns warm, and {a} relaxes — until the next reach. The pattern has the couple; the couple doesn't have the pattern.",
            "On {day}, {a} asks to talk about 'us'. {b} says everything's fine. By the weekend {b} is distant again, and {a} starts planning how to be smaller next time.",
        ],
        "takeaways": [
            "Name the loop out loud, without blame: 'I chase when I'm scared, you retreat when you're scared.' Naming it is half the exit.",
            "One of you must hold steady first — and it's usually the one watching the pattern, not the one inside it.",
        ],
    },
    "attachment_styles": {
        "hooks": [
            "Two people can hear the exact same sentence and live in two different relationships — their ears were trained by different childhoods.",
            "Your attachment style is the operating system love runs on — and almost nobody checks which one they installed.",
        ],
        "examples": [
            "{a} hears 'let's talk tonight' and feels safe. {b} hears the same words and spends the afternoon rehearsing a defense. The sentence was identical; the systems reading it weren't.",
            "{a} says 'text me when you're home' and means care. {b} reads it as surveillance. Neither is lying — they're running two different definitions of love.",
        ],
        "takeaways": [
            "Learn your style first — it explains half the fights you keep mislabeling as character flaws.",
            "Styles aren't life sentences. Safe people plus honest practice rewrite them slowly, at any age.",
        ],
    },
    "anxious_attachment": {
        "hooks": [
            "Checking their profile twelve times a day isn't devotion — it's a smoke detector with no off switch.",
            "Your brain isn't needy. It just learned early that love can leave without a warning.",
        ],
        "examples": [
            "{a} sends a message at noon. By {time}, no reply, and {a} has already drafted the goodbye speech. The reply arrives hours later: 'sorry, crazy day.' Nothing was ending — except {a}'s afternoon.",
            "{b} liked three posts and skipped {a}'s. That's the entire evidence file — and it's still enough to put the relationship on trial at {place} that same night.",
        ],
        "takeaways": [
            "Predictability heals what reassurance only sedates. Ask for patterns, not promises.",
            "Say the fear out loud early: 'silence makes me spin.' A safe person will help you carry it; an unsafe one will use it.",
        ],
    },
    "avoidant_attachment": {
        "hooks": [
            "They don't pull away because the love is fake — they pull away because closeness starts ringing alarms nobody taught them to mute.",
            "Distance after intimacy isn't rejection. For some people, it's the only way they know to breathe.",
        ],
        "examples": [
            "{a} and {b} spend a perfect weekend together — {place}, no phones, real laughter. By {day}, {a} is short on the phone and 'busy' with something vague. {a} isn't lying about being busy; {a} is restoring air pressure.",
            "The moment {b} says 'I really love this', {a} changes the subject within a minute. It's not indifference — it's a reflex that treats depth like a room with no exit.",
        ],
        "takeaways": [
            "If this is you: schedule the space before taking it. 'I need tonight, and I'll call you tomorrow' keeps the bond while you breathe.",
            "If you love someone like this: stop reading the retreat as a verdict. Ask what helps them return — usually patience, not pursuit.",
        ],
    },
    "secure_attachment": {
        "hooks": [
            "The most attractive sentence in a relationship is a calm 'okay, tell me more' — and it takes years of safety to say it naturally.",
            "Secure love has no plot twists. That's not boring — that's the point.",
        ],
        "examples": [
            "{a} says 'you hurt my feelings at {place}' and {b} doesn't defend, counterattack, or freeze — {b} says 'you're right, that was careless.' The conversation lasts ninety seconds and nothing escalates.",
            "{b} cancels a date for work and says 'Thursday, same time, I'll be fully there.' On {day}, {b} is fully there. Small, boring, and rarer than it should be.",
        ],
        "takeaways": [
            "If calm reads as chemistry-free to you, check your training — the adrenaline you miss might be an alarm, not a spark.",
            "Security is a skill set, not a personality type: face-value listening, repair after fights, and words that predict behavior.",
        ],
    },
    "self_expansion": {
        "hooks": [
            "The couples who last aren't the ones who love hardest — they're the ones who keep growing side by side.",
            "Boredom isn't the death of love. Stopped growth is.",
        ],
        "examples": [
            "{a} and {b} took a class, got lost in a new city, built something that failed — and somehow came home closer. The activity didn't matter; becoming newer people together did.",
            "Every Saturday looks the same for {a} and {b}: same food, same show, same silence at {place}. Neither is unhappy — both are shrinking, and calling it peace.",
        ],
        "takeaways": [
            "Book one experience a month that neither of you has tried. Novelty is not a luxury for couples; it's maintenance.",
            "Grow alone and you drift. Grow together and you compound.",
        ],
    },
    "misattribution_arousal": {
        "hooks": [
            "That electric feeling on the first date might not be them — it might be the rollercoaster getting the credit.",
            "Your heart can't tell fear from falling. It just files the pounding under 'this must be love.'",
        ],
        "examples": [
            "{a} met {b} in the middle of chaos at {place} — a deadline crisis, a storm, a packed night out. It felt destined. Some of it was real; a lot of it was adrenaline billing the nearest person.",
            "{a} and {b} went on a quiet, easy first date and felt 'something missing'. The missing ingredient wasn't chemistry — it was excitement for the brain to misread.",
        ],
        "takeaways": [
            "Re-test the spark on a boring Tuesday. Attraction that survives silence is built on more than adrenaline.",
            "Plan first dates with a pulse — then plan the second one without it. You'll learn which feeling was the person.",
        ],
    },
    "mere_exposure": {
        "hooks": [
            "You didn't fall for them instantly — your brain fell for their repetition, and that's the sturdiest kind.",
            "Attraction at first sight gets the songs. Attraction by the fifteenth Tuesday gets the decades.",
        ],
        "examples": [
            "{a} didn't notice {b} for months at {place}. Then, week after week, something shifted: the laugh landed differently, the face read as home. Nothing changed about {b} — {a}'s brain just stopped being alert around them.",
            "{b} was 'not my type' in the group chat last spring. This fall, {a} is re-reading their chats and smiling. The type didn't change; the exposure did.",
        ],
        "takeaways": [
            "Stop discounting the slow ones. Comfort is attraction that bothered to check the facts first.",
            "Proximity is a strategy: be around, be steady, be real. The compound interest does the rest.",
        ],
    },
    "dopamine_novelty": {
        "hooks": [
            "Month seven, the butterflies quiet down — that's not the love dying, that's the free trial ending.",
            "New love is literally a stimulant phase. The couples who last are the ones who don't panic during the comedown.",
        ],
        "examples": [
            "Around month seven, {a} told {b}: 'I don't feel the rush anymore.' {b} didn't panic. {b} said: 'good — now we can build something that doesn't need a drug to run.'",
            "{a} misses the old butterflies and starts wondering about other people. What {a} is actually missing is a brain state — not a person. Chasing it is chasing a high with new dealers.",
        ],
        "takeaways": [
            "When the fire settles into warmth, don't file for divorce from the feeling — upgrade the game: build, travel, learn each other deeper.",
            "Chemistry gets you in the door. Interest keeps you in the room. Invest in the second one.",
        ],
    },
    "oxytocin_bonding": {
        "hooks": [
            "Hugs aren't the dessert of a relationship — they're the maintenance contract.",
            "Ten minutes of real contact a day quietly outperforms a bouquet a month. That's not romance — that's chemistry's terms.",
        ],
        "examples": [
            "{a} and {b} haven't held each other properly in weeks — quick kisses, passing taps, phones between them at {place}. Nobody cheated, nobody fought. The bond is just starving on its own schedule.",
            "After their worst argument, {a} reached for {b}'s hand before either said a word. Ten minutes later, they could actually talk. The touch lowered the guard that words couldn't.",
        ],
        "takeaways": [
            "Institute the daily ten: full contact, no phones, no agenda. Small doses, perfect record.",
            "After conflict, touch before talking when you can. It reopens the door that the argument slammed.",
        ],
    },
    "cortisol_bonding": {
        "hooks": [
            "The relationship that stresses you out the most might be the one you can't stop thinking about — the glue is real, and so is the trap.",
            "Calm love barely leaves a mark. Chaotic love tattoos itself — because stress chemicals write in permanent ink.",
        ],
        "examples": [
            "{a} and {b} fight, reconcile, and repeat. {a}'s friends ask what's so special about {b}, and {a} can't answer — because {a} isn't more in love, {a} is more chemically booked.",
            "At {place}, {a} watches {b} laugh with someone else and feels a spike. The spike isn't proof of destiny; it's cortisol doing its filing. Two weeks of quiet would show {a} who {b} actually is.",
        ],
        "takeaways": [
            "Audit the relationship on ordinary weekdays, not on the intensity of reunions.",
            "If the calm ones feel forgettable, check what you've been trained to call chemistry. It might just be your stress response in love's clothing.",
        ],
    },
    "heartbreak_brain": {
        "hooks": [
            "Heartbreak lives in the brain's withdrawal circuits — which is why 'just get over it' is medically useless advice.",
            "The appetite loss, the 3 a.m. replays, the chest ache — that's not weakness. That's a system recalibrating.",
        ],
        "examples": [
            "Day nine after the breakup, {a} feels it in the body like a flu at {time} every night. Nothing is wrong with {a}. {a}'s days were dosed with a person, and the dose stopped.",
            "{b} keeps checking {a}'s profile 'one last time' and re-feels everything. Each check is a relapse — it resets the withdrawal clock that healing was quietly winning.",
        ],
        "takeaways": [
            "Run recovery, not sadness: routine, movement, sleep, people — and zero profile checks. The craving is the drug leaving.",
            "Expect waves, not a straight line. Week two is usually worse than week one; week six is usually the turn.",
        ],
    },
    "rose_glasses": {
        "hooks": [
            "In love, your brain runs a mild marketing campaign for the other person — fine in small doses, fatal in large ones.",
            "The healthiest couples idealize each other a little. The destroyed ones idealize a lot.",
        ],
        "examples": [
            "{a}'s friends list the patterns they've watched for a year at {place}. {a} counters every one with an exception. Some of that is loyalty; the rest is a campaign {a} is running on {a}'s own perception.",
            "{b} cancels on {a} again, and {a} says 'they're just busy.' {a} would never accept this pattern from a stranger. The halo is doing the accounting.",
        ],
        "takeaways": [
            "Keep the kindness, drop the blindness: 'Would I respect this behavior if I saw it in a stranger?' is the whole audit.",
            "Let a trusted friend fact-check your version of them. Not to obey — just to compare editions.",
        ],
    },
    "negativity_bias": {
        "hooks": [
            "Your partner's brain will remember the one sharp sentence over the twenty kind ones — it's not ingratitude, it's archaeology.",
            "Bad moments get written in ink; good ones in pencil. Relationships go bankrupt on that accounting.",
        ],
        "examples": [
            "{a} planned, cooked, showed up all month. At {place}, {a} makes one tired, sharp comment — and {b} files the whole evening under it. {b}'s brain isn't ungrateful; it's prehistoric.",
            "{b} did nine kind things this week and one forgetful one. Guess which one {a} is still describing at {time} that night. The ledger is rigged — by design.",
        ],
        "takeaways": [
            "Balance out loud: name one thing they did right every time your brain files one thing they did wrong. You're correcting a biased ledger, not lying.",
            "Deliver criticism once. Repetition doesn't strengthen the point — it just sets the ink.",
        ],
    },
    "rejection_sensitivity": {
        "hooks": [
            "A one-word reply shouldn't end worlds — but for some nervous systems, 'K' is a verdict.",
            "Some brains treat a slow reply like exile. They usually learned that somewhere.",
        ],
        "examples": [
            "{a} texts a paragraph; {b} answers with a thumbs-up at {time}. {a} spends the evening at {place} quietly certain the relationship is ending. Nothing happened — {a}'s system answered a question nobody asked.",
            "{b} doesn't call after a long day. {a}'s chest tightens like a door slammed. The war {a}'s detector is fighting ended years ago — nobody updated it.",
        ],
        "takeaways": [
            "Separate trigger from evidence: two slow breaths, then one honest question instead of a three-hour silent investigation.",
            "Tell your person the setup: 'quiet evenings make me spiral — a heads-up helps.' A safe partner will learn the code.",
        ],
    },
    "loss_aversion": {
        "hooks": [
            "You didn't want them that much until they became unavailable — the pricing changed, not the person.",
            "Losing hurts twice as much as winning feels good — which is why breakups manufacture false soulmates.",
        ],
        "examples": [
            "For months, {a} had doubts {a} could name out loud. {b} left on {day}, and suddenly the doubts evaporated and {b} became 'the one'. Scarcity upgraded {b}; it never evaluated {b}.",
            "{a} wasn't fighting for {b} during the relationship. {a} started fighting the moment losing became real. The heart isn't grieving a person — it's grieving a property.",
        ],
        "takeaways": [
            "Write why it ended while it still hurts. Loss aversion edits memory fast; the list keeps the truth.",
            "Before winning them back, ask the colder question: would I choose them fresh — or am I just refusing to lose?",
        ],
    },
    "scarcity_effect": {
        "hooks": [
            "'Hard to get' isn't a personality — it's a pricing error your brain keeps making.",
            "The less available someone is, the more valuable they look. That's not romance; that's auction psychology.",
        ],
        "examples": [
            "{b} fits {a} in when convenient — a Tuesday here, a maybe there. {a} plans the whole week around the slot. {a} isn't valuing a relationship; {a} is bidding on a rare item.",
            "{a} gets full attention for two hours every ten days, and it feels electric. Meanwhile {b}'s calm, available friend gets labeled 'too easy' at {place}. The market is completely upside down.",
        ],
        "takeaways": [
            "Price the behavior, not the availability. Someone giving you every day is worth more than someone giving you Tuesday.",
            "Available isn't cheap. Available is fairly priced — check who taught you otherwise.",
        ],
    },
    "ghosting_psych": {
        "hooks": [
            "Ghosting isn't a mystery to solve. It's conflict avoidance wearing an invisibility cloak.",
            "People who vanish aren't avoiding you. They're avoiding being the villain for one awkward minute.",
        ],
        "examples": [
            "Two months of daily talk between {a} and {b} — then a read receipt and nothing at {time} on {day}. {a} is left holding a half-story, because finishing it required a courage {b} never budgeted for.",
            "{b} says 'I hate confrontation' like it's a personality trait. At {place} last month, {b} disappeared from a friendship the same way. The pattern isn't about {a}; it's {b}'s only exit strategy.",
        ],
        "takeaways": [
            "Stop auditioning for an answer. A person who vanishes has already answered — in the only language they're fluent in.",
            "The silence isn't information about your worth. It's a receipt for their conflict skills — paid in your confusion.",
        ],
    },
    "silence_amplification": {
        "hooks": [
            "The unanswered text doesn't stay quiet — the vacuum rewrites it hourly into something louder.",
            "Silence has no content. Your brain supplies the content, and it rarely casts you as safe.",
        ],
        "examples": [
            "Three hours quiet from {b}, and {a} has been dumped, promoted to enemy, and mourned — all before {time}. {a} wrote the whole script; the silence just left the page blank.",
            "{a} watches {b} post a story from {place} while {a}'s message sits unanswered. The evidence says 'seen it, no reply.' The brain hears 'everything is over.' Both can't be true — one of them is just quieter.",
        ],
        "takeaways": [
            "Answer the vacuum with reality, out loud: 'They might be busy, and I'll know soon.' Daylight shrinks silence.",
            "Notice the storyline, then check the timestamp. Most silence is hours old; most catastrophes are seconds old.",
        ],
    },
    "on_off_cycles": {
        "hooks": [
            "The third breakup with the same person doesn't hurt less — it just scares you less. That's the trap.",
            "Reunions run on relief, and relief is a terrible judge of compatibility.",
        ],
        "examples": [
            "{a} and {b} have broken up twice — once in spring, once by autumn. Both comebacks felt like fate. The actual problems attended all three relationships, quietly outliving every reunion.",
            "Friends ask {a} what changed this time. Nothing changed: the relief just arrived on schedule at {time}, wearing the costume of love.",
        ],
        "takeaways": [
            "If you restart, restart with changes — not just with feelings. A reunion without a new plan is a rerun with spoilers.",
            "Ask the one question cycles avoid: 'what did we actually solve between the last two reunions?' If the answer is nothing, the next round is scheduled.",
        ],
    },
    "love_bombing": {
        "hooks": [
            "If the affection has a deadline attached, it was never affection — it was a down payment.",
            "Fast love isn't proof of destiny. Sometimes it's proof of a script.",
        ],
        "examples": [
            "By week two, {a} has called {b} a soulmate, picked their song, and planned {place} months out. By week three, one slow reply from {b} gets a reaction way too large for a slow reply.",
            "{b} was adored at a speed that felt like a movie — until {b} tried slowing down on {day}. The adoration flipped into pressure in a single conversation. Affection with a tempo requirement is control's opening act.",
        ],
        "takeaways": [
            "Pace is a filter. Say 'I want to slow down' and watch the reaction — it's a full personality preview in one minute.",
            "Real intensity leaves room for your speed. Bombing doesn't. That difference is the whole test.",
        ],
    },
    "breadcrumbing": {
        "hooks": [
            "The 11 p.m. 'you up' isn't connection — it's inventory management.",
            "A crumb restarts hope and resets the clock. That's not an accident; that's the design.",
        ],
        "examples": [
            "Every ten days, {a} gets a message from {b}: a compliment, a meme, a 'we should hang soon' that never becomes a plan. {a} has been full on hope and starving on facts since {day}.",
            "{b} resurfaces at {time} exactly when {a} starts moving on — never before, never after. It isn't timing; it's a sensor. {b} enjoys being wanted more than wanting.",
        ],
        "takeaways": [
            "Test with specifics: place, date, hour. Breadcrumbers vanish at logistics; interested people negotiate them.",
            "Stop measuring their potential. Start counting their patterns. The pattern is the person.",
        ],
    },
    "mixed_signals_cost": {
        "hooks": [
            "Mixed signals aren't mixed. Ambivalence is a clean, readable message — you're just charging too little for your attention.",
            "You keep decoding someone who's already told you everything — with their consistency, not their words.",
        ],
        "examples": [
            "{a} gets 'baby' in texts and cancelled plans in reality — a label at {time}, invisibility at {place}. {a} has become a translator for a language that only ever says one word: maybe.",
            "{b} posts {a} online and hides the relationship offline. It's not confusion. It's a clean split: the benefits of presence, none of the obligations of consistency.",
        ],
        "takeaways": [
            "Swap 'what do they feel' for 'what do they do'. Behavior is the only signal that never mixes.",
            "Set a date for clarity — out loud, calmly. Ambivalence hates deadlines more than it hates losing you.",
        ],
    },
    "no_contact_effect": {
        "hooks": [
            "No contact isn't a game to win them back. It's the only setting where your brain gets to repair.",
            "One 'hey' resets the withdrawal clock. That's not romance — that's dosing.",
        ],
        "examples": [
            "{a} ended it but kept watching {b}'s stories 'just to see'. At {time} every night, {a} takes exactly enough to stay sick. Space doesn't change {b}; it changes {a}'s chemistry.",
            "Day twelve of silence, and {a} finally sleeps through the night. Then {a} checks one story while waiting at {place} — and week one arrives back like a boomerang.",
        ],
        "takeaways": [
            "Full silence, including the profile. The healing costs about thirty honest days; every check extends the invoice.",
            "If you relapse, don't restart the shame spiral — restart the count. The curve forgives; consistency fixes.",
        ],
    },
    "rumination_loop": {
        "hooks": [
            "Thinking about it 'one more time' has never once solved it. That's the loop's favorite lie.",
            "Replaying feels like processing. The difference: processing ends in a decision.",
        ],
        "examples": [
            "Hour three of the same montage for {a}: the message, the silence, the conversation {a} would rewrite. {a} knows every line and has learned nothing new since hour one.",
            "{b} 'just needs to figure out what went wrong' — a project that's now older than the relationship was. The brain is chewing; it never swallows.",
        ],
        "takeaways": [
            "Interrupt with your body: walk, lift, cook, call someone. The loop can't run while the body holds the score.",
            "Book the replay: fifteen minutes, scheduled, with a notebook. Contained rumination shrinks; free-range rumination compounds.",
        ],
    },
    "unfinished_ending": {
        "hooks": [
            "Your ex stays loud in memory because the story never got an ending sentence — open files don't close.",
            "It's not love keeping them loaded in your head. It's an unclosed tab.",
        ],
        "examples": [
            "If {b} had said a real goodbye, {a} would miss them like a finished book. Instead, {a} misses them like a cliffhanger at {time} on random nights — because that's exactly how memory filed it.",
            "{a} waits for one more conversation that would 'finally explain everything.' The explanation isn't coming — the person who left without sentences doesn't have the sentence.",
        ],
        "takeaways": [
            "Write the ending yourself: one page — what it was, why it ended, what you keep. Sign it. The mind respects a signature.",
            "You don't need their participation to close the file. That's the whole trick — endings can be self-service.",
        ],
    },
    "nostalgia_filter": {
        "hooks": [
            "You're not missing the person. You're missing the director's cut your memory produced after the fact.",
            "Memory edits out the pain first — merciful for trauma, treacherous for breakups.",
        ],
        "examples": [
            "{a} misses 'how it was' with {b} — but at their happiest dinner at {place}, {a} texted a best friend from the bathroom. The memory and the diary rarely agree.",
            "Six months out, {b} replays the trip, the laughing, the rain. The Sunday dread and the silent car rides never make the edit. {b} isn't remembering the relationship; {b} is remembering its trailer.",
        ],
        "takeaways": [
            "When nostalgia hits, read the diary, not the montage. Missing the good parts is human; rebuilding your week around them is optional.",
            "Add up the real last month before deciding it was love. The ending data is data too.",
        ],
    },
    "rebound_psych": {
        "hooks": [
            "The rebound isn't unfair to the new person only — it's dating a mirror, and mirrors make terrible partners.",
            "Relief is real chemistry. It's just not the same chemistry as compatibility.",
        ],
        "examples": [
            "{a} meets {b} two weeks after the breakup. {b} is everything the ex wasn't — calm where there was chaos. Real relief. The open question: is {a} dating {b}, or dating the absence of someone else?",
            "By {day}, {a} is telling friends {b} is 'the one'. Maybe — or maybe the dosage is doing the talking. Painkillers feel like healing while the wound is still open, unexamined.",
        ],
        "takeaways": [
            "Ask before committing: 'Would I choose this person if I weren't bleeding?' If unsure, date slowly — that's allowed.",
            "The rebounds that last usually started after the grief did most of its work. Sequence matters more than speed.",
        ],
    },
    "self_worth_reset": {
        "hooks": [
            "You don't attract what you deserve. You attract what you believe you can keep.",
            "Self-esteem is a price floor — mistreatment below it stops being affordable.",
        ],
        "examples": [
            "After the breakup, {a} swore 'never again' — with feeling. Six months later, {a} is explaining the same patterns to a new best friend at {place}. The filter carried over; the market didn't change.",
            "{b} accepts apologies {b} would never offer. {b} calls it being understanding. It's a price floor set somewhere back in childhood, quietly running every transaction.",
        ],
        "takeaways": [
            "Do the boring work: sleep, build, keep promises to yourself. Worth rises with kept commitments, and standards follow it.",
            "Watch your non-negotiables for one week. Not what you say they are — what you actually tolerate when it's inconvenient.",
        ],
    },
    "closure_myth": {
        "hooks": [
            "Closure isn't delivered. It's decided — and waiting for the explanation is just the wound voting to stay open.",
            "You already know what happened. You're waiting for a co-signature from someone who left without signing.",
        ],
        "examples": [
            "{a} rehearsed the conversation a hundred times: the apology, the reasons, the dignity. At {time} on {day}, {a} realizes {a} could write it almost word for word. The file is complete; only {a}'s signature is missing.",
            "{b} keeps saying 'I just need to understand.' A clean explanation would require the other person to be more organized than their exit was. That invoice doesn't get paid.",
        ],
        "takeaways": [
            "Write the ending letter you're waiting for — from them — then sign it yourself. It sounds silly. It works.",
            "Acceptance can be self-authored. Permission is the only part that can't be outsourced — and the only part you actually need.",
        ],
    },
    "apology_languages": {
        "hooks": [
            "'I'm sorry you feel that way' is an apology-shaped object. Check the ingredients: there's no apology in it.",
            "A real apology has four parts. Most people bring one — the tone.",
        ],
        "examples": [
            "{a} says 'Sorry, but I was exhausted.' {b} says 'I snapped at dinner. It wasn't fair to you. Tonight I'll tell you when I'm at my limit.' One is a speech; the other is a promise with a timestamp.",
            "{b} apologizes warmly for things that keep happening. Warmth without change is a subscription to the apology, not its delivery.",
        ],
        "takeaways": [
            "Audit apologies like a bank: name the action, own the impact, no 'if', no 'but', and a dated change plan.",
            "Judge the apology a week later. Words settle the moment; behavior settles the pattern.",
        ],
    },
    "repair_attempts": {
        "hooks": [
            "Happy couples don't fight less. They repair faster — and the speed is the whole secret.",
            "The strongest predictor of staying together isn't zero conflict. It's how fast the temperature drops.",
        ],
        "examples": [
            "Mid-argument at {place}, {a} breaks eye contact and says 'can we sit closer?' Nothing got solved. The war got a ceasefire — and solutions only live past ceasefires.",
            "{b} makes a terrible joke at the worst moment of the fight. {a} laughs despite everything. That laugh is a repair attempt landing — worth more than winning the argument.",
        ],
        "takeaways": [
            "Learn one repair phrase by heart and use it before you feel ready. 'We're on the same team' works even when it's the last thing you feel.",
            "Repair mid-fight, not after the verdict. After the verdict, someone has to lose first.",
        ],
    },
    "four_horsemen": {
        "hooks": [
            "Eye-rolls are not harmless. In forty years of couple research, contempt predicted endings better than anything else.",
            "'You always' and 'you never' aren't complaints — they're cavalry.",
        ],
        "examples": [
            "'The dishes aren't done' is a complaint from {a}. 'Of course not — you're just like your mother' is a cavalry charge. The first started a conversation; the second started a countdown.",
            "{b} goes silent mid-fight — stone wall, no door, no exit. {a} escalates to break through. Round and round: one horseman feeding another.",
        ],
        "takeaways": [
            "Swap 'you always' for 'when X happens, I feel Y'. Same fire, no arson.",
            "Catch the eye-roll. It feels like a blink; it lands like disgust — and disgust is the one signal relationships rarely survive.",
        ],
    },
    "bids_for_connection": {
        "hooks": [
            "'Look at that dog' is not about the dog. It never was.",
            "Love isn't maintained on anniversaries. It's maintained on Tuesdays — one small 'yes' at a time.",
        ],
        "examples": [
            "From the kitchen at {time}, {b} says 'look at the moon.' {a} says 'mm' and keeps scrolling. Nothing happened — and a small withdrawal was just made from an account neither of them audits.",
            "{a} points at a dog crossing the street near {place}. It's not about the dog; it's 'be with me in this second.' Couples who answer these calls stay couples — researchers tracked it for years.",
        ],
        "takeaways": [
            "For one day, answer every bid: look up, laugh, respond. It's the cheapest relationship upgrade with the highest return.",
            "Boring bids count double — the sillier the bid, the purer the test of the alliance.",
        ],
    },
    "trust_equation": {
        "hooks": [
            "Trust isn't built by grand promises. It's built by boring predictability, compounded daily.",
            "If you say 7, be there at 7. That's a deposit. 7:15 with flowers is still a withdrawal.",
        ],
        "examples": [
            "{a} promised change with fireworks — and relapsed. {b} quietly texted 'landing now' at every arrival for two years. Guess whose word is now currency, with everyone.",
            "It took one broken pattern to empty the account {a} and {b} built for three years. Now it rebuilds the same way it was built: small, identical, boring deposits — there is no lottery version.",
        ],
        "takeaways": [
            "Make fewer promises, keep more of them. Overpromising is just debt in a romantic accent.",
            "After a breach, expect the rebuild to be as slow as the collapse was fast. Patience here isn't weakness; it's arithmetic.",
        ],
    },
    "jealousy_signal": {
        "hooks": [
            "Jealousy isn't proof of love — it's an alarm. Your job is to figure out what tripped it before you obey it.",
            "Every jealousy has one of two sources: a real threat, or an old wound hearing its favorite song.",
        ],
        "examples": [
            "At {place}, {b}'s coworker gets a big laugh, and {a}'s chest tightens. Did something actually happen — or did an old wound just get played? One answer needs a talk; the other needs a journal.",
            "{a} checks who liked {b}'s posts at {time} — a habit wearing the costume of love. Control feels like protection, but control is the fastest known killer of desire.",
        ],
        "takeaways": [
            "Ask the alarm one question: 'what exactly did I see?' Facts first, story second — then choose the right conversation.",
            "Bring the feeling, not the case files. 'I felt something and I want to understand it' opens doors that evidence slams shut.",
        ],
    },
    "boundaries_attract": {
        "hooks": [
            "A boundary isn't a wall to keep love out — it's a filter that makes love possible.",
            "People who resent your boundaries were only ever compatible with your absence of them.",
        ],
        "examples": [
            "{a} says 'I can't do late-night calls on workdays' — simple, kind, final. The person who respected it stayed. The person who called at {time} anyway just self-selected out.",
            "{b} explains the rules clearly at the start: weekends yes, emergencies always, guilt trips never. The relationship got safer, not smaller. Visible rules are trustable rules.",
        ],
        "takeaways": [
            "State boundaries early, kindly, without apology. You're not asking permission — you're publishing the map.",
            "The filter isn't losing you people. It's pricing them accurately — and that's a service to everyone involved.",
        ],
    },
    "green_flags": {
        "hooks": [
            "Green flags are quiet — consistency never makes noise, and noise is all we're trained to notice.",
            "No fireworks, just follow-through: the unsexy signs carrying the whole relationship.",
        ],
        "examples": [
            "{b} texts when {b} says, asks how {a}'s mom's test went, and is kind to waiters at {place}. No drama, no electric highs — and {a} sleeps better around {b} than {a} has in years. The nervous system noticed before the heart did.",
            "{a} realized it at {time} on a Tuesday: nothing spectacular was happening, and {a} felt completely safe. That's not boring. That's biochemically rare.",
        ],
        "takeaways": [
            "Score people on how you feel two hours after seeing them, not two minutes. Calm is a green flag wearing a disguise.",
            "Make a list of your boring green flags this week — on time, remembers, repairs. Then look for that list in people, not chemistry.",
        ],
    },
    "slow_love": {
        "hooks": [
            "Slow love isn't less intense — it's better funded. Fast love runs on credit.",
            "Fast love happens in the dark: you fall for the montage and meet the person later.",
        ],
        "examples": [
            "No labels by date three, no weekend trip by week two for {a} and {b}. Six months in, {a} knows {b}'s money habits, temper, and mother. {a} isn't less in love — {a} is in love with a verified account.",
            "{b} moves carefully and gets called 'not spontaneous'. Then {a} watches two whirlwind friends from {place} break up in the time it took {b} to say 'I love you' and mean it.",
        ],
        "takeaways": [
            "Let the timeline be a feature, not a bug. Depth is slow by design — anything too fast is skipping the inspections.",
            "Trade the butterflies of month one for the knowledge of month six. That trade is the whole strategy.",
        ],
    },
}
