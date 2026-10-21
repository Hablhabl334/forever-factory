"""MICRO-EXAMPLES — the Shorts relatability bank (v2 script engine).

Owner rule (2026-10-21): a Short's example must be ONE vivid moment,
never a multi-sentence two-character scenario. The old slot-filled
{narratives} stay in content_variants.py for the long video's couple
scenes; Shorts now draw from these micros instead — short, punchy,
second-person moments with zero dialogue and zero named characters.

Writing rules enforced per micro (asserted by scripts/test_script_v2.py):
  * 1-2 sentences, <= 22 words — never 60% of the video
  * no {a}/{b}/{day}/{time}/{place} slots, no dialogue exchanges
  * never contains the concept's TERM (the reveal keeps its payoff)
  * never contains a reveal marker ("call this", "is called", ...)
  * never echoes the concept's hook (no duplicated opening)
  * passes the story_engine safety audit (no banned framing)
"""
from __future__ import annotations

MICROS: dict[str, list[str]] = {
    "anxious_attachment": [
        "Nine re-reads of the same two-word reply, and each one sounds more doomed than the last.",
        "They said good morning yesterday. Today it's missing, and your whole morning became an investigation.",
        "A slow reply feels like a verdict, so you start drafting your closing argument.",
    ],
    "anxious_avoidant_trap": [
        "You reach for closeness; they reach for the door. Repeat until it feels like passion.",
        "Sunday: warm, close, perfect. Wednesday: gone without a word. You both call it love.",
        "The more you pursue, the further they drift. The further they drift, the harder you run.",
    ],
    "apology_languages": [
        "'Sorry you feel that way' landed with a thud, because it was addressed to your feelings, not their actions.",
        "They apologized with flowers for the same hurt they re-caused by Friday.",
        "'I was wrong, and here is what changes' — one sentence some people never once manage.",
    ],
    "attachment_styles": [
        "'I need space' sounds like freedom to you and abandonment to them.",
        "You both heard 'let's talk tonight.' One of you relaxed. The other spent the day preparing a defense.",
        "What feels clingy to you is what feels like love to someone else — different childhoods, same words.",
    ],
    "avoidant_attachment": [
        "A perfect weekend together, then three days of one-word replies. The closeness set off their alarms.",
        "The moment things got deep, they got 'busy.' Depth, for them, is a room with no exit.",
        "They don't leave the room to hurt you — closeness just starts to feel like disappearing.",
    ],
    "bids_for_connection": [
        "'Look at that dog.' They weren't pointing at the dog. They were asking you to come outside with them.",
        "They said 'look at the moon' from the kitchen. You said 'mm.' Something small just left the room.",
        "The shared meme, the pointless text, the sigh across the couch — each one is a knock on your door.",
    ],
    "boundaries_attract": [
        "You said no late-night calls on workdays, kindly and once. The people who respected it stayed.",
        "The 2 a.m. caller didn't survive your rules. The rules made them visible.",
        "You stopped explaining your no three times a week, and the right people didn't even flinch.",
    ],
    "breadcrumbing": [
        "A meme at midnight, silence all week. You've been fed just enough to stay starving.",
        "'We should hang out soon' — soon has now lasted four months.",
        "They resurface exactly when you start moving on. That's not coincidence; that's a sensor.",
    ],
    "closure_myth": [
        "You rehearsed their apology for months. You could write it word for word — that's the tell.",
        "Waiting for them to explain the ending is just the wound voting to stay open.",
        "The explanation never came, because it would require them to be more organized than their exit was.",
    ],
    "cortisol_bonding": [
        "The fights, the make-ups, the not knowing — and they still own your whole mind. That's chemistry, not love.",
        "Two weeks of peace would feel flat to you now. That's what an up-down diet does to calm.",
        "Your friends ask what's so special about them. You can't answer, because the bond lives in your bloodstream.",
    ],
    "dopamine_novelty": [
        "Month seven: the butterflies clocked out, and you confused a chemical's last shift for the end of love.",
        "You don't miss them today — you miss the high your brain used to print for free.",
        "New love is a drug phase with a scheduled crash, and nobody tells you the crash is normal.",
    ],
    "four_horsemen": [
        "'You're just like your mother' did more damage in one sentence than the dishes ever could.",
        "The eye-roll at dinner was small, and it was the heaviest single predictor in the whole marriage.",
        "One of you went silent mid-fight. The other shouted to break through. Two habits, one collapse.",
    ],
    "ghosting_psych": [
        "Daily talk for months — then a read receipt and nothing. They weren't at war with you, just with discomfort.",
        "Ending things takes one uncomfortable minute. They billed you the confusion instead.",
        "You got no goodbye, because a goodbye requires being the villain for a moment.",
    ],
    "green_flags": [
        "No fireworks — but they text when they say they will, and you sleep better around them.",
        "They remembered how your mom's test went. Steadiness has no theme music, so we miss it.",
        "You felt completely safe on an ordinary Tuesday. That's not boring — that's biochemically rare.",
    ],
    "heartbreak_brain": [
        "Day nine felt like the flu, because your brain is protesting a dose of a person that stopped.",
        "Scans show rejection lighting up next to physical pain and craving. Your chest isn't being poetic.",
        "You check their profile 'one last time.' Each check resets the clock healing was quietly winning.",
    ],
    "intermittent_reinforcement": [
        "They reply exactly when you're ready to give up. That's not luck — that's a slot machine schedule.",
        "Monday you text; Thursday they answer, warm and perfect. Then a week of nothing.",
        "Uncertainty pays better than consistency, which is why the calm ones feel boring to you.",
    ],
    "jealousy_signal": [
        "Their coworker got one laugh, and your chest tightened. A real threat, or an old wound hearing its song?",
        "The alarm went off. Before confronting anyone, ask it: what exactly did I see?",
        "Sometimes the feeling points at them. Sometimes it points at a scar. From inside, they feel identical.",
    ],
    "loss_aversion": [
        "For months you had doubts you could name. They left, and suddenly they became the one.",
        "The exit upgraded their value. Scarcity did that, not their character.",
        "You're not fighting for them; you're fighting against losing. Those feel the same from inside. They aren't.",
    ],
    "love_bombing": [
        "By week two: soulmate, your song, names for the kids. By week three, a slow reply got punished.",
        "Constant messages and grand gifts by day ten — intensity that leaves no room for your pace isn't devotion.",
        "Real intensity lets you set the tempo. The other kind punishes you for having one.",
    ],
    "mere_exposure": [
        "You ignored them in March. By October, the same face read as home. Nothing changed but repetition.",
        "The song you skipped five times now owns your playlist. People work the same way.",
        "'Not my type,' you said in spring. It's fall, and you're re-reading their messages and smiling.",
    ],
    "misattribution_arousal": [
        "You left the horror movie holding their hand, and your brain filed the pounding heart under chemistry.",
        "The chaotic first date felt like destiny. Most of it was adrenaline billing the nearest person.",
        "Coffee felt flat; the rollercoaster felt like fate. Same person, different pulse.",
    ],
    "mixed_signals_cost": [
        "They call you 'baby' and cancel the plans, every week. The behavior isn't mixed — it's the message.",
        "You've become a translator for someone whose language only ever says: benefits without obligations.",
        "You spend your week decoding someone whose actions already said everything. Decoding is the expensive part.",
    ],
    "negativity_bias": [
        "You showed up all month — one sharp comment at dinner, and the evening belongs to it.",
        "Ten kind moments recorded in pencil, one cruel one in ink. That's the brain's ancient accounting.",
        "They did five things right today. Guess which one you're still replaying at midnight.",
    ],
    "no_contact_effect": [
        "You broke it off but kept watching the stories 'just to see.' That's a sip, not a goodbye.",
        "One message resets the craving clock. The steep part of the curve starts over every time.",
        "The silence hurts because it's working — the loudest part of healing sounds exactly like this.",
    ],
    "nostalgia_filter": [
        "You miss 'how it was' — but at your happiest dinner together, you texted your best friend from the bathroom.",
        "Six months out, the memory keeps only the montage. The diary remembers the fights.",
        "Pain fades first from memory — merciful for trauma, treacherous for breakups.",
    ],
    "on_off_cycles": [
        "You've broken up twice. Both comebacks felt like fate. Both times, the same problems were waiting in the room.",
        "Relief is a terrible judge of compatibility, but it powers every reunion.",
        "The third breakup was the easiest to start. That should scare you more than the first.",
    ],
    "oxytocin_bonding": [
        "Quick pecks, passing taps, screens between you. The relationship isn't dying of drama — it's starving for touch.",
        "You haven't hugged properly in three weeks. Words can't re-glue what contact does in seconds.",
        "Distance didn't kill it with a fight. It starved the one chemical that bonds you.",
    ],
    "rebound_psych": [
        "They're nothing like your ex — calm where the other was chaos. Real relief. But are you dating them, or the absence?",
        "The new attention works like a painkiller, and you're crediting the pill with your whole recovery.",
        "Three months in, ask one question: would I have chosen them if I weren't bleeding?",
    ],
    "rejection_sensitivity": [
        "They replied 'K' and you felt fired from the relationship. Nothing happened — your detector answered a question nobody asked.",
        "A one-word answer isn't a verdict. Your nervous system grew up where approval vanished without explanation.",
        "You detect possible rejection before it exists, which means you pay interest on loans never taken.",
    ],
    "repair_attempts": [
        "Mid-argument, one of you said 'can we sit closer?' Nothing got solved — but the war got a ceasefire.",
        "A joke at the right moment, a hand on the arm, a 'we're okay' — small moves that end wars early.",
        "A squeezed hand in the middle of a fight is worth more than the win.",
    ],
    "rose_glasses": [
        "Your friends list the red flags; you list the exceptions. Some of that is love, some is a project funded by hope.",
        "In love, you rate them kinder than reality supports. That's the design, until the interest comes due.",
        "You didn't ignore the warning signs — you gave each one a charitable interpretation. Love is a translator.",
    ],
    "rumination_loop": [
        "It's 1 a.m. and you're still rehearsing a conversation from three weeks ago. Nothing new has been learned tonight.",
        "Your brain calls it problem-solving, but the scene never changes and no answer ever comes.",
        "Each replay paves the path deeper — the thoughts get easier to think and harder to drop.",
    ],
    "scarcity_effect": [
        "They fit you in when convenient, and you plan your life around the slot. That's not romance — that's an auction.",
        "Tuesday-attention got priced like a diamond because it was rare. Rare isn't the same as valuable.",
        "The person with time for you feels 'too easy' now. That mispricing is the whole trick.",
    ],
    "secure_attachment": [
        "You said you're upset, and they didn't defend, attack, or vanish. They got curious. Rarest move in love.",
        "'I'm busy' just means busy. Imagine reading one sentence at face value.",
        "Their calm isn't shallowness — it's what depth looks like after thousands of hours of practice.",
    ],
    "self_expansion": [
        "That first trip, first project, first survived disaster — you weren't high only on them, but on who you became.",
        "You fell for the version of yourself that got bigger around them. Remember that before you chase anyone new.",
        "Adventures bond faster than sofas. Shared novelty is the cheapest renovation a relationship can buy.",
    ],
    "self_worth_reset": [
        "After the breakup you swore 'never again.' Six months later, you're explaining the same red flags to a new best friend.",
        "You tolerate exactly what you believe you deserve, and the belief was set long before this person.",
        "Raise the floor and bad offers stop looking affordable. Standards are economics, not vanity.",
    ],
    "silence_amplification": [
        "Three hours quiet, and you've been dumped, promoted to enemy, and mourned — all before dinner.",
        "The vacuum gets filled with the loudest fear in the room. Silence never stays empty.",
        "A read receipt is an open loop, and open loops itch. None of that is evidence.",
    ],
    "slow_love": [
        "Six months in, you know their money habits, their temper, their mother — because nobody rushed you past the inspections.",
        "Weeks of projection are cheaper than months of information — but only one of them survives winter.",
        "Depth has a speed limit. Anyone rushing you is skipping the inspections.",
    ],
    "trust_equation": [
        "One promised change with fireworks and relapsed. The other texted 'landing now' for two years. Guess whose word is gold.",
        "Grand gestures can't buy back a broken pattern. Trust compounds in small kept deposits only.",
        "Their words, actions, and motives line up, repeatedly — that's the entire formula. It's just hard.",
    ],
    "unfinished_ending": [
        "A real goodbye would have closed the file. Instead your brain keeps them loaded like a browser tab.",
        "You miss them like a cliffhanger, not like a finished book — because that's exactly how the memory filed it.",
        "Finished stories get archived. Open ones keep reloading, and this one was left open.",
    ],
}

# reveal markers must never appear in a micro (the term card triggers on them)
_FORBIDDEN_MARKERS = ("call this", "name for this", "is called", "term for this")
