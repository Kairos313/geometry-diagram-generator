import json
import asyncio
import aiohttp
import os
from pydub import AudioSegment
from pydub.utils import mediainfo # Can be useful for debugging if needed
from dotenv import load_dotenv
from pathlib import Path
import time
from typing import List, Tuple, Optional, Dict, Any

# --- Configuration ---
# Load environment variables from .env file.
# Adjust the path based on where your .env file is relative to this script.
# If this script is in 'Geometry_v2/', and .env is also in 'Geometry_v2/', use Path(__file__).resolve().parent
# If .env is one level up from 'Geometry_v2/', use Path(__file__).resolve().parent.parent
try:
    dotenv_path = Path(".env") # Load .env from current directory
except NameError:
    # Fallback if __file__ is not available
    dotenv_path = Path(".env")

print(f"Loading .env from: {dotenv_path}")
print(f"File exists: {dotenv_path.exists()}")
load_dotenv(dotenv_path)
print(f"After loading, ELEVENLABS_API_KEY: {os.environ.get('ELEVENLABS_API_KEY', 'NOT FOUND')[:10] + '...' if os.environ.get('ELEVENLABS_API_KEY') else 'NOT FOUND'}")

ELEVEN_LABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if ELEVEN_LABS_API_KEY:
    print(f"Loaded ELEVENLABS_API_KEY: {ELEVEN_LABS_API_KEY[:4]}...{'*' * (len(ELEVEN_LABS_API_KEY)-8)}...{ELEVEN_LABS_API_KEY[-4:]}")
else:
    print("ELEVENLABS_API_KEY not found! Please set it in your .env file.")
    exit(1) # Exit if API key is not found

VOICE_ID = "Fahco4VZzobUeiPqni1S" # Example Voice ID. Replace with your preferred voice ID.
MODEL_ID = "eleven_multilingual_v2" 

# Define paths using Pathlib for better cross-OS compatibility
BASE_DIR = Path("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline")

INPUT_JSON_FILE = BASE_DIR / "math_solution_pipeline/math_solution_verbose.json"  # Input file path
OUTPUT_JSON_FILE = BASE_DIR / "deconstruct_parallel_symbols.json"  # Updated output JSON file path
GEOMETRIC_TIMING_OUTPUT_FILE = BASE_DIR / "geometric_elements_with_timing.json"  # Geometric timing output
INDIVIDUAL_AUDIO_DIR = BASE_DIR / "Audio"  # Updated individual audio directory
SCENE_AUDIO_DIR = BASE_DIR / "Scene"  # Updated scene audio directory

TIME_GAP_BETWEEN_SENTENCES = 0.01 # The small gap in seconds between sentences

# Maximum concurrent requests to prevent overwhelming the API
MAX_CONCURRENT_REQUESTS = 5

# --- Helper Classes for Managing Audio Generation Tasks ---

class AudioTask:
    """Represents a single audio generation task"""
    def __init__(self, sentence_text: str, step_id: str, sentence_index: int, output_filepath: Path):
        self.sentence_text = sentence_text
        self.step_id = step_id
        self.sentence_index = sentence_index
        self.output_filepath = output_filepath
        self.duration_seconds = 0.0
        self.audio_segment = None
        self.success = False

# --- Async Helper Function for Eleven Labs API ---

async def generate_audio_async(session: aiohttp.ClientSession, task: AudioTask) -> AudioTask:
    """
    Asynchronously calls the Eleven Labs API to generate audio for a sentence.
    
    Args:
        session: The aiohttp ClientSession for making requests
        task: AudioTask object containing the details for audio generation
        
    Returns:
        The same AudioTask object with results populated
    """
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVEN_LABS_API_KEY
    }

    data = {
        "text": task.sentence_text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        api_start_time = time.time()
        async with session.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}", 
            headers=headers, 
            json=data
        ) as response:
            api_end_time = time.time()
            print(f"API call for '{task.step_id}_{task.sentence_index}' took {api_end_time - api_start_time:.2f} seconds")
            
            if response.status == 200:
                # Save the audio file
                audio_content = await response.read()
                with open(task.output_filepath, 'wb') as f:
                    f.write(audio_content)

                # Measure audio duration and get AudioSegment object
                task.audio_segment = AudioSegment.from_file(str(task.output_filepath), format="mp3")
                task.duration_seconds = round(len(task.audio_segment) / 1000.0, 2)
                task.success = True

                print(f"Generated '{task.output_filepath.name}' (Duration: {task.duration_seconds:.2f}s) for: '{task.sentence_text[:50]}...'")
            else:
                print(f"API Error {response.status} for '{task.sentence_text[:50]}...': {await response.text()}")
                task.success = False

    except Exception as e:
        print(f"Error processing '{task.sentence_text[:50]}...': {e}")
        task.success = False

    return task

