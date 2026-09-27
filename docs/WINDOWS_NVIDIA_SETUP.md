# Windows NVIDIA setup

The production configuration is deliberately CUDA-first. It does not silently switch to CPU, because a 121-song run on a CPU-only PyTorch install can waste hours before the user notices.

## Supported target in this package

The project pins:

- Python 3.12-compatible Windows wheels
- `torch==2.9.1+cu128`
- `torchaudio==2.9.1+cu128`
- `transformers==4.57.6`
- `demucs==4.1.0`

The official PyTorch wheel index contains the exact `cp312` Windows CUDA 12.8 wheels.

## Install

From the project root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_cuda.ps1
```

Then verify:

```powershell
python main.py --doctor
.\scripts\verify_windows_gpu.ps1
```

`cuda_available` must be `True`.

## GPU policy

Default configuration:

```json
"runtime": {
  "device": "cuda",
  "fallback_device": "cpu",
  "require_cuda": true,
  "allow_cpu_fallback": false
}
```

This means a broken/CPU-only PyTorch install fails immediately with `CUDA_REQUIRED` instead of silently processing the batch on CPU.

You can explicitly permit CPU fallback with:

```powershell
python main.py --all --allow-cpu-fallback
```

That option is intentionally not the default.

## Demucs VRAM

The default Demucs configuration uses an 8-second segment on the GPU and retries a CUDA OOM with that segment size before considering CPU fallback. Demucs supports CUDA device selection and segment sizing for GPU memory pressure.

## MMS

MMS is loaded once per process, its Telugu adapter is activated, and the model is moved to the selected CUDA device. The model weights are cached under `models/mms` and are not downloaded per song.

## 3.86 GB model

The large MMS weight file is a model-cache asset, not a per-song asset. Once present in the configured Hugging Face cache, normal `from_pretrained()` calls reuse it.
