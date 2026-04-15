#!/usr/bin/env python3
import json, os, re

corpus = json.load(open('corpus_final.json'))
by_fn = {c['filename']: c for c in corpus}

# ---------- Domain vocabulary (independent wording) ----------
DOMAINS = {
    'ECG':     r'(?:electro ?cardio|ECG|E\.C\.G|heart ?rhythm|arrhythm|atrial ?fib|A-?fib\b|ventricul(?:ar|o)|bradycard|tachycard|cardiac (?:arrhyth|monitor)|MIT[- ]?BIH|PTB[- ]?XL)',
    'EEG':     r'(?:electro ?encephal|EEG\b|intracranial EEG|iEEG|seizure|epilep|brain[- ]?computer|CHB[- ]?MIT|motor ?imagery|BCI)',
    'PPG':     r'(?:photo ?plethysmo|PPG\b|pulse ?oxim|heart[- ]?rate variability|HRV)',
    'IMU/Motion': r'(?:accelerometer|gyroscope|inertial ?measurement|IMU\b|human ?activity ?recogn|fall[- ]?detect|gait)',
    'EMG':     r'(?:electro ?myo|EMG\b|sEMG|surface EMG)',
    'Respiration/Apnea': r'(?:sleep ?apnea|apnoea|respiratory ?rate|cough[- ]?detect|breath(?:ing)? ?monitor)',
    'Imaging': r'(?:capsule ?endoscop|wireless ?capsule|lung ?(?:image|CT|X[- ]?ray|disease)|melanoma|skin ?lesion|retin(?:a|opathy)|ultra ?sound|dermatol)',
    'Glucose': r'(?:continuous ?glucose|CGM\b|glyc(?:emia|emic)|diabet)',
    'Stress/Affect': r'(?:mental ?stress|stress[- ]?recogn|emotion ?(?:recogn|classif)|affective ?computing|depression ?(?:detect|classif)|WESAD|DEAP)',
    'Network/IDS': r'(?:intrusion ?detect|network ?anomaly|DDoS|flooding ?attack|IoMT ?security)',
}

TASKS = {
    'Arrhythmia/AF detection': r'(?:arrhyth|atrial ?fib|A-?fib|PVC|heart ?beat ?(?:detect|classif)|ECG ?(?:classif|beat))',
    'Seizure/Epilepsy detection': r'(?:seizure|epilep|ictal)',
    'Sleep apnea detection':   r'(?:sleep ?apnea|apnoea|OSA)',
    'Stress/Emotion recognition': r'(?:mental ?stress|emotion ?(?:recogn|classif)|affective|depression)',
    'Activity/Fall detection': r'(?:fall[- ]?detect|human ?activity ?recogn|gait ?analys)',
    'Cough/Respiration':       r'(?:cough ?(?:detect|classif)|respiratory ?(?:disease|classif))',
    'Image/Lesion classification': r'(?:melanoma|skin ?lesion|lung ?(?:disease|image)|capsule ?endoscop|retin(?:a|opathy))',
    'Anomaly detection':       r'anomaly ?detect',
    'Intrusion detection':     r'(?:intrusion ?detect|IDS\b)',
    'Authentication':          r'(?:authentic|biometric ?(?:identif|verif))',
}

