#!/usr/bin/env python3
"""
Web demo for the Geometry Diagram Pipeline.

Single-file Flask app that shows the full pipeline running in real-time:
  Stage 1 (Gemini) → Blueprint → Stage 2 (Sonnet) → Code → Execute → Diagram

Usage:
    python3 demo.py
    # Opens browser at http://127.0.0.1:5050
"""

import json
import os
import queue
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    render_template_string,
    request,
    send_from_directory,
)

# Ensure pipeline modules are importable
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

load_dotenv(SCRIPT_DIR / ".env")

app = Flask(__name__)

# Active runs: run_id -> queue.Queue
active_runs = {}  # type: Dict[str, queue.Queue]


# ======================================================================
# Pipeline worker (runs in background thread)
# ======================================================================

def pipeline_worker(run_id, question_text, image_path=None):
    # type: (str, str, Optional[str]) -> None
    q = active_runs[run_id]

    def emit(event_type, data):
        q.put((event_type, json.dumps(data, ensure_ascii=False)))

    try:
        _pipeline_worker_inner(run_id, question_text, image_path, emit)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("[pipeline_worker] Unhandled error:\n" + tb)
        emit("error", {"stage": "unknown", "message": str(e) + "\n\n" + tb[-1000:]})
    finally:
        emit("done", {})


def _pipeline_worker_inner(run_id, question_text, image_path, emit):
    # type: (str, str, Optional[str], callable) -> None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        emit("error", {"stage": "init", "message": "GEMINI_API_KEY not set in .env"})
        return

    total_start = time.time()
    run_output_dir = str(SCRIPT_DIR / "output" / run_id)
    os.makedirs(run_output_dir, exist_ok=True)

    # ---- Stage 1: Generate Blueprint ----
    emit("stage_update", {
        "stage": "blueprint",
        "status": "running",
        "message": "Calling Gemini 3 Flash with reasoning...",
    })

    from generate_blueprint import generate_blueprint
    result = generate_blueprint(
        api_key=api_key,
        question_text=question_text,
        output_dir=run_output_dir,
        image_path=image_path,
    )

    if not result["success"]:
        emit("error", {"stage": "blueprint", "message": result.get("error", "Unknown error")})
        return

    emit("stage_update", {
        "stage": "blueprint",
        "status": "done",
        "duration": round(result["api_call_duration"], 1),
        "tokens": {
            "prompt": result["prompt_tokens"],
            "completion": result["completion_tokens"],
            "total": result["total_tokens"],
        },
    })
    emit("blueprint_text", {"text": result["blueprint"]})

    blueprint_text = result["blueprint"]

    # ---- Dimension Detection ----
    from generate_code import detect_dimension, generate_render_code, execute_code

    dimension_type = detect_dimension(blueprint_text)
    emit("stage_update", {
        "stage": "detect_dim",
        "status": "done",
        "dimension": dimension_type,
    })

    # ---- Stage 2: Generate Code ----
    output_format = "png" if dimension_type == "2d" else "gif"
    output_filename = "diagram.{}".format(output_format)
    output_path = str(Path(run_output_dir) / output_filename)
    target_lib = "matplotlib" if dimension_type == "2d" else "manim"

    emit("stage_update", {
        "stage": "codegen",
        "status": "running",
        "message": "Calling Gemini 3 Flash for {} code...".format(target_lib),
    })

    print("[worker] Calling generate_render_code...")
    code_result = generate_render_code(
        api_key=api_key,
        blueprint_text=blueprint_text,
        output_path=output_path,
        output_format=output_format,
        dimension_type=dimension_type,
        question_text=question_text,
    )
    print("[worker] generate_render_code returned, success={}".format(code_result.get("success")))

    if not code_result["success"]:
        emit("error", {"stage": "codegen", "message": code_result.get("error", "Unknown error")})
        return

    emit("stage_update", {
        "stage": "codegen",
        "status": "done",
        "duration": round(code_result["api_call_duration"], 1),
        "tokens": {
            "prompt": code_result["prompt_tokens"],
            "completion": code_result["completion_tokens"],
            "total": code_result["total_tokens"],
        },
    })
    emit("generated_code", {"code": code_result["code"]})

    # ---- Write & Execute Code ----
    code_path = str(Path(run_output_dir) / "render_code.py")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code_result["code"])

    emit("stage_update", {
        "stage": "execute",
        "status": "running",
        "message": "Executing render_code.py...",
    })

    timeout = 300 if dimension_type == "3d" else 120
    exec_result = execute_code(code_path, timeout=timeout)

    emit("execution_output", {
        "stdout": exec_result["stdout"],
        "stderr": exec_result["stderr"],
        "returncode": exec_result["returncode"],
    })

    if exec_result["success"] and Path(output_path).exists():
        emit("stage_update", {"stage": "execute", "status": "done", "success": True})
        total_duration = time.time() - total_start
        image_url = "/output/{}/{}".format(run_id, output_filename)
        emit("result", {
            "success": True,
            "image_url": image_url,
            "total_duration": round(total_duration, 1),
        })
    else:
        emit("stage_update", {"stage": "execute", "status": "done", "success": False})
        error_msg = exec_result.get("stderr", "Execution failed")
        emit("error", {"stage": "execute", "message": error_msg[-1500:]})


