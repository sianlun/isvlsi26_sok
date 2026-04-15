#!/usr/bin/env python3
import json, os, re, glob

corpus = json.load(open("corpus_final.json"))
by_fn = {c['filename']: c for c in corpus}

# heuristic dictionaries
MCU_PATTERNS = [
    (r'\bSTM32[A-Z]?\w*', 'STM32'),
    (r'\bnRF5\d\w*', 'Nordic nRF'),
    (r'\bESP32\w*', 'ESP32'),
    (r'\bArduino\s+Nano\s+33\s+BLE(?:\s+Sense)?', 'Arduino Nano 33 BLE'),
    (r'\bArduino\b', 'Arduino'),
    (r'\bRaspberry\s+Pi\s+Pico\s*W?', 'RPi Pico'),
    (r'\bRaspberry\s+Pi\b', 'Raspberry Pi'),
    (r'\bCortex-?M0\+?', 'Cortex-M0+'),
    (r'\bCortex-?M4F?', 'Cortex-M4'),
    (r'\bCortex-?M33', 'Cortex-M33'),
    (r'\bCortex-?M55', 'Cortex-M55'),
    (r'\bCortex-?M7', 'Cortex-M7'),
    (r'\bCortex-?A\d+', 'Cortex-A'),
    (r'\bGAP\d\w*', 'GAP8/9'),
    (r'\bSAMD\d\w*', 'SAMD'),
    (r'\bPULP\b', 'PULP'),
    (r'\bMAX\d{5}', 'MAX78000'),
    (r'\bApollo\d?\b', 'Ambiq Apollo'),
    (r'\bSiFive\b', 'SiFive RISC-V'),
    (r'\bRISC-?V\b', 'RISC-V'),
    (r'\bJetson\s+\w+', 'NVIDIA Jetson'),
    (r'\bSyntiant\b', 'Syntiant NDP'),
    (r'\bKendryte\s+K210', 'Kendryte K210'),
]

DOMAINS = {
    'ECG': r'\b(ECG|electrocardiogra\w+|arrhythmia|atrial fibrillat|AFib|AF detect|PVC|MIT-?BIH|PTB-?XL|PhysioNet)\b',
    'EEG': r'\b(EEG|electroencephalogra\w+|seizure|epilep\w+|CHB-?MIT|BCI|motor imagery)\b',
    'PPG': r'\b(PPG|photoplethysmogra\w+|pulse oxim)\b',
    'IMU/Motion': r'\b(IMU|accelerom\w+|gyroscop\w+|activity recogni\w+|HAR|fall detect|gait)\b',
    'EMG': r'\b(EMG|electromyogra\w+)\b',
    'Respiration/Apnea': r'\b(apnea|respirat\w+|cough|breath)\b',
    'Imaging': r'\b(endoscop\w+|capsule endoscopy|lung (?:image|CT|X-?ray)|melanoma|skin lesion|retina|ultrasound|image classif)\b',
    'Glucose': r'\b(glucose|CGM|diabet\w+)\b',
    'Stress/Affect': r'\b(stress detect|emotion|affective|depression|anxiety|mental (?:stress|health))\b',
    'Network/IDS': r'\b(intrusion detect|IDS|network traffic|anomaly.*network|DDoS)\b',
}

TASK = {
    'Arrhythmia/AF detection': r'\b(arrhythmia|atrial fibrillat|AFib|AF detect|heart ?beat|PVC|ECG classif)\b',
    'Seizure/Epilepsy detection': r'\b(seizure|epilep\w+)\b',
    'Sleep apnea detection': r'\bapnea\b',
    'Stress/Emotion recognition': r'\b(stress detect|emotion recogni|affective|depression detect|mental stress)\b',
    'Activity/Fall detection': r'\b(fall detect|activity recogni\w+|HAR|gait)\b',
    'Cough/Respiration': r'\b(cough detect|respirator)\b',
    'Image/Lesion classification': r'\b(melanoma|skin lesion|lung disease|retina|endoscop\w+)\b',
    'Anomaly detection': r'\banomaly detect',
    'Intrusion detection': r'\b(intrusion detect|IDS)\b',
    'Authentication': r'\b(authenticat\w+|biometric)\b',
}

COMPRESSION = {
    'Quantization': r'\b(quantiz\w+|INT8|INT4|int-?8|int-?4|mixed.?precision|PTQ|QAT|fixed.?point|binary neural|ternary)\b',
    'Pruning': r'\b(pruning|sparsif\w+|magnitude prun|structured prun|unstructured prun|channel prun)\b',
    'Knowledge distillation': r'\b(knowledge distillat|KD\b|teacher.?student|distil\w+)\b',
    'NAS': r'\b(neural architecture search|\bNAS\b|hardware.?aware NAS|MCUNet|MicroNets|Once.?for.?All)\b',
    'Weight sharing/Clustering': r'\b(weight sharing|clustering|K.?means quantization)\b',
    'Low-rank/Tensor decomp.': r'\b(low.?rank|tensor decompo|SVD)\b',
    'Early exit': r'\b(early exit|dynamic inference)\b',
}

