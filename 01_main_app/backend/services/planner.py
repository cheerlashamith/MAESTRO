from __future__ import annotations
import json
import re
import time
import random
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import concurrent.futures
from backend.core.schemas import GenerateRequest, Mode, VisualStyle, TaskType
from backend.core.config import project_root, get_config

# ---------------------------------------------------------------------------
# SYLLABUS & CONFIGURATION
# ---------------------------------------------------------------------------

SYLLABUS_PATH = project_root() / "data" / "jntuk_r23_data_structures_syllabus.json"


def _load_syllabus() -> Optional[Dict[str, Any]]:
    """Load the JNTUK R23 Data Structures syllabus JSON."""
    if not SYLLABUS_PATH.exists():
        return None
    try:
        return json.loads(SYLLABUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _flatten_topics(syllabus: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten all units/topics into a single list with unit context."""
    flat = []
    for unit in syllabus.get("units", []):
        for topic in unit.get("topics", []):
            flat.append({
                "unit": unit.get("unit", ""),
                "unit_title": unit.get("title", ""),
                "topic": topic.get("topic", ""),
                "subtopics": topic.get("subtopics", []),
                "recommended_visuals": topic.get("recommended_visuals", []),
                "renderer": topic.get("course_mode_renderer", "manim_course"),
            })
    return flat


# ---------------------------------------------------------------------------
# TOPIC MATCHING
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for fuzzy matching."""
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def _score_match(query: str, topic_name: str) -> float:
    """Return a fuzzy score between query and topic name."""
    q = _normalize(query)
    t = _normalize(topic_name)
    if not q or not t:
        return 0.0
    if q == t:
        return 1.0
    if q in t or t in q:
        return 0.85
    q_words = set(q.split())
    t_words = set(t.split())
    if not q_words or not t_words:
        return 0.0
    intersection = q_words & t_words
    union = q_words | t_words
    return len(intersection) / len(union)


def _match_topic(query: Optional[str], topics: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the best matching topic from the syllabus."""
    if not query:
        return None
    best = None
    best_score = 0.0
    for topic in topics:
        score = _score_match(query, topic["topic"])
        if score > best_score and score >= 0.55:
            best_score = score
            best = topic
    return best


def _match_all_topics(query: Optional[str], topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return all topics that match the query (for broad queries like 'Linked Lists')."""
    if not query:
        return []
    q = _normalize(query)
    matches = []
    for topic in topics:
        score = _score_match(query, topic["topic"])
        if score >= 0.55:
            matches.append((score, topic))
    matches.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in matches]


# ---------------------------------------------------------------------------
# AI ROUTING
# ---------------------------------------------------------------------------
from backend.services.brain_manager import BrainManager, TaskType

def _enrich_task(key: str, prompt: str) -> str:
    return BrainManager.ask(prompt, TaskType.ENRICHMENT)

def _enrich_plan_parallel(plan: Dict[str, Any], topic_name: str) -> Dict[str, Any]:
    prompts = {
        "seo_tags": f"Generate 10 comma-separated SEO tags for an educational video about: {topic_name}. Return ONLY the comma-separated string without explanations.",
        "video_description": f"Write a 3-sentence YouTube video description for a tutorial on {topic_name}. Make it engaging.",
        "thumbnail_prompt": f"Write a prompt for an AI image generator to create a YouTube thumbnail for {topic_name}. Just visual description, no text.",
        "learning_objectives": f"List 3 short bullet-point learning objectives for a lesson on {topic_name}.",
        "social_media_caption": f"Write a short tweet to promote a new video about {topic_name}. Include hashtags."
    }
    
    cfg = get_config().get("brain_manager", {})
    workers = cfg.get("max_parallel_workers", 5)
    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_key = {executor.submit(_enrich_task, key, prompt): key for key, prompt in prompts.items()}
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result().strip()
            except Exception as exc:
                print(f"[Planner] Enrichment task {key} failed: {exc}")
                results[key] = ""
                
    plan["enrichment"] = results
    return plan


# ---------------------------------------------------------------------------
# JSON EXTRACTION
# ---------------------------------------------------------------------------

def _strip_think_tags(text: str) -> str:
    """Remove DeepSeek / QwQ <think>...</think> reasoning blocks."""
    # Remove complete blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Remove truncated opening block if closing tag never appears
    if "<think>" in text and "</think>" not in text:
        text = text.split("<think>")[0]
    return text


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from LLM output."""
    text = _strip_think_tags(text)
    # Try markdown code block first
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try raw JSON object anywhere
    m = re.search(r"(\{.*\})", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try to fix trailing commas / single quotes (last resort)
    try:
        return json.loads(text)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# VISUAL MAPPING
# ---------------------------------------------------------------------------

def _diagram_type_for(subtopic: str, recommended_visuals: List[str]) -> str:
    """Pick a Manim diagram type that best fits a subtopic."""
    st = subtopic.lower()
    # DSA-specific overrides — map to NEW specific diagram types
    if any(w in st for w in ["binary search tree", "bst", "avl", "red-black", "splay tree", "trie"]):
        return "tree"
    if any(w in st for w in ["tree", "traversal", "root", "leaf", "height", "depth", "in-order", "pre-order", "post-order", "inorder", "preorder", "postorder", "level order"]):
        return "tree"
    if any(w in st for w in ["heap", "min heap", "max heap", "heapify"]):
        return "tree"
    if any(w in st for w in ["bubble sort", "bubble", "selection sort", "selection", "insertion sort", "insertion", "quick sort", "merge sort", "sorting", "sort"]):
        return "sorting"
    if any(w in st for w in ["binary search", "linear search", "search"]):
        return "array"
    if any(w in st for w in ["stack", "push", "pop", "lifo", "overflow", "underflow", "call stack"]):
        return "stack"
    if any(w in st for w in ["queue", "enqueue", "dequeue", "fifo", "circular queue", "priority queue", "deque"]):
        return "queue"
    if any(w in st for w in ["linked list", "singly linked", "doubly linked", "circular linked", "list node"]):
        return "linked_list"
    if any(w in st for w in ["hash", "collision", "probing", "chaining", "hashmap", "hash table"]):
        return "hash_table"
    if any(w in st for w in ["graph", "adjacency", "weighted", "directed", "undirected", "bfs", "dfs", "dijkstra"]):
        return "network"
    if any(w in st for w in ["comparison", "vs", "versus", "before", "after"]):
        return "comparison"
    if any(w in st for w in ["equation", "formula", "complexity", "time", "space", "big o", "O(n)", "O(log n)"]):
        return "equation"
    if any(w in st for w in ["cycle", "circular"]):
        return "cycle"
    if any(w in st for w in ["array", "index", "element"]):
        return "array"
    if recommended_visuals:
        first = recommended_visuals[0].lower()
        if "tree" in first or "bst" in first: return "tree"
        if "sort" in first or "bar" in first: return "sorting"
        if "stack" in first: return "stack"
        if "queue" in first: return "queue"
        if "linked" in first or "list" in first: return "linked_list"
        if "hash" in first: return "hash_table"
        if "array" in first or "bars" in first or "highlight" in first: return "array"
        if "flowchart" in first or "map" in first: return "flowchart"
        if "comparison" in first or "table" in first: return "comparison"
        if "timeline" in first: return "timeline"
    return "process"


def _visual_data_for(subtopic: str, topic_name: str, diagram_type: str) -> Dict[str, Any]:
    """Generate visual_data fields for the chosen diagram type."""
    st = subtopic.lower()
    tn = topic_name.lower()

    if diagram_type == "tree":
        if "bst" in tn or "binary search tree" in tn or "bst" in st:
            return {"nodes": [50, 30, 70, 20, 40, 60, 80], "tree_type": "bst",
                    "caption": "BST: left < root < right"}
        if "traversal" in st or "inorder" in st or "in-order" in st:
            return {"nodes": [40, 20, 60, 10, 30, 50, 70], "tree_type": "bst",
                    "highlight": 10, "caption": "In-Order: visit Left → Root → Right"}
        if "preorder" in st or "pre-order" in st:
            return {"nodes": [40, 20, 60, 10, 30, 50, 70], "tree_type": "bst",
                    "highlight": 40, "caption": "Pre-Order: visit Root → Left → Right"}
        if "postorder" in st or "post-order" in st:
            return {"nodes": [40, 20, 60, 10, 30, 50, 70], "tree_type": "bst",
                    "highlight": 70, "caption": "Post-Order: visit Left → Right → Root"}
        if "heap" in tn or "heap" in st:
            return {"nodes": [90, 70, 80, 40, 60, 30, 50], "tree_type": "heap",
                    "caption": "Max-Heap: parent ≥ children"}
        if "search" in st:
            return {"nodes": [50, 30, 70, 20, 40, 60, 80], "tree_type": "bst",
                    "highlight": 40, "caption": "BST Search: compare and go left or right"}
        if "insert" in st:
            return {"nodes": [50, 30, 70, 20, 40, 60, 80], "tree_type": "bst",
                    "insert": 35, "caption": "BST Insert: find correct position"}
        if "avl" in tn or "avl" in st:
            return {"nodes": [30, 20, 40, 10, 25, 35, 50], "tree_type": "bst",
                    "caption": "AVL Tree: balanced BST with rotations"}
        return {"nodes": [50, 30, 70, 20, 40, 60, 80], "tree_type": "bst", "caption": subtopic}

    if diagram_type == "sorting":
        if "bubble" in st:
            return {"values": [64, 34, 25, 12, 22, 11, 90], "swaps": [[0,1],[1,2],[2,3]],
                    "highlight": [0,1], "caption": "Bubble Sort: compare and swap adjacent elements"}
        if "selection" in st:
            return {"values": [29, 10, 14, 37, 13, 8, 43], "highlight": [0],
                    "caption": "Selection Sort: find min, place at sorted boundary"}
        if "insertion" in st:
            return {"values": [4, 3, 7, 1, 5, 9, 2], "highlight": [2],
                    "caption": "Insertion Sort: insert into correct position"}
        if "merge" in st:
            return {"values": [38, 27, 43, 3, 9, 82, 10], "caption": "Merge Sort: divide and merge sorted halves"}
        if "quick" in st:
            return {"values": [10, 80, 30, 90, 40, 50, 70], "highlight": [6],
                    "caption": "Quick Sort: partition around pivot"}
        return {"values": [64, 34, 25, 12, 22, 11, 90], "caption": subtopic}

    if diagram_type == "stack":
        if "push" in st:
            return {"values": ["Base", "A", "B", "C (TOP)"], "caption": "Push: add element to top"}
        if "pop" in st:
            return {"values": ["Base", "A", "B → popped"], "caption": "Pop: remove from top"}
        return {"values": ["Base", "Middle", "Top"], "caption": subtopic}

    if diagram_type == "queue":
        return {"nodes": ["Front", "A", "B", "C", "Rear"], "caption": subtopic}

    if diagram_type == "linked_list":
        if "doubly" in st or "doubly" in tn:
            return {"values": ["head", "10", "20", "30", "null"], "doubly": True, "caption": "Doubly linked: prev and next pointers"}
        if "circular" in st:
            return {"values": ["10", "20", "30", "→head"], "caption": "Circular: last node points to head"}
        return {"values": ["head", "10", "20", "30", "null"], "caption": subtopic}

    if diagram_type == "hash_table":
        if "collision" in st:
            return {"size": 7, "pairs": [["key1", "v1"], ["key8", "v8"], ["key2", "v2"]],
                    "caption": "Hash collision: two keys map to same bucket"}
        return {"size": 7, "pairs": [["name", "Alice"], ["age", "25"], ["city", "NY"]],
                "caption": subtopic}

    if diagram_type == "array":
        if "bubble" in st:
            return {"values": [5, 3, 8, 4, 2], "highlight": 1, "caption": "Compare adjacent elements and swap if needed"}
        if "selection" in st:
            return {"values": [29, 10, 14, 37, 13], "highlight": 1, "caption": "Find the minimum and place it at the sorted boundary"}
        if "insertion" in st:
            return {"values": [4, 3, 7, 1, 5], "highlight": 2, "caption": "Build the sorted portion one element at a time"}
        if "binary" in st:
            return {"values": [2, 5, 8, 12, 16, 23, 38], "highlight": 3, "caption": "Compare with middle element, then narrow the range"}
        if "linear" in st:
            return {"values": [7, 3, 9, 2, 8, 12], "highlight": 2, "caption": "Check each element one by one"}
        return {"values": [4, 8, 15, 16, 23, 42], "highlight": 2, "caption": subtopic}

    if diagram_type == "flowchart":
        if "linked" in tn or "node" in st:
            return {"nodes": ["Head", "Node A", "Node B", "Tail"], "caption": subtopic}
        if "hash" in tn:
            return {"nodes": ["Key", "Hash Function", "Index", "Bucket"], "caption": subtopic}
        return {"nodes": ["Start", subtopic, "Process", "Result"], "caption": subtopic}

    if diagram_type == "process":
        if "stack" in tn:
            return {"steps": ["Push", "Top updates", "Pop", "Top updates"], "caption": subtopic}
        if "queue" in tn:
            return {"steps": ["Enqueue at Rear", "Rear updates", "Dequeue from Front", "Front updates"], "caption": subtopic}
        return {"steps": ["Input", subtopic, "Process", "Output"], "caption": subtopic}

    if diagram_type == "comparison":
        return {
            "left_title": "Before",
            "left_items": ["Unorganized data", "Slow operations"],
            "right_title": "After",
            "right_items": ["Structured data", "Fast operations"],
            "caption": subtopic,
        }

    if diagram_type == "timeline":
        return {"stops": ["Understand", "Implement", "Practice", "Apply"], "caption": subtopic}

    if diagram_type == "network":
        if "tree" in tn or "bst" in tn:
            return {"center_label": "Root", "nodes": ["Left child", "Right child", "Leaf A", "Leaf B"], "caption": subtopic}
        return {"center_label": topic_name, "nodes": ["A", "B", "C", "D"], "caption": subtopic}

    if diagram_type == "equation":
        if "time" in st:
            return {"equation": "T(n) = O(n)  for linear search", "caption": subtopic}
        if "space" in st:
            return {"equation": "S(n) = O(n)  for array of size n", "caption": subtopic}
        return {"equation": f"f(n) = O(\\text{{{subtopic}}})", "caption": subtopic}

    if diagram_type == "cycle":
        return {"steps": ["Step 1", "Step 2", "Step 3", "Step 4"], "caption": subtopic}

    return {"nodes": [subtopic, "Visual", "Result"], "caption": subtopic}


def _keywords_for(topic_name: str, subtopics: List[str]) -> str:
    """Generate SEO keywords from topic and subtopics."""
    words = [topic_name] + subtopics[:5]
    extras = ["data structures", "tutorial", "animation", "visual explanation", "JNTUK", "R23", "education", "Manim"]
    return ", ".join(dict.fromkeys([w.strip() for w in words + extras if w.strip()]))


# ---------------------------------------------------------------------------
# PROMPT BUILDERS
# ---------------------------------------------------------------------------

def _course_prompt(topic_name: str, subtopics: List[str], unit_title: str, notes: Optional[str] = None) -> str:
    """Build a strict prompt for the LLM to generate a course scene plan."""
    subtopics_text = "\n".join([f"- {s}" for s in subtopics])
    notes_line = f"\nAdditional notes: {notes}\n" if notes else ""
    return f"""You are an expert educational video planner for a Data Structures course (JNTUK R23). Create a detailed, professional video script and scene plan for the topic below.

Topic: {topic_name}
Unit context: {unit_title}
Mandatory subtopics (you MUST create one dedicated scene for EACH):
{subtopics_text}{notes_line}

Rules:
1. Create exactly one scene per mandatory subtopic listed above. No more, no less.
2. Each scene must have a clear, concise title and a short 2-3 sentence narration explaining that subtopic in a teaching voice.
3. The first scene should be a "title_card" with the main topic as the title and the unit as the subtitle.
4. Choose a Manim diagram_type for each scene from this FULL list:
   - "title_card" (only for the intro scene)
   - "tree" (for BST, binary trees, AVL trees, heaps, traversals — use this for ALL tree topics)
   - "linked_list" (for singly, doubly, circular linked lists — use this instead of flowchart)
   - "stack" (for stack push/pop operations — use this instead of process)
   - "queue" (for queue enqueue/dequeue — use this instead of process)
   - "sorting" (for bubble, selection, insertion, merge, quick sort — use this instead of array)
   - "hash_table" (for hash tables, collision, chaining — use this instead of flowchart)
   - "array" (for array operations, binary search, linear search)
   - "flowchart" (for algorithm flows)
   - "process" (for step-by-step procedures)
   - "comparison" (for before/after, pros/cons)
   - "equation" (for Big-O complexity formulas)
   - "network" (for graphs, adjacency lists)
   - "cycle" (for circular processes)
   - "timeline" (for historical/sequential steps)
5. For "tree" diagram_type, provide visual_data with: nodes (list of integers like [50,30,70,20,40,60,80]), tree_type ("bst" or "heap"), optionally highlight (integer to highlight), optionally insert (integer being inserted).
   For "sorting", provide visual_data with: values (list of integers), optionally swaps (list of [i,j] pairs), optionally highlight (list of indices).
   For "linked_list", provide visual_data with: values (list of node labels like ["head","10","20","null"]), optionally doubly (true/false).
   For "stack", provide visual_data with: values (list of stack element labels, bottom first).
   For "hash_table", provide visual_data with: size (integer), pairs (list of [key, value] pairs).
6. Provide a full voiceover script (moneyprinter_script) that is a continuous, engaging narration connecting all scenes. It should be 130-180 words for short topics, 200-300 words for topics with many subtopics. The script should sound natural when read by a TTS voice.
7. Provide exactly 8-12 comma-separated SEO keywords in the "keywords" field.
8. Return ONLY a valid JSON object. Do not include markdown code fences, explanations, or <think> tags.

Required JSON format:
{{
  "subject": "{topic_name}",
  "visual_style": "manim_course",
  "keywords": "keyword1, keyword2, ...",
  "moneyprinter_script": "Full voiceover narration here...",
  "scenes": [
    {{
      "name": "scene_01_title",
      "title": "Main Topic Title",
      "diagram_type": "title_card",
      "bullets": ["Welcome point 1", "Welcome point 2"],
      "visual_data": {{"main_title": "Main Topic", "subtitle": "Unit context"}},
      "narration": "Welcome to this lesson..."
    }},
    {{
      "name": "scene_02_subtopic",
      "title": "Subtopic Title",
      "diagram_type": "array",
      "bullets": ["Key point 1", "Key point 2", "Key point 3"],
      "visual_data": {{"values": [1,2,3], "highlight": 1, "caption": "Caption"}},
      "narration": "Now let's learn about..."
    }}
  ]
}}

Generate the JSON now."""


def _story_prompt(topic_name: str, notes: Optional[str] = None) -> str:
    """Build a strict prompt for the LLM to generate a story scene plan."""
    notes_line = f"\nAdditional notes: {notes}\n" if notes else ""
    return f"""You are an expert children's story writer and video planner. Create a warm, moral, age-appropriate story based on the topic below.

Topic: {topic_name}{notes_line}

Rules:
1. Create exactly 4-6 scenes: Beginning, Problem/Rising Action, Choice/Turning Point, Resolution, Happy Ending, Optional Moral Summary.
2. Each scene must have a title, a short 2-3 sentence narration, and a detailed vertical 9:16 image prompt for Stable Diffusion.
3. Image prompts must include: art style, characters, setting, emotion, lighting, color palette, and the rule: "no text, no letters, no numbers, no captions, no watermark, no UI elements".
4. Provide a full continuous voiceover script (moneyprinter_script) that tells the story aloud in 150-250 words. Use simple language suitable for ages 5-10.
5. Provide 8-12 comma-separated SEO keywords in the "keywords" field.
6. Return ONLY a valid JSON object. No markdown code fences, explanations, or <think> tags.

Required JSON format:
{{
  "render_mode": "story",
  "subject": "{topic_name}",
  "keywords": "story, kids, moral, animation, ...",
  "moneyprinter_script": "Once upon a time...",
  "scenes": [
    {{
      "name": "scene_01_beginning",
      "title": "The Magical Beginning",
      "prompt": "Vertical 9:16 children's storybook illustration... no text, no watermark",
      "narration": "Once upon a time..."
    }}
  ]
}}

Generate the JSON now."""


def _pexels_prompt(topic_name: str, notes: Optional[str] = None) -> str:
    """Build a prompt for generating an educational script suitable for Pexels stock clips."""
    notes_line = f"\nAdditional notes: {notes}\n" if notes else ""
    return f"""You are an expert educational video script writer. Create a short, engaging explainer script for the topic below.
The video will use stock footage from Pexels, so the script should describe visual concepts that are easy to match with stock video clips.

Topic: {topic_name}{notes_line}

Rules:
1. Write a continuous voiceover script (moneyprinter_script) of 100-180 words. Use simple, clear, teaching-style language.
2. Provide 8-12 comma-separated SEO keywords / search terms in the "keywords" field. These will be used to search Pexels for stock clips.
3. Return ONLY a valid JSON object. No markdown code fences, explanations, or <think> tags.

Required JSON format:
{{
  "subject": "{topic_name}",
  "render_mode": "pexels",
  "video_source": "pexels",
  "keywords": "keyword1, keyword2, ...",
  "moneyprinter_script": "Full voiceover narration here..."
}}

Generate the JSON now."""


def _youtube_prompt(video_title: str, transcript: str, notes: Optional[str] = None) -> str:
    """Build a prompt for rewriting a YouTube transcript into an educational script."""
    notes_line = f"\nAdditional notes: {notes}\n" if notes else ""
    return f"""You are an expert educational video creator. Rewrite the YouTube transcript below into a concise, engaging explainer script.
The final video will use stock footage from Pexels, so keep the language visual and descriptive.

Video title: {video_title}
Transcript:
{transcript}
{notes_line}

Rules:
1. Summarize the key points into a continuous voiceover script (moneyprinter_script) of 150-250 words.
2. Provide 8-12 comma-separated SEO keywords / search terms in the "keywords" field for Pexels stock footage.
3. Return ONLY a valid JSON object. No markdown code fences, explanations, or <think> tags.

Required JSON format:
{{
  "subject": "{video_title}",
  "render_mode": "pexels",
  "video_source": "pexels",
  "keywords": "keyword1, keyword2, ...",
  "moneyprinter_script": "Rewritten voiceover narration here..."
}}

Generate the JSON now."""


# ---------------------------------------------------------------------------
# PLAN POST-PROCESSING
# ---------------------------------------------------------------------------

def _clean_plan(plan: Dict[str, Any], topic_name: str, unit_title: str, subtopics: List[str]) -> Dict[str, Any]:
    """Normalize the LLM-generated plan so it always renders safely."""
    # Ensure top-level fields
    plan.setdefault("subject", topic_name)
    plan.setdefault("visual_style", "manim_course")
    if "render_mode" in plan and plan["render_mode"] == "story":
        plan.setdefault("visual_style", "comfyui_story")
    else:
        plan.setdefault("visual_style", "manim_course")

    # Normalize keywords
    kw = plan.get("keywords", "")
    if isinstance(kw, list):
        plan["keywords"] = ", ".join(kw)
    elif not isinstance(kw, str):
        plan["keywords"] = _keywords_for(topic_name, subtopics)
    else:
        plan["keywords"] = kw.strip() or _keywords_for(topic_name, subtopics)

    # Normalize script
    script = plan.get("moneyprinter_script", "")
    if isinstance(script, dict):
        script = script.get("full_voiceover") or "\n\n".join(script.get("paragraphs", []))
    plan["moneyprinter_script"] = str(script).strip()

    # Ensure scenes exist
    scenes = plan.get("scenes", [])
    if not isinstance(scenes, list):
        scenes = []

    # Clean each scene
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            scenes[i] = {}
            scene = scenes[i]
        scene.setdefault("name", f"scene_{i+1:02d}_{_slug(scene.get('title', 'scene'))}")
        scene.setdefault("title", f"Scene {i+1}")
        scene.setdefault("bullets", [])
        if not isinstance(scene.get("bullets"), list):
            scene["bullets"] = []
        if not scene["bullets"]:
            scene["bullets"] = [f"Key point: {scene['title']}"]
        vd = scene.get("visual_data")
        if not isinstance(vd, dict):
            scene["visual_data"] = _visual_data_for(scene.get("title", ""), topic_name, scene.get("diagram_type", "process"))
        else:
            # Ensure visual_data has at least the minimum required fields
            if scene.get("diagram_type") in ["array"] and "values" not in vd:
                vd.update({"values": [4, 8, 15, 16, 23, 42], "highlight": 2})
            if scene.get("diagram_type") in ["flowchart", "network"] and "nodes" not in vd:
                vd["nodes"] = ["A", "B", "C", "D"]
            if scene.get("diagram_type") in ["process", "timeline"] and "steps" not in vd and "stops" not in vd:
                vd["steps"] = ["Input", "Process", "Output"]
            if scene.get("diagram_type") in ["comparison"] and ("left_items" not in vd or "right_items" not in vd):
                vd.update({"left_title": "Before", "left_items": ["Old"], "right_title": "After", "right_items": ["New"]})
            if scene.get("diagram_type") in ["equation"] and "equation" not in vd:
                vd["equation"] = "A = B + C"
            if scene.get("diagram_type") in ["cycle"] and "steps" not in vd:
                vd["steps"] = ["Step 1", "Step 2", "Step 3", "Step 4"]
            # New diagram type validations
            if scene.get("diagram_type") in ["tree", "bst", "binary_tree"] and "nodes" not in vd:
                vd.update({"nodes": [50, 30, 70, 20, 40, 60, 80], "tree_type": "bst"})
            if scene.get("diagram_type") in ["sorting", "sort"] and "values" not in vd:
                vd.update({"values": [64, 34, 25, 12, 22, 11, 90]})
            if scene.get("diagram_type") in ["stack"] and "values" not in vd and "items" not in vd:
                vd.update({"values": ["Base", "Middle", "Top"]})
            if scene.get("diagram_type") in ["linked_list"] and "values" not in vd and "nodes" not in vd:
                vd.update({"values": ["head", "10", "20", "30", "null"]})
            if scene.get("diagram_type") in ["hash_table"] and "pairs" not in vd:
                vd.update({"size": 7, "pairs": [["key", "value"], ["name", "Alice"]]})
    plan["scenes"] = scenes
    
    # Skip parallel enrichment to drastically speed up local planning
    # plan = _enrich_plan_parallel(plan, topic_name)
    
    return plan


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "scene"


# ---------------------------------------------------------------------------
# SINGLE PLAN GENERATION
# ---------------------------------------------------------------------------

def _generate_course_plan(topic_name: str, subtopics: List[str], unit_title: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Generate a course plan using the LLM, with schema-safe post-processing and resilient offline fallback."""
    prompt = _course_prompt(topic_name, subtopics, unit_title, notes)
    plan = None
    try:
        raw = BrainManager.ask(prompt, TaskType.PLANNING)
        plan = _extract_json(raw)
    except Exception as e:
        print(f"[Planner] LLM generation failed ({e}). Using curriculum fallback template.")

    if plan is None:
        subs = subtopics if subtopics else ["Introduction and Overview", "Core Mechanics and Properties", "Implementation and Operations", "Real-World Applications and Complexity"]
        scenes = []
        script_parts = [f"Welcome to this lecture on {topic_name} in {unit_title}."]
        for i, sub in enumerate(subs[:4]):
            narration = f"Section {i+1}: {sub}. In computer science and algorithmic system design, mastering {sub} provides critical insights into data organization and computational efficiency."
            script_parts.append(narration)
            scenes.append({
                "name": f"scene_{i+1:02d}_{_slug(sub)}",
                "title": f"{sub}",
                "bullets": [
                    f"Core principles of {sub}",
                    f"Operational workflow in {topic_name}",
                    "Efficiency metrics and asymptotic performance"
                ],
                "narration": narration,
                "diagram_type": "array" if i == 1 else ("tree" if "tree" in topic_name.lower() else "process"),
                "visual_data": {"values": [12, 24, 36, 48, 60], "highlight": 1} if i == 1 else {"steps": ["Input Specification", "Processing Step", "Validation", "Output State"]}
            })
        script_parts.append(f"To summarize, {topic_name} forms a cornerstone concept. Practice these fundamentals to design robust and scalable software.")
        plan = {
            "subject": topic_name,
            "render_mode": "course",
            "visual_style": "manim_course",
            "keywords": f"{topic_name}, Data Structures, Computer Science, Algorithms, Engineering",
            "moneyprinter_script": " ".join(script_parts),
            "scenes": scenes
        }

    return _clean_plan(plan, topic_name, unit_title, subtopics)


def _generate_story_plan(topic_name: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Generate a story plan using the LLM with resilient offline fallback."""
    prompt = _story_prompt(topic_name, notes)
    plan = None
    try:
        raw = BrainManager.ask(prompt, TaskType.STORY)
        plan = _extract_json(raw)
    except Exception as e:
        print(f"[Planner] LLM story generation failed ({e}). Using resilient story fallback.")

    if plan is None:
        plan = {
            "subject": topic_name,
            "render_mode": "story",
            "visual_style": "comfyui_story",
            "keywords": "story, adventure, moral, animated narrative, wisdom",
            "moneyprinter_script": f"Once upon a time in a peaceful village, an inspiring journey began regarding {topic_name}. Together with trusted companions, challenges were faced with perseverance and courage. Through kindness and clever thinking, harmony was restored, teaching everyone the true value of friendship and resilience.",
            "scenes": [
                {
                    "name": "scene_01_beginning",
                    "title": f"The Journey of {topic_name}",
                    "prompt": f"Vertical 9:16 storybook illustration of a magical land with lush green hills and warm morning light, no text, no watermark",
                    "narration": f"Once upon a time in a peaceful village, an inspiring journey began regarding {topic_name}.",
                    "bullets": ["A peaceful beginning", "The calling to adventure"]
                },
                {
                    "name": "scene_02_challenge",
                    "title": "A Great Challenge",
                    "prompt": "Vertical 9:16 illustration of brave characters facing a mystical winding mountain pass at dusk, no text, no watermark",
                    "narration": "Together with trusted companions, challenges were faced with perseverance and courage.",
                    "bullets": ["Confronting the unknown", "Teamwork in action"]
                },
                {
                    "name": "scene_03_resolution",
                    "title": "Wisdom & Victory",
                    "prompt": "Vertical 9:16 vibrant illustration of a glowing celebration under starlight, joyful atmosphere, no text, no watermark",
                    "narration": "Through kindness and clever thinking, harmony was restored, teaching everyone the true value of friendship.",
                    "bullets": ["Harmony restored", "Valuable life lesson"]
                }
            ]
        }

    return _clean_plan(plan, topic_name, "Story Mode", [])


def _generate_pexels_plan(topic_name: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Generate a Pexels-style script plan using the LLM with resilient offline fallback."""
    prompt = _pexels_prompt(topic_name, notes)
    plan = None
    try:
        raw = BrainManager.ask(prompt, TaskType.PLANNING)
        plan = _extract_json(raw)
    except Exception as e:
        print(f"[Planner] LLM stock script generation failed ({e}). Using resilient explainer fallback.")

    if plan is None:
        plan = {
            "subject": topic_name,
            "render_mode": "pexels",
            "video_source": "pexels",
            "keywords": f"{topic_name}, technology, innovation, education, future",
            "moneyprinter_script": f"Have you ever wondered how {topic_name} shapes modern systems? Across global industries, the principles of {topic_name} drive breakthrough innovations. By streamlining complexity and optimizing throughput, it enables high-performance digital infrastructure. Understanding these core fundamentals is key to building future-proof technology.",
            "scenes": [
                {
                    "name": "scene_01_intro",
                    "title": f"The Evolution of {topic_name}",
                    "narration": f"Have you ever wondered how {topic_name} shapes modern systems?",
                    "bullets": ["Global impact", "Core concepts"]
                },
                {
                    "name": "scene_02_application",
                    "title": "Architectural Design",
                    "narration": f"Across global industries, the principles of {topic_name} drive breakthrough innovations.",
                    "bullets": ["High throughput", "Scalable systems"]
                },
                {
                    "name": "scene_03_future",
                    "title": "Looking Ahead",
                    "narration": "Understanding these core fundamentals is key to building future-proof technology.",
                    "bullets": ["Engineering excellence", "Future outlook"]
                }
            ]
        }

    return _clean_plan(plan, topic_name, "General Topic", [])


def _generate_youtube_plan(video_title: str, transcript: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Generate a Pexels-style script plan from a YouTube transcript."""
    prompt = _youtube_prompt(video_title, transcript, notes)
    plan = None
    try:
        raw = BrainManager.ask(prompt, TaskType.PLANNING)
        plan = _extract_json(raw)
    except Exception as e:
        print(f"[Planner] LLM YouTube rewrite failed ({e}). Using transcript excerpt.")

    if plan is None:
        clean_tr = re.sub(r"\s+", " ", transcript)[:300]
        plan = {
            "subject": video_title,
            "render_mode": "pexels",
            "video_source": "pexels",
            "keywords": f"{video_title}, summary, knowledge, tutorial",
            "moneyprinter_script": f"In this video summary of {video_title}, we uncover the essential insights: {clean_tr}... This provides a clear, high-yield overview of the topic.",
            "scenes": [
                {
                    "name": "scene_01_summary",
                    "title": video_title[:40],
                    "narration": f"In this video summary of {video_title}, we uncover the essential insights.",
                    "bullets": ["Key takeaways", "Curated recap"]
                }
            ]
        }

    return _clean_plan(plan, video_title, "YouTube Extraction", [])

def regenerate_plan(req: GenerateRequest) -> Dict[str, Any]:
    """Regenerate a plan using the previous plan and user feedback."""
    if not req.previous_plan:
        raise ValueError("previous_plan is required for regeneration.")
    if not req.feedback:
        raise ValueError("feedback is required for regeneration.")

    prompt = f"""You are an expert educational video planner. You previously generated a JSON video plan, but the user requested changes.
Please update the plan based on the user's feedback.

User Feedback:
{req.feedback}

Previous Plan JSON:
{json.dumps(req.previous_plan, indent=2)}

Rules:
1. Return ONLY the modified JSON object.
2. Keep the same structure (subject, scenes, moneyprinter_script, keywords, etc.).
3. Update the moneyprinter_script or scenes as requested.
4. Do not include markdown code fences, explanations, or <think> tags.
"""
    raw = BrainManager.ask(prompt, TaskType.PLANNING)
    plan = _extract_json(raw)
    if plan is None:
        raise RuntimeError("Failed to extract JSON from Ollama for regeneration.")
    
    # We do a basic clean up without overriding the user's specific modifications to visual_data if they were made.
    topic = plan.get("subject", req.topic or "Regenerated Video")
    return _clean_plan(plan, topic, "Regeneration", [])

# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------


def build_plan(req: GenerateRequest) -> Dict[str, Any]:
    """Build a single plan for the requested topic."""
    mode = Mode(req.mode) if isinstance(req.mode, str) else req.mode

    if mode == Mode.story:
        return _generate_story_plan(req.topic, req.notes)

    if mode == Mode.youtube_extract:
        if not req.youtube_url:
            raise ValueError("YouTube URL is required for YouTube extraction mode.")
        # Pipeline handles transcript extraction; this branch is for topic-only fallback.
        topic = req.topic or (req.youtube_url or "YouTube summary")
        return _generate_pexels_plan(topic, req.notes)

    if mode == Mode.autonomous:
        topic_name = req.topic if req.topic else "Interesting Tech Fact"
        return _generate_pexels_plan(topic_name, req.notes)

    # Manual course mode
    syllabus = _load_syllabus()
    topics = _flatten_topics(syllabus) if syllabus else []
    
    if not req.topic:
        raise ValueError("No topic provided for manual course mode. Leave topic empty only when using batch mode.")

    matched = _match_topic(req.topic, topics)
    if matched:
        return _generate_course_plan(matched["topic"], matched["subtopics"], matched["unit_title"], req.notes)

    # No syllabus match: ask the model to invent a plan based on its own knowledge
    return _generate_course_plan(req.topic, ["Introduction", "Core Concept", "Example", "Summary"], "General Topic", req.notes)


def build_youtube_plan(url: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Build a plan from a YouTube URL by extracting transcript and rewriting it."""
    from backend.services.youtube import summarize_video
    info = summarize_video(url)
    plan = _generate_youtube_plan(info["title"], info["transcript"], notes)
    plan["youtube_info"] = {
        "title": info["title"],
        "channel": info["channel"],
        "description": info["description"],
    }
    return plan


def build_batch_plans(req: GenerateRequest, progress_callback=None) -> List[Tuple[str, Dict[str, Any]]]:
    """Generate a plan for every topic in the syllabus. Returns list of (topic_name, plan)."""
    syllabus = _load_syllabus()
    if not syllabus:
        raise RuntimeError("Syllabus not found. Cannot run batch mode.")
    all_topics = _flatten_topics(syllabus)
    if not all_topics:
        raise RuntimeError("Syllabus has no topics. Cannot run batch mode.")

    topics = []
    query = (req.topic or "").strip().lower()
    
    if query.startswith("batch:"):
        query = query.replace("batch:", "").strip()
    elif query.startswith("unit:"):
        query = query.replace("unit:", "").strip()

    if not query or query in ("all", "everything", "full syllabus"):
        topics = all_topics
    else:
        # Try to match by Unit Title or Unit name (e.g. "Linked Lists" or "UNIT II")
        unit_topics = [t for t in all_topics if query in t["unit"].lower() or query in t["unit_title"].lower()]
        if unit_topics:
            topics = unit_topics
        else:
            # Fallback to broad topic matching across the syllabus
            topics = _match_all_topics(query, all_topics)
            
    if not topics:
        raise RuntimeError(f"No topics found matching '{req.topic}'. Cannot run batch mode.")

    results = []
    total = len(topics)
    for idx, topic in enumerate(topics, 1):
        if progress_callback:
            progress_callback(f"Batch Planning [{idx}/{total}]: {topic['topic']}")
        plan = _generate_course_plan(topic["topic"], topic["subtopics"], topic["unit_title"], req.notes)
        results.append((topic["topic"], plan))
        time.sleep(0.2)  # Small delay to avoid hammering Ollama
    return results


def next_topic_after(topic_name: str) -> Optional[str]:
    """Return the next syllabus topic after the given one, for continuation hooks."""
    syllabus = _load_syllabus()
    if not syllabus:
        return None
    topics = _flatten_topics(syllabus)
    names = [t["topic"] for t in topics]
    if topic_name in names:
        idx = names.index(topic_name)
        if idx + 1 < len(names):
            return names[idx + 1]
    return None
