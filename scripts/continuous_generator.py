#!/usr/bin/env python3
"""
Continuous Book Generator - High-Selling Romance Subgenres

Based on market research (2024-2025):
- Romance: $1.44B annual sales, 300M+ monthly KU page reads
- Romantasy: 31% of Top 100 Romance bestsellers
- Dark Romance: Fastest growing, 4.2B BookTok views
- Contemporary Romance: 67% of Top 100
  - Hockey Romance: 11%
  - Romantic Comedy: 9%
  - Small Town: 8%
- Historical Romance: Up 217% since Bridgerton

Popular tropes: enemies-to-lovers, forced proximity, fated mates,
morally grey heroes, one bed, slow burn, found family
"""

import os
import sys
import json
import random
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add scripts directory and parent to path for lib imports
SCRIPT_DIR = Path(__file__).parent
BOOKCLI_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(BOOKCLI_DIR))

from lib.logging_config import setup_logging, get_logger
from lib.config import get_config

from book_factory import BookFactory, BookConfig, Genre, BookResult

# Initialize centralized logging
setup_logging()
config = get_config()


# ============================================================================
# HIGH-SELLING SUBGENRES
# ============================================================================

class Subgenre(Enum):
    """High-selling subgenres across all fiction categories."""
    # Romance subgenres
    ROMANTASY_FAE = "romantasy_fae"
    ROMANTASY_DRAGON = "romantasy_dragon"
    ROMANTASY_ACADEMY = "romantasy_academy"
    DARK_ROMANCE = "dark_romance"
    MAFIA_ROMANCE = "mafia_romance"
    HOCKEY_ROMANCE = "hockey_romance"
    SPORTS_ROMANCE = "sports_romance"
    SMALL_TOWN = "small_town_romance"
    ROMANTIC_COMEDY = "romantic_comedy"
    GOTHIC_ROMANCE = "gothic_romance"
    PARANORMAL_SHIFTER = "paranormal_shifter"
    PARANORMAL_VAMPIRE = "paranormal_vampire"
    HISTORICAL_REGENCY = "historical_regency"
    HISTORICAL_VICTORIAN = "historical_victorian"
    BILLIONAIRE = "billionaire_romance"
    SECOND_CHANCE = "second_chance_romance"
    ENEMIES_TO_LOVERS = "enemies_to_lovers"
    FORCED_PROXIMITY = "forced_proximity"
    # Thriller subgenres
    PSYCHOLOGICAL_THRILLER = "psychological_thriller"
    TECH_THRILLER = "tech_thriller"
    CONSPIRACY_THRILLER = "conspiracy_thriller"
    SURVIVAL_THRILLER = "survival_thriller"
    CRIME_THRILLER = "crime_thriller"
    # Mystery subgenres
    COZY_MYSTERY = "cozy_mystery"
    POLICE_PROCEDURAL = "police_procedural"
    AMATEUR_SLEUTH = "amateur_sleuth"
    # Sci-Fi subgenres
    SPACE_OPERA = "space_opera"
    CYBERPUNK = "cyberpunk"
    POST_APOCALYPTIC = "post_apocalyptic"
    FIRST_CONTACT = "first_contact"
    # Horror subgenres
    SUPERNATURAL_HORROR = "supernatural_horror"
    PSYCHOLOGICAL_HORROR = "psychological_horror"
    COSMIC_HORROR = "cosmic_horror"
    # Fantasy subgenres (non-romance)
    EPIC_FANTASY = "epic_fantasy"
    URBAN_FANTASY = "urban_fantasy"
    GRIMDARK = "grimdark"
    # Literary
    LITERARY_UPMARKET = "literary_upmarket"
    # Non-Fiction
    SELF_HELP = "self_help"
    BUSINESS = "business"
    PRODUCTIVITY = "productivity"
    FINANCE = "personal_finance"
    HEALTH_WELLNESS = "health_wellness"
    PSYCHOLOGY = "psychology"
    HOW_TO = "how_to"


# ============================================================================
# SUBGENRE PROFILES
# ============================================================================

