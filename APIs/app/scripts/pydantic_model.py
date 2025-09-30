from typing import List
from pydantic import BaseModel, Field

from typing import Optional, Tuple, Dict
from enum import Enum
from pydantic import BaseModel, field_validator

from pydantic import BaseModel, Field, model_validator, constr

# --- Enums --- 

class GameGenre(str, Enum):
    ACTION_ADVENTURE = "Action-Adventure"
    PLATFORM = "Platform"
    PUZZLE = "Puzzle"
    ROLE_PLAYING = "Role Playing"
    SIMULATION = "Simulation"
    STRATEGY = "Strategy"
    SURVIVAL = "Survival"

class GameTone(str, Enum):
    ACTIVE = "Active"
    SERIOUS = "Serious"
    IRONIC = "Ironic"
    HUMOROUS = "Humorous"
    FANTASTIC = "Fantastic"
    POPULAR = "Popular"
    ELEVATED = "Elevated"
    LOVING = "Loving"
    MAGIC = "Magic"
    DRAMATIC = "Dramatic"

class PlotTitle(str, Enum):
    IN_SEARCH_OF_TREASURE = "In Search of Treasure"
    THE_RETURN_TO_HOME = "The Return to Home"
    THE_FOUNDATION_OF_A_NEW_HOMELAND = "The Foundation of a New Homeland"
    THE_BENEFACTOR_INTRUDER = "The Benefactor Intruder"
    THE_DESTRUCTIVE_INTRUDER = "The Destructive Intruder"
    THE_OLD_AND_THE_NEW = "The Old and the New"
    # Keep the original spelling as provided:
    ASCENTION_THROUGH_LOVE = "Ascention through Love"
    SELF_KNOWLEDGE = "Self-Knowledge"
    WITHIN_THE_LABYRINTH = "Within the Labyrinth"
    THE_SPLIT_SELF = "The Split Self"
    THE_PACT_WITH_THE_DEVIL = "The Pact with the Devil"
    THE_DESCENT_INTO_HELL = "The Descent into Hell"
    THE_MARTYR_AND_THE_TYRANT = "The Martyr and the Tyrant"
    THE_THIRST_FOR_POWER = "The Thirst for Power"
    THE_CREATION_OF_ARTIFICIAL_LIFE = "The Creation of Artificial Life"

# --- Plot metadata ---

PLOT_INFO: Dict[PlotTitle, Tuple[str, str]] = {
    PlotTitle.IN_SEARCH_OF_TREASURE: (
        "A mission that leads to a journey where the hero will face duels, unexpected aids, escapes, "
        "and will return victorious to the place of origin, with material and spiritual treasures.",
        "Jason and the Argonauts",
    ),
    PlotTitle.THE_RETURN_TO_HOME: (
        "A journey of identity recovery during which the tension between obligation and the desire for freedom manifests; "
        "between home and the pleasure of the journey; between memory and forgetfulness.",
        "The Odyssey",
    ),
    PlotTitle.THE_FOUNDATION_OF_A_NEW_HOMELAND: (
        "The search for the promised land by a leader with individual desires and collective duties, surrounded by a vulnerable community. "
        "It explains the difficulties and bravery of those who forged the origins of a community.",
        "The Eneida",
    ),
    PlotTitle.THE_BENEFACTOR_INTRUDER: (
        "A human group at a standstill and in crisis faces a transformative, traumatic, and liberating experience "
        "triggered by the arrival of a messianic leader.",
        "Any messianic literature",
    ),
    PlotTitle.THE_DESTRUCTIVE_INTRUDER: (
        "A tale of the emergence of the forces of darkness that sparks the revelation of heroes amid a full internal "
        "cataclysm within the community.",
        "Narratives of the evil",
    ),
    PlotTitle.THE_OLD_AND_THE_NEW: (
        "A world that is hopelessly shipwrecked in the sea of progress, a process of decomposition that shows a social class "
        "that is ending and that gives way to a world of dismantlers without regard or scruples.",
        "The Cherry Orchard",
    ),
    PlotTitle.ASCENTION_THROUGH_LOVE: (
        "A type of love, fundamentally happy and constructive, that represents a social promotion, an improvement. "
        "It develops an everyday universe full of hostility; a fantasy infatuation; and an entry into the ideal world as a reward "
        "for a virtuous and sacrificial life.",
        "Cinderella",
    ),
    PlotTitle.SELF_KNOWLEDGE: (
        "The being who, in his investigation, ends up discovering the most terrible secret within himself. "
        "Characterized by uncertain origin, obsessive search for identity, and an investigation that travels everywhere to return to the start.",
        "Oedipus",
    ),
    PlotTitle.WITHIN_THE_LABYRINTH: (
        "A man alone faced with a universal, opaque and immobile structure. Shows the attempt of power to absorb and annul man; "
        "an adventure across the ocean of disorientation, the abolition of home, and the world as estrangement.",
        "The Castle (Kafka)",
    ),
    PlotTitle.THE_SPLIT_SELF: (
        "The motif of the double that warns against the certainty of identity and opens cracks in the insecure consciousness of the self; "
        "difficulty escaping the shadow; conflict of double personality; confrontation with social morality.",
        "Dr. Jekyll and Mr. Hyde",
    ),
    PlotTitle.THE_PACT_WITH_THE_DEVIL: (
        "The sale of the soul for cosmogonic power, beyond human limits; quest for immortality (in an incomplete existence) and the fight against temptation.",
        "Faust",
    ),
    PlotTitle.THE_DESCENT_INTO_HELL: (
        "The search for lost love beyond life by an artist, a sorcerer of natural forces; renunciation of living in the real world and the need to go beyond the mirror.",
        "Orpheus",
    ),
    PlotTitle.THE_MARTYR_AND_THE_TYRANT: (
        "The conflict between the defender of the innocent (martyr) and the tyrant who represses; political and metaphysical debate around hard written laws without mercy.",
        "Antigone",
    ),
    PlotTitle.THE_THIRST_FOR_POWER: (
        "Humans thirsty for power, willing to do anything to get it, arrive at the summit of ambition and approach isolation and descent.",
        "Macbeth",
    ),
    PlotTitle.THE_CREATION_OF_ARTIFICIAL_LIFE: (
        "Aspiration to create life without sexual generation through intelligent, technological intervention; dangers of usurping divine prerogatives; "
        "the creature’s peculiar life and tremendous loneliness.",
        "Pygmalion",
    ),
}

