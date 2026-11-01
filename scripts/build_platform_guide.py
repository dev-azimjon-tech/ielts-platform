"""Build the original illustrated guide; optional tools: Pillow, imageio-ffmpeg.

Use --prepare to create narration text in --work-dir. On macOS, render each
text with `say -v Samantha -r 165 --file-format=WAVE --data-format=LEI16@22050
-f FILE.txt -o FILE.wav`, then run this script again to build the media.
Build dependencies are not needed to run the Flask application.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import textwrap
import wave

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('platform_guide', ROOT / 'app/platform_guide.py')
content = importlib.util.module_from_spec(spec)
spec.loader.exec_module(content)
CHAPTERS = content.GUIDE_CHAPTERS
W, H, FPS = 1280, 720, 8
GREEN, INK, MUTED, PAPER, MINT, LINE = '#215c4b', '#18211f', '#68736f', '#f8faf7', '#dff1e5', '#e3e9e4'


def timestamp(seconds):
    millis = round(seconds * 1000)
    return f'{millis // 3600000:02d}:{millis // 60000 % 60:02d}:{millis // 1000 % 60:02d}.{millis % 1000:03d}'


def prepare(folder):
    folder.mkdir(parents=True, exist_ok=True)
    segments = []
    for index, chapter in enumerate(CHAPTERS):
        for number, sentence in enumerate(re.split(r'(?<=[.!?])\s+', chapter['narration'])):
            stem = f'{index:02d}-{number:02d}'
            (folder / f'{stem}.txt').write_text(sentence)
            segments.append(dict(chapter=chapter['id'], stem=stem, text=sentence))
    (folder / 'segments.json').write_text(json.dumps(segments, indent=2))
    return segments


def build(folder, destination):
    from PIL import Image, ImageDraw, ImageFont
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    fonts = Path('/System/Library/Fonts/Supplemental')
    normal_path = fonts / 'Arial.ttf'
    bold_path = fonts / 'Arial Bold.ttf'
    if not normal_path.exists():
        fonts = Path('/usr/share/fonts/truetype/dejavu')
        normal_path, bold_path = fonts / 'DejaVuSans.ttf', fonts / 'DejaVuSans-Bold.ttf'
    normal = {size: ImageFont.truetype(str(normal_path), size) for size in (14, 16, 18, 20, 22, 24, 26, 30, 40)}
    bold = {size: ImageFont.truetype(str(bold_path), size) for size in (14, 16, 18, 20, 22, 24, 26, 30, 40, 48, 60)}
    segments = json.loads((folder / 'segments.json').read_text())
    destination.mkdir(parents=True, exist_ok=True)
    cues, timings, position = [], [], 0.0
    audio_path = folder / 'narration.wav'
    with wave.open(str(audio_path), 'wb') as output:
        output.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
        for chapter in CHAPTERS:
            start = position
            for segment in [s for s in segments if s['chapter'] == chapter['id']]:
                with wave.open(str(folder / (segment['stem'] + '.wav'))) as source:
                    assert source.getparams()[:3] == (1, 2, 22050)
                    frames = source.readframes(source.getnframes())
                    length = source.getnframes() / source.getframerate()
                    if length <= 0:
                        raise ValueError(f"Empty narration: {segment['stem']}")
                    output.writeframes(frames)
                cues.append((position, position + length, segment['text']))
                position += length
                output.writeframes(b'\x00\x00' * 3308)
                position += 3308 / 22050
            output.writeframes(b'\x00\x00' * 11025)
            position += .5
            # Start each chapter on an actual video frame so a paused seek shows
            # that chapter immediately rather than the preceding illustration.
            next_frame = math.ceil(position * FPS) / FPS
            padding = round((next_frame - position) * 22050)
            output.writeframes(b'\x00\x00' * padding)
            position = next_frame
            timings.append(dict(id=chapter['id'], start=round(start, 3), end=round(position, 3)))
    total = position
    (destination / 'platform-guide.json').write_text(json.dumps(dict(duration=round(total, 3), chapters=timings), indent=2) + '\n')
    captions = ['WEBVTT', '']
    for start, end, text in cues:
        # Short cues keep captions readable on mobile. Their exact sentence boundaries
        # come from the separately synthesized narration clips.
        pieces = textwrap.wrap(text, 86, break_long_words=False)
        weights = sum(map(len, pieces))
        cursor = start
        for piece in pieces:
            next_time = min(end, cursor + (end - start) * len(piece) / weights)
            captions.extend([f'{timestamp(cursor)} --> {timestamp(next_time)}', '\n'.join(textwrap.wrap(piece, 43)), ''])
            cursor = next_time
    (destination / 'platform-guide.en.vtt').write_text('\n'.join(captions))
    chapters_vtt = ['WEBVTT', '']
    for chapter, timing in zip(CHAPTERS, timings):
        chapters_vtt.extend([f"{timestamp(timing['start'])} --> {timestamp(timing['end'])}", chapter['title'], ''])
    (destination / 'platform-guide.chapters.vtt').write_text('\n'.join(chapters_vtt))

    def draw_scene(index, step, elapsed=0):
        chapter = CHAPTERS[index]
        image = Image.new('RGB', (W, H), PAPER)
        d = ImageDraw.Draw(image)

        def box(x, y, w, h, fill='white', outline=LINE, radius=14):
            d.rounded_rectangle((x, y, x + w, y + h), radius, fill=fill, outline=outline, width=2)

        def txt(x, y, text, size=20, color=INK, heavy=False):
            d.text((x, y), str(text), fill=color, font=(bold if heavy else normal)[size])

        def paragraph(x, y, text, width, size=18, color=INK, heavy=False):
            font = (bold if heavy else normal)[size]
            line, lines = '', []
            for word in text.split():
                candidate = f'{line} {word}'.strip()
                if d.textlength(candidate, font=font) > width and line:
                    lines.append(line); line = word
                else:
                    line = candidate
            if line: lines.append(line)
            for line in lines:
                txt(x, y, line, size, color, heavy); y += size + 6
            return y

        def button(x, y, label, width=180, selected=True):
            box(x, y, width, 42, GREEN if selected else MINT, GREEN if selected else LINE, 9)
            txt(x + 14, y + 11, label, 18, 'white' if selected else GREEN, True)

        d.rectangle((0, 0, W, 76), fill=GREEN)
        txt(48, 23, 'IELTS Platform', 26, 'white', True)
        txt(920, 28, f'QUICK START  /  {index + 1:02d} OF 06', 16, '#dff1e5', True)
        txt(52, 104, f'CHAPTER {index + 1:02d}', 16, GREEN, True)
        txt(52, 136, chapter['title'], 40, INK, True)
        paragraph(52, 193, chapter['summary'], 1150, 22, MUTED)
        count = len(chapter['steps'])
        card_h = 90 if count == 4 else 110
        for n, instruction in enumerate(chapter['steps']):
            y = 264 + n * (card_h + 10)
            active = n == step
            box(52, y, 488, card_h, MINT if active else 'white', GREEN if active else LINE)
            d.ellipse((68, y + 17, 98, y + 47), fill=GREEN if active else '#eef2ef')
            txt(78, y + 24, str(n + 1), 14, 'white' if active else MUTED, True)
            paragraph(110, y + 16, instruction, 405, 18, INK if active else MUTED)

        # Original interface illustrations, using the same labels as the real app.
        box(574, 264, 654, 389)
        d.rounded_rectangle((575, 265, 1227, 307), 13, fill=GREEN)
        txt(594, 278, 'IELTS', 18, 'white', True)
        tabs = ['Dashboard', 'Mocks', 'AI practice', 'Flashcards']
        active_tab = [0, 1, 1, 2, 3, 0][index]
        x = 693
        for n, tab in enumerate(tabs):
            txt(x, 280, tab, 14, '#f2c65b' if n == active_tab else 'white', n == active_tab)
            x += [112, 79, 112, 90][n]
        x, y = 600, 330
        if index in (0, 5):
            txt(x, y, 'Your student dashboard', 24, GREEN, True)
            for n, (label, value) in enumerate([('Mocks completed', '4'), ('Average band', '6.5 / 9'), ('Practice left', '20')]):
                bx = x + n * 202
                box(bx, y + 48, 188, 82, MINT if n == 0 else PAPER)
                txt(bx + 12, y + 63, label, 14, MUTED)
                txt(bx + 12, y + 89, value, 24, GREEN, True)
            for n, skill in enumerate(['Reading', 'Listening', 'Speaking', 'Writing']):
                bx = x + n * 151
                box(bx, y + 150, 138, 97, PAPER)
                txt(bx + 12, y + 165, skill, 18, GREEN, True)
                button(bx + 10, y + 198, 'Practice', 118, False)
            txt(x, 605, 'Example scores  /  Your own results appear after practice.', 14, MUTED)
            if index == 5:
                box(x, 590, 602, 43, MINT)
                txt(x + 13, 602, 'Sun / moon: change theme     •     Dashboard: see progress', 16, GREEN, True)
        elif index == 1:
            txt(x, y, 'Reading & Listening practice', 24, GREEN, True)
            box(x, 379, 279, 186, PAPER)
            txt(x + 13, 393, 'Read the passage', 16, GREEN, True)
            for n, width in enumerate([242, 229, 240, 210, 240, 180]):
                d.rounded_rectangle((x + 14, 427 + n * 19, x + width, 434 + n * 19), 3, fill='#ccd8cf')
            box(x + 293, 379, 310, 186, PAPER)
            txt(x + 307, 393, 'Your answers', 16, GREEN, True)
            for n, label in enumerate(['A. A quieter city', 'B. A greener city', 'C. A larger city']):
                txt(x + 307, 431 + n * 36, label, 18, GREEN if n == 1 else MUTED, n == 1)
            button(x, 587, 'Start audio', 164)
            txt(x + 180, 600, '20 seconds to read first', 16, MUTED)
            button(x + 420, 587, 'Next passage', 183)
        elif index == 2:
            txt(x, y, 'Keep important details close', 24, GREEN, True)
            box(x, 380, 358, 185, PAPER)
            txt(x + 15, 398, 'Read the passage', 16, GREEN, True)
            paragraph(x + 15, 436, 'Regular practice helps learners build confidence and remember new words.', 325, 22)
            d.rectangle((x + 12, 432, x + 260, 463), fill='#ffe58a')
            txt(x + 15, 436, 'Regular practice helps', 22, INK)
            box(x + 374, 380, 229, 185, '#fffcf0', '#eadbb1')
            txt(x + 390, 400, 'Your notes', 20, GREEN, True)
            paragraph(x + 390, 440, 'Main idea: small, regular sessions.', 194, 20, MUTED)
            button(x, 589, 'Highlight selection', 214, False)
            button(x + 228, 589, 'Notes', 120, False)
            txt(x + 366, 602, 'Saved in this browser', 16, GREEN, True)
        elif index == 3:
            txt(x, y, 'AI practice studio', 24, GREEN, True)
            box(x, 380, 292, 182, PAPER)
            txt(x + 15, 396, 'Speaking examiner', 20, GREEN, True)
            paragraph(x + 15, 433, 'Describe a place you enjoy visiting.', 250, 20)
            button(x + 15, 507, 'Start recording', 252)
            box(x + 309, 380, 294, 182, PAPER)
            txt(x + 324, 396, 'Writing checker', 20, GREEN, True)
            paragraph(x + 324, 433, 'Read the task and write your essay.', 250, 20)
            button(x + 324, 507, 'Check with AI', 252)
            paragraph(x, 591, 'Read the feedback. AI band scores are practice estimates.', 602, 18, MUTED)
        elif index == 4:
            txt(x, y, 'Your personal vocabulary', 24, GREEN, True)
            box(x, 378, 284, 185, MINT)
            txt(x + 17, 394, 'WORD', 14, GREEN, True)
            txt(x + 17, 427, 'resilient', 30, GREEN, True)
            paragraph(x + 17, 478, 'Able to recover from difficulties', 250, 20)
            box(x + 300, 378, 303, 185, PAPER)
            txt(x + 315, 394, 'MULTIPLE-CHOICE QUIZ', 14, GREEN, True)
            paragraph(x + 315, 429, 'What does resilient mean?', 267, 22, INK, True)
            paragraph(x + 315, 498, 'Choose the correct meaning.', 267, 18, MUTED)
            button(x, 587, 'Save word', 169)
            button(x + 184, 587, 'Study flashcards', 211, False)
            txt(x + 411, 599, '2 different meanings', 16, GREEN, True)
        d.rectangle((52, 684, 1228, 688), fill=LINE)
        progress = (timings[index]['start'] + elapsed) / total
        d.rectangle((52, 684, 52 + int(1176 * progress), 688), fill=GREEN)
        txt(52, 661, 'ILLUSTRATED WALKTHROUGH', 14, MUTED, True)
        txt(970, 661, 'Learn. Practice. Repeat.', 16, GREEN, True)
        return image

    # A purpose-made poster is legible before the player starts.
    poster = Image.new('RGB', (W, H), GREEN)
    d = ImageDraw.Draw(poster)
    d.text((64, 58), 'IELTS Platform', font=bold[26], fill='white')
    d.text((64, 175), 'Your platform.', font=bold[60], fill='white')
    d.text((64, 250), 'A guided first step.', font=bold[60], fill='white')
    d.text((68, 357), 'A narrated tour of the tools you will use every day.', font=normal[26], fill='#dff1e5')
    d.ellipse((956, 174, 1160, 378), fill='#f2c65b')
    d.polygon([(1036, 229), (1036, 324), (1108, 277)], fill=GREEN)
    for n, label in enumerate(['Mock tests', 'AI practice', 'Flashcards']):
        x = 65 + n * 353
        d.rounded_rectangle((x, 506, x + 324, 578), 14, outline='#8ec3ac', width=2)
        d.text((x + 20, 528), label, font=bold[24], fill='white')
    d.text((67, 644), '6 chapters  •  English narration & captions  •  Follow at your own pace', font=normal[20], fill='#dff1e5')
    poster.save(destination / 'platform-guide-poster.jpg', quality=91)
    for index, chapter in enumerate(CHAPTERS):
        draw_scene(index, 0).save(folder / f'chapter-{index + 1}.png')

    command = [ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{W}x{H}',
               '-framerate', str(FPS), '-i', '-', '-i', str(audio_path), '-c:v', 'libx264', '-preset', 'veryfast',
               '-crf', '24', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart',
               '-shortest', str(destination / 'platform-guide.mp4')]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    frame_count = math.ceil(total * FPS)
    index = 0
    try:
        for frame in range(frame_count):
            time = frame / FPS
            while index < len(CHAPTERS) - 1 and time >= timings[index]['end']:
                index += 1
            elapsed = time - timings[index]['start']
            span = timings[index]['end'] - timings[index]['start']
            step = min(len(CHAPTERS[index]['steps']) - 1, int(elapsed / span * len(CHAPTERS[index]['steps'])))
            process.stdin.write(draw_scene(index, step, elapsed).tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError('Video encoding failed')
    finally:
        if process.poll() is None:
            process.terminate()
    print(json.dumps(dict(duration=round(total, 2), frames=frame_count,
                          video_bytes=(destination / 'platform-guide.mp4').stat().st_size)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=Path('/private/tmp/ielts-guide-build'))
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        prepare(args.work_dir)
    else:
        build(args.work_dir, ROOT / 'app/static/media')
