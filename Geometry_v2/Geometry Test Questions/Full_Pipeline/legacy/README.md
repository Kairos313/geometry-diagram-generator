# Geometry Video Generation Pipeline

A comprehensive AI-powered pipeline for generating educational geometry videos with step-by-step solutions, animations, and audio narration. This project uses Claude-4-Sonnet and Gemini-2.5-Pro to create professional-quality educational content.

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Solomon-Learning-Group/math-video-generator.git
cd math-video-generator
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up API Keys
Create a `.env` file in the root directory:
```bash
# Required API Keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional: Additional AI Services
OPENAI_API_KEY=your_openai_api_key_here
```

### 4. Run the Complete Pipeline
```bash
python terminal_pipeline.py --question-image "Math Questions/question_7.png"
```

## 📁 Project Structure

```
math-video-generator/
├── README.md                                    # This comprehensive documentation
├── terminal_pipeline.py                         # Main pipeline orchestrator
├── generate_solution_steps.py                   # Step 1: Solution analysis
├── geo_scriptwriter_parallel.py                # Step 2: Audio generation
├── integrated_geometry_pipeline.py              # Step 3: Geometry processing
├── video_claude.py                             # Step 4: Video code generation
├── render_and_concatenate_scenes.py            # Step 5: Final video rendering
├── pipeline_prompts.py                          # AI prompt templates
├── functions.py                                 # Utility functions
├── add_geometric_elements.py                    # Geometry element utilities
├── .env                                         # API key configuration (create this)
├── requirements.txt                             # Python dependencies
├── Math Questions/                              # Input question images
├── video_examples/                              # Sample output videos
├── media/                                       # Media assets
└── math_solution_pipeline/                      # Generated solution files
```

## 🔧 Individual Scripts Explained

### Core Pipeline Scripts

#### 1. `terminal_pipeline.py` - Main Orchestrator
**Purpose**: Coordinates the entire 5-step pipeline process
**What it does**:
- Runs all scripts in sequence with validation
- Tracks token usage and costs
- Provides comprehensive logging
- Generates final video output

**Usage**:
```bash
python terminal_pipeline.py --question-image "path/to/question.png"
```

#### 2. `generate_solution_steps.py` - Step 1
**Purpose**: Analyzes geometry questions and generates solution steps
**What it does**:
- Uses Gemini-2.5-Pro to analyze question images
- Generates detailed solution steps using **Solution_Steps_v3** prompt
- Creates structured JSON output with Khan Academy-style explanations
- **Token Usage**: ~13,500 tokens per question

**Prompt Used**: `Solution_Steps_v3` - Expert math tutor prompt that generates:
- Comprehensive solution breakdown with LaTeX mathematical notation
- Khan Academy-style pedagogical text (limited to 4 minutes voiceover)
- Geometric elements mapping for animations
- Structured JSON with step-by-step explanations

**Outputs**:
- `math_solution_pipeline/math_solution_standard.json`
- `math_solution_pipeline/math_solution_verbose.json`

#### 3. `geo_scriptwriter_parallel.py` - Step 2
**Purpose**: Generates audio narration and timing data
**What it does**:
- Converts solution steps to natural language
- Generates audio files using ElevenLabs
- Creates timing synchronization data
- Processes audio in parallel for efficiency

**Outputs**:
- `Audio/` directory with individual audio files
- `Scene/` directory with scene audio files
- `geometric_elements_with_timing.json`

#### 4. `integrated_geometry_pipeline.py` - Step 3
**Purpose**: Creates geometric blueprints and Manim code
**What it does**:
- Analyzes geometry problems using **Geometry_Blueprint_v2** prompt (Step 1)
- Generates precise coordinate systems and geometric calculations
- Creates Manim-compatible code using **Enhanced_Manim_Geometric_Surveyor_v2** prompt (Step 2)
- **Token Usage**: ~14,800 tokens per question

