#!/usr/bin/env python3
"""
Single API Call to Claude Sonnet 4
Makes a single API call to Claude Sonnet 4 using OpenRouter API
Uses the ENHANCED_CODE_GENERATION_PROMPT_v6 from geometry_prompts_v1.py
Includes configurable input files for comprehensive code generation
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
from openai import OpenAI

# Import the enhanced prompt and style config
import sys
sys.path.append('/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline')
from pipeline_prompts import ENHANCED_CODE_GENERATION_PROMPT_v4
# Load environment variables from current directory
load_dotenv('.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SingleClaudeAPICall:
    """Make a single API call to Claude Sonnet 4 using OpenRouter API."""
    
    def __init__(self, api_key: str = None, model: str = "anthropic/claude-sonnet-4"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key, base_url="https://openrouter.ai/api/v1")
        
        logger.info(f"Initialized API client with model: {self.model}")
    
    def load_input_files(self, input_config: dict):
        """
        Load all input files specified in the configuration.
        
        Args:
            input_config (dict): Dictionary containing file paths
            
        Returns:
            dict: Dictionary containing loaded file contents
        """
        loaded_files = {}
        
        for file_type, file_path in input_config.items():
            try:
                if file_type == "question_image":
                    # For images, we just verify they exist
                    if os.path.exists(file_path):
                        loaded_files[file_type] = file_path
                        logger.info(f"✅ Found image file: {file_path}")
                    else:
                        logger.warning(f"⚠️  Image file not found: {file_path}")
                        loaded_files[file_type] = None
                else:
                    # For text files, load the content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if file_path.endswith('.json'):
                            loaded_files[file_type] = json.load(f)
                        else:
                            loaded_files[file_type] = f.read()
                    logger.info(f"✅ Loaded {file_type}: {file_path}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to load {file_type} from {file_path}: {e}")
                loaded_files[file_type] = None
        
        return loaded_files
    
    def create_comprehensive_prompt(self, loaded_files: dict, additional_context: str = ""):
        """
        Create a comprehensive prompt that includes all input files.
        
        Args:
            loaded_files (dict): Dictionary containing loaded file contents
            additional_context (str): Additional context to append
            
        Returns:
            str: Complete prompt for API call
        """
        # Start with the enhanced prompt
        prompt = ENHANCED_CODE_GENERATION_PROMPT_v4
        
        # Add input files section
        prompt += "\n\n" + "="*50 + "\n"
        prompt += "INPUT FILES FOR CODE GENERATION\n"
        prompt += "="*50 + "\n\n"
        
        # Add each loaded file
        for file_type, content in loaded_files.items():
            if content is not None:
                prompt += f"--- {file_type.upper()} ---\n"
                
                if file_type == "question_image":
                    prompt += f"Image file available at: {content}\n"
                elif isinstance(content, dict):
                    prompt += f"JSON Data:\n{json.dumps(content, indent=2)}\n"
                else:
                    prompt += f"File Content:\n{content}\n"
                
                prompt += "\n"
        
        # Note: additional_context intentionally omitted from final prompt
        
        # Add final instructions
        prompt += "\n" + "="*50 + "\n"
        prompt += "FINAL INSTRUCTIONS\n"
        prompt += "="*50 + "\n"
        prompt += """
Generate a complete, production-ready Manim code file that includes all necessary scenes.
The output should be a single Python file that can be run directly with Manim.

CRITICAL REQUIREMENTS:
1. Generate ONLY the Python code - NO explanatory text, comments, or markdown
2. Start the file with the shebang and imports
3. Include all scene classes based on the input data
4. Ensure all code is properly formatted and error-free
5. Use the provided geometric figure code and coordinates
6. Follow the enhanced prompt guidelines for text generation and animations
7. Include proper error handling and audio integration
8. End the file with the last class definition - NO additional text

IMPORTANT: Do NOT include any explanatory text, markdown formatting, or comments about what the code does. Generate ONLY the Python code that can be executed directly.