# ---------- MCU detection: different families, full names ----------
MCU_RULES = [
    ('Arduino Nano 33 BLE',   r'Arduino ?Nano ?33 ?BLE(?: ?Sense)?'),
    ('STM32',                 r'STM32[A-Z]?\d{2,3}[A-Z0-9]*'),
    ('Nordic nRF52/53',       r'nRF5[123]\d{0,3}'),
    ('ESP32',                 r'ESP32(?:[- ]?\w+)?'),
    ('Raspberry Pi Pico',     r'Raspberry ?Pi ?Pico ?W?|RP2040'),
    ('Raspberry Pi',          r'Raspberry ?Pi ?(?:[345]|Zero)'),
    ('NVIDIA Jetson',         r'(?:Jetson ?(?:Nano|Xavier|Orin|TX\d))'),
    ('MAX78000',              r'MAX78\d{3}'),
    ('Ambiq Apollo',          r'Apollo ?[234]?'),
    ('Kendryte K210',         r'K210\b|Kendryte'),
    ('Syntiant NDP',          r'Syntiant|NDP ?10\d'),
    ('GAP8/9',                r'GAP ?[89]\b|GAPuino'),
    ('PULP/RI5CY',            r'\bPULP\b|RI5CY|Ibex'),
    ('Cortex-M0+',            r'Cortex[- ]?M0\+?'),
    ('Cortex-M4',             r'Cortex[- ]?M4F?'),
    ('Cortex-M7',             r'Cortex[- ]?M7'),
    ('Cortex-M33/M55',        r'Cortex[- ]?M(?:33|55)'),
    ('Cortex-A',              r'Cortex[- ]?A\d+'),
    ('RISC-V',                r'RISC[- ]?V'),
    ('SAMD21/SAMD51',         r'SAMD(?:21|51)'),
]

# ---------- Compression: abbreviations + full spellings ----------
COMPRESSION = {
    'Quantization':           r'(?:\bquantiz|\bQAT\b|\bPTQ\b|\bINT[48]\b|\bint[- ]?[48]\b|\bfixed[- ]?point\b|\bmixed[- ]?precision\b|\bbinari(?:zed)?\b|\bternari(?:zed)?\b|\bposit arithmetic\b)',
    'Pruning':                r'(?:\bprun(?:e|ed|ing)\b|\bsparsif\w+\b|\bchannel[- ]?prun\w+\b|\bfilter[- ]?prun\w+\b|\bmagnitude[- ]?prun\w+\b|\bunstructured prun\w+\b|\blottery ticket\b)',
    'Knowledge distillation': r'(?:\bknowledge ?distillat\w+\b|\b(?:teacher|student)[- ]?(?:network|model)\b|\bKD\b(?!\s*=)|\bsoft[- ]?label\w*\b|\bdistill\w+\b)',
    'NAS':                    r'(?:\bneural ?architecture ?search\b|\bNAS\b|\bhardware[- ]?aware (?:search|NAS)\b|\bMCUNet\b|\bMicroNets\b|\bOnce[- ]?for[- ]?All\b|\bOFA\b|\bAutoML\b)',
}

DATASETS = r'(?:MIT[- ]?BIH|PhysioNet|PTB[- ]?XL|CHB[- ]?MIT|BCI ?Competition|CinC[- ]?\d+|WESAD|DEAP|SEED(?:[- ]?IV)?|DREAMER|UCI ?HAR|MHEALTH|SWELL|TUH[- ]?EEG|Sleep[- ]?EDF|Apnea[- ]?ECG|ESC[- ]?50)'

# Numeric regexes written differently from round 1
RE_RAM   = re.compile(r'(?:SRAM|RAM|memory\b)[^.]{0,40}?(\d+(?:\.\d+)?)\s?(KB|MB|kB|Kb|Mb)|\b(\d+(?:\.\d+)?)\s?(KB|MB)\s?(?:of\s+)?(?:SRAM|RAM)', re.I)
RE_FLASH = re.compile(r'\b(\d+(?:\.\d+)?)\s?(KB|MB|kB|Mb)\s?(?:of\s+)?(?:flash|program[- ]?memory)|(?:flash|program[- ]?memory)[^.]{0,40}?(\d+(?:\.\d+)?)\s?(KB|MB)', re.I)
RE_POW   = re.compile(r'\b(\d+(?:\.\d+)?)\s?(nW|uW|µW|μW|mW|W)\b(?!\s*/)')
RE_LAT   = re.compile(r'\b(\d+(?:\.\d+)?)\s?(?:ms|µs|μs|us|s)\b\s*(?:per\s+(?:inference|sample|window|beat)|latenc|inference[- ]?time)|latenc\w*[^.]{0,30}?(\d+(?:\.\d+)?)\s?(ms|s)', re.I)
RE_ACC   = re.compile(r'\b(accuracy|F1[- ]?score|F1|sensitivity|specificity|AUC|ROC[- ]?AUC)\s*(?:of|=|:|was|reached|achiev\w+)?\s*(?:of\s+)?(\d{1,3}(?:\.\d+)?)\s?%', re.I)