SUBGENRE_PROFILES = {
    Subgenre.ROMANTASY_FAE: {
        "name": "Fae Romantasy",
        "genre": Genre.FANTASY,
        "market_share": 0.15,  # 15% weight
        "description": "Fae courts, magical powers, political intrigue",
        "tropes": ["enemies to lovers", "fated mates", "forced proximity", "slow burn", "morally grey hero"],
        "settings": ["Night Court", "Autumn Court", "Underground Fae Kingdom", "Magical Academy", "War-torn realm"],
        "hero_types": ["High Lord", "Dark Fae Prince", "Shadowy spymaster", "Fallen warrior", "Cursed king"],
        "heroine_types": ["Human with hidden powers", "Banished princess", "Mortal spy", "Healer with secrets", "Warrior in training"],
        "conflicts": ["forbidden love across courts", "ancient prophecy", "war between realms", "curse to break", "political marriage"],
        "heat_level": "steamy",
        "word_target": 35000,
        "author_style": "fantasy_epic",
        "cover_mood": "magical, ethereal, dark fantasy, fae court, mystical forest",
    },

    Subgenre.ROMANTASY_DRAGON: {
        "name": "Dragon Romantasy",
        "genre": Genre.FANTASY,
        "market_share": 0.12,
        "description": "Dragon riders, bonds, military academy",
        "tropes": ["bonded pairs", "enemies to lovers", "academy setting", "found family", "slow burn"],
        "settings": ["Dragon rider academy", "Mountain fortress", "War college", "Dragon territory", "Sky citadel"],
        "hero_types": ["Elite dragon rider", "Scarred war hero", "Ruthless commander", "Rival cadet", "Forbidden dragon prince"],
        "heroine_types": ["Underestimated cadet", "Rebel with a secret", "Strategist hiding her past", "Survivor seeking revenge", "Outsider with rare gift"],
        "conflicts": ["deadly competition", "war against invaders", "forbidden bond", "betrayal from within", "ancient dragon magic awakening"],
        "heat_level": "steamy",
        "word_target": 35000,
        "author_style": "fantasy_epic",
        "cover_mood": "dragons, epic fantasy, warrior, mountain fortress, dramatic sky",
    },

    Subgenre.ROMANTASY_ACADEMY: {
        "name": "Academy Romantasy",
        "genre": Genre.FANTASY,
        "market_share": 0.10,
        "description": "Magical schools, rivalries, dark secrets",
        "tropes": ["bully romance", "enemies to lovers", "secret identity", "forbidden magic", "chosen one"],
        "settings": ["Elite magical academy", "Ancient university", "Hidden school for gifted", "Underground training facility"],
        "hero_types": ["Dark prince of the academy", "Mysterious scholarship student", "Ruthless heir", "Brooding outcast"],
        "heroine_types": ["Scholarship student hiding powers", "Fallen noble", "Human among supernaturals", "Amnesiac with deadly past"],
        "conflicts": ["class warfare", "dark magic addiction", "secret society", "deadly trials", "forbidden relationship"],
        "heat_level": "steamy",
        "word_target": 32000,
        "author_style": "fantasy_epic",
        "cover_mood": "gothic academy, dark castle, magical, mysterious, young adult dark",
    },

    Subgenre.DARK_ROMANCE: {
        "name": "Dark Romance",
        "genre": Genre.ROMANCE,
        "market_share": 0.12,
        "description": "Morally grey heroes, intense, obsessive love",
        "tropes": ["captive romance", "obsessive hero", "morally grey", "redemption arc", "possessive love"],
        "settings": ["Criminal underworld", "Isolated estate", "Underground organization", "War-torn country", "Hidden compound"],
        "hero_types": ["Ruthless crime lord", "Damaged assassin", "Obsessive stalker with reasons", "Morally corrupt billionaire", "Dark protector"],
        "heroine_types": ["Captive who challenges him", "Woman on the run", "Undercover agent", "Innocent caught in his world", "His equal in darkness"],
        "conflicts": ["captor/captive tension", "revenge plot", "past trauma", "impossible choices", "enemies closing in"],
        "heat_level": "explicit",
        "word_target": 30000,
        "author_style": "dark_gothic",
        "cover_mood": "dark, intense, shadowy figure, mysterious, dangerous",
    },

    Subgenre.MAFIA_ROMANCE: {
        "name": "Mafia Romance",
        "genre": Genre.ROMANCE,
        "market_share": 0.10,
        "description": "Organized crime, arranged marriages, dangerous men",
        "tropes": ["arranged marriage", "enemies to lovers", "protective hero", "forbidden love", "revenge"],
        "settings": ["New York crime family", "Italian mafia compound", "Las Vegas empire", "Chicago underworld", "Russian bratva territory"],
        "hero_types": ["Mafia don", "Ruthless underboss", "Cold-blooded enforcer", "Heir to the empire", "Reformed killer"],
        "heroine_types": ["Rival family's daughter", "Innocent bargaining chip", "Undercover FBI agent", "Woman seeking revenge", "His arranged bride"],
        "conflicts": ["family loyalty vs love", "gang war", "betrayal from within", "FBI investigation", "blood debt"],
        "heat_level": "explicit",
        "word_target": 30000,
        "author_style": "strong_masculine",
        "cover_mood": "dark urban, man in suit, dangerous, luxurious, noir",
    },

    Subgenre.HOCKEY_ROMANCE: {
        "name": "Hockey Romance",
        "genre": Genre.ROMANCE,
        "market_share": 0.11,
        "description": "Professional athletes, team dynamics, small town charm",
        "tropes": ["grumpy/sunshine", "brother's best friend", "fake dating", "forced proximity", "second chance"],
        "settings": ["NHL team", "College hockey", "Small town team", "Training camp", "Road trip"],
        "hero_types": ["Star player with walls up", "Grumpy team captain", "Charming playboy", "Injured player seeking comeback", "Enforcer with a soft side"],
        "heroine_types": ["Team PR manager", "Best friend's sister", "Physical therapist", "Sports journalist", "His childhood friend"],
        "conflicts": ["no-dating rule", "media scandal", "career vs relationship", "past heartbreak", "team rivalry"],
        "heat_level": "steamy",
        "word_target": 28000,
        "author_style": "punchy_unisex",
        "cover_mood": "athletic, ice rink, man with jersey, sports, winter",
    },

    Subgenre.SMALL_TOWN: {
        "name": "Small Town Romance",
        "genre": Genre.ROMANCE,
        "market_share": 0.08,
        "description": "Cozy communities, returning home, found family",
        "tropes": ["return to hometown", "grumpy/sunshine", "single parent", "second chance", "fake dating"],
        "settings": ["Coastal town", "Mountain village", "Southern small town", "Midwestern farm community", "New England harbor town"],
        "hero_types": ["Brooding rancher", "Grumpy bar owner", "Single dad", "Returning veteran", "Local sheriff"],
        "heroine_types": ["Big city woman starting over", "Returning for family", "New business owner", "Single mom", "Inheriting grandmother's house"],
        "conflicts": ["small town gossip", "past mistakes", "family expectations", "city vs country life", "old flames"],
        "heat_level": "moderate",
        "word_target": 28000,
        "author_style": "soft_feminine",
        "cover_mood": "cozy small town, countryside, warm lighting, charming, romantic",
    },

    Subgenre.ROMANTIC_COMEDY: {
        "name": "Romantic Comedy",
        "genre": Genre.ROMANCE,
        "market_share": 0.09,
        "description": "Witty banter, mishaps, feel-good endings",
        "tropes": ["enemies to lovers", "fake dating", "opposites attract", "workplace romance", "bet/dare"],
        "settings": ["Publishing house", "Wedding planning business", "Tech startup", "TV show set", "Destination wedding"],
        "hero_types": ["Charming rival", "Uptight boss", "Best friend you shouldn't want", "Celebrity in disguise", "The one that got away"],
        "heroine_types": ["Ambitious career woman", "Disaster-prone optimist", "Jaded romantic", "Wedding planner unlucky in love", "Underdog fighting for her dream"],
        "conflicts": ["professional rivalry", "wedding chaos", "mistaken identity", "family meddling", "career vs love"],
        "heat_level": "moderate",
        "word_target": 28000,
        "author_style": "punchy_unisex",
        "cover_mood": "bright, fun, colorful, cheerful, illustrated style",
    },

    Subgenre.GOTHIC_ROMANCE: {
        "name": "Gothic Romance",
        "genre": Genre.ROMANCE,
        "market_share": 0.06,
        "description": "Atmospheric, mysterious, dark mansions, secrets",
        "tropes": ["mysterious hero", "gothic mansion", "dark secrets", "isolation", "slow burn"],
        "settings": ["Crumbling estate", "Isolated castle", "Fog-shrouded moor", "Haunted manor", "Remote island"],
        "hero_types": ["Brooding lord", "Mysterious recluse", "Man with a dark past", "Tortured artist", "Cursed nobleman"],
        "heroine_types": ["New governess", "Distant relative inheriting estate", "Woman fleeing scandal", "Researcher uncovering secrets", "Bride with suspicions"],
        "conflicts": ["family curse", "missing first wife", "supernatural occurrences", "buried secrets", "dangerous obsession"],
        "heat_level": "sensual",
        "word_target": 32000,
        "author_style": "dark_gothic",
        "cover_mood": "gothic mansion, misty, dark, atmospheric, mysterious, Victorian",
    },

    Subgenre.PARANORMAL_SHIFTER: {
        "name": "Shifter Romance",
        "genre": Genre.FANTASY,
        "market_share": 0.08,
        "description": "Wolf shifters, pack dynamics, fated mates",
        "tropes": ["fated mates", "rejected mate", "alpha hero", "pack politics", "enemies to lovers"],
        "settings": ["Remote pack territory", "Hidden supernatural town", "Mountain wolf pack", "Urban shifter community", "Pack compound"],
        "hero_types": ["Alpha of the pack", "Lone wolf", "Rejected alpha", "Beta with secrets", "Rival pack leader"],
        "heroine_types": ["Human discovering shifter world", "Omega with hidden strength", "Alpha female", "Mate who rejected him", "Enemy pack's daughter"],
        "conflicts": ["pack war", "forbidden mate bond", "rogue shifters", "human discovery threat", "alpha challenge"],
        "heat_level": "explicit",
        "word_target": 30000,
        "author_style": "fantasy_epic",
        "cover_mood": "wolf, moonlight, forest, supernatural, muscular man, wild",
    },

    Subgenre.PARANORMAL_VAMPIRE: {
        "name": "Vampire Romance",
        "genre": Genre.FANTASY,
        "market_share": 0.06,
        "description": "Immortal love, blood bonds, dark seduction",
        "tropes": ["mortal/immortal", "blood bond", "enemies to lovers", "forbidden love", "redemption"],
        "settings": ["Gothic mansion", "Underground vampire society", "Modern city with hidden supernatural", "Ancient castle", "Vampire court"],
        "hero_types": ["Ancient vampire lord", "Vampire prince", "Reluctant immortal", "Vampire hunter turned", "Master of the city"],
        "heroine_types": ["Human he can't resist", "Vampire hunter", "His fated blood mate", "Dhampir seeking answers", "Human with special blood"],
        "conflicts": ["vampire politics", "human vs immortal love", "blood addiction", "ancient enemies", "forbidden feeding"],
        "heat_level": "steamy",
        "word_target": 30000,
        "author_style": "dark_gothic",
        "cover_mood": "dark, gothic, vampire, blood red accents, mysterious, seductive",
    },

    Subgenre.HISTORICAL_REGENCY: {
        "name": "Regency Romance",
        "genre": Genre.HISTORICAL,
        "market_share": 0.07,
        "description": "Balls, ton scandals, witty dialogue, Bridgerton-style",
        "tropes": ["marriage of convenience", "rake reformed", "wallflower transformation", "enemies to lovers", "scandal"],
        "settings": ["London Season", "Country estate", "Bath society", "Ton ballroom", "Scottish Highlands"],
        "hero_types": ["Rakish duke", "Brooding earl", "Charming viscount", "Scarred war hero", "Reformed rake"],
        "heroine_types": ["Wallflower with wit", "Ruined lady seeking redemption", "Bluestocking", "Spinster by choice", "Scandalous widow"],
        "conflicts": ["ton scandal", "family debt", "past rake reputation", "class differences", "family feud"],
        "heat_level": "steamy",
        "word_target": 32000,
        "author_style": "classic_literary",
        "cover_mood": "regency dress, elegant, ballroom, estate, romantic, period costume",
    },

    Subgenre.HISTORICAL_VICTORIAN: {
        "name": "Victorian Romance",
        "genre": Genre.HISTORICAL,
        "market_share": 0.05,
        "description": "Gaslight era, industrial age, forbidden desires",
        "tropes": ["class differences", "forbidden love", "gothic elements", "slow burn", "marriage of convenience"],
        "settings": ["London fog", "Industrial city", "Country manor", "Scotland", "Gaslit streets"],
        "hero_types": ["Self-made industrialist", "Titled lord with secrets", "Detective", "Doctor with dark past", "Inventor"],
        "heroine_types": ["Governess", "Factory owner's daughter", "Widow with secrets", "Reform-minded lady", "Woman in disguise"],
        "conflicts": ["class warfare", "industrial dangers", "societal expectations", "past scandals", "family secrets"],
        "heat_level": "sensual",
        "word_target": 32000,
        "author_style": "classic_literary",
        "cover_mood": "Victorian era, gaslight, foggy London, elegant, period costume, mysterious",
    },

    Subgenre.BILLIONAIRE: {
        "name": "Billionaire Romance",
        "genre": Genre.ROMANCE,
        "market_share": 0.06,
        "description": "Wealth, power, glamorous lifestyle, control",
        "tropes": ["boss/employee", "contract relationship", "opposites attract", "protective hero", "rags to riches"],
        "settings": ["Manhattan penthouse", "Private island", "Corporate empire", "Luxury yacht", "International cities"],
        "hero_types": ["Tech billionaire", "Hotel empire heir", "Self-made CEO", "Mysterious tycoon", "Ruthless businessman"],
        "heroine_types": ["His assistant", "Woman who doesn't know his wealth", "Single mom in need", "Business rival", "The one he can't buy"],
        "conflicts": ["power imbalance", "gold-digger accusations", "corporate sabotage", "family disapproval", "trust issues"],
        "heat_level": "steamy",
        "word_target": 28000,
        "author_style": "punchy_unisex",
        "cover_mood": "luxury, city skyline, man in suit, glamorous, wealthy lifestyle",
    },

    Subgenre.SECOND_CHANCE: {
        "name": "Second Chance Romance",
        "genre": Genre.ROMANCE,
        "market_share": 0.05,
        "description": "Reunited lovers, past mistakes, rekindled flames",
        "tropes": ["ex returns", "secret baby", "reunion", "unfinished business", "forgiveness"],
        "settings": ["Hometown", "Class reunion", "Forced work together", "Family emergency", "Wedding brings them together"],
        "hero_types": ["The one who left", "First love returning", "Ex-husband", "Former best friend", "The one she never forgot"],
        "heroine_types": ["Woman who moved on", "Single mom with his child", "Successful woman he left behind", "Widow of his best friend", "The one who got away"],
        "conflicts": ["why he left", "secret she kept", "old wounds", "new relationships", "family interference"],
        "heat_level": "steamy",
        "word_target": 28000,
        "author_style": "soft_feminine",
        "cover_mood": "emotional, couple silhouette, sunset, nostalgic, romantic",
    },

    # ========================================================================
    # THRILLER SUBGENRES
    # ========================================================================

    Subgenre.PSYCHOLOGICAL_THRILLER: {
        "name": "Psychological Thriller",
        "genre": Genre.THRILLER,
        "market_share": 0.10,
        "description": "Mind games, unreliable narrators, dark secrets",
        "tropes": ["unreliable narrator", "gaslighting", "past trauma", "identity crisis", "obsession"],
        "settings": ["Suburban home with secrets", "Isolated house", "Psychiatric facility", "Small town with dark history", "Corporate office"],
        "hero_types": ["Detective with demons", "Therapist who knows too much", "Witness to horror", "Man searching for truth", "FBI profiler"],
        "heroine_types": ["Woman with missing memory", "Survivor questioning reality", "Wife with suspicions", "Sister seeking answers", "Therapist drawn in"],
        "conflicts": ["what really happened", "who to trust", "suppressed memories", "stalker or paranoia", "family secrets"],
        "heat_level": "none",
        "word_target": 30000,
        "author_style": "punchy_unisex",
        "cover_mood": "dark, ominous, psychological, shadowy face, suspenseful",
    },

    Subgenre.TECH_THRILLER: {
        "name": "Tech Thriller",
        "genre": Genre.THRILLER,
        "market_share": 0.08,
        "description": "Technology gone wrong, hackers, AI dangers",
        "tropes": ["whistleblower", "AI threat", "surveillance state", "corporate conspiracy", "hacker protagonist"],
        "settings": ["Silicon Valley", "Tech startup", "Government agency", "Server farms", "Cryptocurrency world"],
        "hero_types": ["Brilliant hacker", "Disillusioned engineer", "Investigative journalist", "Cybersecurity expert", "AI researcher"],
        "heroine_types": ["Whistleblower programmer", "Tech CEO with ethics", "NSA analyst gone rogue", "Data scientist uncovers plot", "AI safety researcher"],
        "conflicts": ["AI consciousness awakening", "data breach with consequences", "surveillance overreach", "tech billionaire power grab", "deepfake weaponization"],
        "heat_level": "none",
        "word_target": 32000,
        "author_style": "punchy_unisex",
        "cover_mood": "technology, digital, code, cybernetic, futuristic cityscape",
    },

    Subgenre.CONSPIRACY_THRILLER: {
        "name": "Conspiracy Thriller",
        "genre": Genre.THRILLER,
        "market_share": 0.08,
        "description": "Hidden powers, secret societies, cover-ups",
        "tropes": ["uncovering the truth", "trusted institutions are corrupt", "lone wolf vs system", "ancient secret", "whistleblower"],
        "settings": ["Washington DC", "Vatican", "Wall Street", "Military base", "Research facility"],
        "hero_types": ["Journalist on the trail", "Former agent turned target", "Conspiracy theorist who's right", "Historian finds truth", "Lawyer uncovers corruption"],
        "heroine_types": ["Investigative reporter", "Government insider", "Daughter of murdered official", "Scientist who discovered too much", "Archivist finds evidence"],
        "conflicts": ["powerful enemies want silence", "evidence keeps disappearing", "trusted allies are compromised", "race against assassination", "expose vs survival"],
        "heat_level": "none",
        "word_target": 32000,
        "author_style": "punchy_unisex",
        "cover_mood": "government buildings, shadows, conspiracy, documents, tense atmosphere",
    },

    Subgenre.SURVIVAL_THRILLER: {
        "name": "Survival Thriller",
        "genre": Genre.THRILLER,
        "market_share": 0.06,
        "description": "Man vs nature, isolation, primal survival",
        "tropes": ["stranded", "hunted", "limited resources", "environmental disaster", "rescue against odds"],
        "settings": ["Remote wilderness", "Crashed plane", "Sinking ship", "Post-disaster city", "Arctic expedition"],
        "hero_types": ["Survivalist expert", "Ordinary man tested", "Soldier behind lines", "Explorer in wilderness", "Father protecting family"],
        "heroine_types": ["Solo adventurer", "Mother surviving for child", "Scientist on expedition", "Crash survivor", "Woman hunted in wilderness"],
        "conflicts": ["nature's fury", "limited supplies", "injury and illness", "human predators", "psychological breakdown"],
        "heat_level": "none",
        "word_target": 28000,
        "author_style": "punchy_unisex",
        "cover_mood": "wilderness, survival, dramatic landscape, isolation, harsh environment",
    },

    Subgenre.CRIME_THRILLER: {
        "name": "Crime Thriller",
        "genre": Genre.THRILLER,
        "market_share": 0.09,
        "description": "Criminal underworld, heists, revenge",
        "tropes": ["heist gone wrong", "criminal code", "double cross", "one last job", "revenge"],
        "settings": ["Underground crime world", "Prison", "Cartel territory", "Money laundering operation", "Diamond district"],
        "hero_types": ["Retired criminal pulled back", "Undercover cop deep cover", "Thief with code", "Hit man with conscience", "Ex-con seeking redemption"],
        "heroine_types": ["Con artist", "Mob lawyer", "Witness protection target", "Criminal mastermind", "Detective obsessed with case"],
        "conflicts": ["betrayal by partner", "crime boss wants blood", "escape impossible odds", "loved one held hostage", "past catching up"],
        "heat_level": "none",
        "word_target": 30000,
        "author_style": "punchy_unisex",
        "cover_mood": "urban noir, crime, city night, dangerous, gritty",
    },

    # ========================================================================
    # MYSTERY SUBGENRES
    # ========================================================================

    Subgenre.COZY_MYSTERY: {
        "name": "Cozy Mystery",
        "genre": Genre.MYSTERY,
        "market_share": 0.07,
        "description": "Amateur sleuth, small town, quirky community",
        "tropes": ["amateur detective", "quirky small town", "dead body in pleasant setting", "suspects among friends", "cozy setting"],
        "settings": ["Small coastal town", "Quaint bookshop", "Bakery or cafe", "Bed and breakfast", "Craft shop"],
        "hero_types": ["Retired detective", "Former journalist", "Curious librarian's husband", "Chef with intuition", "Antique dealer"],
        "heroine_types": ["Bookshop owner", "Bakery owner", "Librarian", "Bed and breakfast owner", "Retired teacher"],
        "conflicts": ["murder in peaceful town", "suspect is a friend", "police won't listen", "killer getting closer", "town secrets exposed"],
        "heat_level": "none",
        "word_target": 25000,
        "author_style": "soft_feminine",
        "cover_mood": "cozy, small town, cute shop, pleasant, warm colors, charming",
    },

    Subgenre.POLICE_PROCEDURAL: {
        "name": "Police Procedural",
        "genre": Genre.MYSTERY,
        "market_share": 0.08,
        "description": "Detective work, forensics, investigation",
        "tropes": ["by the book investigation", "partner dynamics", "forensic breakthrough", "serial killer hunt", "cold case reopened"],
        "settings": ["Major city police department", "FBI field office", "Crime lab", "Interrogation room", "Crime scene"],
        "hero_types": ["Veteran homicide detective", "FBI agent", "Crime scene investigator", "Cold case specialist", "Police captain"],
        "heroine_types": ["Rookie with fresh eyes", "Medical examiner", "Forensic psychologist", "Detective with past", "FBI profiler"],
        "conflicts": ["killer ahead of police", "evidence doesn't add up", "personal connection to case", "corrupt colleague", "race against time"],
        "heat_level": "none",
        "word_target": 32000,
        "author_style": "punchy_unisex",
        "cover_mood": "police, investigation, crime scene, badge, urban, gritty",
    },

    Subgenre.AMATEUR_SLEUTH: {
        "name": "Amateur Sleuth",
        "genre": Genre.MYSTERY,
        "market_share": 0.06,
        "description": "Ordinary person solves crime, wit over authority",
        "tropes": ["wrong place wrong time", "police dismiss amateur", "personal stake", "clues others miss", "final confrontation"],
        "settings": ["Auction house", "Museum", "University", "Publishing house", "Art gallery"],
        "hero_types": ["Professor", "Journalist", "Antique dealer", "Retired professional", "Actor"],
        "heroine_types": ["Art historian", "True crime podcaster", "Estate lawyer", "Insurance investigator", "Museum curator"],
        "conflicts": ["becoming a suspect", "danger from killer", "police interference", "betrayal by trusted figure", "racing the clock"],
        "heat_level": "none",
        "word_target": 28000,
        "author_style": "classic_literary",
        "cover_mood": "mysterious, elegant setting, investigation, sophisticated, clues",
    },

    # ========================================================================
    # SCI-FI SUBGENRES
    # ========================================================================

    Subgenre.SPACE_OPERA: {
        "name": "Space Opera",
        "genre": Genre.SCIFI,
        "market_share": 0.08,
        "description": "Epic space adventure, galactic empires, space battles",
        "tropes": ["chosen one", "ragtag crew", "evil empire", "ancient alien technology", "rebellion"],
        "settings": ["Starship bridge", "Space station", "Alien planet", "Imperial capital", "Outer rim colony"],
        "hero_types": ["Rogue pilot", "Disgraced admiral", "Smuggler with heart", "Exiled prince", "Last of ancient order"],
        "heroine_types": ["Rebel leader", "Ship captain", "Princess in hiding", "Mercenary", "Scientist with discovery"],
        "conflicts": ["empire vs freedom", "ancient evil awakens", "betrayal in ranks", "sacrifice for many", "finding home"],
        "heat_level": "none",
        "word_target": 35000,
        "author_style": "fantasy_epic",
        "cover_mood": "space, starship, planets, nebula, epic sci-fi, cosmic",
    },

    Subgenre.CYBERPUNK: {
        "name": "Cyberpunk",
        "genre": Genre.SCIFI,
        "market_share": 0.06,
        "description": "High tech low life, megacorps, body modification",
        "tropes": ["hacker rebel", "corporate dystopia", "AI consciousness", "body augmentation", "noir detective"],
        "settings": ["Neon-lit megacity", "Underground hacker den", "Corporate arcology", "Black market clinic", "Virtual reality"],
        "hero_types": ["Street hacker", "Ex-corporate mercenary", "Body-modded detective", "AI sympathizer", "Underground doctor"],
        "heroine_types": ["Netrunner", "Corporate defector", "Street samurai", "VR addict seeking truth", "Biohacker activist"],
        "conflicts": ["corporation hunting them", "identity crisis after modding", "AI rights", "memory theft", "toxic megacity"],
        "heat_level": "none",
        "word_target": 30000,
        "author_style": "punchy_unisex",
        "cover_mood": "neon, cyberpunk, rain, city lights, futuristic, dark tech",
    },

    Subgenre.POST_APOCALYPTIC: {
        "name": "Post-Apocalyptic",
        "genre": Genre.SCIFI,
        "market_share": 0.07,
        "description": "After the fall, survival, rebuilding humanity",
        "tropes": ["survival community", "raiders and warlords", "search for safe haven", "remnants of old world", "hope for future"],
        "settings": ["Ruined city", "Desert wasteland", "Underground bunker", "Fortified settlement", "Overgrown suburbs"],
        "hero_types": ["Former soldier", "Lone wanderer", "Community leader", "Scavenger with code", "Doctor keeping hope"],
        "heroine_types": ["Fierce survivor", "Mother protecting children", "Scientist seeking cure", "Trader between settlements", "Radio operator connecting survivors"],
        "conflicts": ["resource scarcity", "raiders attack", "disease outbreak", "journey to rumored sanctuary", "trust after betrayal"],
        "heat_level": "none",
        "word_target": 30000,
        "author_style": "punchy_unisex",
        "cover_mood": "ruins, wasteland, survival, post-apocalyptic landscape, dramatic sky",
    },

    Subgenre.FIRST_CONTACT: {
        "name": "First Contact",
        "genre": Genre.SCIFI,
        "market_share": 0.05,
        "description": "Humanity meets aliens, diplomacy or war",
        "tropes": ["communication barrier", "alien intentions unclear", "humanity divided", "translator protagonist", "paradigm shift"],
        "settings": ["Research station", "First landing site", "UN headquarters", "Alien vessel", "Observatory"],
        "hero_types": ["Linguist", "Scientist first to see", "Military commander", "Diplomat", "Astronaut"],
        "heroine_types": ["Xenobiologist", "Communications specialist", "Ambassador", "First responder", "AI researcher understanding alien AI"],
        "conflicts": ["misunderstanding could mean war", "government cover-up", "alien faction conflict", "humanity's worst revealed", "sacrifice for understanding"],
        "heat_level": "none",
        "word_target": 32000,
        "author_style": "classic_literary",
        "cover_mood": "spacecraft, alien arrival, scientific, cosmic, momentous",
    },

    # ========================================================================
    # HORROR SUBGENRES
    # ========================================================================

    Subgenre.SUPERNATURAL_HORROR: {
        "name": "Supernatural Horror",
        "genre": Genre.HORROR,
        "market_share": 0.07,
        "description": "Ghosts, demons, curses, haunted places",
        "tropes": ["haunted house", "demonic possession", "ancient curse", "supernatural investigation", "innocent corrupted"],
        "settings": ["Old mansion", "Cursed land", "Abandoned asylum", "Funeral home", "Cemetery"],
        "hero_types": ["Paranormal investigator", "Priest with doubt", "Skeptic proven wrong", "Man inheriting cursed house", "Demonologist"],
        "heroine_types": ["Psychic medium", "Woman with gift/curse", "Daughter returning home", "Ghost hunter", "Occult researcher"],
        "conflicts": ["entity wants something", "possession of loved one", "curse spreading", "portal to hell", "sacrifice required"],
        "heat_level": "none",
        "word_target": 28000,
        "author_style": "punchy_unisex",
        "cover_mood": "haunted, dark, supernatural, ghostly, creepy atmosphere, gothic",
    },

    Subgenre.PSYCHOLOGICAL_HORROR: {
        "name": "Psychological Horror",
        "genre": Genre.HORROR,
        "market_share": 0.06,
        "description": "Mind horror, creeping dread, sanity questioned",
        "tropes": ["slow descent", "unreliable perception", "isolation", "gaslighting", "body horror elements"],
        "settings": ["Remote cabin", "Research facility", "Family home", "Hospital", "Mind itself"],
        "hero_types": ["Man questioning reality", "Recovering addict", "Grief-stricken widower", "Patient in treatment", "Artist losing grip"],
        "heroine_types": ["Woman with trauma", "Caretaker isolated", "Mother with postpartum", "Survivor with guilt", "Therapist becoming patient"],
        "conflicts": ["is it real or madness", "something wrong with family", "memory cannot be trusted", "help that isn't help", "becoming the monster"],
        "heat_level": "none",
        "word_target": 26000,
        "author_style": "classic_literary",
        "cover_mood": "psychological, distorted, unsettling, face fragmented, dark",
    },

    Subgenre.COSMIC_HORROR: {
        "name": "Cosmic Horror",
        "genre": Genre.HORROR,
        "market_share": 0.05,
        "description": "Incomprehensible entities, cosmic insignificance, forbidden knowledge",
        "tropes": ["forbidden knowledge", "cult worship", "sanity cost", "ancient entities", "reality breakdown"],
        "settings": ["Coastal New England town", "Antarctic expedition", "Deep ocean", "University archives", "Abandoned observatory"],
        "hero_types": ["Academic researcher", "Deep sea diver", "Cultist having doubts", "Astronomer who saw too much", "Inheritor of occult library"],
        "heroine_types": ["Anthropologist studying cult", "Marine biologist", "Archivist finding patterns", "Daughter of cultist", "Artist channeling visions"],
        "conflicts": ["knowledge that breaks minds", "cult rising", "entity awakening", "reality crumbling", "no victory only survival"],
        "heat_level": "none",
        "word_target": 28000,
        "author_style": "classic_literary",
        "cover_mood": "cosmic, tentacles, ocean depths, eldritch, incomprehensible, dark",
    },

    # ========================================================================
    # FANTASY SUBGENRES (NON-ROMANCE)
    # ========================================================================

    Subgenre.EPIC_FANTASY: {
        "name": "Epic Fantasy",
        "genre": Genre.FANTASY,
        "market_share": 0.09,
        "description": "World-spanning quests, magic systems, good vs evil",
        "tropes": ["chosen one", "magic training", "fellowship", "ancient evil", "prophecy"],
        "settings": ["Kingdom at war", "Magical academy", "Ancient ruins", "Dwarven mines", "Elven forest"],
        "hero_types": ["Reluctant hero", "Young mage", "Fallen knight", "Prince in exile", "Thief with destiny"],
        "heroine_types": ["Warrior queen", "Hedge witch", "Assassin", "Priestess", "Dragon rider"],
        "conflicts": ["dark lord rising", "save the kingdom", "find the artifact", "unite the peoples", "defeat the prophecy"],
        "heat_level": "none",
        "word_target": 35000,
        "author_style": "fantasy_epic",
        "cover_mood": "epic fantasy, castle, dragons, magic, dramatic landscape, heroic",
    },

    Subgenre.URBAN_FANTASY: {
        "name": "Urban Fantasy",
        "genre": Genre.FANTASY,
        "market_share": 0.07,
        "description": "Magic in modern city, hidden supernatural world",
        "tropes": ["hidden world", "supernatural detective", "vampire politics", "were-creature society", "magic noir"],
        "settings": ["Modern city with secrets", "Underground supernatural club", "Police supernatural division", "Witch's shop", "Fae court in NYC"],
        "hero_types": ["Supernatural PI", "Wizard for hire", "Half-demon", "Werewolf alpha", "Necromancer"],
        "heroine_types": ["Bounty hunter", "Witch", "Human cop in supernatural beat", "Vampire trying to go straight", "Fae changeling"],
        "conflicts": ["supernatural war brewing", "murder in supernatural community", "ancient evil in modern city", "treaty violations", "identity exposure"],
        "heat_level": "none",
        "word_target": 30000,
        "author_style": "punchy_unisex",
        "cover_mood": "urban, supernatural, city night, magic, modern fantasy, noir",
    },

    Subgenre.GRIMDARK: {
        "name": "Grimdark Fantasy",
        "genre": Genre.FANTASY,
        "market_share": 0.06,
        "description": "Morally grey, brutal, anti-heroes, dark world",
        "tropes": ["anti-hero", "morally grey choices", "no happy endings", "brutal reality", "power corrupts"],
        "settings": ["War-torn empire", "Corrupt kingdom", "Mercenary company", "Gladiator pits", "Siege warfare"],
        "hero_types": ["Torturer turned fighter", "Disgraced general", "Assassin with no code", "Mercenary captain", "Fallen king"],
        "heroine_types": ["Ruthless queen", "Poisoner", "Inquisitor", "Slave turned warrior", "Witch with dark powers"],
        "conflicts": ["lesser evil vs greater evil", "survival at any cost", "revenge consuming", "war with no good side", "power at soul's cost"],
        "heat_level": "none",
        "word_target": 35000,
        "author_style": "fantasy_epic",
        "cover_mood": "dark, brutal, warrior, blood, grim atmosphere, dramatic",
    },

    # ========================================================================
    # LITERARY FICTION
    # ========================================================================

    Subgenre.LITERARY_UPMARKET: {
        "name": "Literary Upmarket",
        "genre": Genre.LITERARY,
        "market_share": 0.05,
        "description": "Character-driven, beautiful prose, life themes",
        "tropes": ["family saga", "coming of age", "identity journey", "grief and healing", "secrets revealed"],
        "settings": ["Multi-generational family home", "Small town over decades", "Immigrant experience", "Academic setting", "Coastal community"],
        "hero_types": ["Man facing mortality", "Father seeking redemption", "Artist blocked", "Professor with secret", "Returning son"],
        "heroine_types": ["Woman redefining herself", "Mother with past", "Artist finding voice", "Daughter uncovering truth", "Immigrant grandmother"],
        "conflicts": ["family secrets", "identity crisis", "generational trauma", "love vs duty", "past vs present"],
        "heat_level": "none",
        "word_target": 30000,
        "author_style": "classic_literary",
        "cover_mood": "literary, evocative, artistic, meaningful, beautiful scenery",
    },

    # ========================================================================
    # NON-FICTION SUBGENRES
    # ========================================================================

    Subgenre.SELF_HELP: {
        "name": "Self-Help",
        "genre": Genre.NONFICTION,
        "market_share": 0.08,
        "description": "Personal transformation, mindset, life improvement",
        "tropes": ["transformation journey", "practical exercises", "case studies", "step-by-step system", "mindset shift"],
        "settings": ["Modern life challenges", "Career transitions", "Relationship dynamics", "Personal crisis", "Goal achievement"],
        "hero_types": ["Reader as protagonist", "Everyman seeking change", "Professional wanting more", "Parent improving", "Person at crossroads"],
        "heroine_types": ["Woman reclaiming power", "Career woman seeking balance", "Mother finding self", "Creative unlocking potential", "Leader developing"],
        "conflicts": ["limiting beliefs", "fear of change", "old habits", "self-sabotage", "imposter syndrome"],
        "heat_level": "none",
        "word_target": 25000,
        "author_style": "tech_intellectual",
        "cover_mood": "inspirational, professional, clean, uplifting, modern design",
    },

    Subgenre.BUSINESS: {
        "name": "Business & Entrepreneurship",
        "genre": Genre.NONFICTION,
        "market_share": 0.07,
        "description": "Business strategy, leadership, entrepreneurship",
        "tropes": ["success framework", "case studies", "contrarian insight", "scaling strategies", "leadership principles"],
        "settings": ["Startup world", "Corporate environment", "Small business", "Tech industry", "Global markets"],
        "hero_types": ["Entrepreneur", "Executive", "Business owner", "Team leader", "Innovator"],
        "heroine_types": ["Female founder", "Corporate leader", "Business strategist", "Change agent", "Industry disruptor"],
        "conflicts": ["competition", "scaling challenges", "team dynamics", "market changes", "resource constraints"],
        "heat_level": "none",
        "word_target": 28000,
        "author_style": "tech_intellectual",
        "cover_mood": "professional, corporate, success, modern business, clean design",
    },

    Subgenre.PRODUCTIVITY: {
        "name": "Productivity & Performance",
        "genre": Genre.NONFICTION,
        "market_share": 0.06,
        "description": "Time management, efficiency, peak performance",
        "tropes": ["system reveal", "habit stacking", "optimization techniques", "time blocking", "energy management"],
        "settings": ["Modern workplace", "Remote work", "Digital overwhelm", "Busy life", "High-performance environment"],
        "hero_types": ["Overwhelmed professional", "Ambitious achiever", "Knowledge worker", "Creative professional", "Executive"],
        "heroine_types": ["Working mother", "Entrepreneur", "Corporate professional", "Creative", "Leader"],
        "conflicts": ["time scarcity", "distraction epidemic", "burnout risk", "priority confusion", "overwhelm"],
        "heat_level": "none",
        "word_target": 22000,
        "author_style": "tech_intellectual",
        "cover_mood": "clean, minimalist, efficiency, modern, professional",
    },

    Subgenre.FINANCE: {
        "name": "Personal Finance",
        "genre": Genre.NONFICTION,
        "market_share": 0.07,
        "description": "Money management, investing, financial freedom",
        "tropes": ["wealth building system", "debt elimination", "investment principles", "passive income", "financial independence"],
        "settings": ["Modern economy", "Investment markets", "Household finances", "Retirement planning", "Wealth building"],
        "hero_types": ["Average earner", "Young professional", "Family provider", "Pre-retiree", "Debt-burdened worker"],
        "heroine_types": ["Single mother", "Career woman", "Entrepreneur", "New graduate", "Breadwinner"],
        "conflicts": ["debt burden", "financial illiteracy", "market uncertainty", "lifestyle inflation", "retirement fears"],
        "heat_level": "none",
        "word_target": 25000,
        "author_style": "tech_intellectual",
        "cover_mood": "wealth, professional, financial, growth charts, money symbols",
    },

    Subgenre.HEALTH_WELLNESS: {
        "name": "Health & Wellness",
        "genre": Genre.NONFICTION,
        "market_share": 0.08,
        "description": "Physical health, mental wellness, lifestyle optimization",
        "tropes": ["transformation protocol", "science-backed methods", "holistic approach", "habit change", "longevity secrets"],
        "settings": ["Modern health challenges", "Fitness journey", "Nutrition science", "Mental wellness", "Aging well"],
        "hero_types": ["Health seeker", "Fitness enthusiast", "Chronic condition sufferer", "Aging adult", "Stressed professional"],
        "heroine_types": ["Health-conscious woman", "Busy mother", "Fitness beginner", "Wellness seeker", "Midlife woman"],
        "conflicts": ["unhealthy habits", "conflicting advice", "time for self-care", "motivation", "aging concerns"],
        "heat_level": "none",
        "word_target": 25000,
        "author_style": "tech_intellectual",
        "cover_mood": "healthy, vibrant, wellness, nature, clean living",
    },

    Subgenre.PSYCHOLOGY: {
        "name": "Psychology & Behavior",
        "genre": Genre.NONFICTION,
        "market_share": 0.06,
        "description": "Human behavior, cognitive science, mental models",
        "tropes": ["research reveals", "cognitive biases", "behavioral insights", "decision science", "psychological principles"],
        "settings": ["Human mind", "Social dynamics", "Decision making", "Relationships", "Workplace behavior"],
        "hero_types": ["Curious mind", "Self-improver", "Leader", "Professional", "Relationship seeker"],
        "heroine_types": ["Self-aware woman", "Leader", "Therapist", "Educator", "Parent"],
        "conflicts": ["unconscious biases", "irrational behavior", "social pressure", "cognitive errors", "emotional triggers"],
        "heat_level": "none",
        "word_target": 28000,
        "author_style": "tech_intellectual",
        "cover_mood": "brain, mind, psychology, scientific, thoughtful design",
    },

    Subgenre.HOW_TO: {
        "name": "How-To Guide",
        "genre": Genre.NONFICTION,
        "market_share": 0.05,
        "description": "Practical skills, step-by-step instructions, mastery",
        "tropes": ["complete system", "beginner to expert", "common mistakes", "insider tips", "quick wins"],
        "settings": ["Skill development", "Hobby mastery", "Professional skills", "Life skills", "Creative pursuits"],
        "hero_types": ["Beginner", "Hobbyist", "Career changer", "Skill seeker", "DIY enthusiast"],
        "heroine_types": ["New learner", "Career pivoter", "Creative", "Self-improver", "Side-hustler"],
        "conflicts": ["learning curve", "overwhelm", "information overload", "lack of guidance", "fear of failure"],
        "heat_level": "none",
        "word_target": 22000,
        "author_style": "tech_intellectual",
        "cover_mood": "instructional, clear, professional, skill-based, practical",
    },
}


