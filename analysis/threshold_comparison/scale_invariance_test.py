"""
Scale-invariance stress test: fixed vs dynamic threshold.

Idea: resizing a photo (simulating the baby being nearer/farther from the
camera, or a different camera zoom/resolution) does not change the real-world
behavior in the frame -- a hand that is near the mouth stays near the mouth
whether the photo is 60% or 150% of its original size. So each image's own
native-scale (1.0x) prediction is a valid self-consistent reference for what
every rescaled variant of that same image *should* still predict.

A threshold approach that is actually robust to camera distance/zoom should
reproduce its own 1.0x answer at every other scale. This directly tests the
claim in the thesis (3.2.4.1): dynamic threshold should be scale-invariant;
fixed threshold should not, because a constant pixel distance means something
different at every zoom level.
"""
import sys
import csv
import time
from pathlib import Path

sys.path.insert(0, '.')
import cv2
from src.detector import BabyWatcher

IMAGE_DIR = Path('image')
OUT_DIR = Path('analysis/threshold_comparison')

# Stratified across the shoulder_width distribution (see analysis_summary.json bins),
# mixing SAFE and OBJECT_TO_MOUTH native-scale outcomes.
SAMPLE_IMAGES = [
    '325779361_697392898585803_1014280073914063136_n_jpeg.rf.62dd7133f4c68f5e7f55164a6bb6654f.jpg',
    '325717802_3201299213421225_3156402973776784456_n_jpg.rf.b51e13872b5353e175f94e95dc7a9489.jpg',
    '325830439_1216468435654765_8198123771164846849_n_jpg.rf.6d419a8537ed729228daaf2753c667cf.jpg',
    '324392425_708809327578441_4136788493901408811_n_jpg.rf.1611c89a8a10c30802c6bcdd1e291e05.jpg',
    '325744152_2511328462355171_7357332802287911703_n_jpg.rf.450cc1bc46bce951c0b4abceceff22a2.jpg',
    '326394434_5756615407785144_5694530470722789450_n_jpg.rf.483cc4a0e1b2deb14c500f0a3c11a172.jpg',
    '322828325_962944021337628_1874479558312964397_n_jpg.rf.e37dc6a31819104bf1f9c5a0f6d97e89.jpg',
    '325715180_137293365856420_5222945214288864591_n-1-_jpg.rf.f0ef7e0e1f28bf85e14b689698102e21.jpg',
    '326159349_534578221963884_1591071820433039757_n_jpeg.rf.2f5ea5b630f0d34d545249624d079fb7.jpg',
    '325409542_839473773812693_5171051284896275114_n_jpg.rf.7bbcf02183750e5308aaa743707a3912.jpg',
    '325941570_5852048371554790_3949988224046891795_n_jpg.rf.6720ed113da6f0f501dde9f33dc9b41e.jpg',
    '326238267_893401148469647_7085697957128711941_n_jpg.rf.98f335844d41e5c96cfc66b54e9fc647.jpg',
    '325806645_719158326350652_507326228170993943_n_jpg.rf.c9b2235b281dbc6cbf71d47fd52d6fcc.jpg',
    '325703891_555974033244057_1859569487481249809_n_jpg.rf.6bdfa1106097cace272db91db53a20b7.jpg',
    '326020048_737599357577073_6452283636308315272_n_jpg.rf.7b2458c4c47dfabfa2459378a177d127.jpg',
    '325704532_691962849076031_9101256235223666838_n_jpg.rf.b46f0c7ba1559084bc4755a5bb5e6e3b.jpg',
    '325828564_143075851629778_4427204079022360148_n_jpeg.rf.6d88e3f10bf95bdef9ba8c47ec5f007c.jpg',
    '326286485_971713500648088_7958627032111934273_n_jpg.rf.d15bf054b05f1c80200717af2f680f12.jpg',
    '325944427_591711642789313_814042611178577681_n_jpg.rf.d3366488e0a6ba98aad6214d87ca6225.jpg',
    '326157342_202184902316456_6203023765414409336_n_jpg.rf.e2ab49bd7ebe8bbbc980e18b49846bf9.jpg',
    '325912152_1038841907072967_841167442293686645_n_jpeg.rf.412e3c8eb251fcea661c4ceeee7ae051.jpg',
    '325949356_735657664844481_8814291452810595816_n_jpeg.rf.60340b4ca23e864e2abc55572717833c.jpg',
    '326431299_958693652173971_5362073672430628745_n_jpeg.rf.17de8d040db4fbeb7abd8d48e9bd49c5.jpg',
]