TIER_HINTS = {
    'T1 Implantable': r'\b(implant\w+|intracranial|subcutan\w+|iEEG|pacemaker|insulin pump|neurostimulat)\b',
    'T3 Clinical instrument': r'\b(clinical (?:setting|instrument)|hospital|bedside|point.?of.?care|Jetson|Raspberry Pi|Cortex-?A|smartphone)\b',
    # default T2 wearable otherwise
}

DATASET = r'\b(MIT-?BIH|PhysioNet|PTB-?XL|CHB-?MIT|BCI Competition|CinC|AHA database|WESAD|DEAP|UCI HAR|MHEALTH|DREAMER|SWELL|SEED|Sleep-?EDF|TUH\w*)\b'

RAM_RE = re.compile(r'(\d+(?:\.\d+)?)\s*([KMk])B\s*(?:of\s*)?(?:S?RAM|memory)', re.I)
FLASH_RE = re.compile(r'(\d+(?:\.\d+)?)\s*([KMk])B\s*(?:of\s*)?(?:flash|Flash|ROM)', re.I)
POW_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(mW|uW|µW|μW|nW|W)\b')
ACC_RE = re.compile(r'\b(?:accuracy|acc\.?|F1.?score|F1|sensitivity|specificity)\s*(?:of|=|:)?\s*(\d{1,3}(?:\.\d+)?)\s*%?', re.I)
LAT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(ms|µs|us|s)\s*(?:latency|inference|per (?:sample|inference|window))', re.I)

def first(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    return m.group(0) if m else ''

def classify_tier(text, mcu):
    for tag, pat in TIER_HINTS.items():
        if re.search(pat, text, re.I):
            return tag
    # fall back on MCU family
    if any(k in mcu for k in ['Jetson','Cortex-A','Raspberry Pi']):
        return 'T3 Clinical instrument'
    return 'T2 Wearable'

def tag_set(text, kwdict):
    tags=[]
    for tag,pat in kwdict.items():
        if re.search(pat, text, re.I):
            tags.append(tag)
    return ', '.join(tags)

def find_mcu(text):
    hits=[]
    for pat,label in MCU_PATTERNS:
        if re.search(pat, text):
            hits.append(label)
    # dedup
    seen=set(); out=[]
    for h in hits:
        if h not in seen: seen.add(h); out.append(h)
    return ', '.join(out[:3])

def extract_one(fn, text):
    rec = by_fn.get(fn, {})
    # reduce noise: first 8000 chars
    t = text[:12000]
    mcu = find_mcu(t)
    domains = tag_set(t, DOMAINS)
    tasks = tag_set(t, TASK)
    compression = tag_set(t, COMPRESSION)
    tier = classify_tier(t, mcu)
    ram = RAM_RE.search(t); ram_s = f"{ram.group(1)} {ram.group(2).upper()}B" if ram else ''
    flash = FLASH_RE.search(t); flash_s = f"{flash.group(1)} {flash.group(2).upper()}B" if flash else ''
    pw = POW_RE.search(t); pw_s = f"{pw.group(1)} {pw.group(2)}" if pw else ''
    acc = ACC_RE.search(t); acc_s = acc.group(0) if acc else ''
    lat = LAT_RE.search(t); lat_s = lat.group(0) if lat else ''
    ds = re.findall(DATASET, t, re.I)
    ds_s = ', '.join(sorted(set(d.upper() for d in ds)))
    return {
        'Year': rec.get('year',''),
        'Title': rec.get('title',''),
        'DOI': rec.get('doi',''),
        'Filename': fn,
        'Clinical Domain': domains,
        'Task': tasks,
        'Device Tier': tier,
        'MCU/SoC': mcu,
        'RAM': ram_s,
        'Flash': flash_s,
        'Active Power': pw_s,
        'Dataset': ds_s,
        'Compression Techniques': compression,
        'Accuracy (reported)': acc_s,
        'Latency/Inference': lat_s,
        'Notes (manual)': '',
    }

rows=[]
for fn,rec in by_fn.items():
    txt_path = os.path.join('_txt', fn.replace('.pdf','.txt'))
    text = open(txt_path,errors='ignore').read() if os.path.exists(txt_path) else ''
    rows.append(extract_one(fn, text))

json.dump(rows, open('_extracted.json','w'), indent=1)
print(f"Extracted {len(rows)} rows")
# sanity peek
for r in rows[:3]:
    print(r)
