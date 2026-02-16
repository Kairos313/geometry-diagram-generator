import os
import requests
import base64
import json
import time
import argparse
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
import sys

# Import prompts from local pipeline_prompts.py
from pipeline_prompts import Geometry_Blueprint_v2

def encode_image_to_base64(image_path: str) -> str:

    """Encode image to base64 string for API call."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def make_gemini_blueprint_call(
    api_key: str,
    image_path: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    Step 1: Make Gemini API call to generate geometric blueprint.
    This call now includes the solution steps JSON for better context.
    """
    
    # Encode the image
    base64_image = encode_image_to_base64(image_path)
    
    # Load solution steps JSON from Full_Pipeline
    solution_steps_path = "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline/math_solution_standard.json"
    try:
        with open(solution_steps_path, "r", encoding="utf-8") as f:
            solution_steps_json = json.load(f)
        print(f"✓ Loaded solution steps JSON from: {solution_steps_path}")
    except Exception as e:
        print(f"Error reading solution steps JSON: {e}")
        return {"success": False, "error": f"Failed to read solution steps JSON: {e}"}
    
    # Use Geometry_Blueprint prompt from pipeline_prompts.py
    prompt_text = Geometry_Blueprint_v2

    # Prepare the API request payload with solution steps included
    payload = {
        "model": "google/gemini-2.5-pro",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{prompt_text}\n\nSolution steps JSON:\n{json.dumps(solution_steps_json, indent=2)}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 20000,
        "temperature": 0.1
    }
    
    # API endpoint
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",
        "X-Title": "Geometry Blueprint Generator"
    }
    
    try:
        # Start timing the API call
        start_time = time.time()
        
        # Make the API call
        print("Step 1: Making Gemini API call to generate geometric blueprint...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # End timing
        end_time = time.time()
        api_call_duration = end_time - start_time
        
        # Parse the response
        response_data = response.json()
        
        # Extract token usage information
        usage = response_data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        # Extract the generated blueprint
        if response_data.get("choices") and len(response_data["choices"]) > 0:
            blueprint_text = response_data["choices"][0]["message"]["content"]
            
            # Save the blueprint to coordinates.txt
            coordinates_file = os.path.join(output_dir, "coordinates.txt")
            with open(coordinates_file, "w", encoding="utf-8") as f:
                f.write("=== GEOMETRIC BLUEPRINT - COORDINATES ===\n\n")
                f.write(blueprint_text)
            
            print(f"✓ Geometric blueprint saved to: {coordinates_file}")
            
            return {
                "success": True,
                "blueprint": blueprint_text,
                "coordinates_file": coordinates_file,
                "api_call_duration": api_call_duration,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        else:
            error_msg = "No choices in Gemini API response"
            print(f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Gemini API request failed: {str(e)}"
        print(f"Error: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error in Gemini call: {str(e)}"
        print(f"Error: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

def prepare_image_for_api(image_path: str) -> Dict:
    """Prepare image as data URI for API call."""
    ext = Path(image_path).suffix.lower()
    media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
    with open(image_path, "rb") as img_file:
        image_bytes = img_file.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{media_type};base64,{image_b64}"
    return {
        "type": "image_url",
        "image_url": {
            "url": data_uri
        }
    }

def make_manim_code_call(
    api_key: str,
    image_path: str,
    coordinates_file: str,
    output_dir: str
) -> Dict[str, Any]:
    """
    Step 2: Make Claude API call to generate Manim code using the blueprint.
    This call uses the FRESH blueprint from Step 1, not any previous iteration.
    """
    
    try:
        # Import prompts from local pipeline_prompts.py
        from pipeline_prompts import Enhanced_Manim_Geometric_Surveyor_v2
    except ImportError as e:
        print(f"Error importing prompts: {e}")
        return {"success": False, "error": f"Failed to import prompts: {e}"}
    
    # Load coordinate.txt content (FRESH from Step 1)
    try:
        with open(coordinates_file, "r", encoding="utf-8") as f:
            coordinate_txt_content = f.read()
    except Exception as e:
        print(f"Error reading coordinates file: {e}")
        return {"success": False, "error": f"Failed to read coordinates file: {e}"}
    
    # Load solution steps JSON from Full_Pipeline
    solution_steps_path = "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline/math_solution_standard.json"
    try:
        with open(solution_steps_path, "r", encoding="utf-8") as f:
            solution_steps_json = json.load(f)
    except Exception as e:
        print(f"Error reading solution steps JSON: {e}")
        return {"success": False, "error": f"Failed to read solution steps JSON: {e}"}
    
    # Compose the message content (same structure as original geometric_figure.py)
    message_content = [
        {
            "type": "text",
            "text": f"{Enhanced_Manim_Geometric_Surveyor_v2}\n\nSolution steps JSON:\n{json.dumps(solution_steps_json, indent=2)}"
        },
        {
            "type": "text",
            "text": f"Coordinate analysis notes:\n{coordinate_txt_content}"
        },
        prepare_image_for_api(image_path)
    ]
    
    # Initialize OpenAI client for OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    try:
        # Start timing the API call
        start_time = time.time()
        
        # Make the API call
        print("Step 2: Making Claude API call to generate Manim code...")
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://yoursite.com",
                "X-Title": "Manim Code Generator",
            },
            model="anthropic/claude-sonnet-4",
            messages=[
                {
                    "role": "user",
                    "content": message_content
                }
            ],
            max_tokens=8000,
            temperature=0.2
        )
        
        # End timing
        end_time = time.time()
        api_call_duration = end_time - start_time
        
        # Extract the generated Manim code
        manim_code = completion.choices[0].message.content
        
        # Extract only Python code from the response (remove markdown and analysis text)
        import re
        
        # Look for Python code blocks
        python_code_pattern = r'```python\s*(.*?)\s*```'
        python_matches = re.findall(python_code_pattern, manim_code, re.DOTALL)
        
        if python_matches:
            # Use the first Python code block found
            extracted_code = python_matches[0].strip()
            print(f"✓ Extracted Python code block ({len(extracted_code)} characters)")
        else:
            # If no code blocks found, try to extract code after "```python"
            if "```python" in manim_code:
                start_idx = manim_code.find("```python") + 9
                end_idx = manim_code.find("```", start_idx)
                if end_idx != -1:
                    extracted_code = manim_code[start_idx:end_idx].strip()
                    print(f"✓ Extracted Python code after ```python ({len(extracted_code)} characters)")
                else:
                    extracted_code = manim_code
                    print("⚠️ No closing ``` found, using full response")
            else:
                # Fallback: use the entire response
                extracted_code = manim_code
                print("⚠️ No Python code blocks found, using full response")
        
        # Save output to .py file
        output_path = os.path.join(output_dir, "figure.py")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(extracted_code)
        
        print(f"✓ Manim code saved to: {output_path}")
        
        # Extract token usage information
        usage = getattr(completion, 'usage', None)
        prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
        completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
        total_tokens = getattr(usage, 'total_tokens', 0) if usage else 0
        
        return {
            "success": True,
            "manim_code": manim_code,
            "output_file": output_path,
            "api_call_duration": api_call_duration,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
        
    except Exception as e:
        error_msg = f"Claude API call failed: {str(e)}"
        print(f"Error: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

def main():
    """Main function to execute the integrated pipeline."""
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description="Generate geometric blueprint and Manim code from question image")
    parser.add_argument("--question-image", help="Path to the question image file (required)")
    
    args = parser.parse_args()
    
    # Get question image path from command line or prompt user
    image_path = args.question_image
    if not image_path:
        print("❌ Question image path is required!")
        image_path = input("Please enter the path to your question image: ").strip()
        if not image_path:
            print("❌ No question image path provided. Exiting.")
            sys.exit(1)
    
    # Load environment variables from .env file in current directory
    load_dotenv('.env')
    
    # Configuration
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        print("Checked .env file in current directory")
        sys.exit(1)
    
    # Output directory
    output_dir = "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline"
    
    # Verify image file exists
    if not os.path.exists(image_path):
        print(f"❌ Question image file not found: {image_path}")
        sys.exit(1)
    
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    
    print("=== INTEGRATED GEOMETRY PIPELINE ===\n")
    print(f"📁 Question image: {image_path}")
    print("🔄 Starting FRESH pipeline run with solution steps context\n")
    
    # Step 1: Generate geometric blueprint with Gemini
    print("🔄 Step 1: Generating geometric blueprint...")
    gemini_result = make_gemini_blueprint_call(
        api_key=OPENROUTER_API_KEY,
        image_path=image_path,
        output_dir=output_dir
    )
    
    if not gemini_result["success"]:
        print(f"❌ Step 1 failed: {gemini_result['error']}")
        return
    
    print(f"✅ Step 1 completed successfully!")
    print(f"   - Duration: {gemini_result['api_call_duration']:.2f} seconds")
    print(f"   - Tokens: {gemini_result['total_tokens']} (input: {gemini_result['prompt_tokens']}, output: {gemini_result['completion_tokens']})")
    print(f"   - Blueprint saved to: {gemini_result['coordinates_file']}\n")
    
    # Step 2: Generate Manim code with Claude
    print("🔄 Step 2: Generating Manim code...")
    claude_result = make_manim_code_call(
        api_key=OPENROUTER_API_KEY,
        image_path=image_path,
        coordinates_file=gemini_result['coordinates_file'],
        output_dir=output_dir
    )
    
    if not claude_result["success"]:
        print(f"❌ Step 2 failed: {claude_result['error']}")
        return
    
    print(f"✅ Step 2 completed successfully!")
    print(f"   - Duration: {claude_result['api_call_duration']:.2f} seconds")
    print(f"   - Tokens: {claude_result['total_tokens']} (input: {claude_result['prompt_tokens']}, output: {claude_result['completion_tokens']})")
    print(f"   - Manim code saved to: {claude_result['output_file']}\n")
    
    # Summary
    total_duration = gemini_result['api_call_duration'] + claude_result['api_call_duration']
    total_tokens = gemini_result['total_tokens'] + claude_result['total_tokens']
    
    print("=== PIPELINE COMPLETED SUCCESSFULLY ===")
    print(f"📊 Total Pipeline Metrics:")
    print(f"   - Total Duration: {total_duration:.2f} seconds")
    print(f"   - Total Tokens: {total_tokens}")
    print(f"   - Gemini Tokens: {gemini_result['total_tokens']}")
    print(f"   - Claude Tokens: {claude_result['total_tokens']}")
    print(f"\n📁 Generated Files:")
    print(f"   - Geometric Blueprint: {gemini_result['coordinates_file']}")
    print(f"   - Manim Code: {claude_result['output_file']}")
    print(f"\n🎯 Next Steps:")
    print(f"   - Review the geometric blueprint in coordinates.txt")
    print(f"   - Run the Manim code: manim -pql figure.py")
    print(f"   - Each run is independent - no feedback loop!")

if __name__ == "__main__":
    main() 