# ======================================================================
# Flask routes
# ======================================================================

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/generate", methods=["POST"])
def generate():
    question_text = request.form.get("question_text", "").strip()
    if not question_text:
        return jsonify({"error": "Question text is required"}), 400

    run_id = uuid.uuid4().hex[:12]

    # Handle optional image upload
    image_path = None
    if "question_image" in request.files:
        f = request.files["question_image"]
        if f.filename:
            upload_dir = SCRIPT_DIR / "output" / run_id
            os.makedirs(str(upload_dir), exist_ok=True)
            image_path = str(upload_dir / f.filename)
            f.save(image_path)

    active_runs[run_id] = queue.Queue()

    t = threading.Thread(
        target=pipeline_worker,
        args=(run_id, question_text, image_path),
        daemon=True,
    )
    t.start()

    return jsonify({"run_id": run_id})


@app.route("/stream/<run_id>")
def stream(run_id):
    if run_id not in active_runs:
        return "Run not found", 404

    def event_stream():
        q = active_runs[run_id]
        while True:
            try:
                event_type, data = q.get(timeout=180)
                yield "event: {}\ndata: {}\n\n".format(event_type, data)
                if event_type == "done":
                    break
            except queue.Empty:
                yield ": keepalive\n\n"

        # Cleanup after a delay
        def _cleanup():
            time.sleep(300)
            active_runs.pop(run_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/output/<run_id>/<filename>")
def serve_output(run_id, filename):
    output_dir = str(SCRIPT_DIR / "output" / run_id)
    return send_from_directory(output_dir, filename)


# ======================================================================
# HTML Template (embedded)
# ======================================================================

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Geometry Diagram Generator</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0C0C0C;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,monospace;line-height:1.6}
.container{max-width:1200px;margin:0 auto;padding:2rem}
.header{text-align:center;margin-bottom:2rem;border-bottom:1px solid #2a2a2a;padding-bottom:1rem}
.header h1{color:#4ECDC4;font-size:1.8rem;margin-bottom:.25rem}
.subtitle{color:#888;font-size:.9rem}

.input-section{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:1.5rem;margin-bottom:2rem}
.form-group{margin-bottom:1rem}
.form-group label{display:block;margin-bottom:.4rem;color:#ccc;font-weight:600;font-size:.9rem}
textarea{width:100%;background:#0C0C0C;color:#e0e0e0;border:1px solid #333;border-radius:4px;padding:.75rem;font-family:inherit;font-size:.95rem;resize:vertical}
textarea:focus{outline:none;border-color:#4ECDC4}
input[type=file]{color:#888;font-size:.9rem}
.btn-row{display:flex;gap:1rem;align-items:center}
#generate-btn{background:#4ECDC4;color:#0C0C0C;border:none;padding:.7rem 2rem;border-radius:4px;font-size:1rem;font-weight:700;cursor:pointer;transition:background .2s}
#generate-btn:hover{background:#45b7ae}
#generate-btn:disabled{background:#333;color:#666;cursor:not-allowed}
#timer{color:#888;font-size:.9rem;font-variant-numeric:tabular-nums}

.progress-section{margin-bottom:2rem}
.progress-section h2{color:#4ECDC4;margin-bottom:1rem;font-size:1.1rem}
.stage{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:.85rem 1rem;margin-bottom:.5rem;transition:border-color .3s}
.stage.running{border-color:#4ECDC4}
.stage.done{border-color:#96CEB4}
.stage.error{border-color:#FF6B6B}
.stage-header{display:flex;align-items:center;gap:.75rem}
.stage-dot{width:10px;height:10px;border-radius:50%;background:#333;flex-shrink:0;transition:background .3s}
.stage-dot.running{background:#4ECDC4;animation:pulse 1.4s infinite}
.stage-dot.done{background:#96CEB4}
.stage-dot.error{background:#FF6B6B}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.stage-name{font-weight:600;flex-grow:1;font-size:.95rem}
.stage-model{color:#666;font-size:.8rem;font-style:italic}
.stage-badge{background:#2a2a2a;color:#4ECDC4;padding:.1rem .5rem;border-radius:4px;font-size:.8rem;font-weight:700}
.stage-details{margin-top:.4rem;font-size:.82rem;color:#888}
.metric{display:inline-block;margin-right:1.2rem}
.metric-val{color:#e0e0e0;font-weight:600}

.output-section{display:flex;flex-direction:column;gap:1.5rem}
.output-panel{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:1.25rem;overflow:hidden}
.output-panel h3{color:#4ECDC4;margin-bottom:.6rem;font-size:.95rem}
.scroll-box{background:#0C0C0C;border:1px solid #222;border-radius:4px;padding:1rem;max-height:400px;overflow:auto;font-family:'SF Mono','Fira Code',Consolas,monospace;font-size:.82rem;line-height:1.55;white-space:pre-wrap;word-break:break-word;color:#d4d4d4}
.scroll-box::-webkit-scrollbar{width:8px}
.scroll-box::-webkit-scrollbar-track{background:#1a1a1a}
.scroll-box::-webkit-scrollbar-thumb{background:#333;border-radius:4px}

.kw{color:#c586c0}.str{color:#ce9178}.num{color:#b5cea8}.cmt{color:#6a9955}

#result-img-wrap{text-align:center;margin-top:.5rem}
#result-img-wrap img{max-width:100%;border:1px solid #2a2a2a;border-radius:4px}
#result-summary{margin-top:.75rem;text-align:center;color:#96CEB4;font-weight:600}

.hidden{display:none}
</style>
</head>
<body>
<div class="container">

<header class="header">
  <h1>Geometry Diagram Generator</h1>
  <p class="subtitle">AI-powered: Gemini computes coordinates, Sonnet writes rendering code</p>
</header>

<section class="input-section">
  <div class="form-group">
    <label for="qtxt">Geometry Question</label>
    <textarea id="qtxt" rows="4">In triangle ABC, angle ACB = 90 degrees, AC = 24cm, BC = 12cm. D is a point on AC such that AD = 12cm. E is a point on AB such that DE is perpendicular to AC. Find the area of triangle ADE.</textarea>
  </div>
  <div class="form-group">
    <label for="qimg">Question Image (optional)</label>
    <input type="file" id="qimg" accept="image/*">
  </div>
  <div class="btn-row">
    <button id="generate-btn" onclick="startGen()">Generate Diagram</button>
    <span id="timer"></span>
  </div>
</section>

<section id="progress" class="progress-section hidden">
  <h2>Pipeline Progress</h2>
  <div class="stage" id="s-blueprint">
    <div class="stage-header">
      <span class="stage-dot" id="d-blueprint"></span>
      <span class="stage-name">Stage 1: Blueprint Generation</span>
      <span class="stage-model">Gemini 3 Flash</span>
    </div>
    <div class="stage-details" id="det-blueprint"></div>
  </div>
  <div class="stage" id="s-detect">
    <div class="stage-header">
      <span class="stage-dot" id="d-detect"></span>
      <span class="stage-name">Dimension Detection</span>
      <span class="stage-badge hidden" id="badge-dim"></span>
    </div>
  </div>
  <div class="stage" id="s-codegen">
    <div class="stage-header">
      <span class="stage-dot" id="d-codegen"></span>
      <span class="stage-name">Stage 2: Code Generation</span>
      <span class="stage-model">Sonnet 4.5</span>
    </div>
    <div class="stage-details" id="det-codegen"></div>
  </div>
  <div class="stage" id="s-execute">
    <div class="stage-header">
      <span class="stage-dot" id="d-execute"></span>
      <span class="stage-name">Code Execution</span>
    </div>
    <div class="stage-details" id="det-execute"></div>
  </div>
</section>

<section id="outputs" class="output-section hidden">
  <div class="output-panel hidden" id="p-blueprint">
    <h3>Blueprint (coordinates.txt)</h3>
    <div class="scroll-box" id="o-blueprint"></div>
  </div>
  <div class="output-panel hidden" id="p-code">
    <h3>Generated Python Code</h3>
    <div class="scroll-box" id="o-code"></div>
  </div>
  <div class="output-panel hidden" id="p-exec">
    <h3>Execution Log</h3>
    <div class="scroll-box" id="o-exec"></div>
  </div>
  <div class="output-panel hidden" id="p-result">
    <h3>Rendered Diagram</h3>
    <div id="result-img-wrap"></div>
    <div id="result-summary"></div>
  </div>
</section>

</div>

<script>
var es=null,timerInterval=null,startTime=0,totalCost=0;
var SMAP={blueprint:'blueprint',detect_dim:'detect',codegen:'codegen',execute:'execute'};
// Pricing: $/M tokens
var PRICING={
  blueprint:{input:0.50,output:3.00},
  codegen:{input:3,output:15}
};

function startGen(){
  var txt=document.getElementById('qtxt').value.trim();
  if(!txt){alert('Enter a geometry question.');return}
  var btn=document.getElementById('generate-btn');
  btn.disabled=true;btn.textContent='Running...';
  show('progress');hide('outputs');resetUI();
  startTime=Date.now();
  timerInterval=setInterval(updateTimer,100);

  var fd=new FormData();
  fd.append('question_text',txt);
  var fi=document.getElementById('qimg');
  if(fi.files.length)fd.append('question_image',fi.files[0]);

  fetch('/generate',{method:'POST',body:fd})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.error){alert(d.error);finish();return}
      connectSSE(d.run_id);
    })
    .catch(function(e){alert('Request failed: '+e);finish()});
}

function connectSSE(rid){
  if(es)es.close();
  es=new EventSource('/stream/'+rid);

  es.addEventListener('stage_update',function(e){updateStage(JSON.parse(e.data))});
  es.addEventListener('blueprint_text',function(e){
    var d=JSON.parse(e.data);show('outputs');
    document.getElementById('p-blueprint').classList.remove('hidden');
    document.getElementById('o-blueprint').textContent=d.text;
  });
  es.addEventListener('generated_code',function(e){
    var d=JSON.parse(e.data);
    document.getElementById('p-code').classList.remove('hidden');
    document.getElementById('o-code').innerHTML=hlPy(d.code);
  });
  es.addEventListener('execution_output',function(e){
    var d=JSON.parse(e.data);
    document.getElementById('p-exec').classList.remove('hidden');
    var log='';
    if(d.stdout)log+='--- stdout ---\n'+d.stdout+'\n';
    if(d.stderr)log+='--- stderr ---\n'+d.stderr+'\n';
    log+='--- exit code: '+d.returncode+' ---';
    document.getElementById('o-exec').textContent=log;
  });
  es.addEventListener('result',function(e){
    var d=JSON.parse(e.data);
    document.getElementById('p-result').classList.remove('hidden');
    if(d.success&&d.image_url){
      document.getElementById('result-img-wrap').innerHTML=
        '<img src="'+d.image_url+'?t='+Date.now()+'" alt="Rendered diagram">';
    }
    document.getElementById('result-summary').textContent=
      'Pipeline completed in '+d.total_duration+'s \u00B7 Total cost: $'+totalCost.toFixed(4);
  });
  es.addEventListener('error',function(e){
    try{var d=JSON.parse(e.data);setError(d.stage,d.message)}catch(x){
      // Built-in SSE connection error
      setError('connection','SSE connection lost. Check the terminal for errors.');
    }
  });
  es.addEventListener('done',function(){es.close();es=null;finish()});
  es.onerror=function(){
    if(es.readyState===EventSource.CLOSED){
      es.close();es=null;finish();
    }
  };
}

function updateStage(d){
  var id=SMAP[d.stage];if(!id)return;
  var el=document.getElementById('s-'+id);
  var dot=document.getElementById('d-'+id);
  el.className='stage '+d.status;
  dot.className='stage-dot '+d.status;
  var det=document.getElementById('det-'+id);
  if(det){
    if(d.status==='running'&&d.message){
      det.innerHTML='<span class="metric">'+esc(d.message)+'</span>';
    }
    if(d.status==='done'){
      var h='';
      if(d.duration!==undefined)h+='<span class="metric">Duration: <span class="metric-val">'+d.duration+'s</span></span>';
      if(d.tokens){
        h+='<span class="metric">In: <span class="metric-val">'+d.tokens.prompt.toLocaleString()+'</span> &middot; Out: <span class="metric-val">'+d.tokens.completion.toLocaleString()+'</span> &middot; Total: <span class="metric-val">'+d.tokens.total.toLocaleString()+'</span> tokens</span>';
        var pr=PRICING[d.stage];
        if(pr){
          var cost=(d.tokens.prompt/1e6)*pr.input+(d.tokens.completion/1e6)*pr.output;
          totalCost+=cost;
          h+='<span class="metric">Cost: <span class="metric-val">$'+cost.toFixed(4)+'</span></span>';
        }
      }
      if(d.success!==undefined)h+='<span class="metric">'+( d.success?'&#10003; Success':'&#10007; Failed')+'</span>';
      det.innerHTML=h;
    }
  }
  if(d.stage==='detect_dim'&&d.dimension){
    var b=document.getElementById('badge-dim');
    b.textContent=d.dimension.toUpperCase();b.classList.remove('hidden');
  }
}

function setError(stage,msg){
  var id=SMAP[stage]||stage;
  var el=document.getElementById('s-'+id);
  var dot=document.getElementById('d-'+id);
  if(el)el.classList.add('error');
  if(dot){dot.classList.remove('running');dot.classList.add('error')}
  show('outputs');
  document.getElementById('p-exec').classList.remove('hidden');
  var o=document.getElementById('o-exec');
  o.textContent+='\n--- ERROR ('+stage+') ---\n'+msg+'\n';
}

function resetUI(){
  totalCost=0;
  ['blueprint','detect','codegen','execute'].forEach(function(id){
    document.getElementById('s-'+id).className='stage';
    document.getElementById('d-'+id).className='stage-dot';
    var det=document.getElementById('det-'+id);if(det)det.innerHTML='';
  });
  document.getElementById('badge-dim').classList.add('hidden');
  document.getElementById('badge-dim').textContent='';
  ['p-blueprint','p-code','p-exec','p-result'].forEach(function(id){
    document.getElementById(id).classList.add('hidden');
  });
  document.getElementById('result-img-wrap').innerHTML='';
  document.getElementById('result-summary').textContent='';
  document.getElementById('o-blueprint').textContent='';
  document.getElementById('o-code').innerHTML='';
  document.getElementById('o-exec').textContent='';
}

function finish(){
  var btn=document.getElementById('generate-btn');
  btn.disabled=false;btn.textContent='Generate Diagram';
  if(timerInterval){clearInterval(timerInterval);timerInterval=null}
}

function updateTimer(){
  var s=((Date.now()-startTime)/1000).toFixed(1);
  document.getElementById('timer').textContent=s+'s elapsed';
}

function show(id){document.getElementById(id).classList.remove('hidden')}
function hide(id){document.getElementById(id).classList.add('hidden')}
function esc(t){var d=document.createElement('div');d.appendChild(document.createTextNode(t));return d.innerHTML}

function hlPy(code){
  var h=esc(code);
  h=h.replace(/(#[^\n]*)/g,'<span class="cmt">$1</span>');
  h=h.replace(/("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g,'<span class="str">$1</span>');
  h=h.replace(/\b(\d+\.?\d*)\b/g,'<span class="num">$1</span>');
  var kws=['import','from','def','class','return','if','else','elif','for','while','in','not','and','or','try','except','with','as','True','False','None','print','lambda','pass','break','continue','raise'];
  kws.forEach(function(k){h=h.replace(new RegExp('\\b('+k+')\\b','g'),'<span class="kw">$1</span>')});
  return h;
}
</script>
</body>
</html>
"""


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    import webbrowser

    port = 5050
    url = "http://127.0.0.1:{}".format(port)
    print("Starting Geometry Diagram Demo at {}".format(url))
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