# ============================================================================
# BOOK IDEA GENERATOR
# ============================================================================

@dataclass
class BookIdea:
    """A generated book concept."""
    title: str
    author: str
    subgenre: Subgenre
    premise: str
    hero: str
    heroine: str
    setting: str
    tropes: List[str]
    conflict: str
    heat_level: str
    word_target: int
    cover_mood: str


# ============================================================================
# PUBLIC DOMAIN CLASSICS FOR REMIX
# ============================================================================

PUBLIC_DOMAIN_CLASSICS = [
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "year": 1813,
        "genre": "romance",
        "setting": "Regency England",
        "protagonist": "Elizabeth Bennet",
        "love_interest": "Mr. Darcy",
        "core_plot": "A witty woman and a proud aristocrat overcome their prejudices to find love",
        "key_elements": ["class differences", "witty banter", "family pressure", "social balls", "marriage market"],
        "style": "elegant prose, social satire, sharp dialogue, free indirect discourse",
    },
    {
        "title": "Jane Eyre",
        "author": "Charlotte Bronte",
        "year": 1847,
        "genre": "gothic_romance",
        "setting": "Victorian England, Thornfield Hall",
        "protagonist": "Jane Eyre",
        "love_interest": "Mr. Rochester",
        "core_plot": "An orphaned governess finds love with her mysterious employer who hides dark secrets",
        "key_elements": ["gothic mansion", "dark secret", "madwoman in attic", "class differences", "independence"],
        "style": "first-person introspection, gothic atmosphere, passionate prose, moral conviction",
    },
    {
        "title": "Dracula",
        "author": "Bram Stoker",
        "year": 1897,
        "genre": "horror",
        "setting": "Transylvania and Victorian London",
        "protagonist": "Jonathan Harker / Van Helsing",
        "antagonist": "Count Dracula",
        "core_plot": "A vampire count invades England and a group must stop him",
        "key_elements": ["epistolary format", "seduction", "blood drinking", "crosses and garlic", "castle"],
        "style": "epistolary (letters, diaries), gothic horror, Victorian formal language",
    },
    {
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "year": 1818,
        "genre": "horror",
        "setting": "Europe (Geneva, Arctic)",
        "protagonist": "Victor Frankenstein",
        "antagonist": "The Creature",
        "core_plot": "A scientist creates life but abandons his creation, leading to tragedy",
        "key_elements": ["creation myth", "abandonment", "revenge", "playing God", "isolation"],
        "style": "frame narrative, Romantic prose, philosophical reflection, emotional intensity",
    },
    {
        "title": "The Picture of Dorian Gray",
        "author": "Oscar Wilde",
        "year": 1890,
        "genre": "gothic",
        "setting": "Victorian London",
        "protagonist": "Dorian Gray",
        "antagonist": "Lord Henry Wotton (influencer)",
        "core_plot": "A beautiful young man's portrait ages while he remains young, descending into depravity",
        "key_elements": ["portrait magic", "hedonism", "corruption", "beauty worship", "secret sins"],
        "style": "witty epigrams, aesthetic philosophy, decadent prose, sharp social commentary",
    },
    {
        "title": "Wuthering Heights",
        "author": "Emily Bronte",
        "year": 1847,
        "genre": "gothic_romance",
        "setting": "Yorkshire moors",
        "protagonist": "Heathcliff / Catherine",
        "love_interest": "Catherine / Heathcliff",
        "core_plot": "A passionate, destructive love between an orphan and his foster sister",
        "key_elements": ["wild moors", "obsessive love", "revenge", "ghosts", "class resentment"],
        "style": "frame narrative, wild Romantic passion, dark atmosphere, non-linear timeline",
    },
    {
        "title": "The Count of Monte Cristo",
        "author": "Alexandre Dumas",
        "year": 1844,
        "genre": "adventure",
        "setting": "France, Italy, Mediterranean",
        "protagonist": "Edmond Dantes",
        "antagonist": "Fernand, Danglars, Villefort",
        "core_plot": "A wrongly imprisoned man escapes, finds treasure, and enacts elaborate revenge",
        "key_elements": ["false imprisonment", "hidden treasure", "elaborate revenge", "disguises", "justice"],
        "style": "sweeping adventure, intricate plotting, dramatic reveals, serialized tension",
    },
    {
        "title": "The Strange Case of Dr Jekyll and Mr Hyde",
        "author": "Robert Louis Stevenson",
        "year": 1886,
        "genre": "horror",
        "setting": "Victorian London",
        "protagonist": "Dr. Henry Jekyll",
        "antagonist": "Mr. Edward Hyde",
        "core_plot": "A doctor's experiments split him into good and evil personalities",
        "key_elements": ["dual nature", "transformation", "hidden evil", "respectable facade", "addiction"],
        "style": "mystery structure, Victorian restraint, psychological horror, symbolic duality",
    },
    {
        "title": "A Tale of Two Cities",
        "author": "Charles Dickens",
        "year": 1859,
        "genre": "historical",
        "setting": "London and Paris during French Revolution",
        "protagonist": "Sydney Carton / Charles Darnay",
        "love_interest": "Lucie Manette",
        "core_plot": "Two men who look alike love the same woman during the French Revolution",
        "key_elements": ["revolution", "sacrifice", "resurrection", "doppelganger", "guillotine"],
        "style": "Dickensian prose, parallel structure, melodrama, social commentary",
    },
    {
        "title": "The War of the Worlds",
        "author": "H.G. Wells",
        "year": 1898,
        "genre": "scifi",
        "setting": "Victorian England",
        "protagonist": "The Narrator",
        "antagonist": "Martians",
        "core_plot": "Martians invade Earth with superior technology, humanity barely survives",
        "key_elements": ["alien invasion", "tripod war machines", "heat ray", "survival", "bacteria ending"],
        "style": "journalistic realism, scientific detail, survival horror, Victorian voice",
    },
    {
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "year": 1865,
        "genre": "fantasy",
        "setting": "Wonderland",
        "protagonist": "Alice",
        "key_characters": "Queen of Hearts, Cheshire Cat, Mad Hatter, White Rabbit",
        "core_plot": "A girl falls down a rabbit hole into a surreal world of nonsense and wordplay",
        "key_elements": ["size changes", "tea party", "playing cards", "nonsense logic", "talking animals"],
        "style": "whimsical nonsense, wordplay, dream logic, Victorian children's literature",
    },
    {
        "title": "The Odyssey",
        "author": "Homer",
        "year": -800,
        "genre": "epic",
        "setting": "Ancient Greece, Mediterranean",
        "protagonist": "Odysseus",
        "love_interest": "Penelope",
        "core_plot": "A hero's long journey home after war, facing monsters and gods",
        "key_elements": ["homecoming", "monsters", "divine intervention", "cunning", "loyalty"],
        "style": "epic poetry, epithets, in medias res, heroic narrative",
    },
    # ========================================================================
    # BOOK OF MORMON - Public Domain (1830)
    # ========================================================================
    {
        "title": "1 Nephi",
        "author": "Joseph Smith (translator)",
        "year": 1830,
        "genre": "epic",
        "setting": "Jerusalem 600 BC, Arabian desert, ocean voyage, promised land",
        "protagonist": "Nephi",
        "antagonist": "Laman and Lemuel (rebellious brothers)",
        "core_plot": "A faithful young man leads his family from Jerusalem through wilderness and across the ocean to a new promised land",
        "key_elements": ["prophetic visions", "brass plates quest", "family conflict", "divine guidance (Liahona)", "shipbuilding", "promised land"],
        "style": "biblical prose, first-person testimony, prophetic vision, 'and it came to pass' cadence",
        "source": "Book of Mormon",
    },
    {
        "title": "Mosiah",
        "author": "Joseph Smith (translator)",
        "year": 1830,
        "genre": "epic",
        "setting": "Ancient American cities (Zarahemla, Land of Nephi)",
        "protagonist": "King Benjamin, Alma the Elder, Abinadi",
        "antagonist": "King Noah (wicked king)",
        "core_plot": "A righteous king gives his final speech, while a prophet martyred by a tyrant sparks a religious awakening",
        "key_elements": ["king's farewell", "martyrdom", "secret believers", "escape to freedom", "conversion", "baptism at waters of Mormon"],
        "style": "biblical prose, sermon rhetoric, narrative history, 'and it came to pass' cadence",
        "source": "Book of Mormon",
    },
    {
        "title": "Alma",
        "author": "Joseph Smith (translator)",
        "year": 1830,
        "genre": "adventure",
        "setting": "Ancient American lands (Zarahemla, Jershon, battlefields)",
        "protagonist": "Alma the Younger, Captain Moroni, Helaman's stripling warriors",
        "antagonist": "Zerahemnah, Amalickiah, Lamanite armies",
        "core_plot": "A former rebel becomes a prophet while a legendary captain defends freedom against overwhelming forces",
        "key_elements": ["dramatic conversion", "missionary journeys", "title of liberty", "epic battles", "stripling warriors", "fortifications", "strategy"],
        "style": "biblical prose, war narrative, sermon interludes, 'and it came to pass' cadence",
        "source": "Book of Mormon",
    },
    {
        "title": "Helaman",
        "author": "Joseph Smith (translator)",
        "year": 1830,
        "genre": "thriller",
        "setting": "Ancient American cities, corrupt government",
        "protagonist": "Nephi and Lehi (sons of Helaman), Samuel the Lamanite",
        "antagonist": "Gadianton robbers (secret combination)",
        "core_plot": "Brothers survive miraculous imprisonment while a lone prophet stands on a wall warning of destruction",
        "key_elements": ["secret societies", "political corruption", "prison miracles", "prophecy from the wall", "signs and wonders"],
        "style": "biblical prose, prophetic warning, political intrigue, 'and it came to pass' cadence",
        "source": "Book of Mormon",
    },
    {
        "title": "3 Nephi",
        "author": "Joseph Smith (translator)",
        "year": 1830,
        "genre": "epic",
        "setting": "Ancient America, destruction and rebuilding, temple at Bountiful",
        "protagonist": "The people, Christ",
        "core_plot": "After cataclysmic destruction, a divine figure descends from heaven to teach and heal the survivors",
        "key_elements": ["signs of birth and death", "three days of darkness", "destruction", "divine appearance", "sermon at temple", "healing miracles", "children blessed"],
        "style": "biblical prose, apocalyptic narrative, divine discourse, 'and it came to pass' cadence",
        "source": "Book of Mormon",
    },
    {
        "title": "Ether",
        "author": "Joseph Smith (translator)",
        "year": 1830,
        "genre": "epic",
        "setting": "Tower of Babel, ocean crossing in barges, ancient promised land",
        "protagonist": "Brother of Jared (Mahonri Moriancumer)",
        "antagonist": "Shiz (final Jaredite warrior)",
        "core_plot": "A man of great faith leads his people across the ocean in sealed barges lit by glowing stones touched by God's finger",
        "key_elements": ["Tower of Babel", "glowing stones", "sealed barges", "ocean crossing", "rise and fall of civilization", "final battle"],
        "style": "biblical prose, abridged history, faith narrative, apocalyptic ending, 'and it came to pass' cadence",
        "source": "Book of Mormon",
    },
    {
        "title": "Mormon",
        "author": "Joseph Smith (translator)",
        "year": 1830,
        "genre": "tragedy",
        "setting": "Final battles, Hill Cumorah",
        "protagonist": "Mormon (prophet-general), Moroni (his son)",
        "antagonist": "Lamanite armies, societal collapse",
        "core_plot": "A prophet-warrior witnesses the destruction of his entire civilization and writes a final testament for future generations",
        "key_elements": ["civilizational collapse", "last stand", "burying records", "lamentation", "hope for future readers"],
        "style": "biblical prose, elegiac lament, editorial commentary, 'and it came to pass' cadence",
        "source": "Book of Mormon",
    },
    # ========================================================================
    # ADDITIONAL CLASSICS - Expanded Library
    # ========================================================================
    {
        "title": "Les Miserables",
        "author": "Victor Hugo",
        "year": 1862,
        "genre": "historical",
        "setting": "19th century France, Paris, Revolution of 1832",
        "protagonist": "Jean Valjean",
        "antagonist": "Inspector Javert",
        "core_plot": "An ex-convict seeks redemption while pursued by a relentless policeman through revolutionary France",
        "key_elements": ["redemption", "justice vs mercy", "revolution", "sacrifice", "love across class"],
        "style": "sweeping historical narrative, philosophical digressions, epic scope, melodramatic emotion",
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "genre": "literary",
        "setting": "1920s Long Island, New York",
        "protagonist": "Jay Gatsby / Nick Carraway",
        "love_interest": "Daisy Buchanan",
        "core_plot": "A mysterious millionaire throws lavish parties to win back his lost love, revealing the hollowness of the American Dream",
        "key_elements": ["wealth", "obsessive love", "green light", "jazz age", "illusion vs reality"],
        "style": "lyrical prose, unreliable narrator, symbolism, elegiac tone, modernist restraint",
    },
    {
        "title": "A Farewell to Arms",
        "author": "Ernest Hemingway",
        "year": 1929,
        "genre": "war",
        "setting": "World War I Italy",
        "protagonist": "Frederic Henry",
        "love_interest": "Catherine Barkley",
        "core_plot": "An American ambulance driver falls in love with a British nurse amid the chaos of WWI",
        "key_elements": ["war", "doomed romance", "desertion", "tragic ending", "disillusionment"],
        "style": "spare prose, iceberg theory, understated emotion, short declarative sentences",
    },
    {
        "title": "The Maltese Falcon",
        "author": "Dashiell Hammett",
        "year": 1930,
        "genre": "mystery",
        "setting": "San Francisco",
        "protagonist": "Sam Spade",
        "antagonist": "Kasper Gutman",
        "core_plot": "A hard-boiled detective gets caught up in the hunt for a priceless statuette",
        "key_elements": ["private eye", "femme fatale", "MacGuffin", "moral ambiguity", "betrayal"],
        "style": "hard-boiled prose, tough dialogue, objective viewpoint, noir atmosphere",
    },
    {
        "title": "Twenty Thousand Leagues Under the Sea",
        "author": "Jules Verne",
        "year": 1870,
        "genre": "scifi",
        "setting": "World's oceans, aboard the Nautilus",
        "protagonist": "Professor Aronnax",
        "antagonist": "Captain Nemo (ambiguous)",
        "core_plot": "A professor discovers a submarine and its mysterious captain who has abandoned humanity",
        "key_elements": ["submarine", "underwater wonders", "scientific detail", "isolation", "revenge"],
        "style": "scientific adventure, detailed descriptions, Victorian scientific optimism",
    },
    {
        "title": "Around the World in Eighty Days",
        "author": "Jules Verne",
        "year": 1872,
        "genre": "adventure",
        "setting": "Global - India, Hong Kong, America, etc.",
        "protagonist": "Phileas Fogg",
        "key_characters": "Passepartout, Detective Fix, Aouda",
        "core_plot": "A wealthy Englishman bets he can circumnavigate the globe in 80 days",
        "key_elements": ["race against time", "exotic locations", "resourcefulness", "British reserve"],
        "style": "brisk adventure, travelogue detail, comedic elements, Victorian sensibility",
    },
    {
        "title": "The Call of the Wild",
        "author": "Jack London",
        "year": 1903,
        "genre": "adventure",
        "setting": "Yukon, Alaska Gold Rush",
        "protagonist": "Buck (a dog)",
        "core_plot": "A domesticated dog is stolen and sold as a sled dog, gradually returning to his wild nature",
        "key_elements": ["survival", "nature vs civilization", "primal instincts", "harsh conditions"],
        "style": "naturalism, vivid action, animal perspective, primal imagery",
    },
    {
        "title": "Treasure Island",
        "author": "Robert Louis Stevenson",
        "year": 1883,
        "genre": "adventure",
        "setting": "18th century, Caribbean island",
        "protagonist": "Jim Hawkins",
        "antagonist": "Long John Silver",
        "core_plot": "A young boy finds a treasure map and joins a voyage to find buried pirate gold",
        "key_elements": ["treasure map", "pirates", "mutiny", "coming of age", "X marks the spot"],
        "style": "adventure yarn, first-person excitement, Victorian boys' adventure",
    },
    {
        "title": "The Jungle Book",
        "author": "Rudyard Kipling",
        "year": 1894,
        "genre": "fantasy",
        "setting": "Indian jungle",
        "protagonist": "Mowgli",
        "key_characters": "Baloo, Bagheera, Shere Khan, Kaa",
        "core_plot": "A human child is raised by wolves and learns the law of the jungle",
        "key_elements": ["raised by animals", "jungle law", "identity", "belonging", "growing up"],
        "style": "fable-like, talking animals, moral instruction, colonial-era exoticism",
    },
    {
        "title": "The Scarlet Letter",
        "author": "Nathaniel Hawthorne",
        "year": 1850,
        "genre": "historical",
        "setting": "Puritan Boston, 17th century",
        "protagonist": "Hester Prynne",
        "antagonist": "Roger Chillingworth",
        "core_plot": "A woman condemned to wear a scarlet 'A' for adultery becomes a symbol of strength",
        "key_elements": ["sin and redemption", "public shame", "hidden guilt", "Puritan society"],
        "style": "allegorical, romantic prose, psychological depth, moral complexity",
    },
    {
        "title": "Moby-Dick",
        "author": "Herman Melville",
        "year": 1851,
        "genre": "adventure",
        "setting": "Whaling ship Pequod, world's oceans",
        "protagonist": "Ishmael (narrator)",
        "antagonist": "Captain Ahab / Moby Dick",
        "core_plot": "A ship captain's obsessive hunt for the white whale that maimed him",
        "key_elements": ["obsession", "man vs nature", "whale hunting", "fate", "symbolic white whale"],
        "style": "encyclopedic, philosophical digressions, biblical allusions, epic scope",
    },
    {
        "title": "Adventures of Huckleberry Finn",
        "author": "Mark Twain",
        "year": 1884,
        "genre": "adventure",
        "setting": "Mississippi River, antebellum South",
        "protagonist": "Huckleberry Finn",
        "key_characters": "Jim, Tom Sawyer",
        "core_plot": "A boy and an escaped slave float down the Mississippi, encountering America's complexities",
        "key_elements": ["river journey", "freedom", "con men", "social satire", "moral awakening"],
        "style": "vernacular dialogue, satirical humor, picaresque adventure, social criticism",
    },
    {
        "title": "The Adventures of Tom Sawyer",
        "author": "Mark Twain",
        "year": 1876,
        "genre": "adventure",
        "setting": "Fictional St. Petersburg, Missouri",
        "protagonist": "Tom Sawyer",
        "love_interest": "Becky Thatcher",
        "core_plot": "A mischievous boy has adventures including witnessing a murder and finding treasure",
        "key_elements": ["boyhood adventures", "whitewashing fence", "cave exploration", "buried treasure"],
        "style": "nostalgic, humorous, vernacular dialogue, idealized boyhood",
    },
    {
        "title": "The Three Musketeers",
        "author": "Alexandre Dumas",
        "year": 1844,
        "genre": "adventure",
        "setting": "17th century France",
        "protagonist": "D'Artagnan",
        "key_characters": "Athos, Porthos, Aramis",
        "antagonist": "Cardinal Richelieu, Milady de Winter",
        "core_plot": "A young Gascon joins the musketeers and becomes embroiled in royal intrigue",
        "key_elements": ["all for one", "sword fighting", "royal intrigue", "brotherhood", "adventure"],
        "style": "swashbuckling adventure, witty dialogue, serialized excitement",
    },
    {
        "title": "Crime and Punishment",
        "author": "Fyodor Dostoevsky",
        "year": 1866,
        "genre": "literary",
        "setting": "St. Petersburg, Russia",
        "protagonist": "Raskolnikov",
        "antagonist": "Porfiry Petrovich",
        "core_plot": "A poor student commits murder believing himself above moral law, then faces psychological torment",
        "key_elements": ["guilt", "redemption", "poverty", "extraordinary man theory", "confession"],
        "style": "psychological intensity, philosophical dialogue, stream of consciousness, moral anguish",
    },
    {
        "title": "Anna Karenina",
        "author": "Leo Tolstoy",
        "year": 1877,
        "genre": "literary",
        "setting": "Russian high society, Moscow and countryside",
        "protagonist": "Anna Karenina / Levin",
        "love_interest": "Count Vronsky / Kitty",
        "core_plot": "A married aristocrat's affair leads to social ruin while a landowner seeks meaning in life",
        "key_elements": ["adultery", "social judgment", "parallel plots", "family", "spiritual seeking"],
        "style": "realist prose, psychological depth, dual narratives, philosophical reflection",
    },
    {
        "title": "The Phantom of the Opera",
        "author": "Gaston Leroux",
        "year": 1910,
        "genre": "gothic_romance",
        "setting": "Paris Opera House",
        "protagonist": "Christine Daae",
        "love_interest": "Raoul de Chagny / The Phantom",
        "antagonist": "Erik (The Phantom)",
        "core_plot": "A mysterious masked genius beneath the opera house becomes obsessed with a young soprano",
        "key_elements": ["masked figure", "underground lair", "music", "obsessive love", "gothic horror"],
        "style": "gothic melodrama, mysterious atmosphere, romantic tragedy",
    },
    {
        "title": "Robinson Crusoe",
        "author": "Daniel Defoe",
        "year": 1719,
        "genre": "adventure",
        "setting": "Desert island",
        "protagonist": "Robinson Crusoe",
        "key_characters": "Friday",
        "core_plot": "A shipwrecked man survives alone on an island for decades",
        "key_elements": ["survival", "isolation", "resourcefulness", "colonialism", "faith"],
        "style": "realistic detail, first-person journal, practical prose, early novel",
    },
    {
        "title": "Gulliver's Travels",
        "author": "Jonathan Swift",
        "year": 1726,
        "genre": "fantasy",
        "setting": "Lilliput, Brobdingnag, Laputa, Houyhnhnms",
        "protagonist": "Lemuel Gulliver",
        "core_plot": "A ship's surgeon visits strange lands populated by tiny people, giants, and intelligent horses",
        "key_elements": ["satire", "size differences", "social criticism", "human nature", "voyage"],
        "style": "satirical, matter-of-fact narration, social commentary, absurdist logic",
    },
    {
        "title": "The Hound of the Baskervilles",
        "author": "Arthur Conan Doyle",
        "year": 1902,
        "genre": "mystery",
        "setting": "Dartmoor, Devon, England",
        "protagonist": "Sherlock Holmes",
        "key_characters": "Dr. Watson, Sir Henry Baskerville",
        "core_plot": "Holmes investigates a supernatural hound said to haunt a noble family",
        "key_elements": ["detection", "gothic moor", "family curse", "supernatural vs rational", "deduction"],
        "style": "detective fiction, atmospheric setting, logical deduction, Watson narration",
    },
    {
        "title": "A Study in Scarlet",
        "author": "Arthur Conan Doyle",
        "year": 1887,
        "genre": "mystery",
        "setting": "Victorian London",
        "protagonist": "Sherlock Holmes",
        "key_characters": "Dr. Watson",
        "core_plot": "Holmes and Watson meet and solve a mysterious murder linked to Mormon revenge",
        "key_elements": ["first meeting", "deduction", "flashback narrative", "revenge plot"],
        "style": "detective fiction, observation and deduction, dual narrative structure",
    },
    {
        "title": "Madame Bovary",
        "author": "Gustave Flaubert",
        "year": 1856,
        "genre": "literary",
        "setting": "Provincial France",
        "protagonist": "Emma Bovary",
        "antagonist": "Provincial mediocrity",
        "core_plot": "A doctor's wife, seeking romantic fulfillment, destroys herself through affairs and debt",
        "key_elements": ["romantic disillusion", "adultery", "boredom", "debt", "provincial life"],
        "style": "precise realism, free indirect discourse, ironic distance, le mot juste",
    },
    {
        "title": "The Time Machine",
        "author": "H.G. Wells",
        "year": 1895,
        "genre": "scifi",
        "setting": "Future Earth (802,701 AD)",
        "protagonist": "The Time Traveller",
        "core_plot": "A scientist travels to the far future to find humanity split into two degenerate species",
        "key_elements": ["time travel", "Eloi and Morlocks", "social evolution", "entropy"],
        "style": "scientific romance, Victorian narration, social allegory",
    },
    {
        "title": "The Invisible Man",
        "author": "H.G. Wells",
        "year": 1897,
        "genre": "scifi",
        "setting": "English village",
        "protagonist": "Griffin (The Invisible Man)",
        "core_plot": "A scientist discovers invisibility but descends into madness and violence",
        "key_elements": ["invisibility", "scientific hubris", "isolation", "terror", "manhunt"],
        "style": "scientific detail, psychological horror, Victorian setting",
    },
    {
        "title": "Don Quixote",
        "author": "Miguel de Cervantes",
        "year": 1605,
        "genre": "literary",
        "setting": "La Mancha, Spain",
        "protagonist": "Don Quixote",
        "key_characters": "Sancho Panza",
        "core_plot": "A man driven mad by chivalric romances becomes a knight-errant tilting at windmills",
        "key_elements": ["madness", "idealism vs reality", "windmills", "squire", "metafiction"],
        "style": "picaresque, satirical, meta-fictional, comic epic",
    },
    {
        "title": "The Importance of Being Earnest",
        "author": "Oscar Wilde",
        "year": 1895,
        "genre": "comedy",
        "setting": "Victorian London and countryside",
        "protagonist": "Jack Worthing / Algernon Moncrieff",
        "love_interest": "Gwendolen / Cecily",
        "core_plot": "Two men maintain fictitious identities to escape obligations, leading to romantic complications",
        "key_elements": ["mistaken identity", "wit", "social satire", "bunburying", "handbag"],
        "style": "epigrammatic wit, farcical plot, social satire, drawing room comedy",
    },
    {
        "title": "Heart of Darkness",
        "author": "Joseph Conrad",
        "year": 1899,
        "genre": "literary",
        "setting": "Congo River, Africa",
        "protagonist": "Charles Marlow",
        "antagonist": "Kurtz",
        "core_plot": "A riverboat captain journeys into the African interior to find a mysterious ivory trader",
        "key_elements": ["colonialism", "darkness within", "journey upriver", "horror", "civilization"],
        "style": "frame narrative, impressionistic, symbolic, ambiguous, modernist",
    },
    {
        "title": "The Secret Garden",
        "author": "Frances Hodgson Burnett",
        "year": 1911,
        "genre": "children",
        "setting": "Yorkshire moors, Misselthwaite Manor",
        "protagonist": "Mary Lennox",
        "key_characters": "Colin, Dickon",
        "core_plot": "An orphaned girl discovers a locked garden and brings healing to herself and others",
        "key_elements": ["hidden garden", "healing nature", "transformation", "friendship", "spring"],
        "style": "children's literature, nature imagery, redemptive arc, Yorkshire dialect",
    },
    {
        "title": "Little Women",
        "author": "Louisa May Alcott",
        "year": 1868,
        "genre": "literary",
        "setting": "Civil War era Massachusetts",
        "protagonist": "Jo March",
        "key_characters": "Meg, Beth, Amy, Marmee, Laurie",
        "core_plot": "Four sisters navigate growing up, love, loss, and ambition during and after the Civil War",
        "key_elements": ["sisterhood", "coming of age", "domestic life", "writing dreams", "sacrifice"],
        "style": "domestic realism, sentimental, autobiographical, moral instruction",
    },
    {
        "title": "The Adventures of Sherlock Holmes",
        "author": "Arthur Conan Doyle",
        "year": 1892,
        "genre": "mystery",
        "setting": "Victorian London",
        "protagonist": "Sherlock Holmes",
        "key_characters": "Dr. Watson",
        "core_plot": "The world's greatest detective solves baffling cases through observation and deduction",
        "key_elements": ["deduction", "cases", "Baker Street", "observation", "criminal masterminds"],
        "style": "short story collection, puzzle plots, Watson narration, Victorian atmosphere",
    },
]