The generated code should be ready to render immediately with Manim.
"""
        
        return prompt
    
    def fix_common_syntax_issues(self, code: str):
        """
        Fix common syntax issues in the generated code, including invalid escape sequences.
        
        Args:
            code (str): Code that may have syntax issues
            
        Returns:
            str: Fixed code
        """
        # Fix invalid escape sequences by using raw strings for MathTex
        def fix_mathtex_escapes(match):
            content = match.group(1)
            # Use raw string to avoid escape sequence issues
            return f'MathTex(r"{content}")'
        
        # Find MathTex expressions and convert to raw strings
        code = re.sub(r'MathTex\("(.*?)"\)', fix_mathtex_escapes, code, flags=re.DOTALL)
        
        # Remove any remaining backticks that might cause issues
        code = re.sub(r'``([^`]*)``', r'\1', code)
        
        # Remove any remaining markdown-style formatting
        code = re.sub(r'\*\*([^*]*)\*\*', r'\1', code)
        
        # Remove any lines that start with numbers and dots (like "1. **Feature**")
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip numbered list items
            if re.match(r'^\d+\.\s*\*\*', line.strip()):
                continue
            # Skip lines that are just explanatory text
            if line.strip().startswith('The code is production-ready'):
                continue
            if line.strip().startswith('manim all_scenes.py'):
                continue
            if line.strip().startswith('```'):
                continue
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines)
        
        # Ensure proper file ending
        code = code.strip()
        
        # Remove any trailing explanatory text
        code = re.sub(r'\n\nThis complete Manim code file includes:.*', '', code, flags=re.DOTALL)
        code = re.sub(r'\n\nThe code is production-ready.*', '', code, flags=re.DOTALL)
        
        return code

    def clean_code_output(self, code: str):
        """
        Clean the code output by removing markdown code blocks, comments, and extra text.
        
        Args:
            code (str): Raw code output from API
            
        Returns:
            str: Cleaned code ready for saving
        """
        # Remove markdown code blocks
        code = re.sub(r'```python\s*', '', code)
        code = re.sub(r'```\s*$', '', code)
        code = re.sub(r'^```\s*', '', code)
        
        # Remove any remaining markdown formatting
        code = re.sub(r'`([^`]+)`', r'\1', code)  # Remove inline code backticks
        
        # Remove explanatory text and comments that are not part of the code
        # Remove lines that start with explanatory text (not code)
        lines = code.split('\n')
        cleaned_lines = []
        in_code_block = False
        
        for line in lines:
            # Skip lines that are clearly explanatory text (not Python code)
            if (line.strip().startswith('Looking at the provided') or
                line.strip().startswith('This complete Manim code file includes:') or
                line.strip().startswith('The code is production-ready') or
                line.strip().startswith('manim all_scenes.py') or
                line.strip().startswith('``bash') or
                line.strip().startswith('```') or
                line.strip().startswith('1. **') or
                line.strip().startswith('2. **') or
                line.strip().startswith('3. **') or
                line.strip().startswith('4. **') or
                line.strip().startswith('5. **') or
                line.strip().startswith('6. **') or
                line.strip().startswith('7. **') or
                line.strip().startswith('8. **') or
                line.strip().startswith('9. **') or
                line.strip() == '' and not in_code_block):
                continue
            
            # Check if we're entering a code block
            if line.strip().startswith('import ') or line.strip().startswith('#!/usr/bin/env'):
                in_code_block = True
            
            # If we're in a code block, keep the line
            if in_code_block:
                cleaned_lines.append(line)
        
        # Join the cleaned lines
        code = '\n'.join(cleaned_lines)
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        # Ensure it starts with proper Python file header
        if not code.startswith('#!/usr/bin/env python3') and not code.startswith('import'):
            code = '#!/usr/bin/env python3\n"""Generated Manim Code"""\n\n' + code
        
        # Remove any trailing explanatory text
        code = re.sub(r'\n\nThis complete Manim code file includes:.*', '', code, flags=re.DOTALL)
        code = re.sub(r'\n\nThe code is production-ready.*', '', code, flags=re.DOTALL)
        
        return code
    

    
    def make_api_call(self, prompt: str, image_path: str = None, temperature: float = 0.1, max_tokens: int = 20000):
        """
        Make a single API call to Claude Sonnet 4.
        
        Args:
            prompt (str): The prompt to send to the API
            image_path (str, optional): Path to an image file to include
            temperature (float): Temperature for response generation (0.0 to 1.0)
            max_tokens (int): Maximum number of tokens in the response
            
        Returns:
            dict: API response with content and metadata
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Add image if provided
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    messages[0]["content"] = [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                    logger.info(f"Including image in API call: {image_path}")
                except Exception as e:
                    logger.warning(f"Failed to include image: {e}")
            
            # Calculate input tokens (rough estimate)
            input_tokens = len(prompt.split()) * 1.3  # Rough estimate for tokens
            logger.info(f"📊 Estimated input tokens: {input_tokens:.0f}")
            logger.info(f"📝 Prompt length: {len(prompt)} characters")
            
            logger.info("🚀 Making API call to Claude Sonnet 4...")
            start_time = time.time()
            
            # Make the API call
            response = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://github.com/your-repo/prompt-generation",
                    "X-Title": "Prompt Generation Project",
                },
                extra_body={},
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            result = response.choices[0].message.content
            
            # Extract token usage from response
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            total_tokens = usage.total_tokens if usage else None
            
            # Log detailed metrics
            logger.info(f"⏱️  API call completed in {duration:.2f} seconds")
            logger.info(f"📊 Token usage:")
            if prompt_tokens:
                logger.info(f"   Input tokens: {prompt_tokens}")
            else:
                logger.info(f"   Estimated input tokens: {input_tokens:.0f}")
            if completion_tokens:
                logger.info(f"   Output tokens: {completion_tokens}")
            if total_tokens:
                logger.info(f"   Total tokens: {total_tokens}")
            
            logger.info(f"📄 Response length: {len(result)} characters")
            logger.info(f"⚡ Average speed: {len(result)/duration:.0f} characters/second")
            
            # Return comprehensive response
            return {
                'content': result,
                'metadata': {
                    'duration': duration,
                    'prompt_tokens': prompt_tokens or input_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'response_length': len(result),
                    'speed_chars_per_sec': len(result)/duration,
                    'model': self.model,
                    'temperature': temperature,
                    'max_tokens': max_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None
    
    def generate_complete_manim_code(self, input_config: dict, additional_context: str = "", output_file: str = "all_scenes.py"):
        """
        Generate complete Manim code using all input files.
        
        Args:
            input_config (dict): Dictionary containing file paths
            additional_context (str): Additional context for the prompt
            output_file (str): Output file name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load all input files
            logger.info("📁 Loading input files...")
            loaded_files = self.load_input_files(input_config)
            
            # Create comprehensive prompt
            logger.info("📝 Creating comprehensive prompt...")
            prompt = self.create_comprehensive_prompt(loaded_files, additional_context="")
            
            # Get image path for API call
            image_path = loaded_files.get("question_image")
            
            # Make API call
            logger.info("🚀 Making comprehensive API call...")
            response = self.make_api_call(prompt, image_path)
            
            if not response:
                logger.error("❌ API call failed!")
                return False
            
            # Clean the code output
            logger.info("🧹 Cleaning code output...")
            cleaned_code = self.clean_code_output(response['content'])
            
            # Validate that the cleaned code is valid Python
            logger.info("🔍 Validating Python syntax...")
            try:
                compile(cleaned_code, output_file, 'exec')
                logger.info("✅ Code syntax validation passed")
            except SyntaxError as e:
                logger.error(f"❌ Code syntax validation failed: {e}")
                logger.error("Attempting to fix common syntax issues...")
                cleaned_code = self.fix_common_syntax_issues(cleaned_code)
                # Try validation again
                try:
                    compile(cleaned_code, output_file, 'exec')
                    logger.info("✅ Code syntax validation passed after fixes")
                except SyntaxError as e2:
                    logger.error(f"❌ Code syntax still invalid after fixes: {e2}")
                    return False
            
            # Save the cleaned code
            logger.info(f"💾 Saving code to {output_file}...")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_code)
            
            logger.info(f"✅ Successfully generated and saved: {output_file}")
            
            # Save metadata
            metadata_file = output_file.replace('.py', '_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(response['metadata'], f, indent=2)
            logger.info(f"📊 Metadata saved to: {metadata_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generating code: {e}")
            return False
    
    def save_response(self, response: dict, output_file: str = "claude_response.txt"):
        """
        Save the API response to a file.
        
        Args:
            response (dict): The API response dictionary
            output_file (str): Path to save the response
        """
        if not response:
            logger.error("No response to save")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=== CLAUDE SONNET 4 API RESPONSE ===\n\n")
                f.write("CONTENT:\n")
                f.write(response['content'])
                f.write("\n\n=== METADATA ===\n")
                f.write(json.dumps(response['metadata'], indent=2))
            
            logger.info(f"✅ Response saved to: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save response: {e}")

def main():
    """Main function to run the video generation from command line."""
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description="Generate comprehensive Manim code from question image and pipeline data")
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
    
    # Verify question image exists
    if not os.path.exists(question_image_path):
        print(f"❌ Question image file not found: {question_image_path}")
        sys.exit(1)
    
    # Define input file configuration with dynamic question image path
    input_config = {
        "math_solution": "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/math_solution_pipeline/math_solution_standard.json",
        "deconstruct_parallel": "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/geometric_elements_with_timing.json",
        "question_image": question_image_path,
        "coordinates": "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/coordinates.txt",
        "geometry_code": "/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline/figure.py"
    }
    
    # Note: ENHANCED_STYLE_CONFIG is automatically included from geometry_prompts.py
    
    # Initialize the API caller
    try:
        api_caller = SingleClaudeAPICall()
        logger.info("✅ API caller initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize API caller: {e}")
        sys.exit(1)
    
    # Generate complete Manim code
    logger.info("🎬 Starting comprehensive Manim code generation...")
    logger.info(f"📁 Question image: {question_image_path}")
    
    success = api_caller.generate_complete_manim_code(
        input_config=input_config,
        output_file="all_scenes.py"
    )
    
    if success:
        logger.info("✅ Code generation completed successfully!")
        logger.info("📁 Generated files:")
        logger.info("   - all_scenes.py (main code file)")
        logger.info("   - all_scenes_metadata.json (generation metadata)")
        logger.info("🎬 Ready to render with: manim -pql all_scenes.py SceneClassName")
    else:
        logger.error("❌ Code generation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 