# --- Model ---

class StoryInputs(BaseModel):
    """
    Inputs for your story-generation prompt.
    All fields are optional to allow partial forms; enums help constrain allowed values when provided.
    """
    objectives: Optional[str] = None
    genre: Optional[GameGenre] = None
    plot_title: Optional[PlotTitle] = None
    tone: Optional[GameTone] = None
    user_prompt: Optional[str] = None

    # Accept case-insensitive strings for enum fields
    @field_validator("genre", mode="before")
    @classmethod
    def _coerce_genre(cls, v):
        if v is None:
            return v
        if isinstance(v, GameGenre):
            return v
        if isinstance(v, str):
            for g in GameGenre:
                if v.strip().casefold() == g.value.casefold():
                    return g
        raise ValueError(f"Invalid genre: {v!r}. Allowed: {[g.value for g in GameGenre]}")

    @field_validator("tone", mode="before")
    @classmethod
    def _coerce_tone(cls, v):
        if v is None:
            return v
        if isinstance(v, GameTone):
            return v
        if isinstance(v, str):
            for t in GameTone:
                if v.strip().casefold() == t.value.casefold():
                    return t
        raise ValueError(f"Invalid tone: {v!r}. Allowed: {[t.value for t in GameTone]}")

    @field_validator("plot_title", mode="before")
    @classmethod
    def _coerce_plot_title(cls, v):
        if v is None:
            return v
        if isinstance(v, PlotTitle):
            return v
        if isinstance(v, str):
            for p in PlotTitle:
                if v.strip().casefold() == p.value.casefold():
                    return p
        raise ValueError(f"Invalid plot_title: {v!r}. Allowed: {[p.value for p in PlotTitle]}")

    # Convenience accessors
    def plot_metadata(self) -> Optional[Tuple[str, str]]:
        """
        Returns (plot_description, universal_reference) if plot_title is set; otherwise None.
        """
        if not self.plot_title:
            return None
        return PLOT_INFO[self.plot_title]

    def as_dict(self) -> dict:
        """
        Export a clean dict using enum values (strings) instead of Enum objects.
        """
        d = self.model_dump()
        if self.genre:
            d["genre"] = self.genre.value
        if self.tone:
            d["tone"] = self.tone.value
        if self.plot_title:
            d["plot_title"] = self.plot_title.value
            desc, ref = PLOT_INFO[self.plot_title]
            d["plot_description"] = desc
            d["universal_reference"] = ref
        return d


class StoryPrompt(BaseModel):
    objectives: str = Field(default="")
    #genre: List[str] = Field(default_factory=lambda: ["", ""])
    genre: str = Field(default="")
    plot: str = Field(default="")
    tone: str = Field(default="")
    usr_prompt: str = Field(default="")



# ----------------------------
# Enums
# ----------------------------

class GameStyle5(str, Enum):
    RETRO = "Retro style"
    CARTOON = "Cartoon style"
    MINIMALISTIC = "Minimalistic style"
    STYLISED = "Stylised style"
    REALISTIC = "Realistic style"

class TechChoice(str, Enum):
    # 2D
    PIXEL_ART = "Pixel Art"
    ILLUSTRATION_2D = "2D Illustration"
    VECTORISED = "Vectorised"
    # 3D
    POLYGONS = "Polygons"
    VOXELS = "Voxels"
    FIXED_25D = "2.5D / Fixed Camera Graphics"

    def is_2d(self) -> bool:
        return self in {
            TechChoice.PIXEL_ART,
            TechChoice.ILLUSTRATION_2D,
            TechChoice.VECTORISED,
        }

    def is_3d(self) -> bool:
        return not self.is_2d()

# ----------------------------
# Core template (prompt is required)
# ----------------------------

class AestheticsMessage(BaseModel):
    """
    Core message used to build prompts.
    - char_env_item, typo_menu, and maps: choose from GameStyle5
    - technology: choose from TechChoice
    - prompt will be generated from template based on aesthetics
    """
    char_env_item: Optional[GameStyle5] = Field(default=None)
    typo_menu: Optional[GameStyle5] = Field(default=None)
    maps: Optional[GameStyle5] = Field(default=None)
    technology: Optional[TechChoice] = Field(default=None)


# ----------------------------
# (Optional) Companion for external style images
#   – kept separate, as you requested.
# ----------------------------