# Additional twists specifically suited for scriptural adaptations
SCRIPTURAL_TWISTS = [
    {
        "name": "Modern Retelling",
        "description": "Set in contemporary times with modern parallels",
        "genre_shift": None,
        "added_elements": ["modern setting", "contemporary dialogue", "current social issues", "relatable situations"],
        "title_suffix": ["Today", "Now", "2025", "Modern"],
    },
    {
        "name": "Epic Fantasy",
        "description": "Expand with high fantasy worldbuilding and magic systems",
        "genre_shift": Genre.FANTASY,
        "added_elements": ["detailed magic system", "elaborate worldbuilding", "epic battles", "prophecy", "chosen one"],
        "title_suffix": ["Chronicles", "Saga", "Epic", "Legend"],
    },
    {
        "name": "Military Thriller",
        "description": "Focus on warfare, strategy, and combat",
        "genre_shift": Genre.THRILLER,
        "added_elements": ["tactical detail", "military strategy", "band of brothers", "sacrifice", "leadership"],
        "title_suffix": ["Wars", "Battle", "Commander", "Warrior"],
    },
    {
        "name": "Political Intrigue",
        "description": "Focus on courts, conspiracies, and power",
        "genre_shift": Genre.THRILLER,
        "added_elements": ["court politics", "secret combinations", "assassination plots", "power struggles"],
        "title_suffix": ["Throne", "Crown", "Court", "Conspiracy"],
    },
    {
        "name": "Literary Novel",
        "description": "Focus on character psychology and literary prose",
        "genre_shift": Genre.LITERARY,
        "added_elements": ["deep characterization", "internal monologue", "moral complexity", "literary prose"],
        "title_suffix": ["Novel", "Story", "Tale", "Journey"],
    },
    {
        "name": "Young Adult",
        "description": "Accessible for younger readers with coming-of-age themes",
        "genre_shift": None,
        "added_elements": ["coming of age", "identity struggles", "found family", "first love", "discovering destiny"],
        "title_suffix": ["Rising", "Awakening", "Chosen", "Legacy"],
    },
]

