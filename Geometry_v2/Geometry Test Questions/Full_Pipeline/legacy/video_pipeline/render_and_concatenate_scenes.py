#!/usr/bin/env python3
"""
Render and Concatenate All Scenes Script

This script automatically:
1. Reads all scene class names from all_scenes.py in the order they appear
2. Renders each scene sequentially using Manim with -ql quality (480p15)
3. Concatenates all rendered videos using MoviePy with synchronized audio
4. Saves the final video as final_geometry_video.mp4 with proper audio-video sync
5. Opens the final video in default media player for preview

Usage: python render_and_concatenate_scenes.py
"""

import subprocess
import sys
import os
import re
import ast
from pathlib import Path
from typing import List, Tuple

# MoviePy imports for video processing
try:
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, ColorClip
    MOVIEPY_AVAILABLE = True
    print("✅ MoviePy successfully imported")
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    print(f"⚠️  MoviePy not found. Install with: pip install moviepy. Error: {e}")

class SceneRenderer:
    def __init__(self, scenes_file: str = "all_scenes.py", quality: str = "ql"):
        self.scenes_file = scenes_file
        self.current_quality = quality
        self.script_dir = Path(__file__).parent
        self.media_dir = self.script_dir / "media"
        self.scene_dir = self.script_dir / "Scene"
        self.output_video = self.script_dir / "final_geometry_video.mp4"
        
        # Ensure we're in the correct directory
        os.chdir(self.script_dir)
        
    def extract_scene_classes(self) -> List[str]:
        """
        Extract scene class names from all_scenes.py in the order they appear.
        Returns a list of scene class names.
        """
        print("🔍 Extracting scene classes from all_scenes.py...")
        
        try:
            with open(self.scenes_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all class definitions that inherit from Scene or ThreeDScene
            scene_pattern = r'class\s+(\w+Scene)\s*\((?:Scene|ThreeDScene)\):'
            matches = re.findall(scene_pattern, content)
            
            if not matches:
                raise ValueError("No scene classes found in all_scenes.py")
            
            print(f"✅ Found {len(matches)} scene classes:")
            for i, scene in enumerate(matches, 1):
                print(f"   {i}. {scene}")
            
            return matches
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Scene file not found: {self.scenes_file}")
        except Exception as e:
            raise Exception(f"Error reading scene file: {e}")
    
    def render_scene(self, scene_name: str, quality: str = "ql") -> Tuple[str, bool]:
        """
        Render a single scene using Manim with specified quality.
        Quality options: ql (480p15), qm (720p30), qh (1080p60)
        Returns (scene_name, success_status).
        """
        print(f"🎬 Starting render for {scene_name} with quality: {quality}...")
        
        try:
            # Run manim command with specified quality and disable caching to prevent conflicts
            cmd = [
                'manim', f'-q{quality}', '--disable_caching', self.scenes_file, scene_name
            ]
            
            print(f"   Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.script_dir
            )
            
            if result.returncode == 0:
                print(f"✅ Successfully rendered {scene_name}")
                return scene_name, True
            else:
                print(f"❌ Failed to render {scene_name}")
                print(f"   Error output: {result.stderr}")
                return scene_name, False
                
        except FileNotFoundError:
            print(f"❌ Manim not found. Please install Manim: pip install manim")
            return scene_name, False
        except Exception as e:
            print(f"❌ Error rendering {scene_name}: {e}")
            return scene_name, False
    
    def render_scenes_sequentially(self, scene_names: List[str], quality: str = "ql") -> List[Tuple[str, bool]]:
        """
        Render multiple scenes sequentially (one after another).
        Quality options: ql (480p15), qm (720p30), qh (1080p60)
        Returns list of (scene_name, success_status) tuples.
        Stops the entire process if any scene fails.
        """
        print(f"\n🎬 Rendering {len(scene_names)} scenes sequentially with quality: {quality}...")
        print("-" * 40)
        
        results = []
        
        for i, scene_name in enumerate(scene_names, 1):
            print(f"\n📹 Scene {i}/{len(scene_names)}: {scene_name}")
            print("-" * 30)
            
            try:
                result = self.render_scene(scene_name, quality)
                results.append(result)
                
                # Check if this scene failed
                if not result[1]:  # result[1] is the success status
                    print(f"❌ Scene {scene_name} failed. Stopping all renders...")
                    return results  # Return partial results, will be handled in main loop
                    
            except Exception as e:
                print(f"❌ Exception in {scene_name}: {e}")
                results.append((scene_name, False))
                return results  # Return partial results, will be handled in main loop
        
        return results
    
    def find_rendered_video(self, scene_name: str) -> str:
        """
        Find the rendered video file for a scene.
        Returns the path to the video file.
        """
        # Manim creates videos in media/videos/scenes_file_name/quality/
        # The filename is typically scene_name.mp4
        
        # Look for the video file in the media directory with quality-specific patterns
        quality_map = {
            "ql": "480p15",
            "qm": "720p30", 
            "qh": "1080p60"
        }
        
        # Get the quality directory name
        quality_dir = quality_map.get(self.current_quality, "480p15")
        
        video_patterns = [
            self.media_dir / "videos" / self.scenes_file.replace('.py', '') / quality_dir / f"{scene_name}.mp4",
            self.media_dir / "videos" / self.scenes_file.replace('.py', '') / "480p15" / f"{scene_name}.mp4",
            self.media_dir / "videos" / self.scenes_file.replace('.py', '') / "720p30" / f"{scene_name}.mp4",
            self.media_dir / "videos" / self.scenes_file.replace('.py', '') / "1080p60" / f"{scene_name}.mp4",
        ]
        
        for pattern in video_patterns:
            if pattern.exists():
                return str(pattern)
        
        # If not found with standard patterns, search recursively
        for video_file in self.media_dir.rglob(f"{scene_name}.mp4"):
            return str(video_file)
        
        raise FileNotFoundError(f"Rendered video not found for {scene_name}")
    
    def find_audio_file(self, scene_name: str) -> str:
        """
        Find the corresponding audio file for a scene.
        Returns the path to the audio file.
        """
        # Convert scene name to expected audio filename
        # e.g., PartAFindAngleXwyScene -> part_a_find_angle_xwy_scene.mp3
        scene_name_lower = scene_name.lower()
        
        # Handle specific naming patterns
        if "partafindanglexwy" in scene_name_lower:
            audio_filename = "part_a_find_angle_xwy_scene.mp3"
        elif "partbdihedralangle" in scene_name_lower:
            audio_filename = "part_b_dihedral_angle_scene.mp3"
        elif "keytakeaways" in scene_name_lower:
            audio_filename = "key_takeaways_scene.mp3"
        else:
            # Generic fallback: convert camelCase to snake_case
            import re
            audio_filename = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', scene_name).lower() + "_scene.mp3"
        
        audio_path = self.scene_dir / audio_filename
        
        if audio_path.exists():
            return str(audio_path)
        else:
            print(f"⚠️  Audio file not found: {audio_path}")
            return None
    
    def create_concat_list(self, video_files: List[str]) -> str:
        """
        Create a temporary file list for ffmpeg concatenation.
        Returns the path to the temporary file list.
        """
        concat_list_path = self.script_dir / "concat_list.txt"
        
        with open(concat_list_path, 'w') as f:
            for video_file in video_files:
                # Escape single quotes and backslashes for ffmpeg
                escaped_path = video_file.replace("'", "'\"'\"'").replace("\\", "\\\\")
                f.write(f"file '{escaped_path}'\n")
        
        print(f"📝 Created concat list: {concat_list_path}")
        return str(concat_list_path)
    
    def create_black_screen_pause(self, duration: float = 2.0) -> VideoFileClip:
        """
        Create a black screen pause clip with specified duration.
        Returns a VideoFileClip with black screen and no audio.
        """
        # Create a black screen clip (slightly softer black: #0C0C0C)
        black_clip = ColorClip(
            size=(854, 480),  # 480p resolution (854x480)
            color=(12, 12, 12),  # RGB values for #0C0C0C
            duration=duration
        )
        
        # Set the frame rate to match the original videos (15 fps)
        black_clip = black_clip.with_fps(15)
        
        return black_clip
    
    def concatenate_videos_with_moviepy(self, scene_names: List[str], video_files: List[str]) -> bool:
        """
        Concatenate videos using MoviePy with synchronized audio.
        Returns True if successful, False otherwise.
        """
        if not MOVIEPY_AVAILABLE:
            print("❌ MoviePy not available. Please install: pip install moviepy")
            return False
        
        print(f"🎬 Concatenating videos with MoviePy...")
        print("🎵 Synchronizing audio with video timing...")
        
        try:
            video_clips = []
            
            for i, (scene_name, video_path) in enumerate(zip(scene_names, video_files)):
                print(f"   📹 Processing scene {i+1}/{len(scene_names)}: {scene_name}")
                
                # Load video clip
                video_clip = VideoFileClip(video_path)
                
                # Find and load corresponding audio file
                audio_path = self.find_audio_file(scene_name)
                if audio_path:
                    print(f"      🎵 Found audio: {os.path.basename(audio_path)}")
                    audio_clip = AudioFileClip(audio_path)
                    
                    # Synchronize video with audio duration by adjusting video playback speed
                    if audio_clip.duration != video_clip.duration:
                        # Calculate speed factor to match audio duration
                        speed_factor = video_clip.duration / audio_clip.duration
                        
                        # Check speed limits (max 1.5x, min 0.75x)
                        if speed_factor > 1.5:
                            print(f"      ❌ Video speed adjustment too extreme: {speed_factor:.3f}x (max: 1.5x)")
                            print(f"         Video: {video_clip.duration:.2f}s, Audio: {audio_clip.duration:.2f}s")
                            print(f"         Stopping process due to excessive speed adjustment required.")
                            return False
                        elif speed_factor < 0.75:
                            print(f"      ❌ Video speed adjustment too extreme: {speed_factor:.3f}x (min: 0.75x)")
                            print(f"         Video: {video_clip.duration:.2f}s, Audio: {audio_clip.duration:.2f}s")
                            print(f"         Stopping process due to excessive speed adjustment required.")
                            return False
                        
                        if video_clip.duration > audio_clip.duration:
                            print(f"      ⏱️  Speeding up video: {video_clip.duration:.2f}s → {audio_clip.duration:.2f}s (speed: {speed_factor:.3f}x)")
                            # Speed up video to match audio duration
                            video_clip = video_clip.with_speed_scaled(speed_factor)
                        else:
                            print(f"      ⏱️  Slowing down video: {video_clip.duration:.2f}s → {audio_clip.duration:.2f}s (speed: {speed_factor:.3f}x)")
                            # Slow down video to match audio duration
                            video_clip = video_clip.with_speed_scaled(speed_factor)
                    else:
                        print(f"      ⏱️  Video and audio durations match perfectly: {video_clip.duration:.2f}s")
                    
                    # Set the audio for the video clip
                    video_clip = video_clip.with_audio(audio_clip)
                else:
                    print(f"      ⚠️  No audio file found for {scene_name}")
                
                video_clips.append(video_clip)
            
            # Add black screen pauses between scenes
            print(f"\n⏸️  Adding 2-second black screen pauses between scenes...")
            final_clips = []
            
            for i, clip in enumerate(video_clips):
                # Add the scene clip
                final_clips.append(clip)
                
                # Add black screen pause after each scene (except the last one)
                if i < len(video_clips) - 1:
                    black_pause = self.create_black_screen_pause(2.0)
                    final_clips.append(black_pause)
                    print(f"   📹 Added 2s pause after scene {i+1}")
            
            # Concatenate all clips (scenes + pauses)
            print(f"\n🎬 Concatenating {len(final_clips)} clips ({len(video_clips)} scenes + {len(video_clips)-1} pauses)...")
            final_video = concatenate_videoclips(final_clips, method="compose")
            
            # Write the final video
            print(f"💾 Writing final video: {self.output_video}")
            final_video.write_videofile(
                str(self.output_video),
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset='ultrafast',  # Faster encoding
                threads=4  # Use more CPU cores
            )
            
            # Clean up video clips to free memory
            for clip in video_clips:
                clip.close()
            for clip in final_clips:
                clip.close()
            final_video.close()
            
            print(f"✅ Successfully created final video: {self.output_video}")
            return True
            
        except Exception as e:
            print(f"❌ Error concatenating videos with MoviePy: {e}")
            return False
    
    def concatenate_videos_with_ffmpeg(self, video_files: List[str]) -> bool:
        """
        Fallback: Concatenate videos using ffmpeg (original method).
        Returns True if successful, False otherwise.
        """
        print(f"🎬 Concatenating videos with ffmpeg (fallback)...")
        
        try:
            # Check if ffmpeg is available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ FFmpeg not found. Please install FFmpeg:")
            print("   macOS: brew install ffmpeg")
            print("   Ubuntu: sudo apt install ffmpeg")
            print("   Windows: Download from https://ffmpeg.org/download.html")
            return False
        
        try:
            # Create concat list
            concat_list_path = self.create_concat_list(video_files)
            
            # Run ffmpeg command with simple stream copy (no re-encoding)
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list_path,
                '-c', 'copy',            # Copy both video and audio streams without re-encoding
                str(self.output_video),
                '-y'  # Overwrite output file if it exists
            ]
            
            print(f"   Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.script_dir
            )
            
            # Clean up temp file
            self.cleanup_temp_files(concat_list_path)
            
            if result.returncode == 0:
                print(f"✅ Successfully created final video: {self.output_video}")
                return True
            else:
                print(f"❌ Failed to concatenate videos")
                print(f"   Error output: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error concatenating videos with ffmpeg: {e}")
            return False
    
    def cleanup_temp_files(self, concat_list_path: str):
        """Clean up temporary files."""
        try:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)
                print(f"🧹 Cleaned up: {concat_list_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up {concat_list_path}: {e}")
    
    def preview_final_video(self):
        """Preview the final concatenated video."""
        try:
            if not os.path.exists(self.output_video):
                print(f"❌ Final video not found: {self.output_video}")
                return False
            
            print(f"🎬 Previewing final video: {self.output_video}")
            
            # Use system default video player
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(self.output_video)])
            elif sys.platform == "win32":  # Windows
                subprocess.run(["start", str(self.output_video)], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(self.output_video)])
            
            print(f"✅ Video opened in default player")
            return True
            
        except Exception as e:
            print(f"❌ Error previewing video: {e}")
            return False
    
    def run(self):
        """Main execution function."""
        print("🚀 Starting scene rendering and concatenation pipeline...")
        print("📹 Reading scene classes from all_scenes.py, rendering sequentially, concatenating in file order")
        print("=" * 60)
        
        try:
            # Step 1: Extract scene classes from all_scenes.py in order
            scene_classes = self.extract_scene_classes()
            
            # Step 2: Render scenes sequentially
            render_results = self.render_scenes_sequentially(scene_classes, self.current_quality)
            
            # Step 3: Check if all scenes rendered successfully
            print(f"\n📹 Checking render results...")
            failed_scenes = []
            rendered_videos = []
            
            for scene_name in scene_classes:
                # Find the render result for this scene
                render_result = None
                for result_scene, success in render_results:
                    if result_scene == scene_name:
                        render_result = (result_scene, success)
                        break
                
                if render_result and render_result[1]:  # Success
                    try:
                        video_path = self.find_rendered_video(scene_name)
                        rendered_videos.append(video_path)
                        print(f"   ✅ {scene_name} -> {video_path}")
                    except FileNotFoundError as e:
                        print(f"   ❌ {e}. Scene {scene_name} failed.")
                        failed_scenes.append(scene_name)
                else:
                    print(f"   ❌ Failed to render {scene_name}.")
                    failed_scenes.append(scene_name)
            
            # Stop the entire process if any scene failed
            if failed_scenes:
                print(f"\n❌ {len(failed_scenes)} scenes failed to render:")
                for scene in failed_scenes:
                    print(f"   - {scene}")
                print("❌ Stopping entire process. All scenes must render successfully.")
                return False
            
            if not rendered_videos:
                print("❌ No videos were successfully rendered. Stopping execution.")
                return False
            
            # Step 4: Concatenate videos (try MoviePy first, fallback to ffmpeg)
            print(f"\n🎬 Concatenating {len(rendered_videos)} videos...")
            print("🎵 Attempting MoviePy with audio synchronization...")
            print("-" * 40)
            
            # Try MoviePy first for audio synchronization
            if MOVIEPY_AVAILABLE:
                if self.concatenate_videos_with_moviepy(scene_classes, rendered_videos):
                    print("✅ MoviePy concatenation successful!")
                else:
                    print("⚠️  MoviePy failed, trying ffmpeg fallback...")
                    if not self.concatenate_videos_with_ffmpeg(rendered_videos):
                        print("❌ Both MoviePy and ffmpeg failed to concatenate videos.")
                        return False
            else:
                print("⚠️  MoviePy not available, using ffmpeg...")
                if not self.concatenate_videos_with_ffmpeg(rendered_videos):
                    print("❌ Failed to concatenate videos with ffmpeg.")
                    return False
            
            # Step 5: Preview final video
            print(f"\n🎬 Previewing final concatenated video...")
            self.preview_final_video()
            
            # Success!
            print("\n" + "=" * 60)
            print("🎉 Pipeline completed successfully!")
            print(f"📹 Final video: {self.output_video}")
            print(f"📊 Total scenes processed: {len(scene_classes)}")
            print(f"📊 Successfully rendered: {len(rendered_videos)}")
            
            # Display quality information
            quality_info = {
                "ql": "480p15 (Low Quality)",
                "qm": "720p30 (Medium Quality)", 
                "qh": "1080p60 (High Quality)"
            }
            print(f"🎬 Individual scenes: -q{self.current_quality} ({quality_info.get(self.current_quality, 'Unknown Quality')})")
            if MOVIEPY_AVAILABLE:
                print(f"🎬 Final video: MoviePy concatenation with synchronized audio")
            else:
                print(f"🎬 Final video: ffmpeg concatenation (no audio sync)")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Pipeline failed with error: {e}")
            return False

def main():
    """Main function."""
    import argparse
    
    # Set up command line argument parser
    parser = argparse.ArgumentParser(
        description="Render and concatenate Manim scenes with quality options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quality Options:
  ql  - Low quality (480p15) - Fastest rendering
  qm  - Medium quality (720p30) - Balanced speed/quality  
  qh  - High quality (1080p60) - Best quality, slower rendering

Examples:
  python render_and_concatenate_scenes.py
  python render_and_concatenate_scenes.py --quality qm
  python render_and_concatenate_scenes.py --quality qh
        """
    )
    
    parser.add_argument(
        "--quality",
        choices=["ql", "qm", "qh"],
        default="ql",
        help="Video quality (default: ql)"
    )
    
    args = parser.parse_args()
    
    renderer = SceneRenderer(quality=args.quality)
    success = renderer.run()
    
    if success:
        print("\n✅ All done! Check the final video file.")
        sys.exit(0)
    else:
        print("\n❌ Pipeline failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