def first_match(text, patterns_dict):
    """Return tags whose regex matches, with DISTINCT-COUNT weighting."""
    hits = []
    for tag, pat in patterns_dict.items():
        matches = re.findall(pat, text, re.I)
        if matches:
            hits.append((tag, len(matches)))
    # Sort by match count desc; require at least 1 match
    hits.sort(key=lambda x: -x[1])
    return [t for t, _ in hits]


def detect_mcu(text):
    found = []
    for label, pat in MCU_RULES:
        if re.search(pat, text, re.I):
            if label not in found:
                found.append(label)
    return found


def detect_tier(text, mcus):
    """Tier heuristic (MCU-family FIRST, then keyword override)."""
    # MCU family mapping
    t1_mcus = {'Cortex-M0+', 'Ambiq Apollo', 'Kendryte K210'}
    t3_mcus = {'NVIDIA Jetson', 'Raspberry Pi', 'Cortex-A'}
    t2_mcus = {'Cortex-M4', 'Cortex-M7', 'Cortex-M33/M55', 'STM32',
               'Nordic nRF52/53', 'ESP32', 'Arduino Nano 33 BLE',
               'MAX78000', 'SAMD21/SAMD51', 'GAP8/9', 'PULP/RI5CY',
               'Syntiant NDP', 'Raspberry Pi Pico'}
    if any(m in t3_mcus for m in mcus):
        base = 'T3 Clinical instrument'
    elif any(m in t1_mcus for m in mcus):
        base = 'T1 Implantable'
    elif any(m in t2_mcus for m in mcus):
        base = 'T2 Wearable'
    else:
        base = 'T2 Wearable'  # default

    # Keyword override (implantable / point-of-care words)
    if re.search(r'\b(?:implant|subcutan|intracranial|pacemaker|neurostimulat|insulin ?pump|capsule ?endoscop)\w*', text, re.I):
        return 'T1 Implantable'
    if re.search(r'\b(?:point[- ]?of[- ]?care|bedside|hospital[- ]?grade|12[- ]?lead|multi[- ]?lead)\b', text, re.I):
        return 'T3 Clinical instrument'
    return base


def extract_num(regex, text):
    m = regex.search(text)
    if not m:
        return ''
    groups = [g for g in m.groups() if g]
    return ' '.join(groups[:2]) if groups else m.group(0)


def extract_alt(fn, text):
    rec = by_fn.get(fn, {})
    t = text[:20000]  # larger window than round 1

    domains = first_match(t, DOMAINS)
    tasks = first_match(t, TASKS)
    compression = first_match(t, COMPRESSION)
    mcus = detect_mcu(t)
    tier = detect_tier(t, mcus)
    datasets = sorted(set(m.upper() for m in re.findall(DATASETS, t, re.I)))

    return {
        'Year': rec.get('year', ''),
        'Title': rec.get('title', ''),
        'DOI': rec.get('doi', ''),
        'Filename': fn,
        'Clinical Domain': ', '.join(domains),
        'Task': ', '.join(tasks),
        'Device Tier': tier,
        'MCU/SoC': ', '.join(mcus[:3]),
        'RAM': extract_num(RE_RAM, t),
        'Flash': extract_num(RE_FLASH, t),
        'Active Power': extract_num(RE_POW, t),
        'Dataset': ', '.join(datasets),
        'Compression Techniques': ', '.join(compression),
        'Accuracy (reported)': (lambda m: f"{m.group(1)} {m.group(2)}%" if m else '')(RE_ACC.search(t)),
        'Latency/Inference': extract_num(RE_LAT, t),
    }


rows = []
for fn in by_fn:
    tp = os.path.join('_txt_alt', fn.replace('.pdf', '.txt'))
    text = open(tp, errors='ignore').read() if os.path.exists(tp) else ''
    rows.append(extract_alt(fn, text))

json.dump(rows, open('_extracted_alt.json', 'w'), indent=1)
print(f"Alt extraction complete: {len(rows)} rows")