REMIX_TWISTS = [
    {
        "name": "Zombies",
        "description": "Add zombie apocalypse to the setting",
        "genre_shift": Genre.HORROR,
        "added_elements": ["undead hordes", "survival", "infection", "fortification", "moral decay"],
        "title_suffix": ["and Zombies", "of the Dead", "Undead", "Apocalypse"],
    },
    {
        "name": "Vampires",
        "description": "Make key characters vampires or add vampire elements",
        "genre_shift": Genre.HORROR,
        "added_elements": ["immortality", "blood drinking", "seduction", "night society", "turning"],
        "title_suffix": ["and Vampires", "Eternal", "Blood", "Nocturne"],
    },
    {
        "name": "Space Opera",
        "description": "Transport the story to a galactic setting",
        "genre_shift": Genre.SCIFI,
        "added_elements": ["spaceships", "alien species", "galactic empires", "FTL travel", "space battles"],
        "title_suffix": ["in Space", "Galactic", "Starship", "of the Stars"],
    },
    {
        "name": "Steampunk",
        "description": "Add Victorian-era technology and aesthetics",
        "genre_shift": Genre.SCIFI,
        "added_elements": ["clockwork", "airships", "steam power", "brass goggles", "automatons"],
        "title_suffix": ["Clockwork", "Steam", "Brass", "of Gears"],
    },
    {
        "name": "Modern Day",
        "description": "Transplant the story to contemporary times",
        "genre_shift": None,  # Keep original genre
        "added_elements": ["smartphones", "social media", "modern careers", "current events", "technology"],
        "title_suffix": ["2.0", "Today", "Now", "Reloaded"],
    },
    {
        "name": "Gender Swap",
        "description": "Swap the genders of main characters",
        "genre_shift": None,
        "added_elements": ["reversed expectations", "new power dynamics", "fresh perspective"],
        "title_suffix": ["Reversed", "Retold", "Redux"],
    },
    {
        "name": "Dark Retelling",
        "description": "Make it darker, grittier, more morally ambiguous",
        "genre_shift": Genre.THRILLER,
        "added_elements": ["moral ambiguity", "graphic content", "psychological depth", "tragic outcomes"],
        "title_suffix": ["Dark", "Shadow", "Twisted", "Grim"],
    },
    {
        "name": "Romantic Fantasy",
        "description": "Add fae, magic, and romantasy elements",
        "genre_shift": Genre.FANTASY,
        "added_elements": ["fae courts", "magical powers", "fated mates", "immortal beings", "magical bargains"],
        "title_suffix": ["of the Fae", "Enchanted", "Magical", "and Magic"],
    },
    {
        "name": "Mafia/Crime",
        "description": "Set in organized crime underworld",
        "genre_shift": Genre.CRIME,
        "added_elements": ["crime families", "loyalty tests", "dangerous liaisons", "power struggles"],
        "title_suffix": ["Mafia", "Crime", "Underworld", "Syndicate"],
    },
    {
        "name": "Cozy Mystery",
        "description": "Add a murder mystery with cozy elements",
        "genre_shift": Genre.MYSTERY,
        "added_elements": ["amateur detective", "small town", "quirky suspects", "tea and biscuits", "pets"],
        "title_suffix": ["Mystery", "Murders", "Case", "Investigation"],
    },
]


