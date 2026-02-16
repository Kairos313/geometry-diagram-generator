#!/usr/bin/env python3
"""
Solution Steps Generator
Makes an API call to Gemini-2.5-pro using the Solution_Steps prompt from geometry_prompts.py
Stores the entire JSON output in a single file called math_solution_.json
"""

import os
import json
import logging
import time
import base64
import re
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests
from pdf2image import convert_from_path
import tempfile

# Import the Solution_Steps prompt
import sys
sys.path.append('/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline')
from pipeline_prompts import Solution_Steps_v3

# Load environment variables from current directory
load_dotenv('.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SolutionStepsGenerator:
    """Generate solution steps using Gemini-2.5-pro API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        
        logger.info("Initialized Solution Steps Generator with Gemini-2.5-pro")
    
    def convert_pdf_to_images(self, pdf_path: str, dpi: int = 300):
        """
        Convert PDF pages to PIL images.
        
        Args:
            pdf_path (str): Path to the PDF file
            dpi (int): Resolution for image conversion
            
        Returns:
            list: List of PIL Image objects
        """
        try:
            logger.info(f"Converting PDF to images: {pdf_path}")
            images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"✓ Converted {len(images)} pages to images")
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise
    
    def save_image_to_temp(self, image, page_num: int = 0):
        """
        Save a PIL image to a temporary file.
        
        Args:
            image: PIL Image object
            page_num (int): Page number for naming
            
        Returns:
            str: Path to temporary image file
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=f'_page_{page_num}.png', delete=False) as tmp_file:
                image.save(tmp_file.name, 'PNG')
                logger.info(f"✓ Saved page {page_num} to temporary file: {tmp_file.name}")
                return tmp_file.name
        except Exception as e:
            logger.error(f"Error saving image to temp file: {e}")
            raise
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64 string for API call."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def make_gemini_api_call(self, image_paths: list):
        """
        Make API call to Gemini-2.5-pro to generate solution steps.
        
        Args:
            image_paths (list): List of paths to image files
            
        Returns:
            dict: API response with content and metadata
        """
        try:
            # Encode all images
            image_contents = []
            for i, image_path in enumerate(image_paths):
                base64_image = self.encode_image_to_base64(image_path)
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
                logger.info(f"✓ Encoded image {i+1}/{len(image_paths)}")
            
            # Use the full Solution_Steps_v3 prompt
            prompt_text = Solution_Steps_v3
            
            # Prepare the API request payload
            payload = {
                "model": "google/gemini-2.5-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text
                            }
                        ] + image_contents
                    }
                ],
                "max_tokens": 20000,
                "temperature": 0.1
            }
            
            # API endpoint
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            # Headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Solution Steps Generator"
            }
            
            # Start timing the API call
            start_time = time.time()
            
            # Make the API call
            logger.info(f"Making Gemini API call with {len(image_paths)} images...")
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
            
            # Extract the generated content
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                content = response_data["choices"][0]["message"]["content"]
                
                # Use the specific absolute path for debug files
                output_dir = "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline"
                os.makedirs(output_dir, exist_ok=True)
                

                
                logger.info(f"✓ API call completed successfully!")
                logger.info(f"   - Duration: {api_call_duration:.2f} seconds")
                logger.info(f"   - Tokens: {total_tokens} (input: {prompt_tokens}, output: {completion_tokens})")
                logger.info(f"   - Response length: {len(content)} characters")
                
                return {
                    "success": True,
                    "content": content,
                    "api_call_duration": api_call_duration,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            else:
                error_msg = "No choices in Gemini API response"
                logger.error(f"Error: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Gemini API request failed: {str(e)}"
            logger.error(f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error in Gemini call: {str(e)}"
            logger.error(f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def extract_question_number(self, question_image_path: str):
        """
        Extract question number from question image filename.
        
        Args:
            question_image_path (str): Path to question image file
            
        Returns:
            str: Question number or "unknown" if not found
        """
        try:
            if not question_image_path:
                return "unknown"
            
            filename = os.path.basename(question_image_path)
            # Extract number from "question_X.png" format
            match = re.search(r'question_(\d+)', filename)
            if match:
                return match.group(1)
            else:
                return "unknown"
                
        except Exception as e:
            logger.error(f"Error extracting question number: {e}")
            return "unknown"
    
    def extract_both_json_from_response(self, content: str):
        """
        Extract both JSON outputs from the API response content.
        
        Args:
            content (str): Raw API response content
            
        Returns:
            tuple: (standard_json, verbose_json) or (None, None) if not found
        """
        try:
            # Strategy 1: Handle new format with single JSON containing visual_output and tts_output
            logger.info("Checking for new format with visual_output and tts_output...")
            code_blocks = re.findall(r'```json\s*(.*?)```', content, re.DOTALL)
            
            if len(code_blocks) == 1:
                logger.info("✓ Found single JSON block with visual_output and tts_output")
                try:
                    json_content = code_blocks[0].strip()
                    cleaned_json = self._clean_json_content(json_content)
                    main_json_obj = json.loads(cleaned_json)
                    
                    # Check for the new format with visual_output and tts_output
                    if "visual_output" in main_json_obj and "tts_output" in main_json_obj:
                        logger.info("✓ Found visual_output and tts_output structure")
                        standard_json = main_json_obj["visual_output"]
                        verbose_json = main_json_obj["tts_output"]
                        return standard_json, verbose_json
                    
                    # Fallback to old nested JSON objects logic
                    standard_json, verbose_json = self._extract_nested_json_objects(main_json_obj)
                    
                    if standard_json and verbose_json:
                        logger.info("✓ Successfully extracted nested JSON objects")
                        return standard_json, verbose_json
                    else:
                        logger.warning("Could not find nested JSON objects, falling back to single object processing")
                        # Fallback to creating standard and verbose from single object
                        standard_json = self._create_standard_json(main_json_obj)
                        verbose_json = self._create_verbose_json(main_json_obj)
                        return standard_json, verbose_json
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON block: {e}")
                    # Try with raw content as fallback
                    try:
                        raw_json = code_blocks[0].strip().replace('\\', '\\\\')
                        main_json_obj = json.loads(raw_json)
                        
                        # Check for the new format with visual_output and tts_output
                        if "visual_output" in main_json_obj and "tts_output" in main_json_obj:
                            logger.info("✓ Found visual_output and tts_output structure (raw fallback)")
                            standard_json = main_json_obj["visual_output"]
                            verbose_json = main_json_obj["tts_output"]
                            return standard_json, verbose_json
                        
                        standard_json, verbose_json = self._extract_nested_json_objects(main_json_obj)
                        
                        if standard_json and verbose_json:
                            logger.info("✓ Successfully extracted nested JSON objects (raw fallback)")
                            return standard_json, verbose_json
                        else:
                            logger.warning("Could not find nested JSON objects in raw fallback")
                            
                    except json.JSONDecodeError as e2:
                        logger.error(f"Failed to parse JSON block even with fallback: {e2}")
            
            # Strategy 2: Split by markdown headers to isolate each JSON block (for v2 format)
            sections = re.split(r'### \*\*OUTPUT \d+:', content)
            
            if len(sections) >= 3:  # We expect at least 3 sections (empty, OUTPUT 1, OUTPUT 2)
                logger.info(f"✓ Found {len(sections)-1} output sections (v2 format)")
                
                json_objects = []
                
                # Process each section (skip the first empty section)
                for i, section in enumerate(sections[1:], 1):
                    logger.info(f"Processing OUTPUT {i} section...")
                    
                    # Find JSON code block in this section
                    json_match = re.search(r'```json\s*(.*?)```', section, re.DOTALL)
                    
                    if json_match:
                        json_content = json_match.group(1).strip()
                        
                        # Apply comprehensive JSON cleaning
                        cleaned_json = self._clean_json_content(json_content)
                        
                        try:
                            json_obj = json.loads(cleaned_json)
                            json_objects.append(json_obj)
                            logger.info(f"✓ Successfully parsed JSON from OUTPUT {i}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON from OUTPUT {i}: {e}")
                            # Try with raw content as fallback
                            try:
                                raw_json = json_content.replace('\\', '\\\\')
                                json_obj = json.loads(raw_json)
                                json_objects.append(json_obj)
                                logger.info(f"✓ Successfully parsed JSON from OUTPUT {i} (raw fallback)")
                            except json.JSONDecodeError as e2:
                                logger.error(f"Failed to parse JSON from OUTPUT {i} even with fallback: {e2}")
                                continue
                
                if len(json_objects) >= 2:
                    logger.info(f"✓ Successfully extracted {len(json_objects)} JSON objects using section-based approach")
                    return json_objects[0], json_objects[1]
            
            # Strategy 3: Multiple code blocks (fallback for v2 format)
            if len(code_blocks) >= 2:
                logger.info(f"Found {len(code_blocks)} code blocks, processing as v2 format...")
                json_objects = []
                for i, block in enumerate(code_blocks):
                    try:
                        cleaned_json = self._clean_json_content(block.strip())
                        json_obj = json.loads(cleaned_json)
                        json_objects.append(json_obj)
                        logger.info(f"✓ Successfully parsed JSON block {i+1}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON block {i+1}: {e}")
                        continue
                
                if len(json_objects) >= 2:
                    logger.info(f"✓ Successfully extracted {len(json_objects)} JSON objects using code block approach")
                    return json_objects[0], json_objects[1]
            
            # Strategy 4: Last resort - find raw JSON objects
            logger.info("Using last resort raw JSON extraction...")
            json_objects = []
            brace_count = 0
            start_pos = -1
            
            for i, char in enumerate(content):
                if char == '{':
                    if brace_count == 0:
                        start_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_pos != -1:
                        json_str = content[start_pos:i+1]
                        try:
                            json_obj = json.loads(json_str)
                            json_objects.append(json_obj)
                        except json.JSONDecodeError:
                            pass
                        start_pos = -1
            
            if len(json_objects) >= 2:
                logger.info(f"✓ Successfully extracted {len(json_objects)} JSON objects using raw extraction")
                return json_objects[0], json_objects[1]
            elif len(json_objects) == 1:
                logger.info("✓ Found single JSON object using raw extraction")
                standard_json, verbose_json = self._extract_nested_json_objects(json_objects[0])
                if standard_json and verbose_json:
                    return standard_json, verbose_json
                else:
                    # Fallback to creating standard and verbose from single object
                    standard_json = self._create_standard_json(json_objects[0])
                    verbose_json = self._create_verbose_json(json_objects[0])
                    return standard_json, verbose_json
            
            logger.error(f"All extraction strategies failed. Expected JSON objects, found {len(json_objects)}")
            return None, None
                
        except Exception as e:
            logger.error(f"Error extracting JSON from response: {e}")
            return None, None
    
    def _extract_nested_json_objects(self, main_json_obj: dict):
        """
        Extract two nested JSON objects from the main JSON object.
        
        Args:
            main_json_obj (dict): The main JSON object containing nested JSON objects
            
        Returns:
            tuple: (standard_json, verbose_json) or (None, None) if not found
        """
        try:
            # Look for common keys that might contain the nested JSON objects
            possible_keys = [
                "standard_solution", "verbose_solution",
                "standard", "verbose", 
                "output1", "output2",
                "first_json", "second_json",
                "json1", "json2"
            ]
            
            for key in possible_keys:
                if key in main_json_obj:
                    logger.info(f"Found key '{key}' in main JSON object")
                    # This might contain one of the nested JSON objects
            
            # Look for nested JSON objects by checking if any values are dictionaries
            # that contain "solution_steps" (which is our expected structure)
            nested_objects = []
            
            def find_nested_objects(obj, path=""):
                if isinstance(obj, dict):
                    if "solution_steps" in obj and isinstance(obj["solution_steps"], list):
                        nested_objects.append((path, obj))
                    for key, value in obj.items():
                        find_nested_objects(value, f"{path}.{key}" if path else key)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_nested_objects(item, f"{path}[{i}]")
            
            find_nested_objects(main_json_obj)
            
            if len(nested_objects) >= 2:
                logger.info(f"✓ Found {len(nested_objects)} nested JSON objects with solution_steps")
                # First one is standard, second is verbose
                return nested_objects[0][1], nested_objects[1][1]
            elif len(nested_objects) == 1:
                logger.info(f"✓ Found {len(nested_objects)} nested JSON object, creating both versions")
                # Create both standard and verbose from the single nested object
                standard_json = nested_objects[0][1]
                verbose_json = self._create_verbose_json(standard_json)
                return standard_json, verbose_json
            
            logger.warning("No nested JSON objects with solution_steps found")
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting nested JSON objects: {e}")
            return None, None
    
    def _create_standard_json(self, json_obj: dict) -> dict:
        """
        Create standard JSON format from the combined JSON object.
        
        Args:
            json_obj (dict): The combined JSON object from v3 format
            
        Returns:
            dict: Standard JSON format
        """
        # For now, return the original JSON as standard
        # This can be enhanced later to extract specific standard content
        return json_obj
    
    def _create_verbose_json(self, json_obj: dict) -> dict:
        """
        Create verbose JSON format from the combined JSON object.
        
        Args:
            json_obj (dict): The combined JSON object from v3 format
            
        Returns:
            dict: Verbose JSON format
        """
        # Create a simplified version for TTS-friendly content
        verbose_json = {
            "solution_steps": []
        }
        
        if "solution_steps" in json_obj:
            for step in json_obj["solution_steps"]:
                verbose_step = {
                    "step_id": step.get("step_id", ""),
                    "sentences": []
                }
                
                if "sentences" in step:
                    for sentence in step["sentences"]:
                        # Create TTS-friendly sentence (just text, no LaTeX)
                        verbose_sentence = {
                            "text": sentence.get("text", "")
                        }
                        verbose_step["sentences"].append(verbose_sentence)
                
                verbose_json["solution_steps"].append(verbose_step)
        
        return verbose_json
    
    def _clean_json_content(self, json_content: str) -> str:
        """
        Clean JSON content by fixing common escape sequence issues.
        
        Args:
            json_content (str): Raw JSON content
            
        Returns:
            str: Cleaned JSON content
        """
        # Step 1: Check if content is already JSON-escaped (has double backslashes)
        if '\\\\' in json_content:
            # Content is already JSON-escaped, don't add more escaping
            logger.info("Content appears to be already JSON-escaped, skipping additional escaping")
            return json_content
        
        # Step 2: Fix LaTeX backslash sequences (only for raw content)
        latex_patterns = [
            ('\\text{', '\\\\text{'),
            ('\\triangle', '\\\\triangle'),
            ('\\angle', '\\\\angle'),
            ('\\cong', '\\\\cong'),
            ('\\implies', '\\\\implies'),
            ('\\frac', '\\\\frac'),
            ('\\times', '\\\\times'),
            ('\\circ', '\\\\circ'),
            ('\\therefore', '\\\\therefore'),
            ('\\text{ cm}', '\\\\text{ cm}'),
            ('\\text{ cm}^2', '\\\\text{ cm}^2'),
            ('\\text{ is isosceles}', '\\\\text{ is isosceles}'),
            ('\\text{ (Given)}', '\\\\text{ (Given)}'),
            ('\\text{ (Common side)}', '\\\\text{ (Common side)}'),
            ('\\text{ (RHS Congruence)}', '\\\\text{ (RHS Congruence)}'),
            ('\\text{Area(ABCED)}', '\\\\text{Area(ABCED)}'),
            ('\\text{Area}(', '\\\\text{Area}('),
            ('\\text{In }', '\\\\text{In }'),
            ('\\text{Key Method 1:', '\\\\text{Key Method 1:'),
            ('\\text{Key Method 2:', '\\\\text{Key Method 2:'),
            ('\\text{Key Method 3:', '\\\\text{Key Method 3:'),
        ]
        
        cleaned = json_content
        for pattern, replacement in latex_patterns:
            cleaned = cleaned.replace(pattern, replacement)
        
        # Step 3: Handle any remaining problematic backslashes
        # Only escape backslashes that are not already escaped
        import re
        cleaned = re.sub(r'(?<!\\)\\(?!\\)', r'\\\\', cleaned)
        
        return cleaned
    
    def generate_intelligent_filename(self, input_path: str, question_image_path: str = None):
        """
        Generate an intelligent filename based on input files.
        
        Args:
            input_path (str): Path to the main input file
            question_image_path (str): Optional path to question image
            
        Returns:
            str: Generated filename
        """
        try:
            # Extract base names from input files
            input_base = os.path.splitext(os.path.basename(input_path))[0]
            
            if question_image_path:
                question_base = os.path.splitext(os.path.basename(question_image_path))[0]
                # Create filename with both inputs
                filename = f"solution_{input_base}_{question_base}"
            else:
                # Create filename with just main input
                filename = f"solution_{input_base}"
            
            # Add timestamp for uniqueness
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}"
            
            return filename
            
        except Exception as e:
            logger.error(f"Error generating filename: {e}")
            # Fallback to timestamp-based filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            return f"solution_generated_{timestamp}"
    
    def save_raw_output(self, content: str):
        """
        Save the entire raw output from the API as .txt file with fixed filename.
        
        Args:
            content (str): The complete raw API response content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use the specific absolute path for math_solution_pipeline
            output_dir = "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline"
            os.makedirs(output_dir, exist_ok=True)
            
            # Use fixed filename
            output_filename = os.path.join(output_dir, "math_solution_raw.txt")
            
            # Save as .txt file (always overwrite)
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✓ Saved complete raw output to: {output_filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving raw output: {e}")
            return False
    
    def save_parsed_json_files(self, standard_json: dict, verbose_json: dict):
        """
        Save the parsed JSON outputs as separate files with fixed filenames.
        
        Args:
            standard_json (dict): The standard solution JSON
            verbose_json (dict): The verbose solution JSON
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use the specific absolute path for math_solution_pipeline
            output_dir = "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline"
            os.makedirs(output_dir, exist_ok=True)
            
            # Use fixed filenames (always overwrite)
            standard_filename = os.path.join(output_dir, "math_solution_standard.json")
            verbose_filename = os.path.join(output_dir, "math_solution_verbose.json")
            
            # Save standard JSON
            with open(standard_filename, 'w', encoding='utf-8') as f:
                json.dump(standard_json, f, indent=2)
            logger.info(f"✓ Saved standard solution to: {standard_filename}")
            
            # Save verbose JSON
            with open(verbose_filename, 'w', encoding='utf-8') as f:
                json.dump(verbose_json, f, indent=2)
            logger.info(f"✓ Saved verbose solution to: {verbose_filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving parsed JSON files: {e}")
            return False
    
    def cleanup_temp_files(self, temp_files: list):
        """
        Clean up temporary image files.
        
        Args:
            temp_files (list): List of temporary file paths to delete
        """
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
                logger.info(f"✓ Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_file}: {e}")
    
    def generate_solution_steps(self, input_path: str, question_image_path: str):
        """
        Complete pipeline to generate solution steps from an image or PDF, including a question image.
        
        Args:
            input_path (str): Path to the question image or PDF file
            question_image_path (str): Path to additional question image (required)
            
        Returns:
            bool: True if successful, False otherwise
        """
        temp_files = []
        
        try:
            # Check if input is a PDF or image
            is_pdf = input_path.lower().endswith('.pdf')
            
            if is_pdf:
                # Verify PDF file exists
                if not os.path.exists(input_path):
                    logger.error(f"PDF file not found: {input_path}")
                    return False
                
                logger.info(f"🎯 Starting solution steps generation from PDF")
                logger.info(f"📁 PDF file: {input_path}")
                
                # Convert PDF to images
                images = self.convert_pdf_to_images(input_path)
                
                # Save images to temporary files
                image_paths = []
                for i, image in enumerate(images):
                    temp_file = self.save_image_to_temp(image, i)
                    temp_files.append(temp_file)
                    image_paths.append(temp_file)
                
            else:
                # Verify image file exists
                if not os.path.exists(input_path):
                    logger.error(f"Image file not found: {input_path}")
                    return False
                
                logger.info(f"🎯 Starting solution steps generation from image")
                logger.info(f"📁 Image file: {input_path}")
                
                image_paths = [input_path]
            
            # Add question image (required)
            if not os.path.exists(question_image_path):
                logger.error(f"Question image file not found: {question_image_path}")
                return False
            
            logger.info(f"📁 Adding question image: {question_image_path}")
            image_paths.append(question_image_path)
            
            # Make API call
            api_result = self.make_gemini_api_call(image_paths)
            
            if not api_result["success"]:
                logger.error(f"❌ API call failed: {api_result['error']}")
                return False
            
            # Parse the two JSON outputs from the response
            standard_json, verbose_json = self.extract_both_json_from_response(api_result["content"])
            
            if standard_json is None or verbose_json is None:
                logger.error("❌ Failed to parse JSON outputs from API response")
                return False
            
            # Save the complete raw output as .txt file
            if not self.save_raw_output(api_result["content"]):
                logger.error("❌ Failed to save raw output")
                return False
            
            # Save the parsed JSON files
            if not self.save_parsed_json_files(standard_json, verbose_json):
                logger.error("❌ Failed to save parsed JSON files")
                return False
            
            logger.info("✅ Solution steps generation completed successfully!")
            logger.info(f"📁 Generated files:")
            logger.info(f"   - Raw TXT: /Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline/math_solution_raw.txt")
            logger.info(f"   - Standard JSON: /Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline/math_solution_standard.json")
            logger.info(f"   - Verbose JSON: /Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline/math_solution_verbose.json")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in solution steps generation: {e}")
            return False
        finally:
            # Clean up temporary files
            self.cleanup_temp_files(temp_files)

def main():
    """Main function to run the solution steps generation from command line."""
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description="Generate solution steps from PDF and question image")
    parser.add_argument("--question-image", help="Path to the question image file (required)")
    
    args = parser.parse_args()
    
    # Get question image path from command line or prompt user
    question_image_path = args.question_image
    if not question_image_path:
        print("❌ Question image path is required!")
        question_image_path = input("Please enter the path to your question image: ").strip()
        if not question_image_path:
            print("❌ No question image path provided. Exiting.")
            sys.exit(1)
    
    # Fixed PDF path
    input_path = "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Math_Solution/symbols.pdf"
    
    # Verify question image exists
    if not os.path.exists(question_image_path):
        print(f"❌ Question image file not found: {question_image_path}")
        sys.exit(1)
    
    # Initialize the generator
    try:
        generator = SolutionStepsGenerator()
        logger.info("✅ Solution Steps Generator initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize generator: {e}")
        sys.exit(1)
    
    # Generate solution steps
    logger.info("🎬 Starting solution steps generation...")
    logger.info(f"📁 PDF file: {input_path}")
    logger.info(f"📁 Question image: {question_image_path}")
    
    success = generator.generate_solution_steps(input_path, question_image_path)
    
    if success:
        logger.info("✅ Solution steps generation completed successfully!")
        logger.info("📁 Generated files are ready for use")
    else:
        logger.error("❌ Solution steps generation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 