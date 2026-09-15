import sys
import os
import subprocess

rvc_dir = r"C:\Users\Shubham\.gemini\antigravity\scratch\RVC20260718Nvidia"
input_audio = os.path.abspath(sys.argv[1])
output_audio = os.path.abspath(sys.argv[2])
model_name = sys.argv[3] if len(sys.argv) > 3 else "Rem.pth"

weight_root = os.path.join(rvc_dir, "assets", "weights")
rmvpe_root = os.path.join(rvc_dir, "assets", "rmvpe")
index_path = os.path.join(rvc_dir, "logs", "Rem.index")
if not os.path.exists(index_path):
    index_path = ""

script_code = f"""import sys
import os
sys.path.insert(0, r"{rvc_dir}")
os.chdir(r"{rvc_dir}")

os.environ["weight_root"] = r"{weight_root}"
os.environ["rmvpe_root"] = r"{rmvpe_root}"

import torch
from infer.vc.modules import VC
from configs.config import Config

config = Config()
config.device = "cuda:0"
config.is_half = True

vc = VC(config)
vc.get_vc(r"{model_name}")

# Perform RVC v2.3 inference
status, audio_tuple = vc.vc_single(
    sid=0,
    input_audio_path=r"{input_audio}",
    f0_up_key=0,
    f0_method="rmvpe",
    file_index=r"{index_path}",
    index_rate=0.75,
    resample_sr=0,
    rms_mix_rate=0.25,
    protect=0.33
)

if audio_tuple is not None and audio_tuple[1] is not None:
    tgt_sr, audio_opt = audio_tuple
    from scipy.io.wavfile import write
    write(r"{output_audio}", tgt_sr, audio_opt)
    print("RVC_SUCCESS")
"""

temp_py = os.path.join(rvc_dir, "run_rvc_single.py")
with open(temp_py, "w", encoding="utf-8") as f:
    f.write(script_code)

python_exe = os.path.join(rvc_dir, "runtime", "python.exe")
res = subprocess.run([python_exe, temp_py], cwd=rvc_dir, capture_output=True, text=True)

if "RVC_SUCCESS" in res.stdout:
    print("RVC Voice Conversion Successful!")
    sys.exit(0)
else:
    print("RVC Output:\n", res.stdout)
    if res.stderr:
        print("RVC Error:\n", res.stderr)
    sys.exit(1)