@dataclass
class RemixIdea:
    """A public domain classic with a modern twist."""
    original_title: str
    original_author: str
    twist_name: str
    new_title: str
    premise: str
    genre: Genre
    setting: str
    protagonist: str
    key_elements: List[str]
    style_notes: str
    word_target: int = 35000


class BookIdeaGenerator:
    """Generates book ideas for high-selling subgenres."""

    # Title templates by subgenre type
    TITLE_TEMPLATES = {
        "romantasy": [
            "A Court of {noun} and {noun}",
            "House of {noun} and {noun}",
            "Kingdom of {noun}",
            "The {noun} Prince",
            "Crown of {noun}",
            "Throne of {noun}",
            "Wings of {noun}",
            "The {noun} Queen",
            "Heir of {noun}",
            "{noun} and {noun}",
            "A {noun} of {noun}",
            "The {noun} Bargain",
            "Blood of the {noun}",
            "Shadows of {noun}",
        ],
        "dark": [
            "Twisted {noun}",
            "Cruel {noun}",
            "Ruthless {noun}",
            "Wicked {noun}",
            "Captive {noun}",
            "Dark {noun}",
            "Stolen {noun}",
            "Sinful {noun}",
            "Dangerous {noun}",
            "Savage {noun}",
            "The {noun}'s Obsession",
            "His Dark {noun}",
        ],
        "contemporary": [
            "The {noun} Effect",
            "{noun} Rules",
            "Love and Other {noun}",
            "The Art of {noun}",
            "{noun} Season",
            "How to {verb} a {noun}",
            "The {noun} Playbook",
            "{noun} Goals",
            "Faking It with the {noun}",
            "The {noun} Next Door",
        ],
        "gothic": [
            "The {noun} of {location}",
            "{location} Manor",
            "The {noun}'s Bride",
            "Secrets of {location}",
            "The Haunting of {location}",
            "Mistress of {location}",
            "The {noun} in the Tower",
            "Dark {noun}",
        ],
        "historical": [
            "The Duke's {noun}",
            "A {noun} for the Earl",
            "The Viscount's {noun}",
            "Scandal and the {noun}",
            "The {noun} Deception",
            "A Rake's {noun}",
            "The {noun} Affair",
            "Her {noun} Duke",
        ],
        "thriller": [
            "The {noun} Protocol",
            "Dark {noun}",
            "The {noun} Conspiracy",
            "Dead {noun}",
            "The Last {noun}",
            "Silent {noun}",
            "The {noun} Files",
            "No {noun} Left",
            "The {noun} Network",
            "Before the {noun}",
            "{noun} Down",
            "The {noun} Directive",
        ],
        "mystery": [
            "The {noun} Murder",
            "Death at {location}",
            "The {noun} Case",
            "A {noun} to Die For",
            "Murder in the {noun}",
            "The Body in the {noun}",
            "The {location} Mystery",
            "Case of the Missing {noun}",
        ],
        "scifi": [
            "The {noun} Station",
            "{noun} Rising",
            "The Last {noun}",
            "Beyond the {noun}",
            "The {noun} Protocol",
            "Children of {noun}",
            "The {noun} War",
            "Project {noun}",
            "The {noun} Paradox",
            "Echoes of {noun}",
        ],
        "horror": [
            "The {noun} Within",
            "What Lies {preposition}",
            "The {noun} Returns",
            "House of {noun}",
            "The {location} Curse",
            "Something {adjective}",
            "The {noun} Hunger",
            "Dark {noun}",
            "The {adjective} Door",
        ],
        "epic_fantasy": [
            "The {noun} Throne",
            "Crown of {noun}",
            "The {noun} King",
            "Empire of {noun}",
            "The {noun} Wars",
            "Heir to {noun}",
            "The Last {noun}",
            "Keeper of {noun}",
            "The {noun} Blade",
            "Song of {noun}",
        ],
        "literary": [
            "The {noun} Year",
            "A Life in {noun}",
            "The {noun} House",
            "When We Were {adjective}",
            "The {noun} Season",
            "All the {noun} We Carry",
            "Where the {noun} Ends",
            "The Weight of {noun}",
        ],
        "nonfiction": [
            "The {noun} Method",
            "Mastering {noun}",
            "The {noun} Blueprint",
            "Unlock Your {noun}",
            "The {noun} Formula",
            "Beyond {noun}",
            "The {noun} Advantage",
            "Atomic {noun}",
            "The {number}-Hour {noun}",
            "Deep {noun}",
            "The {noun} Code",
            "Think {adjective}",
            "The {adjective} {noun}",
        ],
    }

    TITLE_NOUNS = {
        "romantasy": ["Shadow", "Night", "Stars", "Blood", "Thorns", "Roses", "Ash", "Ember", "Storm",
                      "Frost", "Silver", "Gold", "Iron", "Bone", "Fire", "Ice", "Mist", "Dawn", "Dusk",
                      "Ruin", "Fate", "Desire", "Wrath", "Sin", "Secrets", "Vows", "Oaths", "Dreams"],
        "dark": ["Prince", "King", "Devil", "Beast", "Monster", "Vows", "Lies", "Obsession", "Games",
                 "Empire", "Kingdom", "Heir", "Crown", "Throne", "Hearts", "Sins", "Secrets", "Desire"],
        "contemporary": ["Game", "Rules", "Disasters", "Chaos", "Scoring", "Winning", "Falling",
                        "Player", "Captain", "Coach", "Boss", "Neighbor", "Rival", "Enemy", "Grump"],
        "gothic": ["Widow", "Bride", "Secret", "Ghost", "Shadow", "Mist", "Night", "Storm", "Curse"],
        "historical": ["Wager", "Scandal", "Fortune", "Secret", "Heart", "Desire", "Ruin", "Match",
                       "Mistress", "Wallflower", "Spinster", "Widow", "Debutante", "Heiress"],
        "thriller": ["Witness", "Agent", "Asset", "Target", "Memory", "Identity", "Trace", "Signal",
                     "Zone", "Code", "Silence", "Shadow", "Line", "Edge", "Truth", "Lies"],
        "mystery": ["Gardener", "Butler", "Widow", "Heir", "Artist", "Chef", "Librarian", "Neighbor",
                    "Stranger", "Collector", "Baker", "Antique", "Letter", "Portrait", "Will"],
        "scifi": ["Horizon", "Colony", "Signal", "Void", "Edge", "Gate", "Earth", "Mars", "Star",
                  "Light", "Dark", "Silence", "System", "Memory", "Echo", "Dawn", "Frontier"],
        "horror": ["Darkness", "Whisper", "Silence", "Shadow", "Hunger", "Entity", "Presence", "Thing",
                   "Watcher", "Sleeper", "Bones", "Blood", "Flesh", "Soul", "Mind"],
        "epic_fantasy": ["Iron", "Blood", "Storm", "Shadow", "Stone", "Fire", "Ice", "Bone",
                         "Steel", "Silver", "Gold", "Night", "Dawn", "Ruin", "Glory", "Ash"],
        "literary": ["Light", "Water", "Salt", "Stone", "Sky", "Silence", "Distance", "Forgetting",
                     "Memory", "Hope", "Loss", "Grace", "Truth", "Time", "Love"],
        "nonfiction": ["Productivity", "Focus", "Habits", "Success", "Wealth", "Mindset", "Leadership",
                       "Performance", "Growth", "Work", "Health", "Energy", "Clarity", "Power", "Change",
                       "Excellence", "Results", "Impact", "Influence", "Thinking"],
    }

    TITLE_NUMBERS = ["4", "5", "7", "10", "12", "21", "30", "100"]

    TITLE_ADJECTIVES = ["Hollow", "Silent", "Hidden", "Forgotten", "Lost", "Broken", "Dark", "Last", "Final"]
    TITLE_PREPOSITIONS = ["Beneath", "Below", "Behind", "Within", "Beyond", "Above"]

    LOCATIONS = ["Blackwood", "Thornfield", "Ravenswood", "Ashworth", "Darkmore", "Winterfell",
                 "Shadowmere", "Grimsworth", "Hollowbrook", "Nightshade", "Mistwood", "Coldwell"]

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def _get_title_type(self, subgenre: Subgenre) -> str:
        """Map subgenre to title type."""
        mapping = {
            # Romance
            Subgenre.ROMANTASY_FAE: "romantasy",
            Subgenre.ROMANTASY_DRAGON: "romantasy",
            Subgenre.ROMANTASY_ACADEMY: "romantasy",
            Subgenre.DARK_ROMANCE: "dark",
            Subgenre.MAFIA_ROMANCE: "dark",
            Subgenre.HOCKEY_ROMANCE: "contemporary",
            Subgenre.SPORTS_ROMANCE: "contemporary",
            Subgenre.SMALL_TOWN: "contemporary",
            Subgenre.ROMANTIC_COMEDY: "contemporary",
            Subgenre.GOTHIC_ROMANCE: "gothic",
            Subgenre.PARANORMAL_SHIFTER: "romantasy",
            Subgenre.PARANORMAL_VAMPIRE: "gothic",
            Subgenre.HISTORICAL_REGENCY: "historical",
            Subgenre.HISTORICAL_VICTORIAN: "gothic",
            Subgenre.BILLIONAIRE: "contemporary",
            Subgenre.SECOND_CHANCE: "contemporary",
            Subgenre.ENEMIES_TO_LOVERS: "contemporary",
            Subgenre.FORCED_PROXIMITY: "contemporary",
            # Thriller
            Subgenre.PSYCHOLOGICAL_THRILLER: "thriller",
            Subgenre.TECH_THRILLER: "thriller",
            Subgenre.CONSPIRACY_THRILLER: "thriller",
            Subgenre.SURVIVAL_THRILLER: "thriller",
            Subgenre.CRIME_THRILLER: "thriller",
            # Mystery
            Subgenre.COZY_MYSTERY: "mystery",
            Subgenre.POLICE_PROCEDURAL: "mystery",
            Subgenre.AMATEUR_SLEUTH: "mystery",
            # Sci-Fi
            Subgenre.SPACE_OPERA: "scifi",
            Subgenre.CYBERPUNK: "scifi",
            Subgenre.POST_APOCALYPTIC: "scifi",
            Subgenre.FIRST_CONTACT: "scifi",
            # Horror
            Subgenre.SUPERNATURAL_HORROR: "horror",
            Subgenre.PSYCHOLOGICAL_HORROR: "horror",
            Subgenre.COSMIC_HORROR: "horror",
            # Fantasy
            Subgenre.EPIC_FANTASY: "epic_fantasy",
            Subgenre.URBAN_FANTASY: "thriller",  # urban fantasy uses noir-style titles
            Subgenre.GRIMDARK: "epic_fantasy",
            # Literary
            Subgenre.LITERARY_UPMARKET: "literary",
            # Non-Fiction
            Subgenre.SELF_HELP: "nonfiction",
            Subgenre.BUSINESS: "nonfiction",
            Subgenre.PRODUCTIVITY: "nonfiction",
            Subgenre.FINANCE: "nonfiction",
            Subgenre.HEALTH_WELLNESS: "nonfiction",
            Subgenre.PSYCHOLOGY: "nonfiction",
            Subgenre.HOW_TO: "nonfiction",
        }
        return mapping.get(subgenre, "contemporary")

    def generate_title(self, subgenre: Subgenre) -> str:
        """Generate a genre-appropriate title."""
        title_type = self._get_title_type(subgenre)
        templates = self.TITLE_TEMPLATES.get(title_type, self.TITLE_TEMPLATES["contemporary"])
        nouns = self.TITLE_NOUNS.get(title_type, self.TITLE_NOUNS["contemporary"])

        template = random.choice(templates)

        # Fill in template
        while "{noun}" in template:
            template = template.replace("{noun}", random.choice(nouns), 1)
        while "{location}" in template:
            template = template.replace("{location}", random.choice(self.LOCATIONS), 1)
        while "{verb}" in template:
            verbs = ["Win", "Tame", "Catch", "Resist", "Forget", "Survive", "Handle"]
            template = template.replace("{verb}", random.choice(verbs), 1)
        while "{adjective}" in template:
            template = template.replace("{adjective}", random.choice(self.TITLE_ADJECTIVES), 1)
        while "{preposition}" in template:
            template = template.replace("{preposition}", random.choice(self.TITLE_PREPOSITIONS), 1)
        while "{number}" in template:
            template = template.replace("{number}", random.choice(self.TITLE_NUMBERS), 1)

        return template

    def generate_idea(self, subgenre: Subgenre, author_generator=None) -> BookIdea:
        """Generate a complete book idea for the given subgenre."""
        profile = SUBGENRE_PROFILES[subgenre]

        # Generate title
        title = self.generate_title(subgenre)

        # Generate author name
        if author_generator:
            author_obj = author_generator.generate(profile["genre"], title, "")
            author = author_obj.full_name
        else:
            # Fallback author names
            from book_factory import AuthorNameGenerator
            gen = AuthorNameGenerator()
            author_obj = gen.generate(profile["genre"], title, "")
            author = author_obj.full_name

        # Select elements
        hero = random.choice(profile["hero_types"])
        heroine = random.choice(profile["heroine_types"])
        setting = random.choice(profile["settings"])
        selected_tropes = random.sample(profile["tropes"], min(3, len(profile["tropes"])))
        conflict = random.choice(profile["conflicts"])

        # Build premise
        premise = self._build_premise(hero, heroine, setting, selected_tropes, conflict, profile)

        return BookIdea(
            title=title,
            author=author,
            subgenre=subgenre,
            premise=premise,
            hero=hero,
            heroine=heroine,
            setting=setting,
            tropes=selected_tropes,
            conflict=conflict,
            heat_level=profile["heat_level"],
            word_target=profile["word_target"],
            cover_mood=profile["cover_mood"]
        )

    def _build_premise(self, hero: str, heroine: str, setting: str,
                       tropes: List[str], conflict: str, profile: Dict) -> str:
        """Build a compelling premise from components."""
        trope_str = " and ".join(tropes[:2])

        premise = (
            f"In {setting}, a {heroine.lower()} crosses paths with a {hero.lower()}. "
            f"What begins as {conflict} ignites into a {trope_str} romance "
            f"that will test everything they thought they knew about love and loyalty."
        )

        return premise

    def generate_remix_idea(self, classic: Dict = None, twist: Dict = None,
                            use_scriptural_twists: bool = False) -> RemixIdea:
        """
        Generate a remix of a public domain classic with a modern twist.

        Example: "Pride and Prejudice and Zombies"
        For scriptural works, use use_scriptural_twists=True for appropriate adaptations.
        """
        # Select random classic and twist if not provided
        if classic is None:
            classic = random.choice(PUBLIC_DOMAIN_CLASSICS)
        if twist is None:
            # Use scriptural twists for Book of Mormon content
            is_scriptural = classic.get("source") == "Book of Mormon"
            if is_scriptural or use_scriptural_twists:
                twist = random.choice(SCRIPTURAL_TWISTS)
            else:
                twist = random.choice(REMIX_TWISTS)

        # Generate new title
        suffix = random.choice(twist["title_suffix"])
        if suffix.startswith("and "):
            new_title = f"{classic['title']} {suffix}"
        else:
            new_title = f"{classic['title']}: {suffix}"

        # Determine genre
        genre = twist["genre_shift"] if twist["genre_shift"] else Genre.ROMANCE

        # Combine elements
        combined_elements = classic["key_elements"][:3] + twist["added_elements"][:3]

        # Build remix premise
        premise = self._build_remix_premise(classic, twist)

        # Build style notes emphasizing original author's style
        style_notes = f"Write in the style of {classic['author']}: {classic['style']}. " \
                      f"Maintain the original's tone and literary voice while seamlessly " \
                      f"incorporating the {twist['name'].lower()} elements."

        return RemixIdea(
            original_title=classic["title"],
            original_author=classic["author"],
            twist_name=twist["name"],
            new_title=new_title,
            premise=premise,
            genre=genre,
            setting=f"{classic['setting']} (with {twist['name'].lower()} elements)",
            protagonist=classic.get("protagonist", "The protagonist"),
            key_elements=combined_elements,
            style_notes=style_notes,
            word_target=35000,
        )

    def _build_remix_premise(self, classic: Dict, twist: Dict) -> str:
        """Build a premise for the remix."""
        base_plot = classic["core_plot"]
        twist_elements = ", ".join(twist["added_elements"][:2])

        premise = (
            f"A reimagining of {classic['author']}'s {classic['title']}. "
            f"{base_plot}—but now with {twist_elements}. "
            f"In this fresh take on the beloved classic, {classic.get('protagonist', 'our hero')} "
            f"must navigate not only the original conflicts but also the new challenges "
            f"that {twist['name'].lower()} elements bring to the story. "
            f"Written in the distinctive style of the original work."
        )
        return premise


