"""
ChromaDB-backed vector memory service.

On startup: loads a curated wellness knowledge base into ChromaDB (if empty).
At inference time: retrieves the top-k most relevant tips for the user's state.

Uses chromadb's built-in embedding function (no OpenAI key required for this layer).
"""

import chromadb
from chromadb.utils import embedding_functions
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None
_collection = None

WELLNESS_KNOWLEDGE_BASE = [
    # Sleep
    "Maintain consistent sleep and wake times, even on weekends, to stabilize your circadian rhythm.",
    "Avoid screens for at least 30 minutes before bed to improve sleep onset and quality.",
    "Keep your bedroom cool (around 65-68°F / 18-20°C) for optimal deep sleep.",
    "If you slept fewer than 6 hours, avoid napping longer than 20 minutes to protect nighttime sleep.",
    "A short wind-down routine of 10-15 minutes (reading, stretching, journaling) signals the brain to sleep.",
    # Stress
    "Box breathing (inhale 4s, hold 4s, exhale 4s, hold 4s) activates the parasympathetic nervous system.",
    "When stress peaks, name the emotion aloud or in writing — labeling reduces amygdala activation.",
    "The 5-4-3-2-1 grounding technique (5 sights, 4 sounds, 3 touches, 2 smells, 1 taste) stops anxiety spirals.",
    "Progressive muscle relaxation, tensing and releasing each muscle group, lowers cortisol within minutes.",
    "Schedule a 10-minute 'worry window' daily — contain anxiety to a defined time slot.",
    # Mood
    "Behavioral activation: do one small enjoyable activity even when motivation is low — action precedes mood.",
    "Sunlight exposure within 30 minutes of waking regulates serotonin and dopamine naturally.",
    "Social connection, even a 5-minute text to a friend, meaningfully improves mood.",
    "Gratitude journaling (3 specific items per day) measurably shifts attention toward positives within weeks.",
    "Cold water on your face or wrists triggers the dive reflex and rapidly calms the nervous system.",
    # Activity
    "A 10-minute walk outside is enough to improve mood, focus, and creativity.",
    "Desk stretches every 60 minutes prevent the cognitive dulling caused by prolonged sitting.",
    "Resistance training twice per week reduces anxiety symptoms as effectively as many medications.",
    "Even light yoga or stretching for 15 minutes lowers cortisol and improves sleep quality.",
    "Stair climbing for 3 minutes burns similar calories to a short run and requires no equipment.",
    # Nutrition
    "Eating within 1 hour of waking stabilizes blood sugar and prevents mid-morning energy crashes.",
    "Hydration: even mild dehydration (1-2%) significantly impairs concentration and mood.",
    "Omega-3 rich foods (salmon, walnuts, flaxseed) support brain function and reduce inflammation.",
    "Limiting caffeine after 2pm protects deep sleep stages, even if you feel unaffected.",
    "A protein-rich dinner promotes the melatonin precursor tryptophan for better sleep onset.",
    # Focus
    "The Pomodoro technique (25 min focus, 5 min break) sustains concentration without burnout.",
    "Single-tasking is 40% more efficient than multitasking — close unused browser tabs.",
    "Your peak cognitive window is typically 2-4 hours after waking — schedule hard work then.",
    "Ambient noise at 70 dB (coffee shop level) enhances creative thinking for most people.",
    "Brief physical movement between focus sessions restores sustained attention capacity.",
]


def get_collection():
    global _client, _collection

    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    ef = embedding_functions.DefaultEmbeddingFunction()

    _collection = _client.get_or_create_collection(
        name="wellness_knowledge",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    # Seed the collection if empty
    if _collection.count() == 0:
        logger.info("Seeding ChromaDB wellness knowledge base …")
        _collection.add(
            documents=WELLNESS_KNOWLEDGE_BASE,
            ids=[f"tip_{i}" for i in range(len(WELLNESS_KNOWLEDGE_BASE))],
        )
        logger.info(f"Seeded {len(WELLNESS_KNOWLEDGE_BASE)} wellness tips.")

    return _collection


def retrieve_context(query: str, n_results: int = 3) -> list[str]:
    """
    Retrieve the most relevant wellness tips for a given query string.
    Returns a list of tip strings.
    """
    try:
        collection = get_collection()
        results = collection.query(query_texts=[query], n_results=n_results)
        tips = results["documents"][0] if results["documents"] else []
        logger.info(f"ChromaDB retrieved {len(tips)} tips for query: '{query[:60]}'")
        return tips
    except Exception as e:
        logger.error(f"ChromaDB retrieval failed: {e}")
        return []
