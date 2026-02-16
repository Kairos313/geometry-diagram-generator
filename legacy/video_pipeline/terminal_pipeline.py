#!/usr/bin/env python3
"""
Terminal Pipeline Script
Orchestrates the entire geometry video generation pipeline sequentially.

This script runs the following steps in order:
1. generate_solution_steps.py - Generate solution steps from question image
2. geo_scriptwriter_parallel.py - Generate audio files and timing data
3. integrated_geometry_pipeline.py - Generate geometric blueprint and Manim code
4. video_claude.py - Generate comprehensive Manim scenes
5. render_and_concatenate_scenes.py - Render and concatenate final video

Each step is validated before proceeding to the next.
"""

import os
import sys
import subprocess
import time
import argparse
import logging
from pathlib import Path
from typing import Tuple, List

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TerminalPipeline:
    """Main pipeline orchestrator class."""
    
    def __init__(self, question_image_path: str):
        self.question_image_path = question_image_path
        self.pipeline_dir = Path("/Users/kairos/Desktop/Prompt Generation/Geometry_v2/Geometry Test Questions/Full_Pipeline")
        self.start_time = time.time()
        
        # Token tracking
        self.token_usage = {
            "total": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "by_step": {},
            "by_model": {
                "gemini": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "claude": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
        }
        
        # Ensure we're in the correct directory
        os.chdir(self.pipeline_dir)
        logger.info(f"Pipeline initialized in directory: {self.pipeline_dir}")
        logger.info(f"Question image: {self.question_image_path}")
    
    def validate_file_exists(self, file_path: str, step_name: str) -> bool:
        """Validate that a file exists and log the result."""
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            logger.info(f"✅ {step_name}: {file_path} exists ({file_size} bytes)")
            return True
        else:
            logger.error(f"❌ {step_name}: {file_path} not found")
            return False
    
    def validate_files_exist(self, file_paths: List[str], step_name: str) -> bool:
        """Validate that multiple files exist."""
        all_exist = True
        for file_path in file_paths:
            if not self.validate_file_exists(file_path, step_name):
                all_exist = False
        return all_exist
    
    def run_command(self, command: List[str], step_name: str) -> bool:
        """Run a command and return success status."""
        logger.info(f"🚀 Starting {step_name}...")
        logger.info(f"   Command: {' '.join(command)}")
        
        try:
            start_time = time.time()
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.pipeline_dir
            )
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                logger.info(f"✅ {step_name} completed successfully in {duration:.2f} seconds")
                if result.stdout:
                    logger.debug(f"   Output: {result.stdout}")
                
                # Extract token usage from output if available
                self.extract_token_usage_from_output(result.stdout, step_name)
                
                # Also check stderr for token information
                if result.stderr:
                    self.extract_token_usage_from_output(result.stderr, step_name)
                
                return True
            else:
                logger.error(f"❌ {step_name} failed with return code {result.returncode}")
                logger.error(f"   Error output: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ {step_name} failed with exception: {e}")
            return False
    
    def extract_token_usage_from_output(self, output: str, step_name: str):
        """Extract token usage information from command output."""
        if not output:
            return
        
        # Look for token usage patterns in the output
        import re
        
        # Pattern for token usage information
        token_patterns = [
            r'Input tokens:\s*(\d+)',
            r'Output tokens:\s*(\d+)',
            r'Total tokens:\s*(\d+)',
            r'prompt_tokens.*?(\d+)',
            r'completion_tokens.*?(\d+)',
            r'total_tokens.*?(\d+)',
            r'Tokens:\s*(\d+)\s*\(input:\s*(\d+),\s*output:\s*(\d+)\)',
            r'(\d+)\s*\(input:\s*(\d+),\s*output:\s*(\d+)\)'
        ]
        
        step_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        # Extract token numbers from output
        for i, pattern in enumerate(token_patterns):
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    if i < 6:  # First 6 patterns are single number patterns
                        token_count = int(matches[0])
                        if "prompt" in pattern.lower():
                            step_tokens["prompt_tokens"] = token_count
                        elif "completion" in pattern.lower():
                            step_tokens["completion_tokens"] = token_count
                        elif "total" in pattern.lower():
                            step_tokens["total_tokens"] = token_count
                    else:  # Last 2 patterns are multi-number patterns
                        if len(matches[0]) >= 3:  # Ensure we have all 3 numbers
                            total_tokens = int(matches[0][0])
                            input_tokens = int(matches[0][1])
                            output_tokens = int(matches[0][2])
                            step_tokens["total_tokens"] = total_tokens
                            step_tokens["prompt_tokens"] = input_tokens
                            step_tokens["completion_tokens"] = output_tokens
                except (ValueError, IndexError):
                    continue
        
        # If we found any tokens, store them
        if any(step_tokens.values()):
            self.token_usage["by_step"][step_name] = step_tokens
            
            # Update totals
            self.token_usage["total"]["prompt_tokens"] += step_tokens["prompt_tokens"]
            self.token_usage["total"]["completion_tokens"] += step_tokens["completion_tokens"]
            self.token_usage["total"]["total_tokens"] += step_tokens["total_tokens"]
            
            # Update by model (based on step name)
            if "gemini" in step_name.lower() or "solution" in step_name.lower():
                model_key = "gemini"
            elif "claude" in step_name.lower() or "video" in step_name.lower():
                model_key = "claude"
            else:
                model_key = "claude"  # Default for other steps
            
            self.token_usage["by_model"][model_key]["prompt_tokens"] += step_tokens["prompt_tokens"]
            self.token_usage["by_model"][model_key]["completion_tokens"] += step_tokens["completion_tokens"]
            self.token_usage["by_model"][model_key]["total_tokens"] += step_tokens["total_tokens"]
            
            logger.info(f"📊 Token usage for {step_name}: {step_tokens}")
    
    def extract_token_usage_from_metadata_files(self):
        """Extract token usage from metadata files created by individual scripts."""
        metadata_files = [
            "all_scenes_metadata.json"
        ]
        
        for metadata_file in metadata_files:
            if os.path.exists(metadata_file):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if "prompt_tokens" in metadata and "completion_tokens" in metadata:
                        step_name = metadata_file.replace("_metadata.json", "")
                        step_tokens = {
                            "prompt_tokens": metadata.get("prompt_tokens", 0),
                            "completion_tokens": metadata.get("completion_tokens", 0),
                            "total_tokens": metadata.get("total_tokens", 0)
                        }
                        
                        self.token_usage["by_step"][step_name] = step_tokens
                        self.token_usage["total"]["prompt_tokens"] += step_tokens["prompt_tokens"]
                        self.token_usage["total"]["completion_tokens"] += step_tokens["completion_tokens"]
                        self.token_usage["total"]["total_tokens"] += step_tokens["total_tokens"]
                        
                        # Determine model based on step name
                        if "video" in step_name.lower():
                            model_key = "claude"
                        else:
                            model_key = "claude"  # Default
                        
                        self.token_usage["by_model"][model_key]["prompt_tokens"] += step_tokens["prompt_tokens"]
                        self.token_usage["by_model"][model_key]["completion_tokens"] += step_tokens["completion_tokens"]
                        self.token_usage["by_model"][model_key]["total_tokens"] += step_tokens["total_tokens"]
                        
                        logger.info(f"📊 Token usage from {metadata_file}: {step_tokens}")
                        
                except Exception as e:
                    logger.warning(f"Could not read token usage from {metadata_file}: {e}")
    
    def step_1_generate_solution_steps(self) -> bool:
        """Step 1: Generate solution steps from question image."""
        logger.info("=" * 60)
        logger.info("STEP 1: GENERATE SOLUTION STEPS")
        logger.info("=" * 60)
        
        # Run generate_solution_steps.py
        command = [
            "python", "generate_solution_steps.py",
            "--question-image", self.question_image_path
        ]
        
        success = self.run_command(command, "generate_solution_steps.py")
        if not success:
            return False
        
        # Validate outputs
        logger.info("🔍 Validating Step 1 outputs...")
        expected_files = [
            "math_solution_pipeline/math_solution_standard.json",
            "math_solution_pipeline/math_solution_verbose.json"
        ]
        
        if not self.validate_files_exist(expected_files, "Step 1"):
            logger.error("❌ Step 1 validation failed - required files not found")
            return False
        
        logger.info("✅ Step 1 completed and validated successfully")
        return True
    
    def step_2_generate_audio(self) -> bool:
        """Step 2: Generate audio files and timing data."""
        logger.info("=" * 60)
        logger.info("STEP 2: GENERATE AUDIO FILES")
        logger.info("=" * 60)
        
        # Run geo_scriptwriter_parallel.py
        command = ["python", "geo_scriptwriter_parallel.py"]
        
        success = self.run_command(command, "geo_scriptwriter_parallel.py")
        if not success:
            return False
        
        # Validate outputs
        logger.info("🔍 Validating Step 2 outputs...")
        
        # Check for geometric_elements_with_timing.json
        timing_file = "geometric_elements_with_timing.json"
        if not self.validate_file_exists(timing_file, "Step 2"):
            logger.error("❌ Step 2 validation failed - geometric_elements_with_timing.json not found")
            return False
        
        # Check for audio directories and files
        audio_dirs = ["Audio", "Scene"]
        for audio_dir in audio_dirs:
            if os.path.exists(audio_dir):
                audio_files = list(Path(audio_dir).glob("*.mp3"))
                logger.info(f"✅ Step 2: {audio_dir} directory exists with {len(audio_files)} audio files")
            else:
                logger.warning(f"⚠️ Step 2: {audio_dir} directory not found")
        
        logger.info("✅ Step 2 completed and validated successfully")
        return True
    
    def step_3_generate_geometry_pipeline(self) -> bool:
        """Step 3: Generate geometric blueprint and Manim code."""
        logger.info("=" * 60)
        logger.info("STEP 3: GENERATE GEOMETRIC PIPELINE")
        logger.info("=" * 60)
        
        # Run integrated_geometry_pipeline.py
        command = [
            "python", "integrated_geometry_pipeline.py",
            "--question-image", self.question_image_path
        ]
        
        success = self.run_command(command, "integrated_geometry_pipeline.py")
        if not success:
            return False
        
        # Validate outputs
        logger.info("🔍 Validating Step 3 outputs...")
        expected_files = [
            "coordinates.txt",
            "figure.py"
        ]
        
        if not self.validate_files_exist(expected_files, "Step 3"):
            logger.error("❌ Step 3 validation failed - required files not found")
            return False
        
        logger.info("✅ Step 3 completed and validated successfully")
        return True
    
    def step_4_generate_video_code(self) -> bool:
        """Step 4: Generate comprehensive Manim scenes."""
        logger.info("=" * 60)
        logger.info("STEP 4: GENERATE VIDEO CODE")
        logger.info("=" * 60)
        
        # Run video_claude.py
        command = [
            "python", "video_claude.py",
            "--question-image", self.question_image_path
        ]
        
        success = self.run_command(command, "video_claude.py")
        if not success:
            return False
        
        # Validate outputs
        logger.info("🔍 Validating Step 4 outputs...")
        expected_files = [
            "all_scenes.py",
            "all_scenes_metadata.json"
        ]
        
        if not self.validate_files_exist(expected_files, "Step 4"):
            logger.error("❌ Step 4 validation failed - required files not found")
            return False
        
        logger.info("✅ Step 4 completed and validated successfully")
        return True
    
    def step_5_render_final_video(self) -> bool:
        """Step 5: Render and concatenate final video."""
        logger.info("=" * 60)
        logger.info("STEP 5: RENDER FINAL VIDEO")
        logger.info("=" * 60)
        
        # Run render_and_concatenate_scenes.py
        command = ["python", "render_and_concatenate_scenes.py"]
        
        success = self.run_command(command, "render_and_concatenate_scenes.py")
        if not success:
            return False
        
        # Validate outputs
        logger.info("🔍 Validating Step 5 outputs...")
        expected_files = [
            "final_geometry_video.mp4"
        ]
        
        if not self.validate_files_exist(expected_files, "Step 5"):
            logger.error("❌ Step 5 validation failed - final video not found")
            return False
        
        logger.info("✅ Step 5 completed and validated successfully")
        return True
    
    def run_pipeline(self) -> bool:
        """Run the complete pipeline sequentially."""
        logger.info("🎬 STARTING COMPLETE GEOMETRY VIDEO GENERATION PIPELINE")
        logger.info(f"📁 Question Image: {self.question_image_path}")
        logger.info(f"📁 Working Directory: {self.pipeline_dir}")
        logger.info("=" * 80)
        
        # Step 1: Generate solution steps
        if not self.step_1_generate_solution_steps():
            logger.error("❌ Pipeline failed at Step 1")
            return False
        
        # Step 2: Generate audio files
        if not self.step_2_generate_audio():
            logger.error("❌ Pipeline failed at Step 2")
            return False
        
        # Step 3: Generate geometric pipeline
        if not self.step_3_generate_geometry_pipeline():
            logger.error("❌ Pipeline failed at Step 3")
            return False
        
        # Step 4: Generate video code
        if not self.step_4_generate_video_code():
            logger.error("❌ Pipeline failed at Step 4")
            return False
        
        # Step 5: Render final video
        if not self.step_5_render_final_video():
            logger.error("❌ Pipeline failed at Step 5")
            return False
        
        # Extract token usage from metadata files
        self.extract_token_usage_from_metadata_files()
        
        # Pipeline completed successfully
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        logger.info("=" * 80)
        logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info(f"📊 Total Pipeline Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
        
        # Log comprehensive token usage
        logger.info("📊 COMPREHENSIVE TOKEN USAGE SUMMARY:")
        logger.info("-" * 50)
        logger.info(f"🔢 TOTAL TOKENS ACROSS ALL STEPS:")
        logger.info(f"   • Prompt Tokens: {self.token_usage['total']['prompt_tokens']:,}")
        logger.info(f"   • Completion Tokens: {self.token_usage['total']['completion_tokens']:,}")
        logger.info(f"   • Total Tokens: {self.token_usage['total']['total_tokens']:,}")
        logger.info("")
        
        logger.info(f"🤖 TOKENS BY AI MODEL:")
        for model, tokens in self.token_usage["by_model"].items():
            if tokens["total_tokens"] > 0:
                logger.info(f"   • {model.upper()}: {tokens['total_tokens']:,} tokens")
                logger.info(f"     - Input: {tokens['prompt_tokens']:,}, Output: {tokens['completion_tokens']:,}")
        logger.info("")
        
        logger.info(f"📋 TOKENS BY STEP:")
        for step, tokens in self.token_usage["by_step"].items():
            if tokens["total_tokens"] > 0:
                logger.info(f"   • {step}: {tokens['total_tokens']:,} tokens")
                logger.info(f"     - Input: {tokens['prompt_tokens']:,}, Output: {tokens['completion_tokens']:,}")
        logger.info("")
        
        # Print final summary to terminal
        print("\n" + "=" * 80)
        print("🎯 FINAL TOKEN USAGE SUMMARY")
        print("=" * 80)
        print(f"📊 TOTAL TOKENS: {self.token_usage['total']['total_tokens']:,}")
        print(f"   • Input Tokens: {self.token_usage['total']['prompt_tokens']:,}")
        print(f"   • Output Tokens: {self.token_usage['total']['completion_tokens']:,}")
        print("")
        
        print("🤖 TOKENS BY AI MODEL:")
        for model, tokens in self.token_usage["by_model"].items():
            if tokens["total_tokens"] > 0:
                print(f"   • {model.upper()}: {tokens['total_tokens']:,} tokens")
                print(f"     - Input: {tokens['prompt_tokens']:,}, Output: {tokens['completion_tokens']:,}")
        print("")
        
        print("📋 TOKENS BY STEP:")
        for step, tokens in self.token_usage["by_step"].items():
            if tokens["total_tokens"] > 0:
                print(f"   • {step}: {tokens['total_tokens']:,} tokens")
                print(f"     - Input: {tokens['prompt_tokens']:,}, Output: {tokens['completion_tokens']:,}")
        print("=" * 80)
        
        logger.info(f"📁 Final Video: {self.pipeline_dir}/final_geometry_video.mp4")
        logger.info(f"📁 Log File: {self.pipeline_dir}/pipeline.log")
        logger.info("=" * 80)
        
        # Save token usage to JSON file
        self.save_token_usage_report()
        
        return True
    
    def save_token_usage_report(self):
        """Save comprehensive token usage report to JSON file."""
        try:
            import json
            report = {
                "pipeline_info": {
                    "question_image": self.question_image_path,
                    "total_duration_seconds": time.time() - self.start_time,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "token_usage": self.token_usage
            }
            
            report_file = "pipeline_token_usage_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"📊 Token usage report saved to: {report_file}")
            
        except Exception as e:
            logger.warning(f"Could not save token usage report: {e}")

def main():
    """Main function to run the terminal pipeline."""
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(
        description="Complete Geometry Video Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python terminal_pipeline.py --question-image "Math Questions/question_1.png"
  python terminal_pipeline.py --question-image "/path/to/your/question_image.png"
        """
    )
    
    parser.add_argument(
        "--question-image",
        required=True,
        help="Path to the question image file (required)"
    )
    
    args = parser.parse_args()
    
    # Validate question image exists
    if not os.path.exists(args.question_image):
        print(f"❌ Question image file not found: {args.question_image}")
        sys.exit(1)
    
    # Initialize and run pipeline
    try:
        pipeline = TerminalPipeline(args.question_image)
        success = pipeline.run_pipeline()
        
        if success:
            print("\n🎉 Pipeline completed successfully!")
            print(f"📹 Final video: {pipeline.pipeline_dir}/final_geometry_video.mp4")
            sys.exit(0)
        else:
            print("\n❌ Pipeline failed. Check the log file for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