async def generate_all_audio_async(tasks: List[AudioTask]) -> List[AudioTask]:
    """
    Generate audio for all tasks concurrently with a semaphore to limit concurrent requests.
    
    Args:
        tasks: List of AudioTask objects to process
        
    Returns:
        List of completed AudioTask objects
    """
    # Create a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def bounded_generate_audio(session: aiohttp.ClientSession, task: AudioTask) -> AudioTask:
        async with semaphore:
            return await generate_audio_async(session, task)
    
    # Create aiohttp session with appropriate timeout
    timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout per request
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Execute all tasks concurrently
        completed_tasks = await asyncio.gather(
            *[bounded_generate_audio(session, task) for task in tasks],
            return_exceptions=True
        )
        
        # Handle any exceptions that occurred
        results = []
        for i, result in enumerate(completed_tasks):
            if isinstance(result, Exception):
                print(f"Task {i} failed with exception: {result}")
                tasks[i].success = False
                results.append(tasks[i])
            else:
                results.append(result)
        
        return results

# --- Main Processing Logic ---

def process_solution_steps_with_audio(json_data: dict) -> dict:
    """
    Processes the solution steps, generating audio for each sentence in parallel,
    calculating durations, and assigning timestamps relative to the scene's start,
    and stitching scene audio.

    Args:
        json_data: The parsed JSON data from the input file.

    Returns:
        A new dictionary with updated step and sentence information.
    """
    processed_data = json_data.copy()

    # Ensure output directories exist
    INDIVIDUAL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    SCENE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all audio generation tasks
    all_tasks = []
    task_mapping = {}  # Maps (step_id, sentence_index) to task
    
    for step in processed_data.get("solution_steps", []):
        step_id = step["step_id"]
        
        if "sentences" in step and isinstance(step["sentences"], list):
            for i, sentence_entry in enumerate(step["sentences"]):
                # Extract the sentence text
                if isinstance(sentence_entry, dict) and "text" in sentence_entry:
                    sentence_text = sentence_entry["text"]
                elif isinstance(sentence_entry, str):
                    sentence_text = sentence_entry
                else:
                    print(f"Warning: Unexpected sentence format in step '{step_id}', index {i}. Skipping.")
                    continue

                # Create audio task
                output_filepath = INDIVIDUAL_AUDIO_DIR / f"{step_id}_{i}.mp3"
                task = AudioTask(sentence_text, step_id, i, output_filepath)
                all_tasks.append(task)
                task_mapping[(step_id, i)] = task

    # Generate all audio files concurrently
    print(f"Starting parallel generation of {len(all_tasks)} audio files...")
    generation_start_time = time.time()
    
    # Run the async audio generation
    completed_tasks = asyncio.run(generate_all_audio_async(all_tasks))
    
    generation_end_time = time.time()
    print(f"Parallel audio generation completed in {generation_end_time - generation_start_time:.2f} seconds")

    # Process results and build the final data structure
    for step in processed_data.get("solution_steps", []):
        step_id = step["step_id"]
        
        individual_sentence_segments_for_scene = []
        timestamped_sentences_in_step = []
        
        # Initialize time tracker for the current scene
        current_time_within_scene = 0.0

        if "sentences" in step and isinstance(step["sentences"], list):
            for i, sentence_entry in enumerate(step["sentences"]):
                # Extract the sentence text
                if isinstance(sentence_entry, dict) and "text" in sentence_entry:
                    sentence_text = sentence_entry["text"]
                elif isinstance(sentence_entry, str):
                    sentence_text = sentence_entry
                else:
                    continue

                # Get the completed task
                task = task_mapping.get((step_id, i))
                if not task:
                    continue

                # Calculate start time relative to the beginning of the current scene
                sentence_start_time_relative = current_time_within_scene
                if i > 0:
                    sentence_start_time_relative += TIME_GAP_BETWEEN_SENTENCES

                audio_filename = None
                duration = 0.0

                if task.success and task.audio_segment:
                    audio_filename = str(task.output_filepath)
                    duration = task.duration_seconds
                    individual_sentence_segments_for_scene.append(task.audio_segment)
                else:
                    print(f"Warning: Audio generation failed for sentence '{sentence_text[:50]}...', using simulated duration.")
                    duration = max(0.75, len(sentence_text) * 0.15)  # Fallback heuristic

                sentence_end_time_relative = sentence_start_time_relative + duration

                timestamped_sentences_in_step.append({
                    "text": sentence_text,
                    "audio_file_individual": audio_filename,
                    "duration_seconds": round(duration, 2),
                    "start_time_seconds": round(sentence_start_time_relative, 2),
                    "end_time_seconds": round(sentence_end_time_relative, 2)
                })

                # Update current time for the next sentence WITHIN THIS SCENE
                current_time_within_scene = sentence_end_time_relative
            
            step["sentences"] = timestamped_sentences_in_step

        # --- Stitching Logic for the current Scene (Step) ---
        scene_combined_audio = AudioSegment.empty()
        scene_audio_filepath = None

        if individual_sentence_segments_for_scene:
            for i, segment in enumerate(individual_sentence_segments_for_scene):
                scene_combined_audio += segment
                # Add silence between sentences, but not after the very last one in the scene
                if i < len(individual_sentence_segments_for_scene) - 1:
                    silence = AudioSegment.silent(duration=TIME_GAP_BETWEEN_SENTENCES * 1000)
                    scene_combined_audio += silence
            
            scene_audio_filepath = SCENE_AUDIO_DIR / f"{step_id}_scene.mp3"
            try:
                scene_combined_audio.export(str(scene_audio_filepath), format="mp3")
                print(f"Stitched scene audio for '{step_id}' to '{scene_audio_filepath}'")
                step["audio_file_scene"] = str(scene_audio_filepath)
                step["duration_scene_seconds"] = round(len(scene_combined_audio) / 1000.0, 2)
                
                # Sanity check: Last sentence's end_time should match scene duration
                if timestamped_sentences_in_step and abs(timestamped_sentences_in_step[-1]["end_time_seconds"] - step["duration_scene_seconds"]) > 0.01:
                    print(f"Warning: For scene '{step_id}', last sentence end time ({timestamped_sentences_in_step[-1]['end_time_seconds']:.2f}s) "
                          f"does not exactly match stitched scene duration ({step['duration_scene_seconds']:.2f}s). This can be due to rounding or silence handling differences.")

            except Exception as e:
                print(f"Error stitching audio for scene '{step_id}': {e}")
                step["audio_file_scene"] = "ERROR: Stitching failed"
                step["duration_scene_seconds"] = 0.0
        else:
            print(f"No individual audio segments to stitch for scene '{step_id}'.")
            step["audio_file_scene"] = "N/A (No audio generated for scene)"
            step["duration_scene_seconds"] = 0.0

    return processed_data