SCALES = [0.4, 0.55, 0.7, 0.85, 1.0, 1.2, 1.45, 1.75]
FIXED_MODES = [45, 80, 140]


def make_watcher(config_path='config.yaml'):
    w = BabyWatcher(config_path)
    w.save_danger_clips = False
    w._force_immediate_confirmation = False
    w._single_image_mode = True
    w.last_event_log_time = 1e18
    w.danger_start_time = None
    w._danger_state_since = None
    try:
        w.alert_manager.sound_alert.enabled = False
    except Exception:
        pass
    try:
        w.alert_manager.email_alert.enabled = False
    except Exception:
        pass
    w.logger.log_event = lambda *a, **k: None
    w.logger.log_info = lambda *a, **k: None
    w.logger.log_warning = lambda *a, **k: None
    w.logger.log_error = lambda *a, **k: None
    return w


def run_mode(watcher, frame, mode_name, image_name, source_tag):
    if mode_name == 'dynamic':
        watcher.dynamic_threshold = True
    else:
        watcher.dynamic_threshold = False
        thresh = int(mode_name.split('_')[1])
        watcher.hand_mouth_thresh = thresh
        watcher.hand_obj_thresh = thresh
    watcher.proximity_history = []
    watcher.object_mouth_history = []
    # Treat every call as an independent single-image check. process_frame()'s
    # sustained_danger_duration gate normally requires 0.6s of real wall-clock
    # time to elapse since danger was first observed on this watcher instance --
    # with _danger_state_since left at None it would ALWAYS suppress the very
    # first danger frame of any call (0s elapsed < 0.6s), and with it left over
    # from a previous call the outcome would depend on inference timing between
    # calls rather than on threshold logic. Pre-seeding it 10s in the past makes
    # the gate a no-op deterministically, isolating pure threshold behavior.
    watcher.danger_start_time = None
    watcher._danger_state_since = time.time() - 10.0
    watcher.current_source = source_tag
    _, info = watcher.process_frame(frame)
    return info.get('status', 'SAFE')


def main():
    watcher = make_watcher()
    modes = ['dynamic'] + [f'fixed_{t}' for t in FIXED_MODES]

    rows = []
    t0 = time.time()
    for idx, image_name in enumerate(SAMPLE_IMAGES):
        path = IMAGE_DIR / image_name
        base_frame = cv2.imread(str(path))
        if base_frame is None:
            print(f'  SKIP (unreadable): {image_name}')
            continue
        h, w0 = base_frame.shape[:2]

        for scale in SCALES:
            new_w, new_h = max(32, int(w0 * scale)), max(32, int(h * scale))
            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
            resized = cv2.resize(base_frame, (new_w, new_h), interpolation=interp)

            for mode in modes:
                status = run_mode(watcher, resized, mode, image_name, f'{image_name}@{scale}')
                rows.append({'image': image_name, 'scale': scale, 'mode': mode, 'status': status})

        elapsed = time.time() - t0
        print(f'[{idx+1}/{len(SAMPLE_IMAGES)}] {image_name} done ({elapsed:.0f}s elapsed)')

    out_csv = OUT_DIR / 'scale_invariance_raw.csv'
    with out_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['image', 'scale', 'mode', 'status'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {out_csv} ({len(rows)} rows) in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