**Prompts Used**: 
- **Step 1**: `Geometry_Blueprint_v2` - Computational geometry engine that:
  - Extracts geometric context from solution JSON
  - Performs precise coordinate calculations (3 decimal places)
  - Generates complete geometric blueprints with point coordinates
  - Maps animation sequences to solution steps
  - Handles multi-part problems with independent blueprints
- **Step 2**: `Enhanced_Manim_Geometric_Surveyor_v2` - Manim Cinematic Surveyor that:
  - Translates geometric blueprints into visual Manim representations
  - Generates pedagogically clear and mathematically precise diagrams
  - Creates static Python functions and classes for each solution step
  - Handles both 2D (Scene) and 3D (ThreeDScene) workflows

**Outputs**:
- `coordinates.txt` - Complete geometric blueprint with coordinates
- `figure.py` - Manim-compatible geometric functions

#### 5. `video_claude.py` - Step 4
**Purpose**: Generates comprehensive Manim scenes
**What it does**:
- Uses Claude-4-Sonnet with **ENHANCED_CODE_GENERATION_PROMPT_v4** prompt
- Creates detailed animation sequences with cinematic precision
- Integrates audio timing and pedagogical clarity
- **Token Usage**: ~33,600 tokens per question

**Prompt Used**: `ENHANCED_CODE_GENERATION_PROMPT_v4` - Advanced Manim code generation that:
- Analyzes JSON timing data during code generation
- Generates pure Manim code with no external dependencies
- Hardcodes all timing using exact `self.wait()` calls
- Hardcodes all content (text, animations, audio paths)
- Creates one class per solution step
- Maintains sentence structure with helper functions

**Outputs**:
- `all_scenes.py` - Complete Manim scene classes for all solution steps
- `all_scenes_metadata.json` - Scene metadata and timing information

#### 6. `render_and_concatenate_scenes.py` - Step 5
**Purpose**: Renders final video with audio
**What it does**:
- Renders Manim scenes to video
- Synchronizes audio with video
- Concatenates all scenes
- Creates final MP4 output

**Outputs**:
- `final_geometry_video.mp4`

### Supporting Scripts

#### `pipeline_prompts.py`
**Purpose**: Contains all AI prompt templates
**Size**: 274KB with 5,016 lines
**What it contains**:
- **Solution_Steps_v3**: Expert math tutor prompt for solution generation (Step 1)
- **Geometry_Blueprint_v2**: Computational geometry engine for coordinate calculations (Step 3a)
- **Enhanced_Manim_Geometric_Surveyor_v2**: Manim cinematic surveyor for scene generation (Step 3b)
- **ENHANCED_CODE_GENERATION_PROMPT_v4**: Advanced code generation with helper functions (Step 4)
- Educational content templates with LaTeX mathematical notation
- Geometry-specific instructions and animation mappings

**Note on Prompt Versions**: 
- **Geometry_Blueprint_v3/v4** and **Enhanced_Manim_Geometric_Surveyor_v3/v4** were attempts to include coordinate geometry questions
- These versions did not work as intended and would require additional development work
- The current pipeline uses the stable v2 versions which work reliably for standard geometry problems

#### `functions.py`
**Purpose**: Utility functions for the pipeline
**Size**: 28KB with 705 lines
**What it contains**:
- File processing utilities
- Audio/video manipulation functions
- Geometry calculation helpers

#### `add_geometric_elements.py`
**Purpose**: Geometry element utilities
**What it does**:
- Adds geometric shapes and elements
- Handles coordinate transformations
- Manages visual elements

## 📊 Performance Metrics

### Time Requirements
- **Total Pipeline Duration**: ~8-10 minutes per question
- **Step 1 (Solution Analysis)**: ~2-3 minutes
- **Step 2 (Audio Generation)**: ~1-2 minutes
- **Step 3 (Geometry Processing)**: ~2-3 minutes
- **Step 4 (Video Code Generation)**: ~2-3 minutes
- **Step 5 (Final Rendering)**: ~1-2 minutes

### Token Usage (Per Question)
- **Total Tokens**: ~95,600 tokens
- **Input Tokens**: ~37,300 tokens
- **Output Tokens**: ~24,700 tokens

