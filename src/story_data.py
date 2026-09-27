"""Story atoms and beat templates — the generative grammar of the factory.

NOT a story bank. These are content *atoms*: dimensions of a bedtime tale
(hero, setting, problem, helper, object, moral, twist, motif...). Every
episode the engine draws one atom per dimension, then weaves them through
sixteen narrative beat templates. The Cartesian space of combinations is
counted in quadrillions — with a no-repeat ledger, the machine never tells
the same story twice (at 2 stories/day, the first possible repeat is
billions of years away).
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────
# ATOM BANKS — each dimension of the tale
# ─────────────────────────────────────────────────────────────────────

HEROES = [
    {"full": "a small snow hare", "short": "the snow hare", "tiny": "the little hare", "base": "hare", "paws": "paws"},
    {"full": "a gentle red fox", "short": "the red fox", "tiny": "the little fox", "base": "fox", "paws": "paws"},
    {"full": "a round little hedgehog", "short": "the hedgehog", "tiny": "the little hedgehog", "base": "hedgehog", "paws": "feet"},
    {"full": "a quiet field mouse", "short": "the field mouse", "tiny": "the little mouse", "base": "mouse", "paws": "paws"},
    {"full": "a fluffy gray owl", "short": "the gray owl", "tiny": "the little owl", "base": "owl", "paws": "wings"},
    {"full": "a soft brown bear cub", "short": "the bear cub", "tiny": "the little cub", "base": "bear", "paws": "paws"},
    {"full": "a sleepy badger", "short": "the badger", "tiny": "the little badger", "base": "badger", "paws": "paws"},
    {"full": "a small gray kitten", "short": "the kitten", "tiny": "the little kitten", "base": "cat", "paws": "paws"},
    {"full": "a yellow duckling", "short": "the duckling", "tiny": "the little duckling", "base": "duck", "paws": "feet"},
    {"full": "a patient little turtle", "short": "the turtle", "tiny": "the little turtle", "base": "turtle", "paws": "flippers"},
    {"full": "a speckled fawn", "short": "the fawn", "tiny": "the little fawn", "base": "deer", "paws": "hooves"},
    {"full": "a quick red squirrel", "short": "the squirrel", "tiny": "the little squirrel", "base": "squirrel", "paws": "paws"},
    {"full": "a small gray wolf pup", "short": "the wolf pup", "tiny": "the little pup", "base": "wolf", "paws": "paws"},
    {"full": "a green little frog", "short": "the frog", "tiny": "the little frog", "base": "frog", "paws": "feet"},
    {"full": "a silvery moth", "short": "the moth", "tiny": "the little moth", "base": "moth", "paws": "wings"},
    {"full": "a small brown snail", "short": "the snail", "tiny": "the little snail", "base": "snail", "paws": "foot"},
    {"full": "a playful young otter", "short": "the otter", "tiny": "the little otter", "base": "otter", "paws": "paws"},
    {"full": "a tiny dormouse", "short": "the dormouse", "tiny": "the little dormouse", "base": "mouse", "paws": "paws"},
    {"full": "a small shaggy pony", "short": "the pony", "tiny": "the little pony", "base": "pony", "paws": "hooves"},
    {"full": "a soft white seal pup", "short": "the seal pup", "tiny": "the little seal", "base": "seal", "paws": "flippers"},
    {"full": "a bright blue songbird", "short": "the songbird", "tiny": "the little songbird", "base": "bird", "paws": "wings"},
    {"full": "a round ladybird", "short": "the ladybird", "tiny": "the little ladybird", "base": "ladybug", "paws": "feet"},
    {"full": "a small pale rabbit", "short": "the rabbit", "tiny": "the little rabbit", "base": "rabbit", "paws": "paws"},
    {"full": "a kindly young beaver", "short": "the beaver", "tiny": "the little beaver", "base": "beaver", "paws": "paws"},
]

NAMES = [
    "Pim", "Nuna", "Mila", "Tansy", "Wren", "Juniper", "Fig", "Clover",
    "Ember", "Sage", "Bramble", "Nutmeg", "Poppy", "Fern", "Cobb", "Dune",
    "Misty", "Umi", "Yarrow", "Maple", "Tumble", "Sprout", "Velvet",
    "Quill", "Tuft", "Pebble", "Hush", "Fable", "Puddle", "Crumb", "Tico",
    "Zia", "Breeze", "Halo", "Dewey", "Moonpie", "Starla", "Cosmo", "Nod",
    "Siff", "Lull", "Cosy", "Onda", "Pillow", "Cocoa", "Willow", "Basil",
]

TRAITS = [
    {"adj": "curious", "phrase": "curious about every quiet thing"},
    {"adj": "brave", "phrase": "brave in a small, quiet way"},
    {"adj": "gentle", "phrase": "gentle with everything that moved"},
    {"adj": "dreamy", "phrase": "a little bit dreamy, even in daylight"},
    {"adj": "careful", "phrase": "careful with each step"},
    {"adj": "kind", "phrase": "kind to every creature, big or small"},
    {"adj": "patient", "phrase": "patient as a stone in a stream"},
    {"adj": "thoughtful", "phrase": "thoughtful before every word"},
    {"adj": "hopeful", "phrase": "hopeful, even on grey evenings"},
    {"adj": "quiet", "phrase": "quiet as a falling leaf"},
    {"adj": "determined", "phrase": "quietly determined underneath"},
    {"adj": "soft-spoken", "phrase": "soft-spoken and warm-hearted"},
    {"adj": "imaginative", "phrase": "always imagining friendly possibilities"},
    {"adj": "trustworthy", "phrase": "the one others trusted with small secrets"},
    {"adj": "tender", "phrase": "tender-hearted toward tiny things"},
    {"adj": "watchful", "phrase": "watchful, with big listening ears"},
]

SETTINGS = [
    {"full": "the Whispering Woods", "short": "the woods", "title": "Whispering Woods"},
    {"full": "Silvermeadow", "short": "the meadow", "title": "Silver Meadow"},
    {"full": "the Moonlit Seashore", "short": "the seashore", "title": "Moonlit Seashore"},
    {"full": "Frostpine Forest", "short": "the frost pines", "title": "Frostpine Forest"},
    {"full": "Lantern Hill", "short": "the hill", "title": "Lantern Hill"},
    {"full": "Starfall Valley", "short": "the valley", "title": "Starfall Valley"},
    {"full": "Cloudridge", "short": "the ridge", "title": "Cloudridge"},
    {"full": "Ripple Lake", "short": "the lake", "title": "Ripple Lake"},
    {"full": "Thistledown Field", "short": "the field", "title": "Thistledown Field"},
    {"full": "Honey Hollow", "short": "the hollow", "title": "Honey Hollow"},
    {"full": "Bramblewick", "short": "the brambles", "title": "Bramblewick"},
    {"full": "Mossgarden", "short": "the garden", "title": "Mossgarden"},
    {"full": "Willowmist Marsh", "short": "the marsh", "title": "Willowmist Marsh"},
    {"full": "Pebblebrook", "short": "the brook", "title": "Pebblebrook"},
    {"full": "Sunsleep Orchard", "short": "the orchard", "title": "Sunsleep Orchard"},
    {"full": "Windchime Pass", "short": "the pass", "title": "Windchime Pass"},
    {"full": "Lullaby Loch", "short": "the loch", "title": "Lullaby Loch"},
    {"full": "Cushion Caves", "short": "the caves", "title": "Cushion Caves"},
    {"full": "Bumblebrook", "short": "the brook", "title": "Bumblebrook"},
    {"full": "Pillowtop Peak", "short": "the peak", "title": "Pillowtop Peak"},
    {"full": "Duskhollow", "short": "the hollow", "title": "Duskhollow"},
    {"full": "the Sleepy Dunes", "short": "the dunes", "title": "Sleepy Dunes"},
    {"full": "Everdim Wood", "short": "the wood", "title": "Everdim Wood"},
    {"full": "the Glasswater Ponds", "short": "the ponds", "title": "Glasswater Ponds"},
]

TIMES = [
    {"full": "a soft summer dusk", "mood": "summer_dusk", "sky": "dusk"},
    {"full": "an early-autumn evening", "mood": "autumn_evening", "sky": "evening"},
    {"full": "a wintry starlit night", "mood": "winter_night", "sky": "night"},
    {"full": "a spring twilight", "mood": "spring_twilight", "sky": "twilight"},
    {"full": "a lavender dusk", "mood": "lavender_dusk", "sky": "dusk"},
    {"full": "a moon-bright midnight", "mood": "moonlit_night", "sky": "night"},
    {"full": "a sleepy golden afternoon", "mood": "golden_afternoon", "sky": "afternoon"},
    {"full": "a rainy pattering evening", "mood": "rainy_evening", "sky": "rain"},
    {"full": "a frosty blue evening", "mood": "frost_evening", "sky": "night"},
    {"full": "a snow-quiet night", "mood": "snow_night", "sky": "night"},
    {"full": "a misty morning-touched eve", "mood": "misty_eve", "sky": "twilight"},
    {"full": "a warm honeyed evening", "mood": "honey_evening", "sky": "evening"},
]

OBJECTS = [
    {"full": "a lantern that catches starlight", "short": "the lantern", "noun": "Lantern", "warm": "the lantern's warm circle of light"},
    {"full": "a silver key that hums softly", "short": "the silver key", "noun": "Silver Key", "warm": "the key's gentle hum"},
    {"full": "a map woven from moonbeams", "short": "the moonbeam map", "noun": "Moonbeam Map", "warm": "the map's pale glow"},
    {"full": "a blanket stitched with constellations", "short": "the star blanket", "noun": "Star Blanket", "warm": "the blanket's softness"},
    {"full": "a music box that snows inside", "short": "the music box", "noun": "Music Box", "warm": "the music box's tiny tune"},
    {"full": "a bell that rings only for the kind", "short": "the small bell", "noun": "Small Bell", "warm": "the bell's one clear note"},
    {"full": "a compass that always points to home", "short": "the compass", "noun": "Home Compass", "warm": "the compass's steady needle"},
    {"full": "a ribbon of northern light", "short": "the ribbon of light", "noun": "Light Ribbon", "warm": "the ribbon's soft shimmer"},
    {"full": "a teacup that never empties", "short": "the little teacup", "noun": "Endless Teacup", "warm": "the teacup's steam"},
    {"full": "a snowglobe of tiny seasons", "short": "the snowglobe", "noun": "Season Snowglobe", "warm": "the snowglobe's slow snow"},
    {"full": "a feather that remembers songs", "short": "the song feather", "noun": "Song Feather", "warm": "the feather's faint melody"},
    {"full": "a thread of spider-silk that never tangles", "short": "the silk thread", "noun": "Silk Thread", "warm": "the thread's silver line"},
    {"full": "a pebble warm as a hug", "short": "the warm pebble", "noun": "Warm Pebble", "warm": "the pebble's gentle warmth"},
    {"full": "a jar of bottled lullabies", "short": "the lullaby jar", "noun": "Lullaby Jar", "warm": "the jar's sleepy hum"},
    {"full": "a seed that grows a star", "short": "the star seed", "noun": "Star Seed", "warm": "the seed's faint pulse of light"},
    {"full": "a wooden boat the size of a shoe", "short": "the tiny boat", "noun": "Tiny Boat", "warm": "the boat's neat little bow"},
    {"full": "a candle that glows for the lonely", "short": "the steady candle", "noun": "Steady Candle", "warm": "the candle's patient flame"},
    {"full": "a kite that chases comets", "short": "the comet kite", "noun": "Comet Kite", "warm": "the kite's dancing tail"},
    {"full": "a shell that echoes tomorrow", "short": "the listening shell", "noun": "Listening Shell", "warm": "the shell's far-away song"},
    {"full": "a wooden flute that calls the wind", "short": "the little flute", "noun": "Wind Flute", "warm": "the flute's low note"},
    {"full": "a jar of dew that catches dreams", "short": "the dew jar", "noun": "Dew Jar", "warm": "the jar's cool shine"},
    {"full": "a clock that counts sleepy hours", "short": "the sleepy clock", "noun": "Sleepy Clock", "warm": "the clock's soft tick"},
    {"full": "a pair of slippers that walk on mist", "short": "the mist slippers", "noun": "Mist Slippers", "warm": "the slippers's whisper-soft steps"},
    {"full": "a storybook with no ending yet", "short": "the endless storybook", "noun": "Endless Storybook", "warm": "the book's open pages"},
    {"full": "a nightcap knitted from clouds", "short": "the cloud nightcap", "noun": "Cloud Nightcap", "warm": "the nightcap's softness"},
    {"full": "a lamp that burns colored calm", "short": "the calm lamp", "noun": "Calm Lamp", "warm": "the lamp's gentle colors"},
    {"full": "a windmill the size of a thimble", "short": "the thimble windmill", "noun": "Thimble Windmill", "warm": "the windmill's slow turning"},
    {"full": "a harmonica of mountain air", "short": "the mountain harmonica", "noun": "Mountain Harmonica", "warm": "the harmonica's airy note"},
]

COMPANIONS = [
    {"full": "a talkative old owl", "short": "the old owl", "noun": "Owl"},
    {"full": "a slow, wise turtle", "short": "the wise turtle", "noun": "Turtle"},
    {"full": "a choir of small fireflies", "short": "the fireflies", "noun": "Fireflies"},
    {"full": "a grandmotherly goose", "short": "the grandmother goose", "noun": "Goose"},
    {"full": "a gentle wandering wind", "short": "the gentle wind", "noun": "Wind"},
    {"full": "a moon-touched moth", "short": "the moon moth", "noun": "Moth"},
    {"full": "a storytelling badger", "short": "the storytelling badger", "noun": "Badger"},
    {"full": "a sleepwalking little cloud", "short": "the sleepy cloud", "noun": "Cloud"},
    {"full": "a tiny lost star", "short": "the little star", "noun": "Star"},
    {"full": "a boat-building beaver", "short": "the beaver", "noun": "Beaver"},
    {"full": "a brook that hums lullabies", "short": "the humming brook", "noun": "Brook"},
    {"full": "a pocket mouse with big ideas", "short": "the pocket mouse", "noun": "Mouse"},
    {"full": "a minstrel fox with a fiddle", "short": "the minstrel fox", "noun": "Fox"},
    {"full": "a kind ferryman heron", "short": "the ferryman heron", "noun": "Heron"},
    {"full": "a lantern-keeping moth", "short": "the lantern-keeper", "noun": "Lantern-keeper"},
    {"full": "a marmot who knew every tunnel", "short": "the marmot", "noun": "Marmot"},
    {"full": "a star-charting cricket", "short": "the cricket", "noun": "Cricket"},
    {"full": "a dew-collecting spider", "short": "the dew spider", "noun": "Spider"},
    {"full": "an echo with very good manners", "short": "the polite echo", "noun": "Echo"},
    {"full": "a patient stone giant", "short": "the stone giant", "noun": "Stone Giant"},
]

PROBLEMS = [
    {"full": "the stars have gone dim and sleepy", "short": "the dim stars", "noun": "Sleepy Stars", "why": "the stars had grown too tired to shine"},
    {"full": "the moon is running very late for bedtime", "short": "the late moon", "noun": "Late Moon", "why": "the moon had lost track of the hour"},
    {"full": "the river has forgotten its song", "short": "the quiet river", "noun": "Quiet River", "why": "the river's song had drifted away"},
    {"full": "the dreams are being delivered to the wrong sleepers", "short": "the mixed-up dreams", "noun": "Mixed-up Dreams", "why": "the dream-sacks had tumbled over"},
    {"full": "the wind has lost its way home", "short": "the lost wind", "noun": "Lost Wind", "why": "the wind had wandered too far"},
    {"full": "the harvest lanterns keep blowing out", "short": "the dark lanterns", "noun": "Dark Lanterns", "why": "a stray gust kept snuffing them"},
    {"full": "the last lullaby in the valley was forgotten", "short": "the forgotten lullaby", "noun": "Forgotten Lullaby", "why": "nobody could remember the tune"},
    {"full": "the north star has gone missing", "short": "the missing north star", "noun": "Missing North Star", "why": "the north star had slipped out of place"},
    {"full": "the clouds are hoarding all the rain", "short": "the stingy clouds", "noun": "Stingy Clouds", "why": "the clouds had forgotten how to share"},
    {"full": "winter has arrived far too early", "short": "the early winter", "noun": "Early Winter", "why": "the frost had woken up confused"},
    {"full": "the dawn bird is oversleeping", "short": "the sleepy dawn bird", "noun": "Sleepy Dawn Bird", "why": "the dawn bird's alarm had gone quiet"},
    {"full": "the migrating birds have lost their map", "short": "the mapless birds", "noun": "Mapless Birds", "why": "a storm had scattered their map"},
    {"full": "the meadow's colors have faded to grey", "short": "the grey meadow", "noun": "Grey Meadow", "why": "the colors had simply worn out"},
    {"full": "the village bell has lost its note", "short": "the silent bell", "noun": "Silent Bell", "why": "the bell's note had cracked softly"},
    {"full": "the sea has become far too quiet", "short": "the too-quiet sea", "noun": "Quiet Sea", "why": "the waves had forgotten how to murmur"},
    {"full": "the dreamsugar has run out", "short": "the empty dreamsugar jar", "noun": "Empty Dreamsugar", "why": "the last spoonful had been used up"},
    {"full": "the frost has tucked in the flowers too tightly", "short": "the tucked-in flowers", "noun": "Frosted Flowers", "why": "the frost had been a little too careful"},
    {"full": "the valley's echo has gone missing", "short": "the missing echo", "noun": "Missing Echo", "why": "the echo had wandered into a cave"},
    {"full": "the tide has forgotten when to turn", "short": "the still tide", "noun": "Still Tide", "why": "the tide had lost its clock"},
    {"full": "the moon's cradle has started to creak", "short": "the creaking cradle", "noun": "Creaking Cradle", "why": "the cradle's ropes had grown old"},
    {"full": "the sleepy trains are running out of steam", "short": "the weary trains", "noun": "Weary Trains", "why": "the steam had thinned to a whisper"},
    {"full": "the nightingales have lost their lullaby notes", "short": "the tuneless nightingales", "noun": "Tuneless Nightingales", "why": "their notes had blown away in a gale"},
]

QUESTS = [
    {"full": "climb to the tallest hill and ask the sky for help", "short": "the climb to the tall hill", "noun": "Tall Hill Climb"},
    {"full": "follow the river all the way to its sleepy source", "short": "the river journey", "noun": "River Journey"},
    {"full": "cross the whispering bridge just past midnight", "short": "the bridge crossing", "noun": "Whispering Bridge"},
    {"full": "sail a leaf-boat across the pond of reflected stars", "short": "the star-pond crossing", "noun": "Star-Pond Crossing"},
    {"full": "travel north, to where the cold stars keep their light", "short": "the journey north", "noun": "Journey North"},
    {"full": "find the cave where all the echoes sleep", "short": "the echo cave search", "noun": "Echo Cave"},
    {"full": "wake the dawn bird, gently, with a kind word", "short": "the dawn-bird errand", "noun": "Dawn-Bird Errand"},
    {"full": "trade kindness with the frost, until it loosens", "short": "the frost bargain", "noun": "Frost Bargain"},
    {"full": "mend what was broken, with thread and song", "short": "the mending", "noun": "Great Mending"},
    {"full": "carry the light to whoever needs it most", "short": "the light delivery", "noun": "Light Delivery"},
    {"full": "ask the oldest tree for one more story", "short": "the oldest-tree visit", "noun": "Oldest Tree"},
    {"full": "walk until the road itself turns soft and slow", "short": "the soft-road walk", "noun": "Soft Road"},
    {"full": "keep one small light burning through the longest night", "short": "the longest-night vigil", "noun": "Longest Night"},
    {"full": "return what was borrowed to the deep, deep woods", "short": "the giving-back", "noun": "Giving-Back"},
    {"full": "plant the tiny seed where nothing else will grow", "short": "the planting", "noun": "The Planting"},
    {"full": "follow a bell only {name} can hear", "short": "the bell chase", "noun": "Bell Chase"},
    {"full": "gather the scattered songs one by one", "short": "the song gathering", "noun": "Song Gathering"},
    {"full": "walk the shoreline until the sea speaks", "short": "the shoreline walk", "noun": "Shoreline Walk"},
]

MORALS = [
    {"full": "small hands can carry great light", "short": "small hands can carry great light"},
    {"full": "courage can be as quiet as a whisper", "short": "courage can be quiet"},
    {"full": "patience turns winter into spring", "short": "patience turns winter into spring"},
    {"full": "kindness always finds its way home", "short": "kindness finds its way home"},
    {"full": "listening is its own kind of magic", "short": "listening is magic"},
    {"full": "being gentle is a way of being strong", "short": "gentle is strong"},
    {"full": "every ending is a soft beginning", "short": "endings are beginnings"},
    {"full": "shared things shine brighter", "short": "shared things shine brighter"},
    {"full": "it is brave to ask for help", "short": "asking for help is brave"},
    {"full": "home is wherever you are loved", "short": "home is where you are loved"},
    {"full": "even the moon needs a little help sometimes", "short": "everyone needs help"},
    {"full": "worries shrink when they are spoken softly", "short": "soft words shrink worries"},
    {"full": "the best gifts are given slowly", "short": "good things come slowly"},
    {"full": "rest is not giving up", "short": "rest is not giving up"},
    {"full": "giving away light only makes more light", "short": "shared light grows"},
    {"full": "wonder is worth staying awake for", "short": "wonder is worth it"},
    {"full": "slow is its own kind of swift", "short": "slow can be swift"},
    {"full": "care keeps the whole world turning", "short": "care keeps the world turning"},
    {"full": "everyone drifts off, in their own time", "short": "everyone sleeps in their own time"},
    {"full": "the dark is full of friends, if you look", "short": "the dark is friendly"},
    {"full": "trust the pace of your own paws", "short": "trust your own pace"},
    {"full": "a promise kept is a warm little fire", "short": "kept promises are warm"},
]

TWISTS = [
    {"full": "the missing light had been following {name} all along", "noun": "Follower"},
    {"full": "the moon had only paused to listen to the lullaby", "noun": "Listening Moon"},
    {"full": "the wind simply wanted to be thanked", "noun": "Thankful Wind"},
    {"full": "the treasure had been the friends met along the way", "noun": "True Treasure"},
    {"full": "the song had been inside {name} the whole time", "noun": "Inside Song"},
    {"full": "the map quietly redrew itself, all the way home", "noun": "Home Map"},
    {"full": "the giant had only ever been lonely", "noun": "Lonely Giant"},
    {"full": "the winter had been protecting the sleeping seeds", "noun": "Kind Winter"},
    {"full": "the echo had been answering, all along, softly", "noun": "Soft Answer"},
    {"full": "the dream had been looking for {name}, too", "noun": "Searching Dream"},
    {"full": "the door would only open for the very sleepy", "noun": "Sleepy Door"},
    {"full": "the star had been waiting for exactly this kindness", "noun": "Waiting Star"},
    {"full": "the magic had been borrowed from {name}'s own kindness", "noun": "Borrowed Kindness"},
    {"full": "the night had been tucking the whole valley in", "noun": "Tucking Night"},
]

MOTIFS = [
    {"thing": "fireflies", "one": "firefly", "verb": "drifted"},
    {"thing": "falling feathers", "one": "feather", "verb": "floated"},
    {"thing": "small silver bells", "one": "bell", "verb": "chimed"},
    {"thing": "drifting leaves", "one": "leaf", "verb": "tumbled"},
    {"thing": "snowflakes", "one": "snowflake", "verb": "settled"},
    {"thing": "cocoa steam curls", "one": "curl of steam", "verb": "rose"},
    {"thing": "mossy stepping stones", "one": "stepping stone", "verb": "waited"},
    {"thing": "moth wings", "one": "moth", "verb": "flickered"},
    {"thing": "dewdrops", "one": "dewdrop", "verb": "sparkled"},
    {"thing": "shooting stars", "one": "shooting star", "verb": "slipped"},
    {"thing": "night birds", "one": "night bird", "verb": "called"},
    {"thing": "warm window lights", "one": "window light", "verb": "glowed"},
    {"thing": "cloud ships", "one": "cloud ship", "verb": "sailed"},
    {"thing": "grasshopper songs", "one": "song", "verb": "hushed"},
]

TITLE_PATTERNS = [
    "{name} and the {object_noun}",
    "The {object_noun} of {setting_title}",
    "{name} and the {problem_noun}",
    "The Night of the {problem_noun}",
    "{name}'s {quest_noun}",
    "The {companion_noun} and the {object_noun}",
    "{name} and the {motif_title}",
    "The {object_noun} and the Sleepy {setting_word}",
]

# ─────────────────────────────────────────────────────────────────────
# BEAT TEMPLATES — sixteen narrative beats, three variants each.
# Slots are filled with the SAME atom set for every scene, so any
# combination reads as one coherent, calm bedtime story.
# ─────────────────────────────────────────────────────────────────────

BEATS = [
    # 1 — HOOK
    {
        "id": "hook", "type": "exterior_night", "focus": "sky", "camera": "wide",
        "templates": [
            "Once upon {time_full}, in {setting_full}, {hero_full} named {name} looked up and noticed something unusual: {problem_full}. It was not a scary thing. It was a quiet thing, the kind of thing that makes the whole world hold its breath and listen. {name} {trait_phrase}, and so, instead of worrying, the little one simply tilted one ear toward the sky and wondered what to do. Somewhere above, {motif_thing} {motif_verb} as if the night itself were thinking.",
            "In {setting_full}, on {time_full}, everything was almost asleep. Almost. Because up in the sky above the trees, {problem_full}. {name}, {hero_short}, was the very first to notice. {hero_tiny_cap} blinked once, twice, and sat up very straight. This was not a trouble exactly. It was more like a question, written across the stars in soft, patient letters: who will help? And {name}'s heart, being {trait_adj}, answered before the rest of {hero_paws} could catch up.",
            "This is the story of {time_full} in {setting_full}, when {problem_full}. Down below, tucked in a small warm bed, {hero_full} named {name} was almost, almost asleep. But the night had other plans — gentle ones, promise. {name} heard the silence where {problem_short} used to be, and opened both round eyes. {hero_tiny_cap} was {trait_phrase}, and a {trait_adj} heart cannot ignore a night that needs a friend.",
        ],
    },
    # 2 — SETUP A: the cozy home
    {
        "id": "setup_home", "type": "interior_cozy", "focus": "hero", "camera": "medium",
        "templates": [
            "{name} lived in a small, round house at the edge of {setting_short}, with a squashy bed, a shelf of acorn cups, and one window shaped like a sleepy half-moon. On most evenings the routine was the same: cocoa, a story, a yawn, lights out. {hero_tiny_cap} was {trait_phrase}, which made bedtime easy. But tonight, through the half-moon window, the sky looked different, and {name} could not stop thinking about {problem_short}.",
            "Let me tell you about {name}'s house. It was small and warm and smelled faintly of pine needles and honey. {hero_tiny_cap} had a bed of moss, a quilt with patches the colors of dusk, and a night-lamp shaped like {motif_one}. Every night the same soft routine: wash {hero_paws}, brush fur, cocoa, one chapter, sleep. But this evening, {hero_tiny} paused at the window, cup halfway to lips, watching where {problem_short} ought to be.",
            "Home, for {name}, was a burrow-house with a round red door, tucked under the roots of the oldest tree in {setting_short}. Inside: a tiny stove, a kettle that whistled lullabies, and {hero_tiny}'s very favorite thing — {object_full}, given by a grandmother who said only, \"Use it on a night that needs you.\" {name} had never known such a night. Until this one. This one, with {problem_full}, looked exactly like a night that needed somebody.",
        ],
    },
    # 3 — SETUP B: the problem arrives
    {
        "id": "setup_problem", "type": "exterior_path", "focus": "hero", "camera": "wide",
        "templates": [
            "A soft knock came at the round red door — knock, knock, pause, knock. Outside stood {companion_full}, looking flustered in the way of someone carrying big news gently. \"{name},\" said {companion_short}, \"have you seen it? {problem_full}, and it won't mend itself. The valley needs someone small and steady. Someone exactly your size.\" {hero_tiny_cap} looked at {object_short}, still warm in {hero_paws}. And that was that. A {trait_adj} heart knows when it is being called.",
            "{companion_short} arrived first, as helpers often do, calling softly from the gate. \"{name}! {name}!\" the voice carried, kind but urgent. \"{problem_full} — the whole of {setting_short} can feel it. The flowers are droopier. The wind is shyer. Will you come and see?\" {name} pulled on a small knitted scarf, tucked {object_short} into a satchel, and stood a little taller. {hero_tiny_cap} was {trait_phrase}, and tonight, that was exactly what the night was short of.",
            "The message came on the breeze, the way urgent-but-polite messages do: a rustle at the window, then {companion_full}, tapping at the glass. \"Pardon the hour,\" said {companion_short}, \"but {problem_full}, and the night cannot fix it alone. We need {hero_paws} that are careful and a heart that is {trait_adj}. We need, if I am not mistaken, you.\" {name} took a long breath. Then nodded. Even bedtime can wait, sometimes, for kindness.",
        ],
    },
    # 4 — CHALLENGE 1: first steps
    {
        "id": "challenge_1", "type": "forest_path", "focus": "hero", "camera": "wide",
        "templates": [
            "So the journey began: {quest_full}. The first part was easy, almost fun — the path was soft, {motif_thing} {motif_verb} alongside like slow companions, and the dark between the trees felt friendly rather than deep. {name} walked with small, certain steps, {object_short} swinging gently. But every quest has its first true test, and this one arrived at the bend of the trail, where the path split into three, and none of the three looked sure.",
            "{name} set out to {quest_full}. {companion_short} led the way at first, pointing out roots to step over and branches to duck beneath. The forest at night is a different country: mossy, hushed, lit by {motif_thing} wherever they {motif_verb}. All went well until the first true difficulty — a stream, wide and dark and murmuring, with stepping stones spaced just a little too far apart for {hero_paws} like {name}'s.",
            "The plan was simple and the night was kind: {quest_full}, then home before the cocoa went cold. {name} knew the woods by daylight, but night-woods rearrange themselves. Shadows borrowed the shapes of friendly things; {motif_thing} {motif_verb} in the corners of {hero_tiny}'s eyes. When the little bridge over the first stream appeared — old, swaybacked, missing a plank — {name} stopped. {hero_tiny_cap} counted to three, the way the brave do, quietly, inside.",
        ],
    },
    # 5 — CHALLENGE 2: it gets harder
    {
        "id": "challenge_2", "type": "hill_climb", "focus": "hero", "camera": "medium",
        "templates": [
            "The stream was crossed (one careful paw at a time, {companion_short} cheering softly from the bank), but the night was not finished testing. The way grew steep — up, and up, along a ridge where the wind combed through the grass like a slow hand. {name}'s legs grew tired, the kind of tired that makes eyes want to close. {hero_tiny_cap} sat down on a smooth stone, just for a moment, and held {object_short} close. {object_warm_cap} felt like a small \"keep going\" wrapped around the heart.",
            "Past the bridge and the brambles, the trail climbed. And climbed. {name} is small, and the hill was not, and halfway up, {hero_tiny} began to understand why nobody else had volunteered for this. The sky, where {problem_short} waited to be mended, seemed no closer at all. {companion_short} landed nearby and said gently, \"You are exactly halfway. That is the hardest place. It is where most stories turn around.\" {name} did not turn around. {hero_tiny_cap} was {trait_phrase}, remember, and halfway is where that sort of thing shows.",
            "Challenge the second was quiet but heavy: not a monster, never a monster, just... a long way. The ridge rose and bent and rose again. {motif_thing} {motif_verb} along beside {name} like patient little lanterns. At the steepest part, {hero_tiny}'s ears drooped, {hero_paws} ached, and the warm bed at home felt very far away. Then {object_short} gave its softest glow, and the dark felt less like a wall and more like a blanket with the lights out.",
        ],
    },
    # 6 — MID-CALM: the helper teaches
    {
        "id": "helper_gift", "type": "forest_clearing", "focus": "companion", "camera": "medium",
        "templates": [
            "In a clearing near the top, they rested, and here {companion_short} earned the title of helper properly. \"Listen,\" said the old voice, \"before we go on. The trouble with {problem_short} is not that it is big. It is that it is tired, and tired things do not need heroes. They need patience. Patience, and someone willing to stay until it passes.\" {name} thought about that all the way through, twice. Then {hero_tiny} unpacked a snack, offered half, and the night felt suddenly, deeply friendly.",
            "{companion_short} stopped at the clearing and gestured at the sky. \"Now, the lesson,\" said the helper, \"which every traveler gets exactly once.\" And the lesson was this: \"{problem_short} cannot be forced. Only helped. Dark things are usually just things waiting to be understood.\" {name} nodded slowly. It sounded true — the sort of true that sits comfortably in the chest. {object_warm_cap} pulsed once, as if agreeing. From that moment, {hero_tiny} stopped hurrying, and the quest went from hard to merely long.",
            "They rested in the clearing while {companion_short} shared the only map that mattered: \"Kindness first. Then patience. Then one small light, kept lit.\" {name} repeated the three steps like a tiny poem — kindness, patience, light — until the words were tucked somewhere safe behind the ribs. {companion_short} smiled the way old helpers smile when a lesson lands. Above them, {motif_thing} {motif_verb}, and even {problem_short} seemed, very faintly, to be breathing easier.",
        ],
    },
    # 7 — CHALLENGE 3: the hardest gentle moment
    {
        "id": "challenge_3", "type": "high_place", "focus": "hero", "camera": "wide",
        "templates": [
            "The last stretch was the steepest and the quietest. Here even {companion_short} went slow, and {name} went slower, step by careful step, {object_short} held out like a tiny lantern against the enormous night. At the very top, the wind asked its question — the one every quest asks at least once: \"Are you sure you are the one?\" {hero_tiny_cap} stood very still. Then answered, honestly, \"No. But I am the one who came.\" And that, as it happens, is the correct answer. The wind moved aside.",
            "At the top of the world — or at least of {setting_short} — {name} finally stood close enough to see {problem_short} clearly. It was bigger than it looked from the bedroom window, and somehow also softer, like a great sleeping thing. The final test was not climbing. It was this: {hero_tiny} had to speak, out loud, alone, into all that bigness. {companion_short} stepped back, deliberately, to let the moment belong to the small one. {name} took a breath the size of a cocoa cup.",
            "The hardest part of the whole night came last, as hardest parts tend to do. To reach the place where {problem_short} could be reached at all, {name} had to cross the narrow neck of the ridge in the dark — no {motif_thing} there, no friendly lanterns, just the little circle of {object_warm}. One step. Pause. Another step. {hero_tiny_cap} was frightened in the smallest, most ordinary way, and went on anyway, which is the oldest definition of brave there is.",
        ],
    },
    # 8 — THE TURN: the object's magic works
    {
        "id": "turn", "type": "sky_reach", "focus": "object", "camera": "close",
        "templates": [
            "And then {name} did the simplest, bravest thing: lifted {object_short} up, high as {hero_paws} would reach, and offered it — not took, offered — to the night. What happened next, the valley would talk about for years, softly, at bedtime: {object_warm} unfolded, and unfolded again, until the whole sky was threaded through with a gentleness shaped like help. {problem_short} shivered once, like something waking from a long dream. Then, very slowly, it began to mend.",
            "\"Please,\" said {name}, out loud, in a voice smaller than a wish, \"let me help.\" And {object_short}, which had waited so many quiet years on its shelf for exactly this, finally did the thing it was made for. {object_warm_cap} reached upward like a slow, soft fountain of almost-morning. Wherever the light touched, {problem_short} eased — not all at once, but the way ice gives way to spring, in the order things are meant to.",
            "The magic, when it came, was quiet — no thunder, no flash. Just {name}, holding {object_short} steady, saying, \"I stayed. I stayed the whole way.\" And {object_warm} poured upward, patient as honey, until it found the exact places that hurt. {problem_short} softened under it, the way a frown softens in sleep. From the valley below, anyone still awake would have seen the sky over {setting_short} take one long, relieved breath.",
        ],
    },
    # 9 — RESOLUTION: mended
    {
        "id": "resolve", "type": "valley_view", "focus": "sky", "camera": "wide",
        "templates": [
            "Little by little, the night stitched itself back together. {problem_short} mended, and mended, and then — was simply itself again: whole, ordinary, wonderful. A cheer went up from the valley, the polite kind, mostly made of yawns. {companion_short} put a wing — a paw, a hand — on {name}'s shoulder. \"Well done, small one,\" the helper said. \"You did not fix the night by being big. You fixed it by being here.\" {hero_tiny_cap} watched the sky shine, and felt taller than the hill.",
            "What does mending look like? Like this: {motif_thing} returning one by one to their proper places, {motif_verbing} shyly at first, then confidently. Like {problem_short} gleaming as though nothing had ever been the matter. Like {companion_short} whispering, \"There. There, you see?\" over and over, until {name} believed it too. The valley below sighed its window-lights on, one warm square at a time. It was, everyone agreed later, the best kind of ordinary night.",
            "The mending took as long as it took, because real things do. When it was finished, the sky above {setting_short} was so gently, perfectly itself that {name} laughed — one small, surprised \"ha!\" that {companion_short} would repeat for seasons afterward, in imitation, at parties. The stars, the moon, the wind, the tide or dream or song — whatever had gone dim or late or lost — settled back into its own rhythm, like a sleeper rolling to a better pillow.",
        ],
    },
    # 10 — TWIST: the gentle reveal
    {
        "id": "twist", "type": "water_reflection", "focus": "sky", "camera": "close",
        "templates": [
            "Then came the part {name} did not expect. While {hero_tiny} leaned over the little spring at the hilltop to wash dusty {hero_paws}, the water held a surprise: a reflection that made everything clear at once. {twist_full}. That was the secret of the whole night — the mending had never really been about the sky at all. It had been, all along, also about a small one learning the size of their own heart. {companion_short} pretended not to smile. {hero_tiny_cap} smiled anyway, at both of them.",
            "\"There is one more thing,\" said {companion_short}, as they started down. \"A secret, now that the work is done.\" And the helper leaned close: \"{twist_full}.\" {name} sat right down on the path, astonishing a beetle. All that worry, all that climbing — and the night had been, in its own enormous way, walking beside {hero_tiny} the entire time. \"The best quests are like that,\" said {companion_short}. \"You never walk alone. You just walk un-noticed accompanied.\"",
            "Here is the gentle truth the night saved for last, and told only because {name} had earned it: {twist_full}. Not a trick — a gift, the kind that only shows itself after the helping is done. {name} carried it all the way home like a second, smaller light, next to the first. Some nights give you stars. This night, it turned out, had given {hero_tiny} something better: the knowledge that being small and being mighty are, at bedtime, exactly the same size.",
        ],
    },
    # 11 — MORAL: the lesson lands
    {
        "id": "moral", "type": "home_path", "focus": "hero", "camera": "medium",
        "templates": [
            "On the walk home, {name} turned the night over in thought, the way you turn a warm stone over in your {hero_paws}. The moon slid along beside them, above the trees, keeping easy pace. And {hero_tiny} understood, in the sleepy simple way that truest things arrive: {moral_full}. It had been true all along, of course. But now it was true and had been walked in, all the way through, by {hero_tiny}'s own four feet.",
            "\"Do you know what you learned?\" asked {companion_short}, somewhere in the last stretch of trees. {name} thought hard. Bedtime thoughts come slow and soft, like moths. \"{moral_cap}?\" said {name}, half-asking. \"{moral_cap},\" agreed the helper, \"exactly. Sleep on it. That is how lessons set, like good jelly.\" And the two of them walked on, and the trees overhead bent slightly, the way proud trees do.",
            "The road home felt shorter than the road out — roads are kind that way after good work. {name} felt the lesson settling somewhere near the heart, warm as {object_short} had been at the very start: {moral_full}. Say it once more, softly, the way the night said it to the valley: {moral_full}. There. Now it is yours. It will still be true tomorrow, and after, and after that.",
        ],
    },
    # 12 — RETURN: journey home
    {
        "id": "return", "type": "path_night", "focus": "hero", "camera": "wide",
        "templates": [
            "Down the hill they went, the quest folded up and put away like a quilt. {motif_thing} {motif_verb} along the path home, lighting it in small, polite doses. {companion_short} walked {name} the whole way to the round red door, as helpers do, then tipped a wing or a hat. \"Same time never,\" said the old friend. \"May you always sleep, and only sometimes be needed.\" It was the nicest goodnight the valley ever invented.",
            "The way back was all downhill and easy breathing. {name}'s {hero_paws} knew every root now, every stone, and the forest had gone back to being its friendly night-self: mossy, murmuring, full of small snoring sounds from nests and burrows. At the door, {companion_short} waited until the latch clicked before leaving — a rule among good helpers. \"Sleep deeply, {name},\" came the voice, already fading into the trees. \"You have earned the good kind of tired.\"",
            "Home never looks so homey as at the end of a quest. The round red door. The window shaped like a half-moon, now with the mended sky glinting above it. {name} said goodnight to {companion_short} at the gate, thanked {object_short} with a small polish of one sleeve, and stood one extra moment under the vast, ordinary, miraculous night. Then, because even heroes have bedtimes, the little one went inside.",
        ],
    },
    # 13 — TUCK-IN: home interior
    {
        "id": "tuck_in", "type": "interior_cozy", "focus": "hero", "camera": "medium",
        "templates": [
            "Inside, everything was exactly as it had been left — cocoa cup, quilt, the dent in the pillow shaped like hope. {name} set {object_short} back on its shelf, in its same spot, though it would never quite be an ordinary {object_noun_lower} again; it had been used, and things remember being used. {hero_tiny_cap} washed the travel off of tired {hero_paws}, buttoned the longest yawn of the year, and climbed into the bed of moss and dusk-colored patches.",
            "The kettle had kept the last of the water warm, which was lucky, because adventurers deserve cocoa. {name} drank it slowly, watching through the half-moon window as the sky — the fixed, generous, re-lit sky — went about its quiet business. {object_short} sat on the shelf, giving off one small smug glow, like a job well done. {hero_tiny_cap} brushed fur, tucked the quilt to the chin, and felt the day begin, at last, to let go.",
            "Do you know the best part of every quest? The bed at the end of it. {name}'s bed had never felt so much like a cloud, and the quilt had never been so heavy in the good way, like being tucked in by the whole night sky. {object_short} got a goodnight pat. The pillow got a head. The small round house at the edge of {setting_short} settled into its creaks and sighs, and everything in it began, gently, to float.",
        ],
    },
    # 14 — SLEEP CLOSE A: wind-down
    {
        "id": "sleep_a", "type": "interior_night", "focus": "hero", "camera": "medium",
        "templates": [
            "Now, listener, the story is almost done, and it is time to get sleepy too, just like {name}. Lie down flat and still. Let your arms go soft, like ribbons in a slow stream. Feel the bed holding you up, the way the hill held up the whole sky tonight. Breathe in... and out, slow, like the gentle wind. In... and out. {name} is doing the very same thing, in {setting_short}, eyes fluttering once — then half closed — then barely at all.",
            "Feel your feet get heavy — warm-stone heavy, the good kind. Feel your legs get heavy. Let your shoulders soften down away from your ears, like leaves settling. The room you are in is safe, the way {name}'s little house is safe, the way the whole valley is safe now, tonight, because someone small was brave. Breathe in slowly... and out even slower. There is nothing left to do tonight. Nothing at all. Only this: breathing, and getting heavier, and being held.",
            "In {setting_short}, {name} is drifting off, one sleepy thought at a time. You can drift too. Let your breathing find a slow rhythm, like the tide in Lullaby Loch — in, filling up like a small round moon... and out, empty, calm. Your eyes are heavy now. That is just fine. That is exactly what eyes are for at this hour. Let them close when they want to. The story will keep going, soft as ever, until you are deep, deep, deep asleep.",
        ],
    },
    # 15 — SLEEP CLOSE B: deepening
    {
        "id": "sleep_b", "type": "interior_night", "focus": "hero", "camera": "close",
        "templates": [
            "{name} is dreaming now — about {object_noun_lower}, and hills, and a voice like {companion_short}'s telling the story of this very night, to someone very small, somewhere. Dreams are funny like that: they pass the good things along. You can pass this along too, into your own dream: a lantern, a hill, a mended sky, and the softest fact of all — {moral_full}. Let it be the last thing you think. Let it follow you down into sleep, like a friendly tail.",
            "The whole valley is asleep now. The trees, the brook, the moon in its newly steady cradle. Even {problem_short} has gone back to being just another lovely part of the night. And {name}, tucked in under the constellations, breathes slow as honey pouring — in... and out... — with {object_short} glowing one soft final glow on its shelf, keeping watch the way it always will, whenever a night needs it. You can trust that. Nights like this can be trusted.",
            "Shhh. The house is settling. {hero_tiny_cap} is nearly, nearly under. Whatever was mended tonight stays mended. Whatever was learned — {moral_full} — stays learned, tucked safe behind your ribs where the important things live. Your breathing and {name}'s breathing are doing the same slow dance now, in and out, in and out, two small creatures in two small beds, under one enormous, friendly, well-earned night.",
        ],
    },
    # 16 — GOODNIGHT
    {
        "id": "goodnight", "type": "window_night", "focus": "sky", "camera": "wide",
        "templates": [
            "Goodnight, {name}. Goodnight, {companion_short}. Goodnight, {object_noun_lower}, goodnight hill, goodnight mended and whole night sky. Goodnight, listener. Sleep as soundly as {setting_short} does tonight. The moon will keep the light on for you — dim, and warm, and always, always enough. Goodnight. Goodnight. Goodnight.",
            "The stars over {setting_short} are at their post again, bright and calm and right where they belong. Down in the small round house, one {hero_base} is fast asleep, smiling the tiny smile of a day well spent. And you, listener? Your eyes are closed, or almost. That is perfect. That is the story doing its job. Goodnight, small friend. Goodnight, big night. Goodnight, Moonberry Tales.",
            "So ends tonight's tale: not with a bang, but with a blanket, pulled up to the chin of the world. {name} sleeps. {setting_short} sleeps. The story, having done its work, folds itself up and slides quietly onto the shelf beside {object_short}, ready for tomorrow's little listener. Goodnight. Sleep well. The night is mended, and so are you.",
        ],
    },
]

# Extra calm sensory sentences — sprinkled when word count runs short.
EXPANSIONS = [
    "{name} counted the {motif_thing} until the numbers went soft and round at the edges.",
    "Somewhere far off, an owl called once, politely, and then thought better of it.",
    "{object_warm_cap} made a small warm circle on the path, like a rug of light.",
    "The night smelled of pine, cool stone, and the ghost of cocoa.",
    "{name}'s ears twitched at a sound that turned out to be only the night turning a page.",
    "Above the trees, the sky arranged its stars with great care, like a patient shopkeeper.",
    "{companion_short_cap} hummed four notes of a tune that had no hurry in it at all.",
    "The moss took each footprint gently and kept it safe, the way moss does.",
    "A breeze passed through and touched the top of {name}'s head, like a grandmother checking for fever.",
    "Far below, one window light came on, then thought better of it, and dimmed back to dreaming.",
    "{hero_tiny_cap} felt very small and very much exactly the right size, all at once.",
    "The path curved the way sleepy paths do, as if the road itself were stretching before bed.",
    "Everything was quiet, but it was the full kind of quiet, with the whole night folded into it.",
    "{object_short} grew faintly warmer, the way pockets do when they are being useful.",
    "Overhead, {motif_thing} {motif_verb} in no hurry at all, keeping the sky company.",
    "The dark between the trees was thick and kind, like a blanket with the lights out.",
]

# Words that must never appear (safety gate). Word-boundary matching.
BLOCKED = {
    # brand / franchise names (originality gate)
    "disney", "pixar", "dreamworks", "cinderella", "rapunzel", "snow white",
    "peter pan", "little mermaid", "aladdin", "hansel", "gretel",
    "rumpelstiltskin", "pinocchio", "frozen", "elsa", "mickey", "shrek",
    "nemo", "dory", "pocahontas", "moana", "mulan", "fiona", "golem",
    # violence / scary
    "kill", "killed", "blood", "bloody", "wound", "knife", "gun", "sword",
    "die", "died", "dead", "death", "murder", "torture", "scream",
    "nightmare", "monster", "demon", "devil", "ghost", "corpse", "funeral",
    "war", "weapon", "bullet", "stab", "strangle", "hang", "hanged",
    # adult / inappropriate
    "alcohol", "beer", "wine", "drunk", "cigarette", "drug", "sexy", "kiss me",
    "stupid", "idiot", "hate", "ugly", "dumb",
}

SOFT_OK = {"windy"}  # never blocked; reserved