# ============================================================================
# CONTINUOUS GENERATOR
# ============================================================================

@dataclass
class GenerationStats:
    """Track generation statistics."""
    total_books: int = 0
    total_words: int = 0
    by_subgenre: Dict[str, int] = field(default_factory=dict)
    successful: int = 0
    failed: int = 0
    start_time: float = field(default_factory=time.time)

    def add_book(self, result: BookResult, subgenre: str):
        """Record a generated book."""
        self.total_books += 1
        if result.success:
            self.successful += 1
            self.total_words += result.word_count
            self.by_subgenre[subgenre] = self.by_subgenre.get(subgenre, 0) + 1
        else:
            self.failed += 1

    def to_dict(self) -> Dict:
        elapsed = time.time() - self.start_time
        return {
            "total_books": self.total_books,
            "successful": self.successful,
            "failed": self.failed,
            "total_words": self.total_words,
            "by_subgenre": self.by_subgenre,
            "elapsed_hours": round(elapsed / 3600, 2),
            "books_per_hour": round(self.successful / max(1, elapsed / 3600), 2),
        }


class ContinuousGenerator:
    """
    Continuously generates books in high-selling subgenres.

    Weighted random selection based on market share.
    """

    def __init__(self,
                 output_dir: str = "./output/books",
                 provider: str = "deepseek",
                 parallel_workers: int = 1):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.provider = provider
        self.parallel_workers = parallel_workers  # For parallel chapter generation
        self.factory = BookFactory(provider=provider)
        self.idea_generator = BookIdeaGenerator()
        self.stats = GenerationStats()

        # Build weighted subgenre list
        self.subgenre_weights = []
        self.subgenres = []
        for subgenre, profile in SUBGENRE_PROFILES.items():
            self.subgenres.append(subgenre)
            self.subgenre_weights.append(profile["market_share"])

        # Normalize weights
        total = sum(self.subgenre_weights)
        self.subgenre_weights = [w/total for w in self.subgenre_weights]

        # Use centralized logging
        self.logger = get_logger(__name__)

        # State file for tracking
        self.state_file = self.output_dir / "generation_state.json"

    def select_subgenre(self) -> Subgenre:
        """Select a subgenre weighted by market share."""
        return random.choices(self.subgenres, weights=self.subgenre_weights, k=1)[0]

    def generate_one_book(self) -> Optional[BookResult]:
        """Generate a single book."""
        # Select subgenre
        subgenre = self.select_subgenre()
        profile = SUBGENRE_PROFILES[subgenre]

        self.logger.info(f"Selected subgenre: {profile['name']}")

        # Generate idea
        idea = self.idea_generator.generate_idea(subgenre)

        self.logger.info(f"Title: {idea.title}")
        self.logger.info(f"Author: {idea.author}")
        self.logger.info(f"Premise: {idea.premise[:100]}...")

        # Create config (use parallel workers for 3-5x speedup)
        config = BookConfig(
            title=idea.title,
            premise=idea.premise,
            genre=profile["genre"],
            author_name=idea.author,
            num_chapters=10,
            words_per_chapter=idea.word_target // 10,
            generate_cover=True,
            output_dir=str(self.output_dir),
            provider=self.provider,
            parallel_workers=self.parallel_workers  # Parallel chapter generation!
        )

        # Generate book
        result = self.factory.generate_book(config)

        # Update stats
        self.stats.add_book(result, subgenre.value)

        # Save state
        self._save_state()

        return result

    def run_continuous(self,
                       max_books: Optional[int] = None,
                       hours: Optional[float] = None):
        """
        Run continuous generation.

        Args:
            max_books: Stop after this many books (None = unlimited)
            hours: Stop after this many hours (None = unlimited)
        """
        self.logger.info("="*60)
        self.logger.info("CONTINUOUS BOOK GENERATION STARTING")
        self.logger.info(f"Provider: {self.provider}")
        self.logger.info(f"Output: {self.output_dir}")
        if max_books:
            self.logger.info(f"Max books: {max_books}")
        if hours:
            self.logger.info(f"Max hours: {hours}")
        self.logger.info("="*60)

        start_time = time.time()
        books_generated = 0

        try:
            while True:
                # Check limits
                if max_books and books_generated >= max_books:
                    self.logger.info(f"Reached max books limit: {max_books}")
                    break

                if hours:
                    elapsed = (time.time() - start_time) / 3600
                    if elapsed >= hours:
                        self.logger.info(f"Reached time limit: {hours} hours")
                        break

                # Generate a book
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"GENERATING BOOK #{books_generated + 1}")
                self.logger.info(f"{'='*60}\n")

                try:
                    result = self.generate_one_book()

                    if result and result.success:
                        books_generated += 1
                        self.logger.info(f"\nSUCCESS: {result.title} by {result.author}")
                        self.logger.info(f"  Words: {result.word_count:,}")
                        self.logger.info(f"  ePub: {result.epub_path}")
                        self.logger.info(f"  Cover: {result.cover_path}")
                    else:
                        self.logger.error(f"\nFAILED: {result.error if result else 'Unknown error'}")

                    # Brief pause between books
                    time.sleep(5)

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f"Error generating book: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(10)  # Longer pause on error

        except KeyboardInterrupt:
            self.logger.info("\nGeneration interrupted by user")

        # Final stats
        self._print_final_stats()

    def _save_state(self):
        """Save generation state to file."""
        state = {
            "stats": self.stats.to_dict(),
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _print_final_stats(self):
        """Print final generation statistics."""
        stats = self.stats.to_dict()

        print("\n" + "="*60)
        print("GENERATION COMPLETE - FINAL STATISTICS")
        print("="*60)
        print(f"Total Books Generated: {stats['successful']}")
        print(f"Failed Attempts: {stats['failed']}")
        print(f"Total Words: {stats['total_words']:,}")
        print(f"Time Elapsed: {stats['elapsed_hours']} hours")
        print(f"Books per Hour: {stats['books_per_hour']}")
        print("\nBy Subgenre:")
        for subgenre, count in sorted(stats['by_subgenre'].items(), key=lambda x: -x[1]):
            print(f"  {subgenre}: {count}")
        print("="*60 + "\n")


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Continuous Book Generator - Multi-Genre Fiction"
    )
    parser.add_argument("--books", type=int, help="Number of books to generate")
    parser.add_argument("--hours", type=float, help="Hours to run")
    parser.add_argument("--output", default="./output/books", help="Output directory")
    parser.add_argument("--provider", default="deepseek", help="LLM provider")
    parser.add_argument("--parallel", type=int, default=1,
                       help="Parallel workers for chapter generation (3-5 recommended for 3-5x speedup)")
    parser.add_argument("--list-subgenres", action="store_true", help="List available subgenres")

    args = parser.parse_args()

    if args.list_subgenres:
        print("\nAvailable Subgenres (by market share):\n")
        sorted_subgenres = sorted(
            SUBGENRE_PROFILES.items(),
            key=lambda x: -x[1]["market_share"]
        )
        for subgenre, profile in sorted_subgenres:
            print(f"  {profile['name']:25} ({profile['market_share']*100:.0f}%)")
            print(f"    Tropes: {', '.join(profile['tropes'][:3])}")
            print()
        return

    generator = ContinuousGenerator(
        output_dir=args.output,
        provider=args.provider,
        parallel_workers=args.parallel
    )

    generator.run_continuous(
        max_books=args.books,
        hours=args.hours
    )


if __name__ == "__main__":
    main()