**Breakdown by Step**:
- Step 1 (Gemini-2.5-Pro): 13,538 tokens
- Step 3 (Claude-4-Sonnet): 14,782 tokens
- Step 4 (Claude-4-Sonnet): 33,642 tokens
- Step 5 (Rendering): No tokens (local processing)

### Cost Estimates
**Note**: Costs based on current OpenRouter API pricing

**OpenRouter API Costs**:
- Claude-4-Sonnet: $3.00 per 1M input tokens, $15.00 per 1M output tokens
- Gemini-2.5-Pro: $1.25 per 1M input tokens, $10.00 per 1M output tokens

**Estimated Cost per Question**:
- **Claude-4-Sonnet**: ~$0.11 (input) + ~$0.37 (output) = ~$0.48
- **Gemini-2.5-Pro**: ~$0.006 (input) + ~$0.087 (output) = ~$0.093
- **ElevenLabs**: ~$0.50-1.00
- **Total Estimated Cost**: ~$1.07-1.57 per question

## 🎯 Usage Examples

### Basic Usage
```bash
# Run complete pipeline
python terminal_pipeline.py --question-image "Math Questions/question_7.png"
```

### Individual Steps
```bash
# Step 1: Generate solution steps
python generate_solution_steps.py --question-image "Math Questions/question_7.png"

# Step 2: Generate audio
python geo_scriptwriter_parallel.py

# Step 3: Generate geometry pipeline
python integrated_geometry_pipeline.py --question-image "Math Questions/question_7.png"

# Step 4: Generate video code
python video_claude.py --question-image "Math Questions/question_7.png"

# Step 5: Render final video
python render_and_concatenate_scenes.py

# For higher quality videos:
python render_and_concatenate_scenes.py --quality qm  # 720p30
python render_and_concatenate_scenes.py --quality qh  # 1080p60
```

## 📹 Output Specifications

### Video Output
- **Format**: MP4 (H.264)
- **Default Resolution**: 480p (854x480) at 15 FPS
- **Quality Options**:
  - `ql` (Low): 480p15 - Fastest rendering, smallest file size
  - `qm` (Medium): 720p30 - Balanced speed and quality
  - `qh` (High): 1080p60 - Best quality, slower rendering
- **Duration**: 2-5 minutes (depending on question complexity)
- **File Size**: 3-15 MB (varies by quality)
- **Quality**: Optimized for educational content with clear geometry visualization

### Audio Output
- **Format**: MP3
- **Quality**: High-quality narration
- **Voice**: Professional educational voice
- **Synchronization**: Perfectly timed with video animations

## 🔑 API Key Setup

### Required API Keys

#### 1. OpenRouter API Key
- **Purpose**: Access to Claude-4-Sonnet and Gemini-2.5-Pro
- **Get it from**: https://openrouter.ai/
- **Cost**: Pay-per-token usage
- **Required for**: Steps 1, 3, and 4

#### 2. ElevenLabs API Key
- **Purpose**: Text-to-speech functionality
- **Get it from**: https://elevenlabs.io/
- **Cost**: Pay-per-character usage
- **Required for**: Step 2

### Security Notes
- **Never commit the `.env` file** to version control
- **Keep your API keys secure** and don't share them
- **Use environment variables** in production deployments
- **Rotate API keys regularly** for security


## 📦 Installation

