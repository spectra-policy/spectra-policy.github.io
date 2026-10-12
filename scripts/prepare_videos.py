"""Prepare the reviewed task demonstration excerpts from a local source folder.

Usage: python scripts/prepare_videos.py /path/to/source/videos
Requires ffmpeg. Originals are never changed. Public outputs are written to site/static/.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    clips = json.loads((root / 'scripts/video_clips.json').read_text())['clips']
    output = root / 'site/static/videos'
    output.mkdir(parents=True, exist_ok=True)
    gallery = ['<div class="task-videos" aria-label="Real-robot task demonstrations">']
    timing = []
    for clip in clips:
        name, start, duration = clip['name'], clip['start'], clip['duration']
        source = args.source / clip['source']
        before = hashlib.sha256(source.read_bytes()).digest()
        source_info = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'format=duration:stream=avg_frame_rate',
            '-of', 'json', str(source),
        ], text=True))
        source_duration = float(source_info['format']['duration'])
        assert 0 <= start < start + duration <= source_duration
        # Reset only the excerpt's starting timestamp. Preserve source frame
        # intervals; do not infer camera timing from robot telemetry.
        video_filter = f'trim=duration={duration},setpts=PTS-STARTPTS,scale=640:480,setsar=1'
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-ss', str(start), '-i', str(source),
            '-map', '0:v:0', '-an', '-sn', '-dn',
            '-map_metadata', '-1', '-map_chapters', '-1',
            '-vf', video_filter,
            '-fps_mode', 'passthrough',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '23',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
            str(output / f'{name}.mp4'),
        ], check=True)
        output_info = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'format=duration:stream=avg_frame_rate',
            '-of', 'json', str(output / f'{name}.mp4'),
        ], text=True))
        output_duration = float(output_info['format']['duration'])
        source_fps = source_info['streams'][0]['avg_frame_rate']
        output_fps = output_info['streams'][0]['avg_frame_rate']
        assert source_fps == output_fps, (name, source_fps, output_fps)
        timing.append({
            'name': name,
            'timing_method': 'source',
            'source_duration_s': source_duration,
            'source_frame_rate': source_fps,
            'output_frame_rate': output_fps,
            'time_scale': 1.0,
            'output_duration_s': output_duration,
        })
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-i', str(output / f'{name}.mp4'), '-frames:v', '1',
            '-map_metadata', '-1', '-q:v', '2',
            str(output / f'{name}.jpg'),
        ], check=True)
        assert hashlib.sha256(source.read_bytes()).digest() == before
        version = hashlib.sha256((output / f'{name}.mp4').read_bytes()).hexdigest()[:12]
        gallery.append(f'''  <figure class="task-video">
    <figcaption id="{name}-title">{clip['label']}</figcaption>
    <video width="640" height="480" autoplay muted loop playsinline preload="metadata" disablepictureinpicture disableremoteplayback tabindex="-1" data-play-in-view poster="static/videos/{name}.jpg" aria-labelledby="{name}-title">
      <source src="static/videos/{name}.mp4?v={version}" type="video/mp4">
      Your browser does not support embedded video.
    </video>
  </figure>''')
        print(f'{name}: {output_duration:.2f}s loop, source frame rate {output_fps}, unchanged playback speed')
    gallery.extend(['</div>', '<p class="video-note">Task demonstration excerpts.</p>'])
    (root / 'scripts/real_robot_videos.html').write_text('\n'.join(gallery)+'\n')
    (root / 'scripts/video_timing.json').write_text(json.dumps({
        'method': 'Preserve source AVI playback timing and frame rate for every excerpt. Only reset the starting timestamp; no speed adjustment, frame-rate conversion, or telemetry-based retiming.',
        'clips': timing,
    }, indent=2)+'\n')


if __name__ == '__main__':
    main()