# --- Main execution ---
if __name__ == "__main__":
    total_start_time = time.time()
    if not ELEVEN_LABS_API_KEY:
        print("Please set the ELEVENLABS_API_KEY environment variable. Exiting.")
        exit(1)

    if not INPUT_JSON_FILE.exists():
        print(f"Error: The input file '{INPUT_JSON_FILE}' was not found. Please ensure it exists.")
        exit(1)

    try:
        with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{INPUT_JSON_FILE}'. Please check file format for errors.")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        exit(1)

    # Process the data and generate audio
    processed_data_with_audio = process_solution_steps_with_audio(data)

    # Save the output to a new JSON file
    try:
        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed_data_with_audio, f, indent=2)
        print(f"\n✅ Audio processing complete. Output JSON saved to '{OUTPUT_JSON_FILE}'.")
        print(f"Individual sentence audio files are in '{INDIVIDUAL_AUDIO_DIR}'.")
        print(f"Stitched scene audio files are in '{SCENE_AUDIO_DIR}'.")
    except Exception as e:
        print(f"Error saving output to file: {e}")
    
    # --- Geometric Timing Processing ---
    print(f"\n🎬 Starting geometric timing processing...")
    geometric_timing_start_time = time.time()
    
    # Import and run the add_geometric_elements script
    try:
        import add_geometric_elements
        geometric_result = add_geometric_elements.add_geometric_elements_to_timing()
        
        geometric_timing_end_time = time.time()
        
        if geometric_result:
            print(f"✅ Geometric timing processing completed in {geometric_timing_end_time - geometric_timing_start_time:.2f} seconds")
            print(f"📁 Geometric timing output saved to: '{GEOMETRIC_TIMING_OUTPUT_FILE}'")
        else:
            print(f"❌ Geometric timing processing failed")
    except Exception as e:
        print(f"❌ Error running geometric timing processing: {e}")
        geometric_result = False
    
    total_end_time = time.time()
    print(f"\n🎉 Total script execution time: {total_end_time - total_start_time:.2f} seconds")
    print(f"📊 Generated files:")
    print(f"   • Audio timing: {OUTPUT_JSON_FILE}")
    print(f"   • Geometric timing: {GEOMETRIC_TIMING_OUTPUT_FILE}")
    print(f"   • Individual audio: {INDIVIDUAL_AUDIO_DIR}")
    print(f"   • Scene audio: {SCENE_AUDIO_DIR}")