#!/usr/bin/env python3
"""Independent high-resolution generator for MrX SceneDeck.

Stash invokes this file through the raw plugin interface.  It samples frames
from the scene's real video with Stash's configured ffmpeg, builds one JPEG per
scene and grid size, and stores the result in the plugin's disposable cache.
"""

import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request


PLUGIN_ID = "MrXSceneDeck"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DIR = os.path.join(SCRIPT_DIR, "generated")
CELL_WIDTH = 384
CELL_HEIGHT = 216
JPEG_QUALITY = "3"
MIN_GRID = 4
MAX_GRID = 8
DEFAULT_CACHE_MAX = 250
MAX_WORKERS = 4


def emit_output(value):
    sys.stdout.write(json.dumps({"output": value}))


def emit_error(message):
    sys.stdout.write(json.dumps({"error": str(message)}))


class StashConnection:
    def __init__(self, connection):
        scheme = connection.get("Scheme") or "http"
        host = connection.get("Host") or "127.0.0.1"
        if host in ("", "0.0.0.0", None):
            host = "127.0.0.1"
        port = int(connection.get("Port") or 9999)
        self.url = "%s://%s:%d/graphql" % (scheme, host, port)
        self.headers = {"Content-Type": "application/json"}
        cookie = connection.get("SessionCookie") or {}
        if cookie.get("Name") and cookie.get("Value"):
            self.headers["Cookie"] = "%s=%s" % (cookie["Name"], cookie["Value"])
        if connection.get("ApiKey"):
            self.headers["ApiKey"] = connection["ApiKey"]

    def call(self, query, variables=None):
        body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        request = urllib.request.Request(self.url, data=body, headers=self.headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
        if payload.get("errors"):
            raise RuntimeError("; ".join(item.get("message", "GraphQL error") for item in payload["errors"]))
        return payload.get("data") or {}


def clamp_grid(value):
    try:
        return max(MIN_GRID, min(MAX_GRID, int(value)))
    except (TypeError, ValueError):
        return 6


def resolve_binary(name, configured, generated_path):
    candidates = []
    if configured:
        candidates.append(configured)
    if generated_path:
        candidates.append(os.path.join(os.path.dirname(generated_path), name))
    candidates.extend([
        os.path.join(os.path.expanduser("~"), ".stash", name),
        os.path.join(os.path.expanduser("~"), ".config", "stash", name),
        shutil.which(name),
    ])
    for candidate in candidates:
        if not candidate:
            continue
        if os.path.isfile(candidate):
            return candidate
        if os.path.isfile(candidate + ".exe"):
            return candidate + ".exe"
    return None


def general_configuration(stash):
    data = stash.call("{configuration{general{ffmpegPath generatedPath}}}")
    return (data.get("configuration") or {}).get("general") or {}


def plugin_configuration(stash):
    try:
        data = stash.call("{configuration{plugins}}")
        plugins = (data.get("configuration") or {}).get("plugins") or {}
        return plugins.get(PLUGIN_ID) or {}
    except Exception:
        return {}


def cache_limit(stash, args):
    value = args.get("cache_max")
    if value is None:
        value = plugin_configuration(stash).get("highResCacheMax")
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = DEFAULT_CACHE_MAX
    return value if value > 0 else DEFAULT_CACHE_MAX


def scene_information(stash, scene_id):
    query = ("query($id:ID!){findScene(id:$id){files{path duration "
             "fingerprints{type value}}}}")
    scene = stash.call(query, {"id": str(scene_id)}).get("findScene") or {}
    files = scene.get("files") or []
    if not files:
        return None
    file_info = files[0]
    fingerprint = None
    for item in file_info.get("fingerprints") or []:
        if item.get("type") == "oshash":
            fingerprint = item.get("value")
            break
    if not fingerprint:
        fingerprint = "scene-%s" % scene_id
    safe_key = re.sub(r"[^A-Za-z0-9._-]", "_", str(fingerprint))
    return {
        "path": file_info.get("path"),
        "duration": float(file_info.get("duration") or 0),
        "key": safe_key,
    }


def sheet_filename(key, grid):
    return "%s_%dx%d.jpg" % (key, grid, grid)


def sheet_path(key, grid):
    return os.path.join(GENERATED_DIR, sheet_filename(key, grid))


def capture_frame(ffmpeg, video_path, timestamp, destination):
    cell_filter = (
        "scale=%d:%d:force_original_aspect_ratio=decrease,"
        "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black"
        % (CELL_WIDTH, CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)
    )
    subprocess.run([
        ffmpeg, "-v", "error", "-nostdin", "-y", "-ss", "%.3f" % timestamp,
        "-i", video_path, "-frames:v", "1", "-vf", cell_filter,
        "-q:v", JPEG_QUALITY, destination,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def generate_sheet(ffmpeg, video_path, duration, key, grid):
    destination = sheet_path(key, grid)
    if os.path.isfile(destination):
        os.utime(destination, None)
        return destination
    if not video_path or not os.path.isfile(video_path):
        raise RuntimeError("Scene file is not mounted or is unavailable")
    if duration <= 0:
        raise RuntimeError("Scene duration is unavailable")

    os.makedirs(GENERATED_DIR, exist_ok=True)
    work_dir = tempfile.mkdtemp(prefix=".%s_%dx%d_" % (key, grid, grid), dir=GENERATED_DIR)
    cells = grid * grid
    timestamps = [duration * (index + 0.5) / cells for index in range(cells)]
    try:
        jobs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, cells)) as pool:
            for index, timestamp in enumerate(timestamps):
                frame_path = os.path.join(work_dir, "frame_%03d.jpg" % index)
                jobs.append(pool.submit(capture_frame, ffmpeg, video_path, timestamp, frame_path))
            for job in jobs:
                job.result()

        staged = os.path.join(work_dir, "sheet.jpg")
        subprocess.run([
            ffmpeg, "-v", "error", "-nostdin", "-y", "-framerate", "1",
            "-i", os.path.join(work_dir, "frame_%03d.jpg"),
            "-vf", "tile=%dx%d" % (grid, grid), "-frames:v", "1",
            "-q:v", JPEG_QUALITY, staged,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.replace(staged, destination)
        return destination
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def prune_cache(limit):
    if limit <= 0 or not os.path.isdir(GENERATED_DIR):
        return 0
    entries = []
    for filename in os.listdir(GENERATED_DIR):
        path = os.path.join(GENERATED_DIR, filename)
        if not filename.lower().endswith(".jpg") or not os.path.isfile(path):
            continue
        try:
            entries.append((os.path.getmtime(path), path))
        except OSError:
            pass
    excess = len(entries) - limit
    if excess <= 0:
        return 0
    removed = 0
    for _modified, path in sorted(entries)[:excess]:
        try:
            os.remove(path)
            removed += 1
        except OSError:
            pass
    return removed


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    args = payload.get("args") or {}
    mode = args.get("mode") or "generate"
    try:
        stash = StashConnection(payload.get("server_connection") or {})
        configuration = general_configuration(stash)
        ffmpeg = resolve_binary("ffmpeg", configuration.get("ffmpegPath"),
                                configuration.get("generatedPath"))
        if mode == "prune":
            return emit_output({"removed": prune_cache(cache_limit(stash, args))})
        if mode == "debug":
            return emit_output({"ffmpeg": ffmpeg, "generated": GENERATED_DIR})
        if mode != "generate":
            return emit_error("Unsupported mode: %s" % mode)
        if not ffmpeg:
            return emit_error("Could not locate Stash's ffmpeg binary")

        scene_id = args.get("scene_id")
        if scene_id is None:
            return emit_error("scene_id is required")
        grid = clamp_grid(args.get("n"))
        info = scene_information(stash, scene_id)
        if not info:
            return emit_error("Scene or scene file was not found")
        result = generate_sheet(ffmpeg, info["path"], info["duration"], info["key"], grid)
        removed = prune_cache(cache_limit(stash, args))
        return emit_output({
            "ready": True,
            "file": os.path.basename(result),
            "removed": removed,
        })
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip() if error.stderr else str(error)
        return emit_error("ffmpeg failed: %s" % detail[-1000:])
    except Exception as error:
        return emit_error(error)


if __name__ == "__main__":
    main()