### 1. Clone Repository
```bash
git clone https://github.com/Solomon-Learning-Group/math-video-generator.git
cd math-video-generator
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up API Keys
```bash
# Create .env file
cp .env.example .env
# Edit .env file with your actual API keys
```

### 5. Test Installation
```bash
# Test API connection
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print('OpenRouter API Key loaded:', 'OPENROUTER_API_KEY' in os.environ)"
```

## 🎬 Sample Videos

The repository includes several sample videos demonstrating the pipeline's capabilities:

### Video Examples Directory
Check the `video_examples/` directory for sample outputs:
- `final_geometry_video_question_1.mp4` (6.4MB) - Basic geometry problem
- `final_geometry_video_question_2.mp4` (3.8MB) - Intermediate geometry problem  
- `final_geometry_video_with_pauses.mp4` (10MB) - Advanced problem with pauses

### Root Directory Samples
Additional sample videos in the main directory:
- `final_geometry_video.mp4` (2.9MB) - Latest generated video
- `final_geometry_video_questionz-7.mp4` (2.9MB) - Question 7 example
- `final_geometry_video_question_1_2.mp4` (6.4MB) - Combined questions 1 & 2
- `final_geometry_video_audio_sped_up.mp4` (6.3MB) - Audio-optimized version

**All videos are generated at 480p resolution with 15 FPS for optimal educational viewing.**

### Video Embedding in GitHub README
Unfortunately, GitHub README files do not support direct video embedding or playback. However, you can:

1. **Link to Videos**: Add direct links to the video files in the repository
2. **Create Video Previews**: Use GIFs or screenshots as previews
3. **External Hosting**: Host videos on platforms like YouTube and embed links
4. **Download Instructions**: Provide clear instructions for downloading and viewing

**Example Video Links**:
```markdown
- [Question 1 Video](video_examples/final_geometry_video_question_1.mp4) (6.4MB)
- [Question 2 Video](video_examples/final_geometry_video_question_2.mp4) (3.8MB)
- [Advanced Problem Video](video_examples/final_geometry_video_with_pauses.mp4) (10MB)
```

**Note**: Users will need to download the video files to view them, as GitHub only displays static content in README files.

## 🔍 Troubleshooting

### Common Issues

#### 1. Pipeline Failure
If `terminal_pipeline.py` fails, try running each step individually:
```bash
# Step 1: Generate solution steps
python generate_solution_steps.py --question-image "Math Questions/question_7.png"

# Step 2: Generate audio
python geo_scriptwriter_parallel.py

# Step 3: Generate geometry pipeline
python integrated_geometry_pipeline.py --question-image "Math Questions/question_7.png"

# Step 4: Generate video code
python video_claude.py --question-image "Math Questions/question_7.png"

# Step 5: Render final video
python render_and_concatenate_scenes.py
```

#### 2. API Key Errors
```bash
Error: OPENROUTER_API_KEY environment variable not set
```
**Solution**: Ensure your `.env` file exists and contains valid API keys

#### 3. Import Errors
```bash
ModuleNotFoundError: No module named 'manim'
```
**Solution**: Install all dependencies with `pip install -r requirements.txt`

#### 4. Audio Generation Failures
```bash
ElevenLabs API Error
```
**Solution**: Check your ElevenLabs API key and account balance

#### 5. Video Rendering Issues
```bash
FFmpeg not found
```
**Solution**: Install FFmpeg on your system

### Getting Help
- Check the `pipeline.log` file for detailed error information
- Review the token usage report in `pipeline_token_usage_report.json`
- Ensure all API keys are properly configured

## 📈 Advanced Usage

### Custom Prompts
Edit `pipeline_prompts.py` to customize AI prompts for your specific needs.

### Batch Processing
Create a script to process multiple questions:
```bash
for question in Math\ Questions/*.png; do
    python terminal_pipeline.py --question-image "$question"
done
```

### Quality Settings
Adjust video quality using command-line options:
```bash
# Default quality (480p15)
python render_and_concatenate_scenes.py

# Medium quality (720p30)
python render_and_concatenate_scenes.py --quality qm

# High quality (1080p60)
python render_and_concatenate_scenes.py --quality qh
```

**Quality Trade-offs**:
- **ql (Low)**: Fastest rendering, smallest files, suitable for testing
- **qm (Medium)**: Balanced performance, good for most educational content
- **qh (High)**: Best quality, larger files, longer rendering time

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Claude-4-Sonnet** by Anthropic for advanced reasoning
- **Gemini-2.5-Pro** by Google for multimodal analysis
- **ElevenLabs** for high-quality text-to-speech
- **Manim** community for mathematical animations
- **OpenRouter** for unified AI model access

---

**Ready to create amazing geometry videos? Start with the Quick Start guide above!** 🎬✨
